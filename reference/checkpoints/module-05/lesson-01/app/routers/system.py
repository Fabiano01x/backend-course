"""Rotas operacionais que não pertencem a um domínio de negócio."""

from fastapi import APIRouter

from app.dependencies import AppSettings
from app.schemas import AppInfo, HealthStatus


router = APIRouter(tags=["Sistema"])


@router.get(
    "/health",
    response_model=HealthStatus,
    operation_id="checkHealth",
    summary="Verificar a saúde da API",
    response_description="A aplicação está pronta para receber requisições.",
)
async def health_check() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get(
    "/info",
    response_model=AppInfo,
    operation_id="getAppInfo",
    summary="Consultar informações públicas da API",
    description="Expõe metadados seguros da configuração em uso.",
    response_description="Nome, versão e ambiente atuais da aplicação.",
)
async def app_info(settings: AppSettings) -> AppInfo:
    return AppInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
    )
