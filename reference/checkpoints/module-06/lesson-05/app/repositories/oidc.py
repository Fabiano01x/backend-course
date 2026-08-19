"""Persistência das tentativas e identidades externas OIDC."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExternalIdentity, OidcLoginAttempt, User


class OidcRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_attempt(
        self, *, browser_digest: str, state_digest: str
    ) -> OidcLoginAttempt | None:
        statement = (
            select(OidcLoginAttempt)
            .where(
                OidcLoginAttempt.browser_digest == browser_digest,
                OidcLoginAttempt.state_digest == state_digest,
            )
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def find_external_identity(
        self, *, issuer: str, subject: str
    ) -> tuple[ExternalIdentity, User] | None:
        statement = (
            select(ExternalIdentity, User)
            .join(User, User.id == ExternalIdentity.user_id)
            .where(
                ExternalIdentity.issuer == issuer,
                ExternalIdentity.subject == subject,
            )
        )
        return (await self.session.execute(statement)).one_or_none()

    async def find_user_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return (await self.session.execute(statement)).scalar_one_or_none()

    def add(self, instance: object) -> None:
        self.session.add(instance)

    async def flush(self) -> None:
        await self.session.flush()
