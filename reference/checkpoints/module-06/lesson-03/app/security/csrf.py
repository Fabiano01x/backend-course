"""Defesa CSRF para operações autenticadas por cookie."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.dependencies import AppSettings


CSRF_HEADER_NAME = "X-CSRF-Protection"
CSRF_HEADER_VALUE = "1"


@dataclass(frozen=True, slots=True)
class CsrfVerified:
    origin: str | None


def invalid_browser_request() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Requisição de navegador não autorizada",
    )


async def require_csrf_protection(
    request: Request,
    settings: AppSettings,
    csrf_header: Annotated[
        str | None, Header(alias=CSRF_HEADER_NAME)
    ] = None,
) -> CsrfVerified:
    if csrf_header != CSRF_HEADER_VALUE:
        raise invalid_browser_request()
    origin = request.headers.get("origin")
    target_origin = str(request.base_url).rstrip("/")
    trusted_origins = {*settings.allowed_origins, target_origin}
    if origin is not None and origin not in trusted_origins:
        raise invalid_browser_request()
    return CsrfVerified(origin=origin)


CsrfProtection = Annotated[CsrfVerified, Depends(require_csrf_protection)]
