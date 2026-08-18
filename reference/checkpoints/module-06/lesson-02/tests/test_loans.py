from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.dependencies import load_settings
from app.models import Book, Loan, User
from app.security.tokens import create_access_token
from tests.support import RecordingSession, Result


pytestmark = pytest.mark.anyio


def user(user_id: int, *, active: bool = True) -> User:
    return User(
        id=user_id,
        name="Ada Lovelace",
        email="ada@example.com",
        active=active,
    )


def book(book_id: int) -> Book:
    return Book(
        id=book_id,
        title="Kindred",
        author="Octavia E. Butler",
        isbn="9780807083697",
    )


def loan(
    loan_id: int,
    *,
    returned_at: datetime | None = None,
) -> Loan:
    now = datetime.now(UTC)
    return Loan(
        id=loan_id,
        user_id=1,
        book_id=2,
        user=user(1),
        book=book(2),
        borrowed_at=now,
        due_at=now + timedelta(days=14),
        returned_at=returned_at,
    )


def payload() -> dict[str, object]:
    return {
        "book_id": 2,
        "due_at": (datetime.now(UTC) + timedelta(days=14)).isoformat(),
    }


def authorization(
    user_id: int = 1, *, now: datetime | None = None
) -> dict[str, str]:
    token = create_access_token(
        user_id=user_id, settings=load_settings(), now=now
    )
    return {"Authorization": f"Bearer {token}"}


async def test_borrows_book_inside_one_transaction(
    client: AsyncClient, session: RecordingSession
) -> None:
    session.execute_results.extend(
        [
            Result(scalars=[user(1)]),
            Result(scalars=[book(2)]),
            Result(),
        ]
    )

    response = await client.post(
        "/loans", json=payload(), headers=authorization()
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == 1
    assert response.json()["book_id"] == 2
    assert response.json()["returned_at"] is None
    assert len(session.added) == 1
    assert isinstance(session.added[0], Loan)
    assert session.begin_count == 1
    assert session.flush_count == 1
    assert session.transaction_commit_count == 1
    assert session.transaction_rollback_count == 0
    assert session.commit_count == 0
    assert "FOR UPDATE" in str(session.statements[1])


@pytest.mark.parametrize(
    ("results", "detail", "status_code"),
    [
        ([Result()], "Credencial de acesso inválida", 401),
        (
            [Result(scalars=[user(1, active=False)])],
            "Credencial de acesso inválida",
            401,
        ),
        (
            [Result(scalars=[user(1)]), Result()],
            "Livro não encontrado",
            404,
        ),
        (
            [
                Result(scalars=[user(1)]),
                Result(scalars=[book(2)]),
                Result(scalars=[loan(9)]),
            ],
            "Livro indisponível para empréstimo",
            409,
        ),
    ],
)
async def test_rejects_rule_before_writing_and_rolls_back(
    client: AsyncClient,
    session: RecordingSession,
    results: list[Result],
    detail: str,
    status_code: int,
) -> None:
    session.execute_results.extend(results)

    response = await client.post(
        "/loans", json=payload(), headers=authorization()
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    if status_code == 401:
        assert response.headers["www-authenticate"] == "Bearer"
    assert session.added == []
    assert session.flush_count == 0
    assert session.transaction_commit_count == 0
    assert session.transaction_rollback_count == 1


async def test_unique_constraint_is_the_concurrency_safety_net(
    client: AsyncClient, session: RecordingSession
) -> None:
    session.execute_results.extend(
        [
            Result(scalars=[user(1)]),
            Result(scalars=[book(2)]),
            Result(),
        ]
    )
    session.flush_errors.append(
        IntegrityError("INSERT INTO loans", {}, Exception("unique index"))
    )

    response = await client.post(
        "/loans", json=payload(), headers=authorization()
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Livro indisponível para empréstimo"}
    assert session.flush_count == 1
    assert session.transaction_rollback_count == 1
    assert session.transaction_commit_count == 0


async def test_lists_and_returns_a_loan(
    client: AsyncClient, session: RecordingSession
) -> None:
    active = loan(1)
    session.execute_results.extend(
        [Result(scalars=[active]), Result(scalars=[active])]
    )

    listed = await client.get("/loans")
    returned = await client.post("/loans/1/return")

    assert listed.status_code == 200
    assert listed.json()[0]["returned_at"] is None
    assert listed.json()[0]["user"] == {"id": 1, "name": "Ada Lovelace"}
    assert listed.json()[0]["book"] == {
        "id": 2,
        "title": "Kindred",
        "author": "Octavia E. Butler",
    }
    assert returned.status_code == 200
    assert returned.json()["returned_at"] is not None
    assert session.begin_count == 1
    assert session.flush_count == 1
    assert session.transaction_commit_count == 1
    assert "FOR UPDATE" in str(session.statements[1])
    listed_sql = str(session.statements[0]).lower()
    assert listed_sql.count("left outer join") == 2


@pytest.mark.parametrize(
    ("existing", "detail", "status_code"),
    [
        (None, "Empréstimo não encontrado", 404),
        (loan(1, returned_at=datetime.now(UTC)), "Empréstimo já devolvido", 409),
    ],
)
async def test_rejects_invalid_return_and_rolls_back(
    client: AsyncClient,
    session: RecordingSession,
    existing: Loan | None,
    detail: str,
    status_code: int,
) -> None:
    session.execute_results.append(
        Result(scalars=[] if existing is None else [existing])
    )

    response = await client.post("/loans/1/return")

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert session.flush_count == 0
    assert session.transaction_rollback_count == 1


@pytest.mark.parametrize(
    "due_at",
    [
        datetime.now().replace(microsecond=0).isoformat(),
        (datetime.now(UTC) - timedelta(days=1)).isoformat(),
    ],
)
async def test_rejects_naive_or_past_due_date(
    client: AsyncClient, due_at: str
) -> None:
    invalid = {**payload(), "due_at": due_at}

    response = await client.post(
        "/loans", json=invalid, headers=authorization()
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic credentials"},
        {"Authorization": "Bearer not-a-jwt"},
    ],
)
async def test_rejects_missing_or_malformed_access_token(
    client: AsyncClient,
    session: RecordingSession,
    headers: dict[str, str],
) -> None:
    response = await client.post("/loans", json=payload(), headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Credencial de acesso inválida"}
    assert response.headers["www-authenticate"] == "Bearer"
    assert session.statements == []


async def test_rejects_expired_access_token(
    client: AsyncClient, session: RecordingSession
) -> None:
    expired_at = datetime.now(UTC) - timedelta(minutes=16)
    response = await client.post(
        "/loans",
        json=payload(),
        headers=authorization(now=expired_at),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Credencial de acesso inválida"}
    assert session.statements == []


async def test_loan_uses_token_subject_and_rejects_client_user_id(
    client: AsyncClient, session: RecordingSession
) -> None:
    injected = await client.post(
        "/loans",
        json={**payload(), "user_id": 999},
        headers=authorization(user_id=7),
    )
    assert injected.status_code == 422
    assert session.statements == []

    session.execute_results.extend(
        [Result(scalars=[user(7)]), Result(scalars=[book(2)]), Result()]
    )
    accepted = await client.post(
        "/loans", json=payload(), headers=authorization(user_id=7)
    )

    assert accepted.status_code == 201
    assert accepted.json()["user_id"] == 7
    assert session.added[0].user_id == 7
