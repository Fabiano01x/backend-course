"""Cadastro e verificação de credenciais locais."""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.database import DatabaseSession
from app.models import User
from app.schemas import (
    ErrorResponse,
    LoginRequest,
    RegistrationCreate,
    UserResponse,
)
from app.security.passwords import hash_password
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
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="verifyLocalCredentials",
    summary="Verificar credenciais locais",
    description=(
        "Confirma e-mail e senha com uma resposta genérica. A próxima aula "
        "trocará o sucesso vazio pela emissão de um access token."
    ),
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Credenciais ausentes ou inválidas.",
        }
    },
)
async def verify_local_credentials(
    payload: LoginRequest, session: DatabaseSession
) -> Response:
    user = await authenticate_password(
        session, email=payload.email, password=payload.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
