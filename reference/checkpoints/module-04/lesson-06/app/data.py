"""Estado temporário em memória; será substituído no módulo de banco."""

from itertools import count

from app.schemas import BookCreate, BookResponse, UserCreate, UserResponse


books: dict[int, BookResponse]
users: dict[int, UserResponse]
_book_ids: count
_user_ids: count


def reset_data() -> None:
    global books, users, _book_ids, _user_ids
    books = {
        1: BookResponse(id=1, title="Clean Architecture", author="Robert C. Martin", isbn="9780134494166", available=True),
        2: BookResponse(id=2, title="Kindred", author="Octavia E. Butler", isbn="9780807083697", available=True),
        3: BookResponse(id=3, title="Designing Data-Intensive Applications", author="Martin Kleppmann", isbn="9781449373320", available=False),
        4: BookResponse(id=4, title="Fluent Python", author="Luciano Ramalho", isbn="9781492056355", available=True),
    }
    users = {1: UserResponse(id=1, name="Ada Lovelace", email="ada@example.com", active=True)}
    _book_ids = count(5)
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
