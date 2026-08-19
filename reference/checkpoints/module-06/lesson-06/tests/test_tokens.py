from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from jwt import InvalidTokenError

from app.config import Settings
from app.security.tokens import (
    ACCESS_TOKEN_ALGORITHM,
    ACCESS_TOKEN_HEADER_TYPE,
    create_access_token,
    decode_access_token,
)


SETTINGS = Settings(
    _env_file=None,
    environment="test",
    jwt_secret_key="a" * 64,
    jwt_issuer="urn:library-api:test",
    jwt_audience="library-api-test",
)
TOKEN_ID = UUID("52b43080-ee44-4b50-a7f7-b70f4ecbb43e")


def unsigned_claims(token: str) -> dict[str, object]:
    return jwt.decode(token, options={"verify_signature": False})


def resign(claims: dict[str, object], *, typ: str = ACCESS_TOKEN_HEADER_TYPE) -> str:
    return jwt.encode(
        claims,
        SETTINGS.jwt_secret_key.get_secret_value(),
        algorithm=ACCESS_TOKEN_ALGORITHM,
        headers={"typ": typ},
    )


def test_access_token_has_fixed_header_required_claims_and_short_lifetime() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    token = create_access_token(
        user_id=7, settings=SETTINGS, now=now, token_id=TOKEN_ID
    )
    header = jwt.get_unverified_header(token)
    claims = unsigned_claims(token)
    decoded = decode_access_token(token, SETTINGS)

    assert header == {"alg": "HS256", "typ": "at+jwt"}
    assert claims == {
        "iss": "urn:library-api:test",
        "aud": "library-api-test",
        "sub": "7",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "jti": str(TOKEN_ID),
        "token_type": "access",
    }
    assert decoded.user_id == 7
    assert decoded.token_id == TOKEN_ID
    assert decoded.expires_at == now + timedelta(minutes=15)


def test_rejects_expired_or_signed_by_another_key() -> None:
    expired = create_access_token(
        user_id=1,
        settings=SETTINGS,
        now=datetime.now(UTC) - timedelta(minutes=16),
    )
    foreign_settings = SETTINGS.model_copy(
        update={"jwt_secret_key": SETTINGS.jwt_secret_key.__class__("b" * 64)}
    )
    foreign = create_access_token(user_id=1, settings=foreign_settings)

    with pytest.raises(InvalidTokenError):
        decode_access_token(expired, SETTINGS)
    with pytest.raises(InvalidTokenError):
        decode_access_token(foreign, SETTINGS)


@pytest.mark.parametrize(
    ("change", "typ"),
    [
        ({"iss": "urn:other"}, ACCESS_TOKEN_HEADER_TYPE),
        ({"aud": "other-api"}, ACCESS_TOKEN_HEADER_TYPE),
        ({"sub": "01"}, ACCESS_TOKEN_HEADER_TYPE),
        ({"sub": "user-1"}, ACCESS_TOKEN_HEADER_TYPE),
        ({"jti": "not-a-uuid"}, ACCESS_TOKEN_HEADER_TYPE),
        ({"token_type": "refresh"}, ACCESS_TOKEN_HEADER_TYPE),
        ({}, "JWT"),
    ],
)
def test_rejects_wrong_context_or_malformed_claims(
    change: dict[str, object], typ: str
) -> None:
    token = create_access_token(user_id=1, settings=SETTINGS)
    claims = {**unsigned_claims(token), **change}

    with pytest.raises(InvalidTokenError):
        decode_access_token(resign(claims, typ=typ), SETTINGS)


def test_rejects_missing_claim_and_algorithm_substitution() -> None:
    token = create_access_token(user_id=1, settings=SETTINGS)
    claims = unsigned_claims(token)
    claims.pop("exp")
    missing = resign(claims)
    wrong_algorithm = jwt.encode(
        unsigned_claims(token),
        SETTINGS.jwt_secret_key.get_secret_value(),
        algorithm="HS384",
        headers={"typ": ACCESS_TOKEN_HEADER_TYPE},
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(missing, SETTINGS)
    with pytest.raises(InvalidTokenError):
        decode_access_token(wrong_algorithm, SETTINGS)
