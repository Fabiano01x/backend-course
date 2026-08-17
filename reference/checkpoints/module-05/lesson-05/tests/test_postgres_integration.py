import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect

from app.config import Settings
from app.database import create_postgres_database
from app.main import create_app


PROJECT = Path(__file__).resolve().parents[1]
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("LIBRARY_TEST_POSTGRES") != "1",
        reason="defina LIBRARY_TEST_POSTGRES=1 para usar PostgreSQL real",
    ),
]


def alembic_config() -> Config:
    config = Config(PROJECT / "alembic.ini")
    config.set_main_option("script_location", str(PROJECT / "alembic"))
    return config


async def table_names(settings: Settings) -> set[str]:
    database = create_postgres_database(settings)
    try:
        async with database.engine.connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: set(inspect(sync_connection).get_table_names())
            )
    finally:
        await database.engine.dispose()


async def exercise_http_contract(settings: Settings) -> None:
    token = uuid4()
    isbn = str(token.int % 10**13).zfill(13)
    author = f"Integration {token.hex[:8]}"
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


def test_migration_round_trip_and_book_crud_against_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = os.getenv("LIBRARY_TEST_DATABASE_HOST", "localhost")
    port = os.getenv("LIBRARY_TEST_DATABASE_PORT", "5432")
    monkeypatch.setenv("LIBRARY_ENVIRONMENT", "test")
    monkeypatch.setenv("LIBRARY_DATABASE_HOST", host)
    monkeypatch.setenv("LIBRARY_DATABASE_PORT", port)
    settings = Settings(_env_file=None)
    config = alembic_config()

    try:
        command.upgrade(config, "head")
        command.check(config)
        assert {"users", "books", "loans", "alembic_version"} <= asyncio.run(
            table_names(settings)
        )

        command.downgrade(config, "base")
        assert {"users", "books", "loans"}.isdisjoint(
            asyncio.run(table_names(settings))
        )

        command.upgrade(config, "head")
        asyncio.run(exercise_http_contract(settings))
    finally:
        command.downgrade(config, "base")
