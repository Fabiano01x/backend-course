"""Superfície explícita para clientes de máquina."""

from fastapi import APIRouter
from sqlalchemy import select

from app.database import DatabaseSession
from app.dependencies import BooksReadClient, LoansReadClient
from app.models import Book
from app.repositories.loans import LoanRepository
from app.routers.books import availability_expression, to_book_response
from app.routers.loans import to_loan_detail_response
from app.schemas import BookResponse, ErrorResponse, LoanDetailResponse


router = APIRouter(prefix="/integrations", tags=["Integrações"])


@router.get(
    "/books",
    response_model=list[BookResponse],
    operation_id="exportBooksForIntegration",
    summary="Exportar o acervo para uma integração",
    description="Exige uma chave de API atual com o escopo books:read.",
    response_description="Livros do acervo em ordem de identificador.",
    responses={
        401: {"model": ErrorResponse, "description": "Chave de API inválida."},
        403: {"model": ErrorResponse, "description": "Escopo books:read ausente."},
    },
)
async def export_books(
    session: DatabaseSession, _client: BooksReadClient
) -> list[BookResponse]:
    statement = select(
        Book, availability_expression().label("available")
    ).order_by(Book.id)
    rows = (await session.execute(statement)).all()
    return [
        to_book_response(book, available=bool(is_available))
        for book, is_available in rows
    ]


@router.get(
    "/loans",
    response_model=list[LoanDetailResponse],
    operation_id="exportLoansForIntegration",
    summary="Exportar empréstimos para uma integração",
    description="Exige uma chave de API atual com o escopo loans:read.",
    response_description="Empréstimos enriquecidos em ordem de criação.",
    responses={
        401: {"model": ErrorResponse, "description": "Chave de API inválida."},
        403: {"model": ErrorResponse, "description": "Escopo loans:read ausente."},
    },
)
async def export_loans(
    session: DatabaseSession, _client: LoansReadClient
) -> list[LoanDetailResponse]:
    loans = await LoanRepository(session).list_all_with_details()
    return [to_loan_detail_response(loan) for loan in loans]
