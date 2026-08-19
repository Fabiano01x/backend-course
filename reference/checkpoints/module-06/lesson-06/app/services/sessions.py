"""Início, rotação e encerramento de sessões renováveis."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import RefreshToken
from app.repositories.sessions import RefreshTokenRepository
from app.security.refresh import digest_refresh_token, generate_refresh_token


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    value: str
    expires_at: datetime


class RotationStatus(str, Enum):
    ROTATED = "rotated"
    INVALID = "invalid"
    REUSED = "reused"


@dataclass(frozen=True, slots=True)
class RotationResult:
    status: RotationStatus
    user_id: int | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None


def new_refresh_record(
    *,
    user_id: int,
    family_id: UUID,
    expires_at: datetime,
    now: datetime,
) -> tuple[RefreshToken, str]:
    raw_token = generate_refresh_token()
    record = RefreshToken(
        id=uuid4(),
        family_id=family_id,
        user_id=user_id,
        token_digest=digest_refresh_token(raw_token),
        created_at=now,
        expires_at=expires_at,
    )
    return record, raw_token


async def start_refresh_session(
    session: AsyncSession,
    *,
    user_id: int,
    settings: Settings,
    now: datetime | None = None,
) -> IssuedRefreshToken:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(days=settings.refresh_token_expire_days)
    record, raw_token = new_refresh_record(
        user_id=user_id,
        family_id=uuid4(),
        expires_at=expires_at,
        now=issued_at,
    )
    session.add(record)
    await session.commit()
    return IssuedRefreshToken(value=raw_token, expires_at=expires_at)


async def rotate_refresh_session(
    session: AsyncSession,
    raw_token: str,
    *,
    now: datetime | None = None,
) -> RotationResult:
    current_time = now or datetime.now(UTC)
    repository = RefreshTokenRepository(session)
    async with session.begin():
        current = await repository.lock_by_digest(
            digest_refresh_token(raw_token)
        )
        if current is None:
            return RotationResult(status=RotationStatus.INVALID)
        if current.used_at is not None:
            await repository.revoke_family(current.family_id, current_time)
            return RotationResult(status=RotationStatus.REUSED)
        if current.revoked_at is not None:
            return RotationResult(status=RotationStatus.INVALID)
        if current.expires_at <= current_time:
            await repository.revoke_family(current.family_id, current_time)
            return RotationResult(status=RotationStatus.INVALID)

        user = await repository.find_user(current.user_id)
        if user is None or not user.active:
            await repository.revoke_family(current.family_id, current_time)
            return RotationResult(status=RotationStatus.INVALID)

        replacement, replacement_value = new_refresh_record(
            user_id=current.user_id,
            family_id=current.family_id,
            expires_at=current.expires_at,
            now=current_time,
        )
        repository.add(replacement)
        await repository.flush()
        current.used_at = current_time
        current.replaced_by_id = replacement.id
        await repository.flush()
        return RotationResult(
            status=RotationStatus.ROTATED,
            user_id=current.user_id,
            refresh_token=replacement_value,
            expires_at=replacement.expires_at,
        )


async def revoke_refresh_family(
    session: AsyncSession,
    raw_token: str | None,
    *,
    now: datetime | None = None,
) -> None:
    if raw_token is None:
        return
    current_time = now or datetime.now(UTC)
    repository = RefreshTokenRepository(session)
    async with session.begin():
        current = await repository.lock_by_digest(
            digest_refresh_token(raw_token)
        )
        if current is not None:
            await repository.revoke_family(current.family_id, current_time)
