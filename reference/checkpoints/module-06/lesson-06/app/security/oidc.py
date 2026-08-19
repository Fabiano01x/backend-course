"""Segredos efêmeros que vinculam o fluxo OIDC ao navegador iniciador."""

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import secrets

from fastapi import Response

from app.config import Settings


OIDC_ATTEMPT_COOKIE = "library_oidc_attempt"
OIDC_COOKIE_PATH = "/auth/oidc"


def digest_secret(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def base64url_sha256(value: str) -> str:
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


@dataclass(frozen=True, slots=True)
class OidcAttemptSecrets:
    browser_secret: str
    state: str
    nonce: str
    code_verifier: str
    expires_at: datetime

    @property
    def cookie_value(self) -> str:
        return f"{self.browser_secret}.{self.code_verifier}"

    @property
    def code_challenge(self) -> str:
        return base64url_sha256(self.code_verifier)


def new_oidc_attempt(
    settings: Settings, *, now: datetime | None = None
) -> OidcAttemptSecrets:
    created_at = now or datetime.now(UTC)
    return OidcAttemptSecrets(
        browser_secret=secrets.token_urlsafe(32),
        state=secrets.token_urlsafe(32),
        nonce=secrets.token_urlsafe(32),
        code_verifier=secrets.token_urlsafe(64),
        expires_at=created_at
        + timedelta(minutes=settings.oidc_attempt_expire_minutes),
    )


def parse_attempt_cookie(raw_cookie: str | None) -> tuple[str, str] | None:
    if raw_cookie is None:
        return None
    browser_secret, separator, code_verifier = raw_cookie.partition(".")
    if not separator or not browser_secret or not code_verifier:
        return None
    try:
        browser_secret.encode("ascii")
        code_verifier.encode("ascii")
    except UnicodeEncodeError:
        return None
    return browser_secret, code_verifier


def set_oidc_attempt_cookie(
    response: Response, secrets_: OidcAttemptSecrets, settings: Settings
) -> None:
    max_age = settings.oidc_attempt_expire_minutes * 60
    response.set_cookie(
        key=OIDC_ATTEMPT_COOKIE,
        value=secrets_.cookie_value,
        max_age=max_age,
        expires=secrets_.expires_at,
        path=OIDC_COOKIE_PATH,
        secure=settings.environment == "production" or settings.https_enabled,
        httponly=True,
        samesite="lax",
    )


def clear_oidc_attempt_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=OIDC_ATTEMPT_COOKIE,
        path=OIDC_COOKIE_PATH,
        secure=settings.environment == "production" or settings.https_enabled,
        httponly=True,
        samesite="lax",
    )
