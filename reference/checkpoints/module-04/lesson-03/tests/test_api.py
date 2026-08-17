import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_health_and_seed_collections(client: AsyncClient) -> None:
    health = await client.get("/health")
    books = await client.get("/books")
    users = await client.get("/users")

    assert health.json() == {"status": "ok"}
    assert books.json()[0]["isbn"] == "9780134494166"
    assert users.json()[0]["email"] == "ada@example.com"


async def test_creates_and_finds_book(client: AsyncClient) -> None:
    created = await client.post(
        "/books",
        json={"title": "Kindred", "author": "Octavia E. Butler", "isbn": "9780807083697"},
    )
    found = await client.get("/books/2")

    assert created.status_code == 201
    assert created.json() == {
        "id": 2,
        "title": "Kindred",
        "author": "Octavia E. Butler",
        "isbn": "9780807083697",
        "available": True,
    }
    assert found.json() == created.json()


async def test_rejects_invalid_and_extra_book_fields(client: AsyncClient) -> None:
    response = await client.post(
        "/books",
        json={"title": "", "author": "Author", "isbn": "short", "available": False},
    )

    assert response.status_code == 422
    fields = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert {("body", "title"), ("body", "isbn"), ("body", "available")} <= fields


async def test_returns_404_for_missing_resources(client: AsyncClient) -> None:
    missing_book = await client.get("/books/999")
    missing_user = await client.get("/users/999")

    assert missing_book.status_code == 404
    assert missing_book.json() == {"detail": "Livro não encontrado"}
    assert missing_user.status_code == 404
    assert missing_user.json() == {"detail": "Usuário não encontrado"}


async def test_creates_user_and_validates_email(client: AsyncClient) -> None:
    created = await client.post(
        "/users", json={"name": "Grace Hopper", "email": "grace@example.com"}
    )
    found = await client.get("/users/2")
    invalid = await client.post("/users", json={"name": "G", "email": "invalid"})

    assert created.status_code == 201
    assert created.json()["active"] is True
    assert found.json() == created.json()
    assert invalid.status_code == 422


async def test_openapi_preserves_contracts_and_groups_routers(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    schemas = schema["components"]["schemas"]

    assert {"BookCreate", "BookResponse", "UserCreate", "UserResponse"} <= set(schemas)
    assert set(schema["paths"]) == {
        "/health",
        "/books",
        "/books/{book_id}",
        "/users",
        "/users/{user_id}",
    }
    assert schema["paths"]["/health"]["get"]["tags"] == ["Sistema"]
    assert schema["paths"]["/books"]["get"]["tags"] == ["Livros"]
    assert schema["paths"]["/users"]["post"]["tags"] == ["Usuários"]
    response_schema = schema["paths"]["/books"]["post"]["responses"]["201"]
    assert response_schema["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BookResponse"
    )
