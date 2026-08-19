"""Contrato de configuração da Library API."""

from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
DEVELOPMENT_JWT_SECRET = (
    "development-only-library-api-jwt-key-change-before-production"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="LIBRARY_",
        extra="forbid",
        frozen=True,
    )

    app_name: str = Field(default="Library API", min_length=1, max_length=100)
    app_version: str = Field(default="0.20.0", pattern=r"^\d+\.\d+\.\d+$")
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=100)
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    https_enabled: bool = False
    database_host: str = Field(default="localhost", min_length=1)
    database_port: int = Field(default=5432, ge=1, le=65535)
    database_name: str = Field(default="library", min_length=1)
    database_user: str = Field(default="library", min_length=1)
    database_password: SecretStr = Field(
        default=SecretStr("local-library-password"), min_length=1
    )
    jwt_secret_key: SecretStr = Field(
        default=SecretStr(DEVELOPMENT_JWT_SECRET), min_length=32
    )
    jwt_issuer: str = Field(default="urn:library-api", min_length=1, max_length=200)
    jwt_audience: str = Field(default="library-api", min_length=1, max_length=200)
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    oidc_issuer: str | None = Field(default=None, max_length=255)
    oidc_client_id: str | None = Field(default=None, max_length=255)
    oidc_client_secret: SecretStr | None = Field(default=None, min_length=16)
    oidc_redirect_uri: str | None = Field(default=None, max_length=500)
    oidc_attempt_expire_minutes: int = Field(default=10, ge=2, le=15)

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
        if (
            self.environment == "production"
            and self.jwt_secret_key.get_secret_value() == DEVELOPMENT_JWT_SECRET
        ):
            raise ValueError("produção exige uma jwt_secret_key exclusiva")
        oidc_fields = (
            self.oidc_issuer,
            self.oidc_client_id,
            self.oidc_client_secret,
            self.oidc_redirect_uri,
        )
        if any(value is not None for value in oidc_fields) and not all(
            value is not None for value in oidc_fields
        ):
            raise ValueError("configuração OIDC deve ser informada por completo")
        if self.oidc_issuer is not None:
            issuer = urlsplit(self.oidc_issuer)
            if (
                issuer.scheme != "https"
                or not issuer.netloc
                or issuer.query
                or issuer.fragment
            ):
                raise ValueError("oidc_issuer deve ser uma URL HTTPS sem query")
            redirect = urlsplit(self.oidc_redirect_uri or "")
            if redirect.scheme not in {"http", "https"} or not redirect.netloc:
                raise ValueError("oidc_redirect_uri deve ser uma URL HTTP(S)")
            if self.environment == "production" and redirect.scheme != "https":
                raise ValueError("redirect OIDC de produção deve usar HTTPS")
        return self

    @property
    def oidc_enabled(self) -> bool:
        return self.oidc_issuer is not None
