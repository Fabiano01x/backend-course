"""Orquestra tentativas OIDC curtas e vínculo estável de identidades."""

from dataclasses import dataclass
from datetime import UTC, datetime
import hmac
import re
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorization import MEMBER_ROLE
from app.config import Settings
from app.integrations.oidc import OidcClaims
from app.models import ExternalIdentity, OidcLoginAttempt, User, UserRole
from app.repositories.oidc import OidcRepository
from app.security.oidc import (
    OidcAttemptSecrets,
    digest_secret,
    new_oidc_attempt,
    parse_attempt_cookie,
)
from app.services.auth import normalize_email


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class OidcFlowError(Exception):
    def __init__(self, detail: str, *, kind: str = "invalid") -> None:
        super().__init__(detail)
        self.detail = detail
        self.kind = kind


@dataclass(frozen=True, slots=True)
class ConsumedOidcAttempt:
    code_verifier: str
    nonce_digest: str


async def start_oidc_attempt(
    session: AsyncSession,
    settings: Settings,
    *,
    issuer: str,
    now: datetime | None = None,
) -> OidcAttemptSecrets:
    created_at = now or datetime.now(UTC)
    secrets_ = new_oidc_attempt(settings, now=created_at)
    session.add(
        OidcLoginAttempt(
            id=uuid4(),
            issuer=issuer,
            browser_digest=digest_secret(secrets_.browser_secret),
            state_digest=digest_secret(secrets_.state),
            nonce_digest=digest_secret(secrets_.nonce),
            verifier_digest=digest_secret(secrets_.code_verifier),
            created_at=created_at,
            expires_at=secrets_.expires_at,
        )
    )
    await session.commit()
    return secrets_


async def consume_oidc_attempt(
    session: AsyncSession,
    *,
    raw_cookie: str | None,
    state: str,
    issuer: str,
    now: datetime | None = None,
) -> ConsumedOidcAttempt:
    parsed_cookie = parse_attempt_cookie(raw_cookie)
    if parsed_cookie is None:
        raise OidcFlowError("Tentativa OpenID Connect inválida")
    browser_secret, code_verifier = parsed_cookie
    current_time = now or datetime.now(UTC)
    repository = OidcRepository(session)
    async with session.begin():
        attempt = await repository.lock_attempt(
            browser_digest=digest_secret(browser_secret),
            state_digest=digest_secret(state),
        )
        if (
            attempt is None
            or attempt.issuer != issuer
            or attempt.used_at is not None
            or attempt.expires_at <= current_time
            or not hmac.compare_digest(
                attempt.verifier_digest, digest_secret(code_verifier)
            )
        ):
            raise OidcFlowError("Tentativa OpenID Connect inválida")
        attempt.used_at = current_time
        await repository.flush()
        return ConsumedOidcAttempt(
            code_verifier=code_verifier,
            nonce_digest=attempt.nonce_digest,
        )


def normalized_external_email(claims: OidcClaims) -> str:
    if claims.email is None or not claims.email_verified:
        raise OidcFlowError(
            "O provedor não confirmou um e-mail utilizável", kind="forbidden"
        )
    email = normalize_email(claims.email)
    if len(email) > 254 or EMAIL_PATTERN.fullmatch(email) is None:
        raise OidcFlowError(
            "O provedor não confirmou um e-mail utilizável", kind="forbidden"
        )
    return email


def external_display_name(claims: OidcClaims, email: str) -> str:
    candidate = (claims.name or email.partition("@")[0]).strip()
    if len(candidate) < 2:
        candidate = "Usuário OIDC"
    return candidate[:120]


async def resolve_external_identity(
    session: AsyncSession,
    claims: OidcClaims,
    *,
    now: datetime | None = None,
) -> int:
    current_time = now or datetime.now(UTC)
    repository = OidcRepository(session)
    try:
        async with session.begin():
            existing = await repository.find_external_identity(
                issuer=claims.issuer, subject=claims.subject
            )
            if existing is not None:
                identity, user = existing
                if not user.active:
                    raise OidcFlowError(
                        "Conta local inativa", kind="forbidden"
                    )
                identity.last_login_at = current_time
                await repository.flush()
                return user.id

            email = normalized_external_email(claims)
            if await repository.find_user_by_email(email) is not None:
                raise OidcFlowError(
                    "E-mail já pertence a uma conta local", kind="conflict"
                )
            user = User(
                name=external_display_name(claims, email),
                email=email,
                password_hash=None,
                role_assignments=[UserRole(role_name=MEMBER_ROLE)],
            )
            identity = ExternalIdentity(
                issuer=claims.issuer,
                subject=claims.subject,
                last_login_at=current_time,
                user=user,
            )
            repository.add(user)
            repository.add(identity)
            await repository.flush()
            return user.id
    except IntegrityError as error:
        raise OidcFlowError(
            "Identidade externa já vinculada", kind="conflict"
        ) from error
