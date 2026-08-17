"""Primeira versão executável da Library API."""

from fastapi import FastAPI


app = FastAPI(
    title="Library API",
    description="Projeto cumulativo do curso de backend Python.",
    version="0.1.0",
)

books: list[dict[str, object]] = [
    {
        "id": 1,
        "title": "Clean Architecture",
        "author": "Robert C. Martin",
        "available": True,
    }
]

users: list[dict[str, object]] = [
    {"id": 1, "name": "Ada Lovelace", "active": True}
]


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/books")
async def list_books() -> list[dict[str, object]]:
    return books


@app.get("/users")
async def list_users() -> list[dict[str, object]]:
    return users
