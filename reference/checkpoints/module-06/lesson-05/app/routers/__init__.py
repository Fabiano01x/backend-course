"""Routers da Library API."""

from app.routers import auth, books, loans, oidc, system, users

__all__ = ["auth", "books", "loans", "oidc", "system", "users"]
