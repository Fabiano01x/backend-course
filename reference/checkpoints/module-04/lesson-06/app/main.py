"""Ponto de composição da Library API."""

from fastapi import FastAPI

from app.dependencies import load_settings
from app.routers import books, system, users


startup_settings = load_settings()

app = FastAPI(
    title=startup_settings.app_name,
    description="Projeto cumulativo do curso de backend Python.",
    version=startup_settings.app_version,
    debug=startup_settings.debug,
)

app.include_router(system.router)
app.include_router(books.router)
app.include_router(users.router)
