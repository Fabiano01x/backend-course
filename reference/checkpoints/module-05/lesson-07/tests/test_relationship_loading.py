from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from app.models import Base, Book, Loan, User
from app.repositories.loans import build_loan_detail_query
from app.routers.users import build_user_detail_query


@pytest.fixture
def engine():
    database = create_engine("sqlite://")

    @event.listens_for(database, "connect")
    def add_postgresql_string_functions(connection, _record) -> None:
        connection.create_function("btrim", 1, lambda value: value.strip())
        connection.create_function("char_length", 1, len)

    Base.metadata.create_all(database)
    now = datetime.now(UTC)

    with Session(database) as session:
        users = [
            User(id=1, name="Ada Lovelace", email="ada@example.com"),
            User(id=2, name="Grace Hopper", email="grace@example.com"),
        ]
        books = [
            Book(
                id=1,
                title="Kindred",
                author="Octavia E. Butler",
                isbn="9780807083697",
            ),
            Book(
                id=2,
                title="The Left Hand of Darkness",
                author="Ursula K. Le Guin",
                isbn="9780441478125",
            ),
        ]
        loans = [
            Loan(
                id=1,
                user=users[0],
                book=books[0],
                borrowed_at=now,
                due_at=now + timedelta(days=14),
            ),
            Loan(
                id=2,
                user=users[0],
                book=books[1],
                borrowed_at=now,
                due_at=now + timedelta(days=14),
            ),
        ]
        session.add_all([*users, *books, *loans])
        session.commit()

    yield database
    database.dispose()


def statement_counter(engine):
    statements: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def record_statement(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    return statements


def test_joinedload_keeps_loan_list_at_one_query(engine) -> None:
    statements = statement_counter(engine)

    with Session(engine) as session:
        loans = session.scalars(build_loan_detail_query()).all()
        related = [(loan.user.name, loan.book.title) for loan in loans]

    assert related == [
        ("Ada Lovelace", "Kindred"),
        ("Ada Lovelace", "The Left Hand of Darkness"),
    ]
    assert len(statements) == 1
    assert statements[0].lower().count("left outer join") == 2


def test_selectinload_keeps_user_history_at_two_queries(engine) -> None:
    statements = statement_counter(engine)

    with Session(engine) as session:
        user = session.scalars(build_user_detail_query(1)).one()
        titles = [loan.book.title for loan in user.loans]

    assert titles == ["Kindred", "The Left Hand of Darkness"]
    assert len(statements) == 2
    assert "from users" in statements[0].lower()
    assert "from loans" in statements[1].lower()


def test_unplanned_relationship_access_raises_instead_of_querying(engine) -> None:
    statements = statement_counter(engine)

    with Session(engine) as session:
        loan = session.scalars(select(Loan).where(Loan.id == 1)).one()
        with pytest.raises(InvalidRequestError, match="lazy='raise'"):
            _ = loan.user

    assert len(statements) == 1
