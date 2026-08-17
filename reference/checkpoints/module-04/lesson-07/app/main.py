"""Ponto de composição da Library API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.dependencies import load_settings
from app.middleware.security import SecurityHeadersMiddleware
from app.routers import books, system, users


def create_app(settings: Settings | None = None) -> FastAPI:
    startup_settings = settings or load_settings()
    application = FastAPI(
        title=startup_settings.app_name,
        description="Projeto cumulativo do curso de backend Python.",
        version=startup_settings.app_version,
        debug=startup_settings.debug,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=startup_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=(
            startup_settings.environment == "production"
            and startup_settings.https_enabled
        ),
    )
    application.include_router(system.router)
    application.include_router(books.router)
    application.include_router(users.router)
    return application


app = create_app()
