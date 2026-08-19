"""Persistência do ciclo de vida de clientes e chaves de API."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import ApiClient, ApiKey


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_client_by_name(self, name: str) -> ApiClient | None:
        statement = select(ApiClient).where(ApiClient.name == name)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def lock_client(self, client_id: UUID) -> ApiClient | None:
        statement = (
            select(ApiClient)
            .where(ApiClient.id == client_id)
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def lock_key_by_prefix(self, prefix: str) -> ApiKey | None:
        statement = (
            select(ApiKey)
            .options(joinedload(ApiKey.client, innerjoin=True))
            .where(ApiKey.prefix == prefix)
            .with_for_update(of=ApiKey)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def lock_key(self, key_id: UUID) -> ApiKey | None:
        statement = (
            select(ApiKey)
            .options(joinedload(ApiKey.client, innerjoin=True))
            .where(ApiKey.id == key_id)
            .with_for_update(of=ApiKey)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    def add_client(self, client: ApiClient) -> None:
        self.session.add(client)

    def add_key(self, key: ApiKey) -> None:
        self.session.add(key)

    async def flush(self) -> None:
        await self.session.flush()
