"""Leitura da fonte persistida de autorização."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Role, User, UserRole


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: int
    roles: frozenset[str]

    def has_role(self, role: str) -> bool:
        return role in self.roles


def build_principal_query(user_id: int):
    return (
        select(User, Role.name)
        .outerjoin(UserRole, UserRole.user_id == User.id)
        .outerjoin(Role, Role.name == UserRole.role_name)
        .where(User.id == user_id)
    )


class AuthorizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_active_principal(self, user_id: int) -> Principal | None:
        rows = (await self.session.execute(build_principal_query(user_id))).all()
        if not rows:
            return None
        user = rows[0][0]
        if not user.active:
            return None
        return Principal(
            user_id=user.id,
            roles=frozenset(
                role_name for _, role_name in rows if role_name is not None
            ),
        )
