"""Política do cookie que transporta o refresh token."""

from datetime import UTC, datetime
from math import ceil

from fastapi import Response

from app.config import Settings


REFRESH_COOKIE_NAME = "library_refresh"
REFRESH_COOKIE_PATH = "/auth"


def cookie_requires_secure(settings: Settings) -> bool:
    return settings.environment == "production" or settings.https_enabled


def set_refresh_cookie(
    response: Response,
    token: str,
    expires_at: datetime,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(UTC)
    max_age = max(0, ceil((expires_at - current_time).total_seconds()))
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=expires_at,
        path=REFRESH_COOKIE_PATH,
        secure=cookie_requires_secure(settings),
        httponly=True,
        samesite="strict",
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=cookie_requires_secure(settings),
        httponly=True,
        samesite="strict",
    )
