"""CRUD persistente do domínio de livros."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import ColumnElement

from app.database import DatabaseSession
from app.dependencies import AppSettings
from app.models import Book, Loan
from app.schemas import (
    BookCreate,
    BookPage,
    BookResponse,
    BookUpdate,
    ErrorResponse,
)


router = APIRouter(prefix="/books", tags=["Livros"])
BookSortField = Literal["id", "title", "author"]
SortOrder = Literal["asc", "desc"]


def active_loan_expression() -> ColumnElement[bool]:
    return (
        select(Loan.id)
        .where(Loan.book_id == Book.id, Loan.returned_at.is_(None))
        .exists()
    )


def availability_expression() -> ColumnElement[bool]:
    return ~active_loan_expression()


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_book_queries(
    *,
    available: bool | None,
    author: str | None,
    sort_by: BookSortField,
    order: SortOrder,
    limit: int,
    offset: int,
):
    active_loan = active_loan_expression()
    is_available = ~active_loan
    filters: list[ColumnElement[bool]] = []
    if available is not None:
        filters.append(is_available if available else active_loan)
    if author is not None:
        filters.append(
            Book.author.ilike(f"%{escape_like(author)}%", escape="\\")
        )

    count_statement = select(func.count(Book.id)).where(*filters)
    sort_columns = {
        "id": Book.id,
        "title": func.lower(Book.title),
        "author": func.lower(Book.author),
    }
    direction = desc if order == "desc" else asc
    ordering = [direction(sort_columns[sort_by])]
    if sort_by != "id":
        ordering.append(direction(Book.id))

    page_statement = (
        select(Book, is_available.label("available"))
        .where(*filters)
        .order_by(*ordering)
        .limit(limit)
        .offset(offset)
    )
    return count_statement, page_statement


def to_book_response(book: Book, *, available: bool) -> BookResponse:
    return BookResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        available=available,
    )


async def get_book_row(session: DatabaseSession, book_id: int):
    statement = select(
        Book, availability_expression().label("available")
    ).where(Book.id == book_id)
    return (await session.execute(statement)).one_or_none()


async def commit_or_conflict(
    session: DatabaseSession, *, detail: str
) -> None:
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=detail
        ) from error


@router.get(
    "",
    response_model=BookPage,
    operation_id="listBooks",
    summary="Listar livros",
    description="Filtra, ordena e pagina o acervo persistido no PostgreSQL.",
    response_description="Uma página de livros e o total após os filtros.",
)
async def list_books(
    settings: AppSettings,
    session: DatabaseSession,
    available: Annotated[
        bool | None, Query(description="Filtra pela disponibilidade do livro.")
    ] = None,
    author: Annotated[
        str | None,
        Query(min_length=1, max_length=120, description="Busca parcial por autor."),
    ] = None,
    sort_by: Annotated[
        BookSortField, Query(description="Campo usado para ordenar os livros.")
    ] = "id",
    order: Annotated[
        SortOrder, Query(description="Direção da ordenação.")
    ] = "asc",
    limit: Annotated[
        int | None,
        Query(ge=1, le=100, description="Itens por página; vazio usa a configuração."),
    ] = None,
    offset: Annotated[
        int, Query(ge=0, description="Itens ignorados após a ordenação.")
    ] = 0,
) -> BookPage:
    page_limit = settings.default_page_size if limit is None else limit
    if page_limit > settings.max_page_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"limit não pode exceder {settings.max_page_size}",
        )

    count_statement, page_statement = build_book_queries(
        available=available,
        author=author,
        sort_by=sort_by,
        order=order,
        limit=page_limit,
        offset=offset,
    )
    total = await session.scalar(count_statement) or 0
    rows = (await session.execute(page_statement)).all()
    return BookPage(
        items=[
            to_book_response(book, available=bool(is_available))
            for book, is_available in rows
        ],
        total=total,
        limit=page_limit,
        offset=offset,
    )


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    operation_id="getBook",
    summary="Consultar um livro pelo identificador",
    response_description="O livro correspondente ao identificador.",
    responses={
        404: {"model": ErrorResponse, "description": "Livro não encontrado."}
    },
)
async def get_book(book_id: int, session: DatabaseSession) -> BookResponse:
    row = await get_book_row(session, book_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    book, is_available = row
    return to_book_response(book, available=bool(is_available))


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createBook",
    summary="Cadastrar um livro",
    description="Persiste um novo livro, inicialmente disponível no acervo.",
    response_description="O livro criado com identificador gerado pelo banco.",
    responses={
        409: {"model": ErrorResponse, "description": "ISBN já cadastrado."}
    },
)
async def create_book(
    payload: BookCreate, session: DatabaseSession
) -> BookResponse:
    book = Book(**payload.model_dump())
    session.add(book)
    await commit_or_conflict(session, detail="ISBN já cadastrado")
    await session.refresh(book)
    return to_book_response(book, available=True)


@router.put(
    "/{book_id}",
    response_model=BookResponse,
    operation_id="replaceBook",
    summary="Substituir os dados de um livro",
    description="Substitui título, autor e ISBN; disponibilidade continua derivada.",
    response_description="O livro atualizado.",
    responses={
        404: {"model": ErrorResponse, "description": "Livro não encontrado."},
        409: {"model": ErrorResponse, "description": "ISBN já cadastrado."},
    },
)
async def replace_book(
    book_id: int, payload: BookUpdate, session: DatabaseSession
) -> BookResponse:
    row = await get_book_row(session, book_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    book, is_available = row
    for field, value in payload.model_dump().items():
        setattr(book, field, value)

    await commit_or_conflict(session, detail="ISBN já cadastrado")
    await session.refresh(book)
    return to_book_response(book, available=bool(is_available))


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteBook",
    summary="Remover um livro",
    description="Remove um livro sem histórico de empréstimos.",
    responses={
        404: {"model": ErrorResponse, "description": "Livro não encontrado."},
        409: {
            "model": ErrorResponse,
            "description": "Livro possui histórico e não pode ser removido.",
        },
    },
)
async def delete_book(book_id: int, session: DatabaseSession) -> Response:
    book = await session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")

    await session.delete(book)
    await commit_or_conflict(
        session, detail="Livro possui histórico de empréstimos"
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
