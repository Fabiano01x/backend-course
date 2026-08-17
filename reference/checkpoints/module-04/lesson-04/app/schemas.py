"""Contratos HTTP da Library API."""

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BookCreate(StrictSchema):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    isbn: str = Field(min_length=10, max_length=17)


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
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserResponse(StrictSchema):
    id: int
    name: str
    email: str
    active: bool
