"""Routers da Library API."""

from app.routers import api_keys, auth, books, integrations, loans, oidc, system, users

__all__ = [
    "api_keys",
    "auth",
    "books",
    "integrations",
    "loans",
    "oidc",
    "system",
    "users",
]
