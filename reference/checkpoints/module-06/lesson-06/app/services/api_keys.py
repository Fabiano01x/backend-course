"""Regras de emissão, autenticação, rotação e revogação de API keys."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiClient, ApiKey
from app.repositories.api_keys import ApiKeyRepository
from app.security.api_keys import (
    api_key_prefix,
    generate_api_key,
    matches_api_key,
)


DUMMY_DIGEST = "0" * 64
SUPPORTED_API_SCOPES = frozenset({"books:read", "loans:read"})


@dataclass(frozen=True, slots=True)
class ApiClientPrincipal:
    client_id: UUID
    key_id: UUID
    name: str
    scopes: frozenset[str]

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


@dataclass(frozen=True, slots=True)
class IssuedApiKey:
    key: ApiKey
    raw: str


class ApiKeyRuleError(Exception):
    def __init__(
        self,
        detail: str,
        *,
        not_found: bool = False,
        conflict: bool = False,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.not_found = not_found
        self.conflict = conflict


def utc_now() -> datetime:
    return datetime.now(UTC)


def validate_expiration(expires_at: datetime | None, now: datetime) -> None:
    if expires_at is None:
        return
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise ApiKeyRuleError(
            "A expiração precisa informar fuso horário", conflict=True
        )
    if expires_at <= now:
        raise ApiKeyRuleError("A expiração precisa estar no futuro", conflict=True)


def build_key(
    *,
    client_id: UUID,
    scopes: set[str] | frozenset[str],
    expires_at: datetime | None,
    created_at: datetime,
) -> IssuedApiKey:
    unsupported = set(scopes) - SUPPORTED_API_SCOPES
    if unsupported or not scopes:
        raise ApiKeyRuleError("Escopos de API inválidos", conflict=True)
    generated = generate_api_key()
    key = ApiKey(
        id=uuid4(),
        client_id=client_id,
        prefix=generated.prefix,
        secret_digest=generated.digest,
        scopes=sorted(scopes),
        created_at=created_at,
        expires_at=expires_at,
    )
    return IssuedApiKey(key=key, raw=generated.raw)


async def create_api_client(session: AsyncSession, name: str) -> ApiClient:
    repository = ApiKeyRepository(session)
    normalized_name = name.strip()
    try:
        if await repository.find_client_by_name(normalized_name) is not None:
            raise ApiKeyRuleError("Cliente de API já cadastrado", conflict=True)
        client = ApiClient(
            id=uuid4(), name=normalized_name, created_at=utc_now()
        )
        repository.add_client(client)
        await repository.flush()
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise ApiKeyRuleError(
            "Cliente de API já cadastrado", conflict=True
        ) from error
    except Exception:
        await session.rollback()
        raise
    return client


async def issue_api_key(
    session: AsyncSession,
    *,
    client_id: UUID,
    scopes: set[str],
    expires_at: datetime | None,
) -> IssuedApiKey:
    repository = ApiKeyRepository(session)
    now = utc_now()
    validate_expiration(expires_at, now)
    try:
        client = await repository.lock_client(client_id)
        if client is None:
            raise ApiKeyRuleError("Cliente de API não encontrado", not_found=True)
        if not client.active:
            raise ApiKeyRuleError("Cliente de API inativo", conflict=True)
        issued = build_key(
            client_id=client.id,
            scopes=scopes,
            expires_at=expires_at,
            created_at=now,
        )
        repository.add_key(issued.key)
        await repository.flush()
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return issued


async def authenticate_api_key(
    session: AsyncSession, raw: str, *, now: datetime | None = None
) -> ApiClientPrincipal | None:
    checked_at = now or utc_now()
    prefix = api_key_prefix(raw)
    repository = ApiKeyRepository(session)
    async with session.begin():
        key = await repository.lock_key_by_prefix(prefix) if prefix else None
        expected = key.secret_digest if key is not None else DUMMY_DIGEST
        digest_matches = matches_api_key(raw, expected)
        if (
            key is None
            or not digest_matches
            or not key.client.active
            or key.revoked_at is not None
            or (key.expires_at is not None and key.expires_at <= checked_at)
        ):
            return None
        key.last_used_at = checked_at
        return ApiClientPrincipal(
            client_id=key.client_id,
            key_id=key.id,
            name=key.client.name,
            scopes=frozenset(key.scopes),
        )


async def rotate_api_key(
    session: AsyncSession,
    *,
    key_id: UUID,
    expires_at: datetime | None,
) -> IssuedApiKey:
    repository = ApiKeyRepository(session)
    now = utc_now()
    validate_expiration(expires_at, now)
    try:
        previous = await repository.lock_key(key_id)
        if previous is None:
            raise ApiKeyRuleError("Chave de API não encontrada", not_found=True)
        if previous.revoked_at is not None:
            raise ApiKeyRuleError("Chave de API já revogada", conflict=True)
        if not previous.client.active:
            raise ApiKeyRuleError("Cliente de API inativo", conflict=True)
        issued = build_key(
            client_id=previous.client_id,
            scopes=frozenset(previous.scopes),
            expires_at=expires_at,
            created_at=now,
        )
        repository.add_key(issued.key)
        await repository.flush()
        previous.revoked_at = now
        previous.replaced_by_id = issued.key.id
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return issued


async def revoke_api_key(session: AsyncSession, key_id: UUID) -> None:
    repository = ApiKeyRepository(session)
    try:
        key = await repository.lock_key(key_id)
        if key is None:
            raise ApiKeyRuleError("Chave de API não encontrada", not_found=True)
        if key.revoked_at is None:
            key.revoked_at = utc_now()
        await session.commit()
    except Exception:
        await session.rollback()
        raise
