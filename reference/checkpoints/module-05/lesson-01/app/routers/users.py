"""Operações HTTP do domínio de usuários."""

from fastapi import APIRouter, HTTPException, status

from app import data
from app.schemas import ErrorResponse, UserCreate, UserResponse


router = APIRouter(prefix="/users", tags=["Usuários"])


@router.get(
    "",
    response_model=list[UserResponse],
    operation_id="listUsers",
    summary="Listar usuários",
    response_description="Todos os usuários cadastrados no estado temporário.",
)
async def list_users() -> list[UserResponse]:
    return list(data.users.values())


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
async def get_user(user_id: int) -> UserResponse:
    user = data.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createUser",
    summary="Cadastrar um usuário",
    description="Cria um usuário ativo no estado temporário.",
    response_description="O usuário criado com identificador gerado pela API.",
)
async def create_user(payload: UserCreate) -> UserResponse:
    return data.create_user(payload)
