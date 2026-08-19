import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Library API", version="0.1.0")

books = [
    {
        "id": 1,
        "title": "Clean Architecture",
        "author": "Robert C. Martin",
        "available": True,
    }
]

users = [
    {
        "id": 1,
        "name": "Ada Lovelace",
        "active": True
    }
]

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/books")
async def list_books() -> list[dict[str, object]]:
    return books

@app.get("/users")
async def list_user() -> list[dict[str, object]]:
    return users

@app.get("/welcome")
async def welcome() -> dict[str, str]:
    return {"Welcome": "Bem vindo"}


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)
if __name__ == "__main__":
    main()
