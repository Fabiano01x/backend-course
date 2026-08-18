"""Cadastro e verificação de credenciais locais."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.database import DatabaseSession
from app.dependencies import AppSettings
from app.models import User
from app.schemas import (
    ErrorResponse,
    LoginRequest,
    RegistrationCreate,
    TokenResponse,
    UserResponse,
)
from app.security.passwords import hash_password
from app.security.tokens import create_access_token
from app.services.auth import authenticate_password, normalize_email


router = APIRouter(prefix="/auth", tags=["Autenticação"])


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        active=user.active,
    )


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
    encoded_password = await run_in_threadpool(
        hash_password, payload.password
    )
    user = User(
        name=payload.name,
        email=normalize_email(payload.email),
        password_hash=encoded_password,
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
    summary="Entrar e emitir um access token",
    description=(
        "Confirma e-mail e senha com erro genérico e emite um JWT curto "
        "para uso no esquema Bearer."
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
    payload: LoginRequest, session: DatabaseSession, settings: AppSettings
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
    token = create_access_token(user_id=user.id, settings=settings)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
