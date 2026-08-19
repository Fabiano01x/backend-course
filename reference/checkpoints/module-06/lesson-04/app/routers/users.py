"""Operações persistentes do domínio de usuários."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.authorization import LIBRARIAN_ROLE
from app.database import DatabaseSession
from app.dependencies import (
    CurrentPrincipal,
    LibrarianPrincipal,
    insufficient_permission,
)
from app.models import Loan, User
from app.schemas import (
    ErrorResponse,
    LoanBookSummary,
    UserDetailResponse,
    UserLoanSummary,
    UserResponse,
)


router = APIRouter(prefix="/users", tags=["Usuários"])


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        active=user.active,
    )


def build_user_detail_query(user_id: int):
    return (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.loans).joinedload(Loan.book))
    )


def to_user_detail_response(user: User) -> UserDetailResponse:
    return UserDetailResponse(
        **to_user_response(user).model_dump(),
        loans=[
            UserLoanSummary(
                id=loan.id,
                borrowed_at=loan.borrowed_at,
                due_at=loan.due_at,
                returned_at=loan.returned_at,
                book=LoanBookSummary(
                    id=loan.book.id,
                    title=loan.book.title,
                    author=loan.book.author,
                ),
            )
            for loan in user.loans
        ],
    )


@router.get(
    "",
    response_model=list[UserResponse],
    operation_id="listUsers",
    summary="Listar usuários",
    response_description="Todos os usuários persistidos, ordenados por identificador.",
    responses={
        401: {"model": ErrorResponse, "description": "Access token inválido."},
        403: {"model": ErrorResponse, "description": "Papel librarian ausente."},
    },
)
async def list_users(
    session: DatabaseSession, _librarian: LibrarianPrincipal
) -> list[UserResponse]:
    result = await session.execute(select(User).order_by(User.id))
    return [to_user_response(user) for user in result.scalars().all()]


@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
    operation_id="getUser",
    summary="Consultar um usuário pelo identificador",
    description=(
        "Carrega a coleção de empréstimos em uma segunda consulta previsível "
        "e inclui os livros relacionados."
    ),
    response_description="O usuário e seu histórico de empréstimos.",
    responses={
        401: {"model": ErrorResponse, "description": "Access token inválido."},
        403: {
            "model": ErrorResponse,
            "description": "Acesso a outro usuário sem papel librarian.",
        },
        404: {"model": ErrorResponse, "description": "Usuário não encontrado."},
    },
)
async def get_user(
    user_id: int,
    session: DatabaseSession,
    principal: CurrentPrincipal,
) -> UserDetailResponse:
    if user_id != principal.user_id and not principal.has_role(LIBRARIAN_ROLE):
        raise insufficient_permission()
    result = await session.execute(build_user_detail_query(user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return to_user_detail_response(user)
