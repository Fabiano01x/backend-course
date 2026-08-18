import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.models import User
from app.security.passwords import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.security.tokens import decode_access_token
from app.services import auth as auth_service
from tests.support import RecordingSession, Result


pytestmark = pytest.mark.anyio
VALID_PASSWORD = "correct horse battery staple"
VALID_HASH = hash_password(VALID_PASSWORD)


def user(
    *,
    password_hash: str | None = VALID_HASH,
    active: bool = True,
) -> User:
    return User(
        id=1,
        name="Ada Lovelace",
        email="ada@example.com",
        password_hash=password_hash,
        active=active,
    )


async def test_registers_normalized_email_and_persists_only_hash(
    client: AsyncClient, session: RecordingSession
) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "name": "Ada Lovelace",
            "email": "  ADA@EXAMPLE.COM ",
            "password": VALID_PASSWORD,
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "active": True,
    }
    stored = session.added[0]
    assert isinstance(stored, User)
    assert stored.password_hash != VALID_PASSWORD
    assert stored.password_hash is not None
    assert verify_password(VALID_PASSWORD, stored.password_hash)
    assert "password" not in response.text


async def test_duplicate_registration_rolls_back_with_generic_conflict(
    client: AsyncClient, session: RecordingSession
) -> None:
    session.commit_errors.append(
        IntegrityError("INSERT INTO users", {}, Exception("duplicate"))
    )

    response = await client.post(
        "/auth/register",
        json={
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "password": VALID_PASSWORD,
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Não foi possível cadastrar usuário"}
    assert "ada@example.com" not in response.text
    assert session.rollback_count == 1
    assert session.refresh_count == 0


async def test_valid_credentials_issue_a_short_access_token(
    client: AsyncClient, session: RecordingSession
) -> None:
    session.execute_results.append(Result(scalars=[user()]))

    response = await client.post(
        "/auth/login",
        json={"email": "ADA@example.com", "password": VALID_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert "refresh_token" not in body
    claims = decode_access_token(
        body["access_token"], Settings(_env_file=None)
    )
    assert claims.user_id == 1
    assert len(session.statements) == 1
    assert "users.email" in str(session.statements[0])


@pytest.mark.parametrize(
    ("existing", "password"),
    [
        (None, VALID_PASSWORD),
        (user(), "incorrect password"),
        (user(password_hash=None), VALID_PASSWORD),
        (user(active=False), VALID_PASSWORD),
    ],
)
async def test_all_invalid_credentials_share_one_response(
    client: AsyncClient,
    session: RecordingSession,
    existing: User | None,
    password: str,
) -> None:
    session.execute_results.append(
        Result(scalars=[] if existing is None else [existing])
    )

    response = await client.post(
        "/auth/login",
        json={"email": "ada@example.com", "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciais inválidas"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("existing", [None, user(password_hash=None)])
async def test_missing_credential_still_executes_dummy_hash_verification(
    client: AsyncClient,
    session: RecordingSession,
    monkeypatch: pytest.MonkeyPatch,
    existing: User | None,
) -> None:
    checked_hashes: list[str] = []

    def record_verification(_password: str, encoded_hash: str) -> bool:
        checked_hashes.append(encoded_hash)
        return False

    monkeypatch.setattr(auth_service, "verify_password", record_verification)
    session.execute_results.append(
        Result(scalars=[] if existing is None else [existing])
    )

    response = await client.post(
        "/auth/login",
        json={"email": "unknown@example.com", "password": VALID_PASSWORD},
    )

    assert response.status_code == 401
    assert checked_hashes == [DUMMY_PASSWORD_HASH]


@pytest.mark.parametrize(
    "password",
    ["short", "x" * 129],
)
async def test_registration_bounds_password_work(
    client: AsyncClient, password: str
) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "password": password,
        },
    )

    assert response.status_code == 422
