"""Rotas operacionais que não pertencem a um domínio de negócio."""

from fastapi import APIRouter

from app.dependencies import AppSettings
from app.schemas import AppInfo


router = APIRouter(tags=["Sistema"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/info", response_model=AppInfo)
async def app_info(settings: AppSettings) -> AppInfo:
    return AppInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
    )
