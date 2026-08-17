"""Provedores injetáveis da Library API."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import Settings


@lru_cache
def load_settings() -> Settings:
    return Settings()


async def get_settings() -> Settings:
    return load_settings()


AppSettings = Annotated[Settings, Depends(get_settings)]
