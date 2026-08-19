import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.dialects import postgresql

from app.dependencies import get_current_principal, load_settings
from app.main import app
from app.models import User
from app.repositories.authorization import build_principal_query
from app.security.tokens import (
    ACCESS_TOKEN_ALGORITHM,
    ACCESS_TOKEN_HEADER_TYPE,
    create_access_token,
)
from tests.support import RecordingSession, Result


pytestmark = pytest.mark.anyio
BOOK = {
    "title": "Kindred",
    "author": "Octavia E. Butler",
    "isbn": "9780807083697",
}


def user(user_id: int = 1, *, active: bool = True) -> User:
    return User(
        id=user_id,
        name="Ada Lovelace",
        email="ada@example.com",
        active=active,
    )


def authorization(user_id: int = 1, *, roles_claim: list[str] | None = None):
    settings = load_settings()
    if roles_claim is None:
        token = create_access_token(user_id=user_id, settings=settings)
    else:
        claims = jwt.decode(
            create_access_token(user_id=user_id, settings=settings),
            options={"verify_signature": False},
        )
        claims["roles"] = roles_claim
        token = jwt.encode(
            claims,
            settings.jwt_secret_key.get_secret_value(),
            algorithm=ACCESS_TOKEN_ALGORITHM,
            headers={"typ": ACCESS_TOKEN_HEADER_TYPE},
        )
    return {"Authorization": f"Bearer {token}"}


def use_real_authorization_dependency() -> None:
    app.dependency_overrides.pop(get_current_principal, None)


async def test_librarian_route_distinguishes_401_from_403(
    client: AsyncClient, session: RecordingSession
) -> None:
    use_real_authorization_dependency()

    missing = await client.post("/books", json=BOOK)
    assert missing.status_code == 401
    assert session.statements == []

    session.execute_results.append(Result(rows=[]))
    unknown = await client.post(
        "/books", json=BOOK, headers=authorization(user_id=99)
    )
    assert unknown.status_code == 401
    assert unknown.headers["www-authenticate"] == "Bearer"

    session.execute_results.append(
        Result(rows=[(user(active=False), "librarian")])
    )
    inactive = await client.post(
        "/books", json=BOOK, headers=authorization()
    )
    assert inactive.status_code == 401

    session.execute_results.append(Result(rows=[(user(), "member")]))
    forbidden = await client.post(
        "/books", json=BOOK, headers=authorization()
    )
    assert forbidden.status_code == 403
    assert forbidden.json() == {"detail": "Permissão insuficiente"}
    assert "www-authenticate" not in forbidden.headers


async def test_persisted_role_revocation_takes_effect_with_the_same_jwt(
    client: AsyncClient, session: RecordingSession
) -> None:
    use_real_authorization_dependency()
    headers = authorization(roles_claim=["librarian"])

    session.execute_results.append(Result(rows=[(user(), "librarian")]))
    allowed = await client.post("/books", json=BOOK, headers=headers)

    session.execute_results.append(Result(rows=[(user(), "member")]))
    revoked = await client.post(
        "/books",
        json={**BOOK, "isbn": "9780441172719"},
        headers=headers,
    )

    assert allowed.status_code == 201
    assert revoked.status_code == 403
    assert len(session.added) == 1
    assert session.commit_count == 1


async def test_user_detail_uses_ownership_separately_from_global_role(
    client: AsyncClient, session: RecordingSession
) -> None:
    use_real_authorization_dependency()
    ada = user()
    ada.loans = []

    session.execute_results.extend(
        [Result(rows=[(ada, "member")]), Result(scalars=[ada])]
    )
    own_profile = await client.get("/users/1", headers=authorization())

    session.execute_results.append(Result(rows=[(ada, "member")]))
    someone_else = await client.get("/users/2", headers=authorization())

    assert own_profile.status_code == 200
    assert own_profile.json()["email"] == "ada@example.com"
    assert someone_else.status_code == 403
    assert someone_else.json() == {"detail": "Permissão insuficiente"}


def test_principal_query_reads_current_assignments_from_the_database() -> None:
    sql = str(
        build_principal_query(7).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower()

    assert "from users" in sql
    assert "left outer join user_roles" in sql
    assert "left outer join roles" in sql
    assert "where users.id = 7" in sql
