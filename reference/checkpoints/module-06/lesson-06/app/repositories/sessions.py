"""Persistência focada nas famílias de refresh tokens."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken, User


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_by_digest(self, token_digest: str) -> RefreshToken | None:
        statement = (
            select(RefreshToken)
            .where(RefreshToken.token_digest == token_digest)
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def find_user(self, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        await self.session.execute(statement)

    def add(self, token: RefreshToken) -> None:
        self.session.add(token)

    async def flush(self) -> None:
        await self.session.flush()
