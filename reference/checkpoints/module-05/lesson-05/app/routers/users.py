"""Operações persistentes do domínio de usuários."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import DatabaseSession
from app.models import User
from app.schemas import ErrorResponse, UserCreate, UserResponse


router = APIRouter(prefix="/users", tags=["Usuários"])


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        active=user.active,
    )


@router.get(
    "",
    response_model=list[UserResponse],
    operation_id="listUsers",
    summary="Listar usuários",
    response_description="Todos os usuários persistidos, ordenados por identificador.",
)
async def list_users(session: DatabaseSession) -> list[UserResponse]:
    result = await session.execute(select(User).order_by(User.id))
    return [to_user_response(user) for user in result.scalars().all()]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    operation_id="getUser",
    summary="Consultar um usuário pelo identificador",
    response_description="O usuário correspondente ao identificador.",
    responses={
        404: {"model": ErrorResponse, "description": "Usuário não encontrado."}
    },
)
async def get_user(user_id: int, session: DatabaseSession) -> UserResponse:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return to_user_response(user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createUser",
    summary="Cadastrar um usuário",
    description="Persiste um novo usuário ativo.",
    response_description="O usuário criado com identificador gerado pelo banco.",
    responses={
        409: {"model": ErrorResponse, "description": "E-mail já cadastrado."}
    },
)
async def create_user(
    payload: UserCreate, session: DatabaseSession
) -> UserResponse:
    user = User(**payload.model_dump())
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        ) from error
    await session.refresh(user)
    return to_user_response(user)
