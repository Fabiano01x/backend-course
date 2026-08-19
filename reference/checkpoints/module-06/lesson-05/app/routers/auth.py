"""Cadastro, login e ciclo de sessões renováveis."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.authorization import MEMBER_ROLE
from app.config import Settings
from app.database import DatabaseSession
from app.dependencies import AppSettings
from app.models import User, UserRole
from app.schemas import (
    ErrorResponse,
    LoginRequest,
    RegistrationCreate,
    TokenResponse,
    UserResponse,
)
from app.security.cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from app.security.csrf import CsrfProtection
from app.security.passwords import hash_password
from app.security.tokens import create_access_token
from app.security.workers import run_password_operation
from app.services.auth import authenticate_password, normalize_email
from app.services.sessions import (
    RotationStatus,
    revoke_refresh_family,
    rotate_refresh_session,
    start_refresh_session,
)


router = APIRouter(prefix="/auth", tags=["Autenticação"])


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        active=user.active,
    )


def build_token_response(user_id: int, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id=user_id, settings=settings),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def invalid_refresh_response(settings: Settings) -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Sessão renovável inválida"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    clear_refresh_cookie(response, settings)
    return response


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="registerLocalUser",
    summary="Cadastrar uma identidade local",
    description=(
        "Cria um usuário com hash Argon2id; a senha original nunca é "
        "persistida nem devolvida."
    ),
    response_description="O usuário criado, sem dados de credencial.",
    responses={
        409: {
            "model": ErrorResponse,
            "description": "Cadastro não pôde ser concluído.",
        }
    },
)
async def register_local_user(
    payload: RegistrationCreate, session: DatabaseSession
) -> UserResponse:
    encoded_password = await run_password_operation(
        hash_password, payload.password
    )
    user = User(
        name=payload.name,
        email=normalize_email(payload.email),
        password_hash=encoded_password,
        role_assignments=[UserRole(role_name=MEMBER_ROLE)],
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível cadastrar usuário",
        ) from error
    await session.refresh(user)
    return to_user_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    operation_id="loginForAccessToken",
    summary="Entrar e iniciar uma sessão renovável",
    description=(
        "Confirma e-mail e senha, emite um access token e entrega o refresh "
        "token opaco somente em cookie HttpOnly."
    ),
    response_description="Access token curto e seu tempo de validade.",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Credenciais ausentes ou inválidas.",
        }
    },
)
async def verify_local_credentials(
    payload: LoginRequest,
    response: Response,
    session: DatabaseSession,
    settings: AppSettings,
) -> TokenResponse:
    user = await authenticate_password(
        session, email=payload.email, password=payload.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    refresh_token = await start_refresh_session(
        session, user_id=user.id, settings=settings
    )
    set_refresh_cookie(
        response,
        refresh_token.value,
        refresh_token.expires_at,
        settings,
    )
    return build_token_response(user.id, settings)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    operation_id="rotateRefreshToken",
    summary="Rotacionar a sessão renovável",
    description=(
        "Consome uma vez o refresh token do cookie, emite um substituto na "
        "mesma família e devolve um novo access token."
    ),
    response_description="Novo access token; o refresh substituto fica no cookie.",
    responses={
        401: {"model": ErrorResponse, "description": "Sessão inválida."},
        403: {"model": ErrorResponse, "description": "Defesa CSRF recusou a origem."},
    },
)
async def refresh_access_token(
    request: Request,
    response: Response,
    session: DatabaseSession,
    settings: AppSettings,
    _csrf: CsrfProtection,
) -> TokenResponse | JSONResponse:
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token is None:
        return invalid_refresh_response(settings)
    result = await rotate_refresh_session(session, raw_token)
    if (
        result.status is not RotationStatus.ROTATED
        or result.user_id is None
        or result.refresh_token is None
        or result.expires_at is None
    ):
        return invalid_refresh_response(settings)
    set_refresh_cookie(
        response,
        result.refresh_token,
        result.expires_at,
        settings,
    )
    return build_token_response(result.user_id, settings)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="logoutRefreshSession",
    summary="Encerrar a família da sessão",
    description=(
        "Revoga a família identificada pelo cookie e sempre remove o cookie "
        "do navegador."
    ),
    responses={
        403: {"model": ErrorResponse, "description": "Defesa CSRF recusou a origem."}
    },
)
async def logout_refresh_session(
    request: Request,
    session: DatabaseSession,
    settings: AppSettings,
    _csrf: CsrfProtection,
) -> Response:
    await revoke_refresh_family(
        session, request.cookies.get(REFRESH_COOKIE_NAME)
    )
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_refresh_cookie(response, settings)
    return response
