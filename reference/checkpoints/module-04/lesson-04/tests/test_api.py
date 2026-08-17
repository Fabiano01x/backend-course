import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_health_and_default_book_page(client: AsyncClient) -> None:
    health = await client.get("/health")
    books = await client.get("/books")

    assert health.json() == {"status": "ok"}
    assert books.json() == {
        "items": [
            {
                "id": 1,
                "title": "Clean Architecture",
                "author": "Robert C. Martin",
                "isbn": "9780134494166",
                "available": True,
            },
            {
                "id": 2,
                "title": "Kindred",
                "author": "Octavia E. Butler",
                "isbn": "9780807083697",
                "available": True,
            },
            {
                "id": 3,
                "title": "Designing Data-Intensive Applications",
                "author": "Martin Kleppmann",
                "isbn": "9781449373320",
                "available": False,
            },
            {
                "id": 4,
                "title": "Fluent Python",
                "author": "Luciano Ramalho",
                "isbn": "9781492056355",
                "available": True,
            },
        ],
        "total": 4,
        "limit": 20,
        "offset": 0,
    }


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
    assert response.json()["limit"] == 2
    assert response.json()["offset"] == 1
    assert [book["title"] for book in response.json()["items"]] == [
        "Fluent Python",
        "Clean Architecture",
    ]


async def test_filters_author_case_insensitively(client: AsyncClient) -> None:
    response = await client.get("/books", params={"author": "MARTIN"})

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert {book["id"] for book in response.json()["items"]} == {1, 3}


async def test_filters_explicit_false_availability(client: AsyncClient) -> None:
    response = await client.get("/books", params={"available": "false"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [book["id"] for book in response.json()["items"]] == [3]


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


async def test_creates_and_finds_book(client: AsyncClient) -> None:
    created = await client.post(
        "/books",
        json={
            "title": "Parable of the Sower",
            "author": "Octavia E. Butler",
            "isbn": "9781538732182",
        },
    )
    found = await client.get("/books/5")

    assert created.status_code == 201
    assert created.json()["id"] == 5
    assert found.json() == created.json()


async def test_rejects_invalid_and_extra_book_fields(client: AsyncClient) -> None:
    response = await client.post(
        "/books",
        json={"title": "", "author": "Author", "isbn": "short", "available": False},
    )

    assert response.status_code == 422
    fields = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert {("body", "title"), ("body", "isbn"), ("body", "available")} <= fields


async def test_users_and_missing_resources_keep_their_contracts(client: AsyncClient) -> None:
    users = await client.get("/users")
    missing_book = await client.get("/books/999")
    missing_user = await client.get("/users/999")

    assert users.json()[0]["email"] == "ada@example.com"
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


async def test_openapi_documents_page_and_query_contract(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    operation = schema["paths"]["/books"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    assert set(schema["paths"]) == {
        "/health",
        "/books",
        "/books/{book_id}",
        "/users",
        "/users/{user_id}",
    }
    assert {"BookCreate", "BookResponse", "BookPage", "UserCreate", "UserResponse"} <= set(
        schema["components"]["schemas"]
    )
    assert {"available", "author", "sort_by", "order", "limit", "offset"} == set(parameters)
    assert parameters["limit"]["schema"]["minimum"] == 1
    assert parameters["limit"]["schema"]["maximum"] == 100
    assert parameters["sort_by"]["schema"]["enum"] == ["id", "title", "author"]
    page_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert page_schema["$ref"].endswith("/BookPage")
