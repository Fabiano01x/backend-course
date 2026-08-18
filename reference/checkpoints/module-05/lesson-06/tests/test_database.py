from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.sql.elements import TextClause
from starlette.requests import Request

from app.config import Settings
from app.database import Database, build_database_url, create_database, get_session
from app.main import create_app


pytestmark = pytest.mark.anyio


class RecordingSession:
    def __init__(self) -> None:
        self.was_closed = False
        self.statements: list[TextClause] = []

    async def execute(self, statement: TextClause) -> None:
        self.statements.append(statement)


class SessionContext:
    def __init__(self, session: RecordingSession) -> None:
        self.session = session

    async def __aenter__(self) -> RecordingSession:
        return self.session

    async def __aexit__(self, *_: object) -> None:
        self.session.was_closed = True


class RecordingSessionFactory:
    def __init__(self) -> None:
        self.created: list[RecordingSession] = []

    def __call__(self) -> SessionContext:
        session = RecordingSession()
        self.created.append(session)
        return SessionContext(session)


class RecordingEngine:
    def __init__(self) -> None:
        self.was_disposed = False

    def begin(self) -> None:
        raise AssertionError("o startup não deve alterar o esquema")

    async def dispose(self) -> None:
        self.was_disposed = True


def make_database(
    engine: object, sessions: RecordingSessionFactory | None = None
) -> Database:
    return Database(
        engine=cast(Any, engine),
        sessions=cast(Any, sessions or RecordingSessionFactory()),
    )


def make_request(application: FastAPI) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "app": application,
        }
    )


def test_builds_postgresql_url_without_misreading_special_password() -> None:
    settings = Settings(
        _env_file=None,
        database_host="db.internal",
        database_name="library_prod",
        database_user="webapp",
        database_password="s3cure_p@ss/word",
    )

    url = build_database_url(settings)

    assert url.drivername == "postgresql+asyncpg"
    assert url.username == "webapp"
    assert url.password == "s3cure_p@ss/word"
    assert url.host == "db.internal"
    assert url.database == "library_prod"
    assert "s3cure_p%40ss%2Fword" in url.render_as_string(hide_password=False)
    assert "s3cure_p@ss/word" not in str(url)


async def test_creates_asyncpg_engine_and_typed_session_factory() -> None:
    database = create_database(
        "postgresql+asyncpg://library:password@localhost/library"
    )

    assert database.engine.url.drivername == "postgresql+asyncpg"
    assert database.sessions.kw["expire_on_commit"] is False
    await database.engine.dispose()


async def test_dependency_yields_a_new_session_and_closes_it() -> None:
    sessions = RecordingSessionFactory()
    database = make_database(RecordingEngine(), sessions)
    application = FastAPI()
    application.state.database = database

    first_dependency = get_session(make_request(application))
    second_dependency = get_session(make_request(application))
    first = await anext(first_dependency)
    second = await anext(second_dependency)

    assert first is not second
    assert first.was_closed is False
    assert second.was_closed is False

    await first_dependency.aclose()
    await second_dependency.aclose()
    assert first.was_closed is True
    assert second.was_closed is True


async def test_lifespan_does_not_change_schema_and_disposes_engine() -> None:
    engine = RecordingEngine()
    database = make_database(engine)
    application = create_app(Settings(_env_file=None), database)

    async with application.router.lifespan_context(application):
        assert engine.was_disposed is False

    assert engine.was_disposed is True


async def test_database_health_executes_sql_instead_of_inspecting_session_flag() -> None:
    sessions = RecordingSessionFactory()
    database = make_database(RecordingEngine(), sessions)
    application = create_app(Settings(_env_file=None), database)

    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/health/database")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
    assert len(sessions.created) == 1
    assert sessions.created[0].was_closed is True
    assert [str(statement) for statement in sessions.created[0].statements] == [
        "SELECT 1"
    ]
