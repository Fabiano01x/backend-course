"""Operações HTTP do domínio de livros."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from app import data
from app.dependencies import AppSettings
from app.schemas import BookCreate, BookPage, BookResponse


router = APIRouter(prefix="/books", tags=["Livros"])
BookSortField = Literal["id", "title", "author"]
SortOrder = Literal["asc", "desc"]


@router.get("", response_model=BookPage)
async def list_books(
    settings: AppSettings,
    available: Annotated[bool | None, Query(description="Filtra pela disponibilidade do livro.")] = None,
    author: Annotated[str | None, Query(min_length=1, max_length=120, description="Busca parcial por autor.")] = None,
    sort_by: Annotated[BookSortField, Query(description="Campo usado para ordenar os livros.")] = "id",
    order: Annotated[SortOrder, Query(description="Direção da ordenação.")] = "asc",
    limit: Annotated[int | None, Query(ge=1, le=100, description="Itens por página; vazio usa a configuração.")] = None,
    offset: Annotated[int, Query(ge=0, description="Itens ignorados após a ordenação.")] = 0,
) -> BookPage:
    page_limit = settings.default_page_size if limit is None else limit
    if page_limit > settings.max_page_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"limit não pode exceder {settings.max_page_size}",
        )

    filtered_books = list(data.books.values())
    if available is not None:
        filtered_books = [book for book in filtered_books if book.available is available]
    if author is not None:
        normalized_author = author.casefold()
        filtered_books = [book for book in filtered_books if normalized_author in book.author.casefold()]

    sort_keys = {
        "id": lambda book: (book.id,),
        "title": lambda book: (book.title.casefold(), book.id),
        "author": lambda book: (book.author.casefold(), book.id),
    }
    filtered_books.sort(key=sort_keys[sort_by], reverse=order == "desc")
    return BookPage(
        items=filtered_books[offset : offset + page_limit],
        total=len(filtered_books),
        limit=page_limit,
        offset=offset,
    )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int) -> BookResponse:
    book = data.books.get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return book


@router.post("", response_model=BookResponse, status_code=201)
async def create_book(payload: BookCreate) -> BookResponse:
    return data.create_book(payload)
