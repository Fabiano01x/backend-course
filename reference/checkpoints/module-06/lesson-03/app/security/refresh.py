"""Geração e digest de refresh tokens opacos."""

from hashlib import sha256
import secrets


REFRESH_TOKEN_BYTES = 32
REFRESH_TOKEN_PREFIX = "rt_"


def generate_refresh_token() -> str:
    return REFRESH_TOKEN_PREFIX + secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def digest_refresh_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
