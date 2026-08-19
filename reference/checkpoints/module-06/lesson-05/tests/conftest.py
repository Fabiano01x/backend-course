from collections.abc import AsyncIterator, Iterator
from typing import cast

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization import LIBRARIAN_ROLE, MEMBER_ROLE
from app.database import get_session
from app.dependencies import get_current_principal
from app.main import app
from app.repositories.authorization import Principal
from tests.support import RecordingSession


@pytest.fixture(autouse=True)
def reset_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def session() -> RecordingSession:
    return RecordingSession()


@pytest.fixture
async def client(session: RecordingSession) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, session)

    app.dependency_overrides[get_session] = override_session

    async def override_principal() -> Principal:
        return Principal(
            user_id=1,
            roles=frozenset({MEMBER_ROLE, LIBRARIAN_ROLE}),
        )

    app.dependency_overrides[get_current_principal] = override_principal
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
