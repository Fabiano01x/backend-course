"""Contrato de configuração da Library API."""

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="LIBRARY_",
        extra="forbid",
        frozen=True,
    )

    app_name: str = Field(default="Library API", min_length=1, max_length=100)
    app_version: str = Field(default="0.10.0", pattern=r"^\d+\.\d+\.\d+$")
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=100)
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    https_enabled: bool = False

    @model_validator(mode="after")
    def default_page_size_cannot_exceed_maximum(self) -> Self:
        if self.default_page_size > self.max_page_size:
            raise ValueError("default_page_size não pode exceder max_page_size")
        if "*" in self.allowed_origins:
            raise ValueError("allowed_origins não aceita wildcard com credenciais")
        if self.environment == "production" and any(
            not origin.startswith("https://") for origin in self.allowed_origins
        ):
            raise ValueError("origens de produção devem usar HTTPS")
        return self
