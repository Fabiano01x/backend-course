from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.dependencies import get_current_api_client
from app.main import app
from app.models import ApiClient, ApiKey, Book
from app.security.api_keys import (
    api_key_prefix,
    digest_api_key,
    generate_api_key,
    matches_api_key,
)
from app.services.api_keys import (
    ApiClientPrincipal,
    ApiKeyRuleError,
    authenticate_api_key,
    create_api_client,
    issue_api_key,
    revoke_api_key,
    rotate_api_key,
)
from tests.support import RecordingSession, Result


pytestmark = pytest.mark.anyio


def machine_client(*, active: bool = True) -> ApiClient:
    return ApiClient(id=uuid4(), name="relatorios", active=active)


def stored_key(
    raw: str,
    client: ApiClient,
    *,
    scopes: list[str] | None = None,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> ApiKey:
    return ApiKey(
        id=uuid4(),
        client_id=client.id,
        client=client,
        prefix=api_key_prefix(raw),
        secret_digest=digest_api_key(raw),
        scopes=scopes or ["loans:read"],
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


def test_generated_key_has_scannable_prefix_and_only_digest_is_stored() -> None:
    generated = generate_api_key()

    assert generated.raw.startswith(f"lka_{generated.prefix}_")
    assert len(generated.prefix) == 12
    assert api_key_prefix(generated.raw) == generated.prefix
    assert generated.raw not in generated.digest
    assert generated.digest == digest_api_key(generated.raw)
    assert matches_api_key(generated.raw, generated.digest)
    assert not matches_api_key(generated.raw + "x", generated.digest)


@pytest.mark.parametrize(
    "raw",
    ["", "lka_short_secret", "lka_zzzzzzzzzzzz_" + "a" * 43, "ç"],
)
def test_malformed_key_has_no_lookup_prefix(raw: str) -> None:
    assert api_key_prefix(raw) is None


async def test_service_rejects_naive_expiration_even_without_http_schema() -> None:
    session = RecordingSession()

    with pytest.raises(ApiKeyRuleError, match="fuso horário") as captured:
        await issue_api_key(
            session,
            client_id=uuid4(),
            scopes={"books:read"},
            expires_at=datetime.now(),
        )

    assert captured.value.conflict
    assert not session.statements


async def test_issuing_key_persists_digest_but_returns_secret_once() -> None:
    session = RecordingSession()
    client = machine_client()
    session.execute_results.append(Result(scalars=[client]))

    issued = await issue_api_key(
        session,
        client_id=client.id,
        scopes={"books:read", "loans:read"},
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    assert issued.raw.startswith(f"lka_{issued.key.prefix}_")
    assert issued.key.secret_digest == digest_api_key(issued.raw)
    assert issued.key.scopes == ["books:read", "loans:read"]
    assert not hasattr(issued.key, "raw")
    assert session.commit_count == 1


async def test_concurrent_client_name_conflict_becomes_domain_conflict() -> None:
    session = RecordingSession()
    session.flush_errors.append(IntegrityError("insert", {}, Exception()))

    with pytest.raises(ApiKeyRuleError, match="já cadastrado") as captured:
        await create_api_client(session, "relatorios")

    assert captured.value.conflict
    assert session.rollback_count == 1


async def test_authentication_updates_audit_and_returns_machine_identity() -> None:
    session = RecordingSession()
    raw = generate_api_key().raw
    client = machine_client()
    key = stored_key(raw, client, scopes=["books:read"])
    session.execute_results.append(Result(scalars=[key]))
    checked_at = datetime.now(UTC)

    principal = await authenticate_api_key(session, raw, now=checked_at)

    assert principal == ApiClientPrincipal(
        client_id=client.id,
        key_id=key.id,
        name="relatorios",
        scopes=frozenset({"books:read"}),
    )
    assert key.last_used_at == checked_at
    assert session.transaction_commit_count == 1


@pytest.mark.parametrize("reason", ["wrong", "expired", "revoked", "inactive"])
async def test_invalid_lifecycle_state_never_authenticates(reason: str) -> None:
    session = RecordingSession()
    generated = generate_api_key()
    client = machine_client(active=reason != "inactive")
    now = datetime.now(UTC)
    key = stored_key(
        generated.raw,
        client,
        expires_at=now - timedelta(seconds=1) if reason == "expired" else None,
        revoked_at=now if reason == "revoked" else None,
    )
    session.execute_results.append(Result(scalars=[key]))
    presented = (
        f"lka_{generated.prefix}_{'a' * 43}"
        if reason == "wrong"
        else generated.raw
    )

    assert await authenticate_api_key(session, presented, now=now) is None
    assert key.last_used_at is None


async def test_rotation_creates_replacement_and_revokes_previous_atomically() -> None:
    session = RecordingSession()
    old_raw = generate_api_key().raw
    client = machine_client()
    previous = stored_key(old_raw, client, scopes=["loans:read"])
    session.execute_results.append(Result(scalars=[previous]))

    replacement = await rotate_api_key(
        session, key_id=previous.id, expires_at=None
    )

    assert replacement.raw != old_raw
    assert replacement.key.client_id == client.id
    assert replacement.key.scopes == ["loans:read"]
    assert previous.revoked_at is not None
    assert previous.replaced_by_id == replacement.key.id
    assert session.commit_count == 1


async def test_revocation_is_idempotent_but_missing_key_is_not() -> None:
    session = RecordingSession()
    client = machine_client()
    key = stored_key(generate_api_key().raw, client)
    session.execute_results.append(Result(scalars=[key]))
    await revoke_api_key(session, key.id)
    first_revocation = key.revoked_at

    session.execute_results.append(Result(scalars=[key]))
    await revoke_api_key(session, key.id)
    assert key.revoked_at == first_revocation

    session.execute_results.append(Result())
    with pytest.raises(ApiKeyRuleError, match="não encontrada") as captured:
        await revoke_api_key(session, uuid4())
    assert captured.value.not_found


async def test_machine_route_distinguishes_invalid_key_and_missing_scope(
    client: AsyncClient,
) -> None:
    missing = await client.get("/integrations/books")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "ApiKey"

    async def loans_only() -> ApiClientPrincipal:
        return ApiClientPrincipal(
            client_id=uuid4(),
            key_id=uuid4(),
            name="relatorios",
            scopes=frozenset({"loans:read"}),
        )

    app.dependency_overrides[get_current_api_client] = loans_only
    forbidden = await client.get("/integrations/books")
    assert forbidden.status_code == 403
    assert forbidden.json() == {"detail": "Permissão insuficiente"}


async def test_scoped_machine_client_can_export_books(
    client: AsyncClient, session: RecordingSession
) -> None:
    async def books_reader() -> ApiClientPrincipal:
        return ApiClientPrincipal(
            client_id=uuid4(),
            key_id=uuid4(),
            name="catalogo",
            scopes=frozenset({"books:read"}),
        )

    app.dependency_overrides[get_current_api_client] = books_reader
    session.execute_results.append(
        Result(
            rows=[
                (
                    Book(
                        id=1,
                        title="Kindred",
                        author="Octavia E. Butler",
                        isbn="9780807083697",
                    ),
                    True,
                )
            ]
        )
    )

    response = await client.get("/integrations/books")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "title": "Kindred",
            "author": "Octavia E. Butler",
            "isbn": "9780807083697",
            "available": True,
        }
    ]


async def test_openapi_separates_human_and_machine_credentials(
    client: AsyncClient,
) -> None:
    schema = (await client.get("/openapi.json")).json()
    schemes = schema["components"]["securitySchemes"]

    assert schemes["MachineApiKey"] == {
        "type": "apiKey",
        "description": "Credencial opaca emitida para um cliente de máquina.",
        "in": "header",
        "name": "X-API-Key",
    }
    assert schema["paths"]["/integrations/books"]["get"]["security"] == [
        {"MachineApiKey": []}
    ]
    assert schema["paths"]["/api-clients"]["post"]["security"] == [
        {"AccessToken": []}
    ]
    issue_schema = schema["components"]["schemas"]["ApiKeyIssueResponse"]
    assert "api_key" in issue_schema["required"]
    assert "secret_digest" not in str(schema)
