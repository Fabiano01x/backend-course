from datetime import UTC, datetime, timedelta

from fastapi import Response

from app.config import Settings
from app.security.cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from app.security.refresh import digest_refresh_token, generate_refresh_token


def cookie_header(response: Response) -> str:
    return response.headers["set-cookie"]


def test_refresh_tokens_are_random_opaque_and_stored_as_digest() -> None:
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first.startswith("rt_")
    assert second.startswith("rt_")
    assert len(first) >= 45
    assert first != second
    assert len(digest_refresh_token(first)) == 64
    assert digest_refresh_token(first) == digest_refresh_token(first)
    assert first not in digest_refresh_token(first)


def test_development_cookie_is_http_only_strict_and_path_limited() -> None:
    settings = Settings(_env_file=None, environment="test")
    now = datetime(2030, 1, 1, tzinfo=UTC)
    response = Response()
    set_refresh_cookie(
        response,
        "rt_example",
        now + timedelta(days=7),
        settings,
        now=now,
    )
    header = cookie_header(response)

    assert header.startswith(f"{REFRESH_COOKIE_NAME}=rt_example;")
    assert "HttpOnly" in header
    assert "SameSite=strict" in header
    assert "Path=/auth" in header
    assert "Max-Age=604800" in header
    assert "Secure" not in header


def test_production_cookie_is_secure_and_clear_preserves_scope() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        allowed_origins=["https://library.example"],
        jwt_secret_key="production-test-jwt-key-" + "x" * 40,
    )
    response = Response()
    clear_refresh_cookie(response, settings)
    header = cookie_header(response)

    assert header.startswith(f'{REFRESH_COOKIE_NAME}="";')
    assert "Max-Age=0" in header
    assert "HttpOnly" in header
    assert "Secure" in header
    assert "SameSite=strict" in header
    assert "Path=/auth" in header
