import asyncio
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect
from sqlalchemy import select

from app.config import Settings
from app.database import create_postgres_database
from app.dependencies import get_oidc_provider
from app.integrations.oidc import OidcClaims
from app.main import create_app
from app.models import ApiClient, ApiKey, ExternalIdentity, RefreshToken, UserRole
from app.security.cookies import REFRESH_COOKIE_NAME
from app.security.csrf import CSRF_HEADER_NAME, CSRF_HEADER_VALUE


PROJECT = Path(__file__).resolve().parents[1]
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("LIBRARY_TEST_POSTGRES") != "1",
        reason="defina LIBRARY_TEST_POSTGRES=1 para usar PostgreSQL real",
    ),
]


def alembic_config() -> Config:
    config = Config(PROJECT / "alembic.ini")
    config.set_main_option("script_location", str(PROJECT / "alembic"))
    return config


async def table_names(settings: Settings) -> set[str]:
    database = create_postgres_database(settings)
    try:
        async with database.engine.connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: set(inspect(sync_connection).get_table_names())
            )
    finally:
        await database.engine.dispose()


async def exercise_http_contract(settings: Settings) -> None:
    token = uuid4()
    isbn = str(token.int % 10**13).zfill(13)
    author = f"Integration {token.hex[:8]}"
    application = create_app(settings)

    class IntegrationOidcProvider:
        async def authorization_url(
            self, *, state: str, nonce: str, code_challenge: str
        ) -> str:
            return f"https://idp.example/authorize?{urlencode({'state': state, 'nonce': nonce, 'code_challenge': code_challenge})}"

        async def exchange_code(
            self,
            *,
            code: str,
            code_verifier: str,
            expected_nonce_digest: str,
        ) -> OidcClaims:
            assert code == "integration-code"
            assert code_verifier
            assert len(expected_nonce_digest) == 64
            return OidcClaims(
                issuer="https://idp.example",
                subject=f"external-{token.hex}",
                email=f"external-{token.hex}@example.com",
                email_verified=True,
                name="External Integration User",
            )

    async def override_oidc_provider() -> IntegrationOidcProvider:
        return IntegrationOidcProvider()

    application.dependency_overrides[get_oidc_provider] = override_oidc_provider

    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            created_user = await client.post(
                "/auth/register",
                json={
                    "name": "Integration User",
                    "email": f"{token.hex}@example.com",
                    "password": "integration password 2026",
                },
            )
            user_id = created_user.json()["id"]
            async with application.state.database.sessions() as session:
                session.add(
                    UserRole(user_id=user_id, role_name="librarian")
                )
                await session.commit()
            valid_login = await client.post(
                "/auth/login",
                json={
                    "email": f"{token.hex}@example.com",
                    "password": "integration password 2026",
                },
            )
            authorization = {
                "Authorization": (
                    f"Bearer {valid_login.json()['access_token']}"
                )
            }
            machine_client = await client.post(
                "/api-clients",
                json={"name": f"catalog-{token.hex}"},
                headers=authorization,
            )
            machine_client_id = machine_client.json()["id"]
            machine_client_uuid = UUID(machine_client_id)
            issued_key = await client.post(
                f"/api-clients/{machine_client_id}/keys",
                json={"scopes": ["books:read"]},
                headers=authorization,
            )
            raw_api_key = issued_key.json()["api_key"]
            created = await client.post(
                "/books",
                json={"title": "Integration Book", "author": author, "isbn": isbn},
                headers=authorization,
            )
            book_id = created.json()["id"]
            duplicate = await client.post(
                "/books",
                json={"title": "Duplicate", "author": author, "isbn": isbn},
                headers=authorization,
            )
            detail = await client.get(f"/books/{book_id}")
            page = await client.get("/books", params={"author": author})
            machine_export = await client.get(
                "/integrations/books", headers={"X-API-Key": raw_api_key}
            )
            rotated_key = await client.post(
                f"/api-keys/{issued_key.json()['id']}/rotate",
                json={},
                headers=authorization,
            )
            replacement_api_key = rotated_key.json()["api_key"]
            old_key_after_rotation = await client.get(
                "/integrations/books", headers={"X-API-Key": raw_api_key}
            )
            replacement_export = await client.get(
                "/integrations/books",
                headers={"X-API-Key": replacement_api_key},
            )
            revoked_key = await client.delete(
                f"/api-keys/{rotated_key.json()['id']}",
                headers=authorization,
            )
            replacement_after_revocation = await client.get(
                "/integrations/books",
                headers={"X-API-Key": replacement_api_key},
            )
            replaced = await client.put(
                f"/books/{book_id}",
                json={"title": "Integration Book 2", "author": author, "isbn": isbn},
                headers=authorization,
            )
            invalid_login = await client.post(
                "/auth/login",
                json={
                    "email": f"{token.hex}@example.com",
                    "password": "incorrect password",
                },
            )
            oidc_start = await client.get("/auth/oidc/login")
            oidc_state = parse_qs(
                urlsplit(oidc_start.headers["location"]).query
            )["state"][0]
            oidc_callback = await client.get(
                "/auth/oidc/callback",
                params={"code": "integration-code", "state": oidc_state},
            )
            initial_refresh_token = valid_login.cookies[REFRESH_COOKIE_NAME]

            async def rotate_once():
                async with AsyncClient(
                    transport=ASGITransport(app=application),
                    base_url="http://test",
                ) as refresh_client:
                    return await refresh_client.post(
                        "/auth/refresh",
                        headers={
                            CSRF_HEADER_NAME: CSRF_HEADER_VALUE,
                            "Cookie": (
                                f"{REFRESH_COOKIE_NAME}="
                                f"{initial_refresh_token}"
                            ),
                        },
                    )

            concurrent_refreshes = await asyncio.gather(
                rotate_once(), rotate_once()
            )
            rotated = next(
                response
                for response in concurrent_refreshes
                if response.status_code == 200
            )
            replayed = next(
                response
                for response in concurrent_refreshes
                if response.status_code == 401
            )
            replacement_refresh_token = rotated.cookies[REFRESH_COOKIE_NAME]
            replacement_after_reuse = await client.post(
                "/auth/refresh",
                headers={
                    CSRF_HEADER_NAME: CSRF_HEADER_VALUE,
                    "Cookie": (
                        f"{REFRESH_COOKIE_NAME}={replacement_refresh_token}"
                    ),
                },
            )
            authorization = {
                "Authorization": (
                    f"Bearer {rotated.json()['access_token']}"
                )
            }
            user_detail = await client.get(
                f"/users/{user_id}", headers=authorization
            )
            due_at = (datetime.now(UTC) + timedelta(days=14)).isoformat()
            concurrent_loans = await asyncio.gather(
                client.post(
                    "/loans",
                    json={"book_id": book_id, "due_at": due_at},
                    headers=authorization,
                ),
                client.post(
                    "/loans",
                    json={"book_id": book_id, "due_at": due_at},
                    headers=authorization,
                ),
            )
            accepted = next(
                response for response in concurrent_loans if response.status_code == 201
            )
            rejected = next(
                response for response in concurrent_loans if response.status_code == 409
            )
            unavailable = await client.get(f"/books/{book_id}")
            loans = await client.get("/loans", headers=authorization)
            returned = await client.post(
                f"/loans/{accepted.json()['id']}/return",
                headers=authorization,
            )
            duplicate_return = await client.post(
                f"/loans/{accepted.json()['id']}/return",
                headers=authorization,
            )
            available_again = await client.get(f"/books/{book_id}")
            protected = await client.delete(
                f"/books/{book_id}", headers=authorization
            )

            disposable = await client.post(
                "/books",
                json={
                    "title": "Disposable",
                    "author": author,
                    "isbn": str((token.int + 1) % 10**13).zfill(13),
                },
                headers=authorization,
            )
            deleted = await client.delete(
                f"/books/{disposable.json()['id']}", headers=authorization
            )
            missing = await client.get(f"/books/{disposable.json()['id']}")

            logout_login = await client.post(
                "/auth/login",
                json={
                    "email": f"{token.hex}@example.com",
                    "password": "integration password 2026",
                },
            )
            logout_refresh_token = logout_login.cookies[REFRESH_COOKIE_NAME]
            logged_out = await client.post(
                "/auth/logout",
                headers={CSRF_HEADER_NAME: CSRF_HEADER_VALUE},
            )
            refresh_after_logout = await client.post(
                "/auth/refresh",
                headers={
                    CSRF_HEADER_NAME: CSRF_HEADER_VALUE,
                    "Cookie": (
                        f"{REFRESH_COOKIE_NAME}={logout_refresh_token}"
                    ),
                },
            )

            async with application.state.database.sessions() as session:
                digests = list(
                    (
                        await session.scalars(
                            select(RefreshToken.token_digest)
                        )
                    ).all()
                )
                external_identity = await session.scalar(
                    select(ExternalIdentity).where(
                        ExternalIdentity.issuer == "https://idp.example",
                        ExternalIdentity.subject == f"external-{token.hex}",
                    )
                )
                stored_api_keys = list(
                    (
                        await session.scalars(
                            select(ApiKey).where(
                                ApiKey.client_id == machine_client_uuid
                            )
                        )
                    ).all()
                )
                stored_api_client = await session.get(
                    ApiClient, machine_client_uuid
                )

    assert created.status_code == 201
    assert created.json()["available"] is True
    assert duplicate.status_code == 409
    assert detail.json()["id"] == book_id
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["id"] == book_id
    assert replaced.json()["title"] == "Integration Book 2"
    assert machine_client.status_code == 201
    assert issued_key.status_code == 201
    assert machine_export.status_code == 200
    assert machine_export.json()[0]["id"] == book_id
    assert rotated_key.status_code == 201
    assert old_key_after_rotation.status_code == 401
    assert replacement_export.status_code == 200
    assert revoked_key.status_code == 204
    assert replacement_after_revocation.status_code == 401
    assert stored_api_client is not None
    assert len(stored_api_keys) == 2
    assert all(len(key.secret_digest) == 64 for key in stored_api_keys)
    assert raw_api_key not in {key.secret_digest for key in stored_api_keys}
    assert replacement_api_key not in {
        key.secret_digest for key in stored_api_keys
    }
    assert all(key.revoked_at is not None for key in stored_api_keys)
    assert created_user.status_code == 201
    assert valid_login.status_code == 200
    assert valid_login.json()["token_type"] == "bearer"
    assert valid_login.json()["expires_in"] == 900
    assert "refresh_token" not in valid_login.json()
    assert "HttpOnly" in valid_login.headers["set-cookie"]
    assert "SameSite=strict" in valid_login.headers["set-cookie"]
    assert invalid_login.status_code == 401
    assert oidc_start.status_code == 307
    assert oidc_callback.status_code == 200
    assert external_identity is not None
    assert rotated.status_code == 200
    assert rotated.json()["expires_in"] == 900
    assert replayed.json() == {"detail": "Sessão renovável inválida"}
    assert replacement_after_reuse.status_code == 401
    assert user_detail.json()["email"] == f"{token.hex}@example.com"
    assert user_detail.json()["loans"] == []
    assert accepted.json()["book_id"] == book_id
    assert rejected.json() == {"detail": "Livro indisponível para empréstimo"}
    assert unavailable.json()["available"] is False
    assert len(loans.json()) == 1
    assert loans.json()[0]["user"]["id"] == user_id
    assert loans.json()[0]["book"]["title"] == "Integration Book 2"
    assert returned.json()["returned_at"] is not None
    assert duplicate_return.status_code == 409
    assert available_again.json()["available"] is True
    assert protected.status_code == 409
    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert logout_login.status_code == 200
    assert logged_out.status_code == 204
    assert "Max-Age=0" in logged_out.headers["set-cookie"]
    assert refresh_after_logout.status_code == 401
    assert digests
    assert all(len(digest) == 64 for digest in digests)
    assert initial_refresh_token not in digests
    assert replacement_refresh_token not in digests
    assert logout_refresh_token not in digests


