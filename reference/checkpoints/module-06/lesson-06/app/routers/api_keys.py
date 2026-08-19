"""Administração de identidades e credenciais de clientes de máquina."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.database import DatabaseSession
from app.dependencies import LibrarianPrincipal
from app.models import ApiClient, ApiKey
from app.schemas import (
    ApiClientCreate,
    ApiClientResponse,
    ApiKeyIssueRequest,
    ApiKeyIssueResponse,
    ApiKeyRotateRequest,
    ErrorResponse,
)
from app.services.api_keys import (
    ApiKeyRuleError,
    IssuedApiKey,
    create_api_client,
    issue_api_key,
    revoke_api_key,
    rotate_api_key,
)


router = APIRouter(tags=["Credenciais de máquina"])


def translate_rule_error(error: ApiKeyRuleError) -> HTTPException:
    if error.not_found:
        code = status.HTTP_404_NOT_FOUND
    elif error.conflict:
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail=error.detail)


def to_client_response(client: ApiClient) -> ApiClientResponse:
    return ApiClientResponse(
        id=client.id,
        name=client.name,
        active=client.active,
        created_at=client.created_at or datetime.now(UTC),
    )


def to_key_response(issued: IssuedApiKey) -> ApiKeyIssueResponse:
    key: ApiKey = issued.key
    return ApiKeyIssueResponse(
        id=key.id,
        client_id=key.client_id,
        prefix=key.prefix,
        scopes=key.scopes,
        created_at=key.created_at or datetime.now(UTC),
        expires_at=key.expires_at,
        revoked_at=key.revoked_at,
        last_used_at=key.last_used_at,
        replaced_by_id=key.replaced_by_id,
        api_key=issued.raw,
    )


@router.post(
    "/api-clients",
    response_model=ApiClientResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createApiClient",
    summary="Cadastrar um cliente de máquina",
    responses={
        401: {"model": ErrorResponse, "description": "Access token inválido."},
        403: {"model": ErrorResponse, "description": "Papel librarian ausente."},
        409: {"model": ErrorResponse, "description": "Nome já cadastrado."},
    },
)
async def create_client(
    payload: ApiClientCreate,
    session: DatabaseSession,
    _librarian: LibrarianPrincipal,
) -> ApiClientResponse:
    try:
        client = await create_api_client(session, payload.name)
    except ApiKeyRuleError as error:
        raise translate_rule_error(error) from error
    return to_client_response(client)


@router.post(
    "/api-clients/{client_id}/keys",
    response_model=ApiKeyIssueResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="issueApiKey",
    summary="Emitir uma chave de API",
    description="O segredo completo aparece somente nesta resposta.",
    responses={
        401: {"model": ErrorResponse, "description": "Access token inválido."},
        403: {"model": ErrorResponse, "description": "Papel librarian ausente."},
        404: {"model": ErrorResponse, "description": "Cliente não encontrado."},
        409: {"model": ErrorResponse, "description": "Cliente inativo."},
    },
)
async def issue_key(
    client_id: UUID,
    payload: ApiKeyIssueRequest,
    session: DatabaseSession,
    _librarian: LibrarianPrincipal,
) -> ApiKeyIssueResponse:
    try:
        issued = await issue_api_key(
            session,
            client_id=client_id,
            scopes=set(payload.scopes),
            expires_at=payload.expires_at,
        )
    except ApiKeyRuleError as error:
        raise translate_rule_error(error) from error
    return to_key_response(issued)


@router.post(
    "/api-keys/{key_id}/rotate",
    response_model=ApiKeyIssueResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="rotateApiKey",
    summary="Rotacionar uma chave de API",
    description="Cria a substituta e revoga a chave anterior atomicamente.",
    responses={
        401: {"model": ErrorResponse, "description": "Access token inválido."},
        403: {"model": ErrorResponse, "description": "Papel librarian ausente."},
        404: {"model": ErrorResponse, "description": "Chave não encontrada."},
        409: {"model": ErrorResponse, "description": "Chave já revogada."},
    },
)
async def rotate_key(
    key_id: UUID,
    payload: ApiKeyRotateRequest,
    session: DatabaseSession,
    _librarian: LibrarianPrincipal,
) -> ApiKeyIssueResponse:
    try:
        issued = await rotate_api_key(
            session, key_id=key_id, expires_at=payload.expires_at
        )
    except ApiKeyRuleError as error:
        raise translate_rule_error(error) from error
    return to_key_response(issued)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="revokeApiKey",
    summary="Revogar uma chave de API",
    responses={
        401: {"model": ErrorResponse, "description": "Access token inválido."},
        403: {"model": ErrorResponse, "description": "Papel librarian ausente."},
        404: {"model": ErrorResponse, "description": "Chave não encontrada."},
    },
)
async def revoke_key(
    key_id: UUID,
    session: DatabaseSession,
    _librarian: LibrarianPrincipal,
) -> Response:
    try:
        await revoke_api_key(session, key_id)
    except ApiKeyRuleError as error:
        raise translate_rule_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
