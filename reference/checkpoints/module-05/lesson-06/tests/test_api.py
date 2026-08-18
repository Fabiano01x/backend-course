import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.dependencies import get_settings
from app.main import app
from app.models import Book, User
from tests.support import RecordingSession, Result


pytestmark = pytest.mark.anyio


def book(
    book_id: int,
    *,
    title: str = "Kindred",
    author: str = "Octavia E. Butler",
    isbn: str = "9780807083697",
) -> Book:
    return Book(id=book_id, title=title, author=author, isbn=isbn)


def user(user_id: int) -> User:
    return User(
        id=user_id,
        name="Ada Lovelace",
        email="ada@example.com",
        active=True,
    )


async def test_defaults_and_previous_contracts(
    client: AsyncClient, session: RecordingSession
) -> None:
    session.scalar_results.append(0)
    session.execute_results.append(Result(rows=[]))

    info = await client.get("/info")
    books = await client.get("/books")
    created = await client.post(
        "/users", json={"name": "Grace Hopper", "email": "grace@example.com"}
    )

    assert info.json()["version"] == "0.14.0"
    assert books.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}
    assert created.status_code == 201
    assert created.json()["active"] is True
    assert session.commit_count == 1


async def test_lists_books_with_derived_availability(
    client: AsyncClient, session: RecordingSession
) -> None:
    session.scalar_results.append(2)
    session.execute_results.append(
        Result(rows=[(book(1), True), (book(2, title="Dune"), False)])
    )

    response = await client.get(
        "/books",
        params={
            "available": "false",
            "author": "butler",
            "sort_by": "title",
            "order": "desc",
            "limit": 2,
            "offset": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["available"] for item in response.json()["items"]] == [True, False]


async def test_creates_replaces_and_deletes_book(
    client: AsyncClient, session: RecordingSession
) -> None:
    created = await client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "isbn": "9780441172719"},
    )

    existing = book(1)
    session.execute_results.append(Result(rows=[(existing, True)]))
    replaced = await client.put(
        "/books/1",
        json={
            "title": "Kindred - Nova edição",
            "author": "Octavia E. Butler",
            "isbn": "9780807083697",
        },
    )

    session.get_results.append(existing)
    deleted = await client.delete("/books/1")

    assert created.status_code == 201
    assert created.json()["available"] is True
    assert replaced.json()["title"] == "Kindred - Nova edição"
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert session.added[0].title == "Dune"
    assert session.deleted == [existing]
    assert session.commit_count == 3
    assert session.refresh_count == 2


async def test_rolls_back_and_returns_conflict_for_duplicate_isbn(
    client: AsyncClient, session: RecordingSession
) -> None:
    session.commit_errors.append(
        IntegrityError("INSERT INTO books", {}, Exception("duplicate"))
    )

    response = await client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "isbn": "9780441172719"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "ISBN já cadastrado"}
    assert session.rollback_count == 1
    assert session.refresh_count == 0


async def test_protects_loan_history_when_deleting_book(
    client: AsyncClient, session: RecordingSession
) -> None:
    existing = book(1)
    session.get_results.append(existing)
    session.commit_errors.append(
        IntegrityError("DELETE FROM books", {}, Exception("foreign key"))
    )

    response = await client.delete("/books/1")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Livro possui histórico de empréstimos"
    }
    assert session.deleted == [existing]
    assert session.rollback_count == 1


async def test_reads_persistent_users(
    client: AsyncClient, session: RecordingSession
) -> None:
    ada = user(1)
    session.execute_results.append(Result(scalars=[ada]))
    session.get_results.append(ada)

    listed = await client.get("/users")
    detail = await client.get("/users/1")

    assert listed.json() == [
        {"id": 1, "name": "Ada Lovelace", "email": "ada@example.com", "active": True}
    ]
    assert detail.json() == listed.json()[0]


async def test_overrides_settings_without_reimporting_app(
    client: AsyncClient, session: RecordingSession
) -> None:
    test_settings = Settings(
        _env_file=None,
        app_name="Library API de Teste",
        app_version="9.9.9",
        environment="test",
        default_page_size=2,
        max_page_size=3,
    )

    async def override_settings() -> Settings:
        return test_settings

    app.dependency_overrides[get_settings] = override_settings
    session.scalar_results.extend([0, 0])
    session.execute_results.extend([Result(rows=[]), Result(rows=[])])

    info = await client.get("/info")
    default_page = await client.get("/books")
    valid_page = await client.get("/books", params={"limit": 3})
    invalid_page = await client.get("/books", params={"limit": 4})

    assert info.json()["name"] == "Library API de Teste"
    assert info.json()["environment"] == "test"
    assert default_page.json()["limit"] == 2
    assert valid_page.json()["limit"] == 3
    assert invalid_page.status_code == 422
    assert invalid_page.json() == {"detail": "limit não pode exceder 3"}


@pytest.mark.parametrize(
    ("parameter", "value"),
    [("sort_by", "isbn"), ("order", "sideways"), ("limit", "0"), ("offset", "-1")],
)
async def test_rejects_invalid_query_parameters(
    client: AsyncClient, parameter: str, value: str
) -> None:
    response = await client.get("/books", params={parameter: value})
    assert response.status_code == 422


async def test_missing_and_invalid_body_contracts_remain(
    client: AsyncClient, session: RecordingSession
) -> None:
    session.execute_results.append(Result(rows=[]))
    session.get_results.append(None)
    missing = await client.get("/books/999")
    missing_user = await client.get("/users/999")
    invalid = await client.post(
        "/books",
        json={"title": "", "author": "Author", "isbn": "short", "available": False},
    )
    blank = await client.post(
        "/books", json={"title": "   ", "author": "Author", "isbn": "9780000000001"}
    )
    invalid_user = await client.post("/users", json={"name": "G", "email": "invalid"})
    partial_replace = await client.put(
        "/books/1", json={"title": "Somente um campo"}
    )

    assert missing.json() == {"detail": "Livro não encontrado"}
    assert missing_user.json() == {"detail": "Usuário não encontrado"}
    assert invalid.status_code == 422
    assert blank.status_code == 422
    assert invalid_user.status_code == 422
    assert partial_replace.status_code == 422


async def test_dependency_does_not_leak_into_openapi(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    parameters = schema["paths"]["/books"]["get"]["parameters"]

    assert "settings" not in {parameter["name"] for parameter in parameters}
    assert "session" not in {parameter["name"] for parameter in parameters}
    assert set(schema["paths"]) == {
        "/health",
        "/health/database",
        "/info",
        "/books",
        "/books/{book_id}",
        "/users",
        "/users/{user_id}",
        "/loans",
        "/loans/{loan_id}/return",
    }
