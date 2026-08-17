import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_lists_and_finds_seed_book(client: AsyncClient) -> None:
    listing = await client.get("/books")
    detail = await client.get("/books/1")

    assert listing.status_code == 200
    assert listing.json()[0]["title"] == "Clean Architecture"
    assert detail.status_code == 200
    assert detail.json()["isbn"] == "9780134494166"


async def test_creates_book_with_response_contract(client: AsyncClient) -> None:
    response = await client.post(
        "/books",
        json={
            "title": "Fluent Python",
            "author": "Luciano Ramalho",
            "isbn": "9781492056355",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 2,
        "title": "Fluent Python",
        "author": "Luciano Ramalho",
        "isbn": "9781492056355",
        "available": True,
    }


async def test_rejects_invalid_book_payload(client: AsyncClient) -> None:
    response = await client.post(
        "/books",
        json={"title": "", "author": "Author", "isbn": "short", "unknown": True},
    )

    assert response.status_code == 422
    fields = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "title") in fields
    assert ("body", "isbn") in fields
    assert ("body", "unknown") in fields


async def test_returns_404_for_missing_book(client: AsyncClient) -> None:
    response = await client.get("/books/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Livro não encontrado"}


async def test_creates_and_finds_user(client: AsyncClient) -> None:
    created = await client.post(
        "/users", json={"name": "Grace Hopper", "email": "grace@example.com"}
    )
    found = await client.get("/users/2")

    assert created.status_code == 201
    assert created.json()["active"] is True
    assert found.status_code == 200
    assert found.json()["name"] == "Grace Hopper"


async def test_rejects_invalid_email(client: AsyncClient) -> None:
    response = await client.post("/users", json={"name": "Grace", "email": "invalid"})

    assert response.status_code == 422


async def test_openapi_exposes_router_paths_and_tags(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()

    assert {"/health", "/books", "/books/{book_id}", "/users", "/users/{user_id}"} <= set(
        schema["paths"]
    )
    assert schema["paths"]["/books"]["get"]["tags"] == ["Livros"]
    assert schema["paths"]["/users"]["post"]["tags"] == ["Usuários"]
