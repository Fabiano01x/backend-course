"""Contratos HTTP da Library API."""

from datetime import UTC, datetime
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


class RegistrationCreate(StrictSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Ada Lovelace",
                    "email": "ada@example.com",
                    "password": "correct horse battery staple",
                }
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
    password: str = Field(
        min_length=12,
        max_length=128,
        description="Senha local; nunca é devolvida nem persistida em texto puro.",
    )

    @field_validator("name")
    @classmethod
    def name_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("nome não pode conter somente espaços")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_registration_email(cls, value: object) -> object:
        return value.strip().casefold() if isinstance(value, str) else value


class LoginRequest(StrictSchema):
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Endereço de e-mail da conta local.",
    )
    password: str = Field(
        min_length=1,
        max_length=128,
        description="Senha apresentada somente para verificação.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_login_email(cls, value: object) -> object:
        return value.strip().casefold() if isinstance(value, str) else value


class TokenResponse(StrictSchema):
    access_token: str = Field(description="JWT curto para uso como Bearer token.")
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0, description="Validade do token em segundos.")


class UserResponse(StrictSchema):
    id: int
    name: str
    email: str
    active: bool


class LoanCreate(StrictSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "book_id": 1,
                    "due_at": "2030-09-01T18:00:00Z",
                }
            ]
        }
    )

    book_id: int = Field(gt=0, description="Livro retirado do acervo.")
    due_at: datetime = Field(description="Prazo de devolução com fuso horário.")

    @field_validator("due_at")
    @classmethod
    def due_date_must_be_aware_and_future(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("due_at deve informar fuso horário")
        if value <= datetime.now(UTC):
            raise ValueError("due_at deve estar no futuro")
        return value


class LoanResponse(StrictSchema):
    id: int
    user_id: int
    book_id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None


class LoanUserSummary(StrictSchema):
    id: int
    name: str


class LoanBookSummary(StrictSchema):
    id: int
    title: str
    author: str


class LoanDetailResponse(LoanResponse):
    user: LoanUserSummary
    book: LoanBookSummary


class UserLoanSummary(StrictSchema):
    id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
    book: LoanBookSummary


class UserDetailResponse(UserResponse):
    loans: list[UserLoanSummary]


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