def test_migration_round_trip_and_book_crud_against_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = os.getenv("LIBRARY_TEST_DATABASE_HOST", "localhost")
    port = os.getenv("LIBRARY_TEST_DATABASE_PORT", "5432")
    monkeypatch.setenv("LIBRARY_ENVIRONMENT", "test")
    monkeypatch.setenv("LIBRARY_DATABASE_HOST", host)
    monkeypatch.setenv("LIBRARY_DATABASE_PORT", port)
    monkeypatch.setenv("LIBRARY_OIDC_ISSUER", "https://idp.example")
    monkeypatch.setenv("LIBRARY_OIDC_CLIENT_ID", "library-web")
    monkeypatch.setenv("LIBRARY_OIDC_CLIENT_SECRET", "external-client-secret")
    monkeypatch.setenv(
        "LIBRARY_OIDC_REDIRECT_URI", "http://test/auth/oidc/callback"
    )
    settings = Settings(_env_file=None)
    config = alembic_config()

    try:
        command.upgrade(config, "head")
        command.check(config)
        assert {
            "users",
            "books",
            "loans",
            "refresh_tokens",
            "roles",
            "user_roles",
            "external_identities",
            "oidc_login_attempts",
            "api_clients",
            "api_keys",
            "alembic_version",
        } <= asyncio.run(table_names(settings))

        command.downgrade(config, "base")
        assert {
            "users",
            "books",
            "loans",
            "refresh_tokens",
            "roles",
            "user_roles",
            "external_identities",
            "oidc_login_attempts",
            "api_clients",
            "api_keys",
        }.isdisjoint(asyncio.run(table_names(settings)))

        command.upgrade(config, "head")
        asyncio.run(exercise_http_contract(settings))
    finally:
        command.downgrade(config, "base")
