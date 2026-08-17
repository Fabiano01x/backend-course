"""Ponto de composição da Library API após a adoção de APIRouter."""

from fastapi import FastAPI

from app.routers import books, system, users


app = FastAPI(
    title="Library API",
    description="Projeto cumulativo do curso de backend Python.",
    version="0.3.0",
)

app.include_router(system.router)
app.include_router(books.router)
app.include_router(users.router)

