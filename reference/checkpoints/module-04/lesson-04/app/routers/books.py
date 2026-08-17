"""Operações HTTP do domínio de livros."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from app import data
from app.schemas import BookCreate, BookPage, BookResponse


router = APIRouter(prefix="/books", tags=["Livros"])

BookSortField = Literal["id", "title", "author"]
SortOrder = Literal["asc", "desc"]


@router.get("", response_model=BookPage)
async def list_books(
    available: Annotated[
        bool | None,
        Query(description="Filtra pela disponibilidade do livro."),
    ] = None,
    author: Annotated[
        str | None,
        Query(min_length=1, max_length=120, description="Busca parcial por autor."),
    ] = None,
    sort_by: Annotated[
        BookSortField,
        Query(description="Campo usado para ordenar os livros."),
    ] = "id",
    order: Annotated[
        SortOrder,
        Query(description="Direção da ordenação."),
    ] = "asc",
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Quantidade máxima de itens na página."),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Quantidade de itens ignorados após a ordenação."),
    ] = 0,
) -> BookPage:
    filtered_books = list(data.books.values())

    if available is not None:
        filtered_books = [book for book in filtered_books if book.available is available]

    if author is not None:
        normalized_author = author.casefold()
        filtered_books = [
            book for book in filtered_books if normalized_author in book.author.casefold()
        ]

    sort_keys = {
        "id": lambda book: (book.id,),
        "title": lambda book: (book.title.casefold(), book.id),
        "author": lambda book: (book.author.casefold(), book.id),
    }
    filtered_books.sort(key=sort_keys[sort_by], reverse=order == "desc")

    return BookPage(
        items=filtered_books[offset : offset + limit],
        total=len(filtered_books),
        limit=limit,
        offset=offset,
    )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int) -> BookResponse:
    book = data.books.get(book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livro não encontrado")
    return book


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(payload: BookCreate) -> BookResponse:
    return data.create_book(payload)
