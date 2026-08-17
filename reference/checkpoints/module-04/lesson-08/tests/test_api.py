import pytest
from httpx import AsyncClient

from app.config import Settings
from app.dependencies import get_settings
from app.main import app


pytestmark = pytest.mark.anyio


async def test_defaults_and_previous_contracts(client: AsyncClient) -> None:
    info = await client.get("/info")
    books = await client.get("/books")
    filtered = await client.get("/books", params={"available": "false"})
    created = await client.post(
        "/users", json={"name": "Grace Hopper", "email": "grace@example.com"}
    )

    assert info.json()["version"] == "0.8.0"
    assert books.json()["limit"] == 20
    assert [book["id"] for book in filtered.json()["items"]] == [3]
    assert created.status_code == 201


async def test_keeps_deterministic_sort_tie_breaker(client: AsyncClient) -> None:
    for isbn in ("9780000000001", "9780000000002"):
        response = await client.post(
            "/books",
            json={"title": "Shared Title", "author": "Shared Author", "isbn": isbn},
        )
        assert response.status_code == 201

    first = await client.get(
        "/books", params={"author": "Shared Author", "sort_by": "title", "limit": 1}
    )
    second = await client.get(
        "/books",
        params={"author": "Shared Author", "sort_by": "title", "limit": 1, "offset": 1},
    )
    assert [book["id"] for book in first.json()["items"]] == [5]
    assert [book["id"] for book in second.json()["items"]] == [6]


async def test_overrides_settings_without_reimporting_app(client: AsyncClient) -> None:
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


async def test_missing_and_invalid_body_contracts_remain(client: AsyncClient) -> None:
    missing = await client.get("/books/999")
    missing_user = await client.get("/users/999")
    invalid = await client.post(
        "/books",
        json={"title": "", "author": "Author", "isbn": "short", "available": False},
    )
    invalid_user = await client.post("/users", json={"name": "G", "email": "invalid"})
    assert missing.json() == {"detail": "Livro não encontrado"}
    assert missing_user.json() == {"detail": "Usuário não encontrado"}
    assert invalid.status_code == 422
    assert invalid_user.status_code == 422


async def test_dependency_does_not_leak_into_openapi(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    parameters = schema["paths"]["/books"]["get"]["parameters"]

    assert "settings" not in {parameter["name"] for parameter in parameters}
    assert set(schema["paths"]) == {
        "/health", "/info", "/books", "/books/{book_id}", "/users", "/users/{user_id}"
    }
