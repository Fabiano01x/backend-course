from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models import RefreshToken, User
from app.security.cookies import REFRESH_COOKIE_NAME
from app.security.csrf import CSRF_HEADER_NAME, CSRF_HEADER_VALUE
from app.security.refresh import digest_refresh_token
from tests.support import RecordingSession, Result


pytestmark = pytest.mark.anyio
CSRF_HEADERS = {CSRF_HEADER_NAME: CSRF_HEADER_VALUE}


def user(active: bool = True) -> User:
    return User(
        id=1,
        name="Ada Lovelace",
        email="ada@example.com",
        active=active,
    )


def refresh_record(
    raw_token: str, *, used: bool = False
) -> RefreshToken:
    now = datetime.now(UTC)
    return RefreshToken(
        id=uuid4(),
        family_id=uuid4(),
        user_id=1,
        token_digest=digest_refresh_token(raw_token),
        created_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=6),
        used_at=now - timedelta(minutes=1) if used else None,
    )


def cookie_header(raw_token: str) -> dict[str, str]:
    return {"Cookie": f"{REFRESH_COOKIE_NAME}={raw_token}"}


async def test_refresh_rotates_cookie_and_returns_only_new_access_token(
    client: AsyncClient, session: RecordingSession
) -> None:
    raw_token = "rt_current"
    current = refresh_record(raw_token)
    session.execute_results.extend(
        [Result(scalars=[current]), Result(scalars=[user()])]
    )

    response = await client.post(
        "/auth/refresh",
        headers={**CSRF_HEADERS, **cookie_header(raw_token)},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert "refresh_token" not in response.json()
    replacement_value = response.cookies[REFRESH_COOKIE_NAME]
    replacement = session.added[0]
    assert isinstance(replacement, RefreshToken)
    assert replacement.token_digest == digest_refresh_token(replacement_value)
    assert current.used_at is not None
    assert current.replaced_by_id == replacement.id
    assert "HttpOnly" in response.headers["set-cookie"]


async def test_reused_cookie_revokes_family_and_is_cleared(
    client: AsyncClient, session: RecordingSession
) -> None:
    raw_token = "rt_reused"
    session.execute_results.append(
        Result(scalars=[refresh_record(raw_token, used=True)])
    )

    response = await client.post(
        "/auth/refresh",
        headers={**CSRF_HEADERS, **cookie_header(raw_token)},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Sessão renovável inválida"}
    assert response.headers["www-authenticate"] == "Bearer"
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert "UPDATE refresh_tokens" in str(session.statements[1])
    assert session.transaction_commit_count == 1


async def test_missing_cookie_is_generic_and_cleared_without_database_io(
    client: AsyncClient, session: RecordingSession
) -> None:
    response = await client.post("/auth/refresh", headers=CSRF_HEADERS)

    assert response.status_code == 401
    assert response.json() == {"detail": "Sessão renovável inválida"}
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert session.statements == []


@pytest.mark.parametrize(
    "headers",
    [
        cookie_header("rt_value"),
        {**cookie_header("rt_value"), CSRF_HEADER_NAME: "wrong"},
        {
            **cookie_header("rt_value"),
            **CSRF_HEADERS,
            "Origin": "https://evil.example",
        },
    ],
)
async def test_csrf_guard_rejects_missing_header_or_untrusted_origin(
    client: AsyncClient,
    session: RecordingSession,
    headers: dict[str, str],
) -> None:
    response = await client.post("/auth/refresh", headers=headers)

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Requisição de navegador não autorizada"
    }
    assert session.statements == []


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://test"])
async def test_csrf_guard_accepts_frontend_or_api_origin(
    client: AsyncClient, session: RecordingSession, origin: str
) -> None:
    session.execute_results.append(Result())
    response = await client.post(
        "/auth/refresh",
        headers={
            **CSRF_HEADERS,
            **cookie_header("rt_unknown"),
            "Origin": origin,
        },
    )

    assert response.status_code == 401
    assert len(session.statements) == 1


async def test_logout_revokes_family_and_expires_cookie(
    client: AsyncClient, session: RecordingSession
) -> None:
    raw_token = "rt_logout"
    session.execute_results.append(
        Result(scalars=[refresh_record(raw_token)])
    )

    response = await client.post(
        "/auth/logout",
        headers={**CSRF_HEADERS, **cookie_header(raw_token)},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert "UPDATE refresh_tokens" in str(session.statements[1])
