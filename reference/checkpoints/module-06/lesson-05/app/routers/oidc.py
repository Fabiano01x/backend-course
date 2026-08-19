"""Authorization Code OIDC e criação da sessão local."""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import Settings
from app.database import DatabaseSession
from app.dependencies import AppSettings, OidcProviderDependency
from app.integrations.oidc import OidcProviderError
from app.schemas import ErrorResponse, TokenResponse
from app.security.cookies import set_refresh_cookie
from app.security.oidc import (
    OIDC_ATTEMPT_COOKIE,
    clear_oidc_attempt_cookie,
    set_oidc_attempt_cookie,
)
from app.security.tokens import create_access_token
from app.services.oidc import (
    OidcFlowError,
    consume_oidc_attempt,
    resolve_external_identity,
    start_oidc_attempt,
)
from app.services.sessions import start_refresh_session


router = APIRouter(prefix="/auth/oidc", tags=["Autenticação"])


def oidc_error_response(
    status_code: int, detail: str, settings: Settings
) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content={"detail": detail})
    clear_oidc_attempt_cookie(response, settings)
    return response


@router.get(
    "/login",
    response_model=None,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    operation_id="startOpenIdConnectLogin",
    summary="Iniciar login com o provedor OpenID Connect",
    description=(
        "Cria state, nonce e PKCE S256 vinculados ao navegador e redireciona "
        "para o authorization endpoint descoberto no issuer configurado."
    ),
    responses={
        307: {"description": "Redirecionamento para o provedor."},
        502: {"model": ErrorResponse, "description": "Provedor indisponível."},
        503: {"model": ErrorResponse, "description": "OIDC não configurado."},
    },
)
async def start_openid_connect_login(
    session: DatabaseSession,
    settings: AppSettings,
    provider: OidcProviderDependency,
) -> RedirectResponse | JSONResponse:
    secrets_ = await start_oidc_attempt(
        session, settings, issuer=settings.oidc_issuer or ""
    )
    try:
        authorization_url = await provider.authorization_url(
            state=secrets_.state,
            nonce=secrets_.nonce,
            code_challenge=secrets_.code_challenge,
        )
    except OidcProviderError:
        return oidc_error_response(
            status.HTTP_502_BAD_GATEWAY,
            "Provedor OpenID Connect indisponível",
            settings,
        )
    response = RedirectResponse(
        authorization_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
    set_oidc_attempt_cookie(response, secrets_, settings)
    return response


@router.get(
    "/callback",
    response_model=TokenResponse,
    operation_id="completeOpenIdConnectLogin",
    summary="Concluir login OpenID Connect",
    description=(
        "Consome a tentativa vinculada ao navegador, troca o code com PKCE, "
        "valida o ID Token e cria uma sessão local."
    ),
    response_description="Access token local e refresh token em cookie.",
    responses={
        400: {"model": ErrorResponse, "description": "Tentativa inválida."},
        401: {"model": ErrorResponse, "description": "ID Token inválido."},
        403: {"model": ErrorResponse, "description": "Conta não utilizável."},
        409: {"model": ErrorResponse, "description": "Vínculo exige ação explícita."},
        502: {"model": ErrorResponse, "description": "Provedor indisponível."},
        503: {"model": ErrorResponse, "description": "OIDC não configurado."},
    },
)
async def complete_openid_connect_login(
    request: Request,
    response: Response,
    session: DatabaseSession,
    settings: AppSettings,
    provider: OidcProviderDependency,
    code: Annotated[str | None, Query(min_length=1, max_length=2048)] = None,
    state: Annotated[str | None, Query(min_length=1, max_length=512)] = None,
    error: Annotated[str | None, Query(max_length=200)] = None,
) -> TokenResponse | JSONResponse:
    if error is not None or code is None or state is None:
        return oidc_error_response(
            status.HTTP_400_BAD_REQUEST,
            "Tentativa OpenID Connect inválida",
            settings,
        )
    try:
        attempt = await consume_oidc_attempt(
            session,
            raw_cookie=request.cookies.get(OIDC_ATTEMPT_COOKIE),
            state=state,
            issuer=settings.oidc_issuer or "",
        )
    except OidcFlowError:
        return oidc_error_response(
            status.HTTP_400_BAD_REQUEST,
            "Tentativa OpenID Connect inválida",
            settings,
        )
    try:
        claims = await provider.exchange_code(
            code=code,
            code_verifier=attempt.code_verifier,
            expected_nonce_digest=attempt.nonce_digest,
        )
    except OidcProviderError as provider_error:
        return oidc_error_response(
            status.HTTP_502_BAD_GATEWAY
            if provider_error.unavailable
            else status.HTTP_401_UNAUTHORIZED,
            "Provedor OpenID Connect indisponível"
            if provider_error.unavailable
            else "Resposta OpenID Connect inválida",
            settings,
        )
    try:
        user_id = await resolve_external_identity(session, claims)
    except OidcFlowError as flow_error:
        error_status = {
            "forbidden": status.HTTP_403_FORBIDDEN,
            "conflict": status.HTTP_409_CONFLICT,
        }.get(flow_error.kind, status.HTTP_400_BAD_REQUEST)
        return oidc_error_response(error_status, flow_error.detail, settings)

    refresh_token = await start_refresh_session(
        session, user_id=user_id, settings=settings
    )
    set_refresh_cookie(
        response,
        refresh_token.value,
        refresh_token.expires_at,
        settings,
    )
    clear_oidc_attempt_cookie(response, settings)
    return TokenResponse(
        access_token=create_access_token(user_id=user_id, settings=settings),
        expires_in=settings.access_token_expire_minutes * 60,
    )
