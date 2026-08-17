import inspect

import pytest
from httpx import AsyncClient

from app.main import health_check, list_books, list_users


pytestmark = pytest.mark.anyio


async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_lists_seed_book(client: AsyncClient) -> None:
    response = await client.get("/books")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "title": "Clean Architecture",
            "author": "Robert C. Martin",
            "available": True,
        }
    ]


async def test_lists_seed_user(client: AsyncClient) -> None:
    response = await client.get("/users")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Ada Lovelace", "active": True}
    ]


async def test_endpoints_are_coroutine_functions() -> None:
    assert inspect.iscoroutinefunction(health_check)
    assert inspect.iscoroutinefunction(list_books)
    assert inspect.iscoroutinefunction(list_users)
