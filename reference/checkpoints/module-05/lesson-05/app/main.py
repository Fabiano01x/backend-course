"""Ponto de composição da Library API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.database import Database, create_postgres_database
from app.dependencies import load_settings
from app.middleware.security import SecurityHeadersMiddleware
from app.routers import books, system, users


API_DESCRIPTION = """
A **Library API** oferece contratos HTTP para consultar livros e cadastrar
livros e usuários.

## Estado atual

- livros e usuários são consultados e cadastrados no PostgreSQL;
- o ciclo completo de livros inclui leitura, criação, substituição e remoção;
- a listagem de livros aceita filtros, ordenação e paginação;
- autenticação e empréstimos ainda não fazem parte deste módulo.
"""

OPENAPI_TAGS = [
    {
        "name": "Sistema",
        "description": "Saúde da aplicação e configuração pública.",
    },
    {
        "name": "Livros",
        "description": "CRUD persistente do acervo da biblioteca.",
    },
    {
        "name": "Usuários",
        "description": "Consulta e cadastro persistente de usuários.",
    },
]


def database_lifespan(database: Database):
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await database.engine.dispose()

    return lifespan


def create_app(
    settings: Settings | None = None, database: Database | None = None
) -> FastAPI:
    startup_settings = settings or load_settings()
    startup_database = database or create_postgres_database(startup_settings)
    application = FastAPI(
        title=startup_settings.app_name,
        summary="API didática para gerenciar uma biblioteca.",
        description=API_DESCRIPTION,
        version=startup_settings.app_version,
        debug=startup_settings.debug,
        openapi_tags=OPENAPI_TAGS,
        lifespan=database_lifespan(startup_database),
    )
    application.state.database = startup_database
    application.add_middleware(
        CORSMiddleware,
        allow_origins=startup_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=(
            startup_settings.environment == "production"
            and startup_settings.https_enabled
        ),
    )
    application.include_router(system.router)
    application.include_router(books.router)
    application.include_router(users.router)
    return application


app = create_app()
