"""Engine assíncrona, fábrica de sessões e dependência por requisição."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings


@dataclass(frozen=True, slots=True)
class Database:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]


def build_database_url(settings: Settings) -> URL:
    """Monta a URL sem submeter a senha ao parser de uma string."""
    return URL.create(
        "postgresql+asyncpg",
        username=settings.database_user,
        password=settings.database_password.get_secret_value(),
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database_name,
    )


def create_database(url: str | URL, *, echo: bool = False) -> Database:
    engine = create_async_engine(url, echo=echo)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    return Database(engine=engine, sessions=sessions)


def create_postgres_database(settings: Settings) -> Database:
    return create_database(build_database_url(settings), echo=settings.debug)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.sessions() as session:
        yield session


DatabaseSession = Annotated[AsyncSession, Depends(get_session)]
