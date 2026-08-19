"""Provedores injetáveis da Library API."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
import httpx
from jwt import InvalidTokenError

from app.authorization import LIBRARIAN_ROLE
from app.config import Settings
from app.database import DatabaseSession
from app.integrations.oidc import HttpOidcProvider, OidcProvider
from app.repositories.authorization import AuthorizationRepository, Principal
from app.services.api_keys import ApiClientPrincipal, authenticate_api_key
from app.security.tokens import decode_access_token


@lru_cache
def load_settings() -> Settings:
    return Settings()


async def get_settings() -> Settings:
    return load_settings()


AppSettings = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    user_id: int


access_token_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="AccessToken",
    bearerFormat="JWT",
    description="Access token JWT emitido por POST /auth/login.",
)


def invalid_access_credential() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credencial de acesso inválida",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_identity(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(access_token_bearer)
    ],
    settings: AppSettings,
) -> AuthenticatedIdentity:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise invalid_access_credential()
    try:
        claims = decode_access_token(credentials.credentials, settings)
    except InvalidTokenError as error:
        raise invalid_access_credential() from error
    return AuthenticatedIdentity(user_id=claims.user_id)


CurrentIdentity = Annotated[AuthenticatedIdentity, Depends(get_current_identity)]


async def get_current_principal(
    identity: CurrentIdentity, session: DatabaseSession
) -> Principal:
    principal = await AuthorizationRepository(session).find_active_principal(
        identity.user_id
    )
    if principal is None:
        raise invalid_access_credential()
    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


def insufficient_permission() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permissão insuficiente",
    )


async def require_librarian(principal: CurrentPrincipal) -> Principal:
    if not principal.has_role(LIBRARIAN_ROLE):
        raise insufficient_permission()
    return principal


LibrarianPrincipal = Annotated[Principal, Depends(require_librarian)]


async def get_oidc_provider(settings: AppSettings) -> AsyncIterator[OidcProvider]:
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenID Connect não configurado",
        )
    async with httpx.AsyncClient(
        timeout=5.0, follow_redirects=False
    ) as client:
        yield HttpOidcProvider(settings, client)


OidcProviderDependency = Annotated[OidcProvider, Depends(get_oidc_provider)]


api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    scheme_name="MachineApiKey",
    description="Credencial opaca emitida para um cliente de máquina.",
)


def invalid_api_key() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Chave de API inválida",
        headers={"WWW-Authenticate": "ApiKey"},
    )


async def get_current_api_client(
    raw_api_key: Annotated[str | None, Depends(api_key_header)],
    session: DatabaseSession,
) -> ApiClientPrincipal:
    if raw_api_key is None:
        raise invalid_api_key()
    principal = await authenticate_api_key(session, raw_api_key)
    if principal is None:
        raise invalid_api_key()
    return principal


CurrentApiClient = Annotated[
    ApiClientPrincipal, Depends(get_current_api_client)
]


def require_api_scope(scope: str):
    async def dependency(principal: CurrentApiClient) -> ApiClientPrincipal:
        if not principal.has_scope(scope):
            raise insufficient_permission()
        return principal

    return dependency


BooksReadClient = Annotated[
    ApiClientPrincipal, Depends(require_api_scope("books:read"))
]
LoansReadClient = Annotated[
    ApiClientPrincipal, Depends(require_api_scope("loans:read"))
]
