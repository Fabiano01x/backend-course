"""Contratos HTTP da Library API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BookCreate(StrictSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Kindred",
                    "author": "Octavia E. Butler",
                    "isbn": "9780807083697",
                }
            ]
        }
    )

    title: str = Field(min_length=1, max_length=200, description="Título do livro.")
    author: str = Field(min_length=1, max_length=120, description="Nome do autor.")
    isbn: str = Field(
        min_length=10,
        max_length=17,
        description="ISBN informado pelo catálogo, com ou sem separadores.",
    )

    @field_validator("title", "author")
    @classmethod
    def text_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("texto não pode conter somente espaços")
        return value


class BookUpdate(StrictSchema):
    title: str = Field(min_length=1, max_length=200, description="Título do livro.")
    author: str = Field(min_length=1, max_length=120, description="Nome do autor.")
    isbn: str = Field(
        min_length=10,
        max_length=17,
        description="ISBN informado pelo catálogo, com ou sem separadores.",
    )

    @field_validator("title", "author")
    @classmethod
    def text_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("texto não pode conter somente espaços")
        return value


class BookResponse(StrictSchema):
    id: int
    title: str
    author: str
    isbn: str
    available: bool


class BookPage(StrictSchema):
    items: list[BookResponse]
    total: int
    limit: int
    offset: int


class UserCreate(StrictSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Ada Lovelace", "email": "ada@example.com"}
            ]
        }
    )

    name: str = Field(min_length=2, max_length=120, description="Nome completo.")
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Endereço de e-mail do usuário.",
    )

    @field_validator("name")
    @classmethod
    def name_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("nome não pode conter somente espaços")
        return value


class UserResponse(StrictSchema):
    id: int
    name: str
    email: str
    active: bool


class AppInfo(StrictSchema):
    name: str
    version: str
    environment: Literal["development", "test", "production"]
    debug: bool


class HealthStatus(StrictSchema):
    status: Literal["ok"]


class DatabaseHealthStatus(HealthStatus):
    database: Literal["reachable"]


class ErrorResponse(StrictSchema):
    detail: str = Field(description="Mensagem legível que explica a falha.")
