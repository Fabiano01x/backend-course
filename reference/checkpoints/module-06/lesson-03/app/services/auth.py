"""Regras de autenticação local independentes do contrato HTTP."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.models import User
from app.security.passwords import DUMMY_PASSWORD_HASH, verify_password


def normalize_email(email: str) -> str:
    return email.strip().casefold()


async def authenticate_password(
    session: AsyncSession, *, email: str, password: str
) -> User | None:
    statement = select(User).where(User.email == normalize_email(email))
    user = (await session.execute(statement)).scalar_one_or_none()
    candidate_hash = (
        user.password_hash
        if user is not None and user.password_hash is not None
        else DUMMY_PASSWORD_HASH
    )
    password_matches = await run_in_threadpool(
        verify_password, password, candidate_hash
    )
    if (
        user is None
        or user.password_hash is None
        or not user.active
        or not password_matches
    ):
        return None
    return user
