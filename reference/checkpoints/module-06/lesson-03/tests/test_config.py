from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import DEVELOPMENT_JWT_SECRET, Settings


def test_uses_validated_defaults_without_dotenv() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_version == "0.18.0"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.default_page_size == 20
    assert settings.max_page_size == 100
    assert settings.database_password.get_secret_value() == "local-library-password"
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 7
    assert settings.jwt_issuer == "urn:library-api"
    assert settings.jwt_audience == "library-api"
    assert settings.jwt_secret_key.get_secret_value() == DEVELOPMENT_JWT_SECRET
    assert "local-library-password" not in str(settings)
    assert DEVELOPMENT_JWT_SECRET not in str(settings)


def test_environment_variables_are_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIBRARY_ENVIRONMENT", "test")
    monkeypatch.setenv("LIBRARY_DEBUG", "true")
    monkeypatch.setenv("LIBRARY_DEFAULT_PAGE_SIZE", "7")
    settings = Settings(_env_file=None)
    assert settings.environment == "test"
    assert settings.debug is True
    assert settings.default_page_size == 7


def test_environment_overrides_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        'LIBRARY_APP_NAME="Nome do arquivo"\nLIBRARY_DEFAULT_PAGE_SIZE="8"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("LIBRARY_APP_NAME", "Nome do ambiente")
    settings = Settings(_env_file=env_file)
    assert settings.app_name == "Nome do ambiente"
    assert settings.default_page_size == 8


def test_rejects_unknown_dotenv_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('LIBRARY_PAGE_SZE="8"\n', encoding="utf-8")
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Settings(_env_file=env_file)


@pytest.mark.parametrize(
    ("values", "field"),
    [
        ({"app_version": "v6"}, "app_version"),
        ({"environment": "local"}, "environment"),
        ({"max_page_size": 101}, "max_page_size"),
        ({"access_token_expire_minutes": 0}, "access_token_expire_minutes"),
        ({"refresh_token_expire_days": 31}, "refresh_token_expire_days"),
        ({"jwt_secret_key": "short"}, "jwt_secret_key"),
        ({"allowed_origins": ["*"]}, "wildcard"),
        (
            {"environment": "production", "allowed_origins": ["http://example.com"]},
            "HTTPS",
        ),
        (
            {
                "environment": "production",
                "allowed_origins": ["https://example.com"],
            },
            "jwt_secret_key exclusiva",
        ),
        (
            {"default_page_size": 50, "max_page_size": 10},
            "default_page_size não pode exceder max_page_size",
        ),
    ],
)
def test_rejects_invalid_configuration(values: dict[str, object], field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        Settings(_env_file=None, **values)
