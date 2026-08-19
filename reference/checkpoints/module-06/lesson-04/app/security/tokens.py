"""Emissão e validação estrita dos access tokens da Library API."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError

from app.config import Settings


ACCESS_TOKEN_ALGORITHM = "HS256"
ACCESS_TOKEN_HEADER_TYPE = "at+jwt"
ACCESS_TOKEN_CLAIMS = (
    "iss",
    "aud",
    "sub",
    "iat",
    "nbf",
    "exp",
    "jti",
    "token_type",
)


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: int
    token_id: UUID
    expires_at: datetime


def create_access_token(
    *,
    user_id: int,
    settings: Settings,
    now: datetime | None = None,
    token_id: UUID | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    claims = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": str(user_id),
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
        "jti": str(token_id or uuid4()),
        "token_type": "access",
    }
    return jwt.encode(
        claims,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=ACCESS_TOKEN_ALGORITHM,
        headers={"typ": ACCESS_TOKEN_HEADER_TYPE},
    )


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    header = jwt.get_unverified_header(token)
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[ACCESS_TOKEN_ALGORITHM],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": list(ACCESS_TOKEN_CLAIMS), "strict_aud": True},
    )
    if header.get("typ") != ACCESS_TOKEN_HEADER_TYPE:
        raise InvalidTokenError("tipo de cabeçalho inválido")
    if claims.get("token_type") != "access":
        raise InvalidTokenError("tipo de token inválido")

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.isdecimal():
        raise InvalidTokenError("subject inválido")
    user_id = int(subject)
    if user_id <= 0 or str(user_id) != subject:
        raise InvalidTokenError("subject inválido")

    numeric_dates = (claims.get("iat"), claims.get("nbf"), claims.get("exp"))
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in numeric_dates
    ):
        raise InvalidTokenError("data numérica inválida")

    token_identifier = claims.get("jti")
    if not isinstance(token_identifier, str):
        raise InvalidTokenError("jti inválido")
    try:
        parsed_token_id = UUID(token_identifier)
    except ValueError as error:
        raise InvalidTokenError("jti inválido") from error

    return AccessTokenClaims(
        user_id=user_id,
        token_id=parsed_token_id,
        expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
    )
