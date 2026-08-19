"""Rotas operacionais que não pertencem a um domínio de negócio."""

from fastapi import APIRouter
from sqlalchemy import text

from app.database import DatabaseSession
from app.dependencies import AppSettings
from app.schemas import AppInfo, DatabaseHealthStatus, HealthStatus


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
    "/health/database",
    response_model=DatabaseHealthStatus,
    operation_id="checkDatabaseHealth",
    summary="Verificar a conexão com o banco",
    description="Executa uma consulta mínima usando a sessão desta requisição.",
    response_description="O banco respondeu à consulta de saúde.",
)
async def database_health_check(session: DatabaseSession) -> DatabaseHealthStatus:
    await session.execute(text("SELECT 1"))
    return DatabaseHealthStatus(status="ok", database="reachable")


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
