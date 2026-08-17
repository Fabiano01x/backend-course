import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_health_info_and_default_book_page(client: AsyncClient) -> None:
    health = await client.get("/health")
    info = await client.get("/info")
    books = await client.get("/books")

    assert health.json() == {"status": "ok"}
    assert info.json() == {
        "name": "Library API",
        "version": "0.5.0",
        "environment": "development",
        "debug": False,
    }
    assert books.json()["total"] == 4
    assert books.json()["limit"] == 20


async def test_filters_books_before_counting_and_paginating(client: AsyncClient) -> None:
    response = await client.get(
        "/books",
        params={
            "available": "true",
            "sort_by": "title",
            "order": "desc",
            "limit": 2,
            "offset": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert [book["title"] for book in response.json()["items"]] == [
        "Fluent Python",
        "Clean Architecture",
    ]


async def test_filters_explicit_false_and_author(client: AsyncClient) -> None:
    unavailable = await client.get("/books", params={"available": "false"})
    author = await client.get("/books", params={"author": "MARTIN"})

    assert [book["id"] for book in unavailable.json()["items"]] == [3]
    assert {book["id"] for book in author.json()["items"]} == {1, 3}


async def test_uses_id_to_break_sort_ties(client: AsyncClient) -> None:
    payloads = [
        {
            "title": "Shared Title",
            "author": "Shared Author",
            "isbn": "9780000000001",
        },
        {
            "title": "Shared Title",
            "author": "Shared Author",
            "isbn": "9780000000002",
        },
    ]
    for payload in payloads:
        response = await client.post("/books", json=payload)
        assert response.status_code == 201

    first_page = await client.get(
        "/books",
        params={"author": "Shared Author", "sort_by": "title", "limit": 1},
    )
    second_page = await client.get(
        "/books",
        params={
            "author": "Shared Author",
            "sort_by": "title",
            "limit": 1,
            "offset": 1,
        },
    )

    assert [book["id"] for book in first_page.json()["items"]] == [5]
    assert [book["id"] for book in second_page.json()["items"]] == [6]


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("sort_by", "isbn"),
        ("order", "sideways"),
        ("limit", "0"),
        ("limit", "101"),
        ("offset", "-1"),
        ("author", ""),
    ],
)
async def test_rejects_invalid_query_parameters(
    client: AsyncClient, parameter: str, value: str
) -> None:
    response = await client.get("/books", params={parameter: value})

    assert response.status_code == 422


async def test_creation_detail_and_user_contracts_remain(client: AsyncClient) -> None:
    created_book = await client.post(
        "/books",
        json={
            "title": "Parable of the Sower",
            "author": "Octavia E. Butler",
            "isbn": "9781538732182",
        },
    )
    found_book = await client.get("/books/5")
    created_user = await client.post(
        "/users", json={"name": "Grace Hopper", "email": "grace@example.com"}
    )

    assert created_book.status_code == 201
    assert found_book.json() == created_book.json()
    assert created_user.status_code == 201
    assert created_user.json()["active"] is True


async def test_validation_and_missing_resource_contracts_remain(
    client: AsyncClient,
) -> None:
    invalid_book = await client.post(
        "/books",
        json={"title": "", "author": "Author", "isbn": "short", "available": False},
    )
    invalid_user = await client.post(
        "/users", json={"name": "G", "email": "invalid"}
    )
    missing_book = await client.get("/books/999")
    missing_user = await client.get("/users/999")

    assert invalid_book.status_code == 422
    fields = {tuple(item["loc"]) for item in invalid_book.json()["detail"]}
    assert {("body", "title"), ("body", "isbn"), ("body", "available")} <= fields
    assert invalid_user.status_code == 422
    assert missing_book.json() == {"detail": "Livro não encontrado"}
    assert missing_user.json() == {"detail": "Usuário não encontrado"}


async def test_openapi_uses_configured_metadata_and_limits(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    parameters = {
        parameter["name"]: parameter
        for parameter in schema["paths"]["/books"]["get"]["parameters"]
    }

    assert schema["info"]["title"] == "Library API"
    assert schema["info"]["version"] == "0.5.0"
    assert set(schema["paths"]) == {
        "/health",
        "/info",
        "/books",
        "/books/{book_id}",
        "/users",
        "/users/{user_id}",
    }
    assert parameters["limit"]["schema"]["default"] == 20
    assert parameters["limit"]["schema"]["maximum"] == 100
