import uvicorn
from fastapi import FastAPI,status, HTTPException
import data
from schemas import BookCreate, BookResponse, UserCreate, UserResponse

app = FastAPI(
    title="Library API",
    description="Projeto cumulativo do curso de backend Python",
    version="0.1.0"
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/books", response_model=list[BookResponse])
async def list_books() -> list[BookResponse]:
    return list(data.books.values())

@app.post("/books", response_model=BookResponse, status_code= status.HTTP_201_CREATED)
async def create_book(payload: BookCreate) -> BookResponse:
    return data.create_book(payload)

@app.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int) -> BookResponse:
    book = data.books.get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return book

@app.get("/users", response_model=list[UserResponse])
async def list_user() -> list[UserResponse]:
    return list(data.users.values())

@app.post("users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate) -> UserResponse:
    return data.create_user(payload)

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    user = data.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    return user


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)
if __name__ == "__main__":
    main()
