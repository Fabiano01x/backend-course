"""Estado temporário em memória; será substituído no módulo de banco"""

from itertools import count
from schemas import BookCreate, BookResponse, UserCreate, UserResponse

books: dict[int, BookResponse]
users: dict[int, UserResponse]
_book_ids: count
_user_ids: count

def reset_data() -> None:
    global books, users, _book_ids, _user_ids
    books = {
        1: BookResponse(
            id=1,
            title="Clean Architecture",
            author="Robert C. Martins",
            isbn="9780134494166",
            available=True,
        )
    }
    users = {
        1:UserResponse(
            id=1,
            name="Ada Lovelace",
            email="ada@example.com",
            active=True
        )
    }
    _book_ids = count(2)
    _user_ids = count(2)

def create_book(payload: BookCreate) -> BookResponse:
    book = BookResponse(id=next(_book_ids), available=True, **payload.model_dump())
    books[book.id] = book
    return book

def create_user(payload: UserCreate) -> UserResponse:
    user = UserResponse(id=next(_user_ids), active=True, **payload.model_dump())
    users[user.id] = user
    return user

reset_data()


