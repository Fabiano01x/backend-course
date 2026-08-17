import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("LIBRARY_TEST_POSTGRES") != "1",
        reason="defina LIBRARY_TEST_POSTGRES=1 para usar PostgreSQL real",
    ),
]


async def test_book_crud_against_postgresql() -> None:
    token = uuid4()
    isbn = str(token.int % 10**13).zfill(13)
    author = f"Integration {token.hex[:8]}"
    settings = Settings(
        _env_file=None,
        environment="test",
        database_host=os.getenv("LIBRARY_TEST_DATABASE_HOST", "localhost"),
        database_port=int(os.getenv("LIBRARY_TEST_DATABASE_PORT", "5432")),
    )
    application = create_app(settings)

    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            created = await client.post(
                "/books",
                json={"title": "Integration Book", "author": author, "isbn": isbn},
            )
            book_id = created.json()["id"]
            duplicate = await client.post(
                "/books",
                json={"title": "Duplicate", "author": author, "isbn": isbn},
            )
            detail = await client.get(f"/books/{book_id}")
            page = await client.get("/books", params={"author": author})
            replaced = await client.put(
                f"/books/{book_id}",
                json={"title": "Integration Book 2", "author": author, "isbn": isbn},
            )
            deleted = await client.delete(f"/books/{book_id}")
            missing = await client.get(f"/books/{book_id}")
            created_user = await client.post(
                "/users",
                json={
                    "name": "Integration User",
                    "email": f"{token.hex}@example.com",
                },
            )
            user_detail = await client.get(f"/users/{created_user.json()['id']}")

    assert created.status_code == 201
    assert created.json()["available"] is True
    assert duplicate.status_code == 409
    assert detail.json()["id"] == book_id
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["id"] == book_id
    assert replaced.json()["title"] == "Integration Book 2"
    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert created_user.status_code == 201
    assert user_detail.json()["email"] == f"{token.hex}@example.com"
