"""Operações HTTP do domínio de livros."""

from fastapi import APIRouter, HTTPException, status

from app import data
from app.schemas import BookCreate, BookResponse


router = APIRouter(prefix="/books", tags=["Livros"])


@router.get("", response_model=list[BookResponse])
async def list_books() -> list[BookResponse]:
    return list(data.books.values())


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int) -> BookResponse:
    book = data.books.get(book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livro não encontrado")
    return book


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(payload: BookCreate) -> BookResponse:
    return data.create_book(payload)

