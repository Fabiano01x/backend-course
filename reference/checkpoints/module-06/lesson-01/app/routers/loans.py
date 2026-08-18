"""Rotas do ciclo transacional de empréstimos."""

from fastapi import APIRouter, HTTPException, status

from app.database import DatabaseSession
from app.models import Loan
from app.repositories.loans import LoanRepository
from app.schemas import (
    ErrorResponse,
    LoanBookSummary,
    LoanCreate,
    LoanDetailResponse,
    LoanResponse,
    LoanUserSummary,
)
from app.services.loans import LoanRuleError, borrow_book, return_book


router = APIRouter(prefix="/loans", tags=["Empréstimos"])


def to_loan_response(loan: Loan) -> LoanResponse:
    return LoanResponse(
        id=loan.id,
        user_id=loan.user_id,
        book_id=loan.book_id,
        borrowed_at=loan.borrowed_at,
        due_at=loan.due_at,
        returned_at=loan.returned_at,
    )


def to_loan_detail_response(loan: Loan) -> LoanDetailResponse:
    return LoanDetailResponse(
        **to_loan_response(loan).model_dump(),
        user=LoanUserSummary(id=loan.user.id, name=loan.user.name),
        book=LoanBookSummary(
            id=loan.book.id,
            title=loan.book.title,
            author=loan.book.author,
        ),
    )


def translate_rule_error(error: LoanRuleError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if error.not_found
        else status.HTTP_409_CONFLICT
    )
    return HTTPException(status_code=code, detail=error.detail)


@router.get(
    "",
    response_model=list[LoanDetailResponse],
    operation_id="listLoans",
    summary="Listar o histórico de empréstimos",
    description=(
        "Lista o histórico com usuário e livro carregados explicitamente "
        "em uma única consulta."
    ),
    response_description="Empréstimos enriquecidos em ordem de criação.",
)
async def list_loans(session: DatabaseSession) -> list[LoanDetailResponse]:
    loans = await LoanRepository(session).list_all_with_details()
    return [to_loan_detail_response(loan) for loan in loans]


@router.post(
    "",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="borrowBook",
    summary="Emprestar um livro",
    description="Valida as regras e registra o empréstimo em uma transação.",
    response_description="O empréstimo confirmado.",
    responses={
        404: {"model": ErrorResponse, "description": "Usuário ou livro ausente."},
        409: {"model": ErrorResponse, "description": "Regra de empréstimo violada."},
    },
)
async def create_loan(
    payload: LoanCreate, session: DatabaseSession
) -> LoanResponse:
    try:
        loan = await borrow_book(session, payload)
    except LoanRuleError as error:
        raise translate_rule_error(error) from error
    return to_loan_response(loan)


@router.post(
    "/{loan_id}/return",
    response_model=LoanResponse,
    operation_id="returnBook",
    summary="Registrar a devolução",
    description="Encerra um empréstimo ativo em uma transação.",
    response_description="O empréstimo com a data de devolução.",
    responses={
        404: {"model": ErrorResponse, "description": "Empréstimo ausente."},
        409: {"model": ErrorResponse, "description": "Empréstimo já devolvido."},
    },
)
async def finish_loan(loan_id: int, session: DatabaseSession) -> LoanResponse:
    try:
        loan = await return_book(session, loan_id)
    except LoanRuleError as error:
        raise translate_rule_error(error) from error
    return to_loan_response(loan)
