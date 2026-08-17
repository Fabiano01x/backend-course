"""Ponto de composição da Library API."""

from fastapi import FastAPI

from app.config import settings
from app.routers import books, system, users


app = FastAPI(
    title=settings.app_name,
    description="Projeto cumulativo do curso de backend Python.",
    version=settings.app_version,
    debug=settings.debug,
)

app.include_router(system.router)
app.include_router(books.router)
app.include_router(users.router)
