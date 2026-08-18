from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.config import Settings
from app.models import RefreshToken, User
from app.security.refresh import digest_refresh_token
from app.services.sessions import (
    RotationStatus,
    revoke_refresh_family,
    rotate_refresh_session,
    start_refresh_session,
)
from tests.support import RecordingSession, Result


pytestmark = pytest.mark.anyio
NOW = datetime(2030, 1, 1, tzinfo=UTC)


def refresh_record(
    raw_token: str,
    *,
    used_at: datetime | None = None,
    revoked_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> RefreshToken:
    return RefreshToken(
        id=uuid4(),
        family_id=uuid4(),
        user_id=7,
        token_digest=digest_refresh_token(raw_token),
        created_at=NOW - timedelta(days=1),
        expires_at=expires_at or NOW + timedelta(days=6),
        used_at=used_at,
        revoked_at=revoked_at,
    )


def active_user(active: bool = True) -> User:
    return User(
        id=7,
        name="Ada Lovelace",
        email="ada@example.com",
        active=active,
    )


async def test_login_starts_one_absolute_lifetime_family() -> None:
    session = RecordingSession()
    settings = Settings(_env_file=None, environment="test")
    issued = await start_refresh_session(
        session, user_id=7, settings=settings, now=NOW
    )
    record = session.added[0]

    assert isinstance(record, RefreshToken)
    assert record.user_id == 7
    assert record.expires_at == NOW + timedelta(days=7)
    assert record.token_digest == digest_refresh_token(issued.value)
    assert issued.value not in record.token_digest
    assert session.commit_count == 1


async def test_rotation_consumes_once_and_keeps_family_expiration() -> None:
    raw_token = "rt_original"
    current = refresh_record(raw_token)
    session = RecordingSession()
    session.execute_results.extend(
        [Result(scalars=[current]), Result(scalars=[active_user()])]
    )

    result = await rotate_refresh_session(session, raw_token, now=NOW)

    assert result.status is RotationStatus.ROTATED
    assert result.user_id == 7
    assert result.refresh_token is not None
    assert result.expires_at == current.expires_at
    assert current.used_at == NOW
    replacement = session.added[0]
    assert isinstance(replacement, RefreshToken)
    assert replacement.family_id == current.family_id
    assert replacement.expires_at == current.expires_at
    assert replacement.token_digest == digest_refresh_token(
        result.refresh_token
    )
    assert current.replaced_by_id == replacement.id
    assert session.begin_count == 1
    assert session.flush_count == 2
    assert session.transaction_commit_count == 1


async def test_reuse_revokes_the_whole_family_and_commits_detection() -> None:
    raw_token = "rt_used"
    current = refresh_record(raw_token, used_at=NOW - timedelta(minutes=1))
    session = RecordingSession()
    session.execute_results.append(Result(scalars=[current]))

    result = await rotate_refresh_session(session, raw_token, now=NOW)

    assert result.status is RotationStatus.REUSED
    assert len(session.statements) == 2
    assert "UPDATE refresh_tokens" in str(session.statements[1])
    assert "family_id" in str(session.statements[1])
    assert session.transaction_commit_count == 1
    assert session.transaction_rollback_count == 0


@pytest.mark.parametrize(
    "current",
    [
        None,
        refresh_record("rt_revoked", revoked_at=NOW - timedelta(minutes=1)),
        refresh_record("rt_expired", expires_at=NOW - timedelta(seconds=1)),
    ],
)
async def test_missing_revoked_or_expired_token_is_invalid(
    current: RefreshToken | None,
) -> None:
    raw_token = (
        "rt_missing"
        if current is None
        else "rt_revoked" if current.revoked_at else "rt_expired"
    )
    session = RecordingSession()
    session.execute_results.append(
        Result(scalars=[] if current is None else [current])
    )

    result = await rotate_refresh_session(session, raw_token, now=NOW)

    assert result.status is RotationStatus.INVALID
    assert session.added == []
    assert session.transaction_commit_count == 1


async def test_inactive_user_revokes_family_without_issuing_replacement() -> None:
    raw_token = "rt_inactive"
    current = refresh_record(raw_token)
    session = RecordingSession()
    session.execute_results.extend(
        [Result(scalars=[current]), Result(scalars=[active_user(False)])]
    )

    result = await rotate_refresh_session(session, raw_token, now=NOW)

    assert result.status is RotationStatus.INVALID
    assert "UPDATE refresh_tokens" in str(session.statements[2])
    assert session.added == []


async def test_logout_is_idempotent_and_revokes_known_family() -> None:
    raw_token = "rt_logout"
    current = refresh_record(raw_token)
    session = RecordingSession()
    session.execute_results.append(Result(scalars=[current]))

    await revoke_refresh_family(session, raw_token, now=NOW)

    assert "UPDATE refresh_tokens" in str(session.statements[1])
    assert session.transaction_commit_count == 1

    empty_session = RecordingSession()
    await revoke_refresh_family(empty_session, None, now=NOW)
    assert empty_session.statements == []
