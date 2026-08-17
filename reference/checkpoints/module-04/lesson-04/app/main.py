"""Ponto de composição da Library API."""

from fastapi import FastAPI

from app.routers import books, system, users


app = FastAPI(
    title="Library API",
    description="Projeto cumulativo do curso de backend Python.",
    version="0.4.0",
)

app.include_router(system.router)
app.include_router(books.router)
app.include_router(users.router)
