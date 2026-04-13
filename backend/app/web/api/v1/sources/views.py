"""Sources API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from redis.asyncio import ConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, require_admin, require_authenticated_user
from app.core.db.dependencies import get_db_session
from app.repository.repository import SourceRepository
from app.domain.sources.schemas import (
    CreateSourceRequest,
    DeleteSourceFileRequest,
    DeleteSuccessResponse,
    SourceFilesResponse,
    SourceItem,
    SourcesGroupedResponse,
    UpdateSourceRequest,
    UploadSourceFilesResponse,
)
from app.domain.sources.service import SourceService
from app.services.redis.dependency import get_redis_pool

router = APIRouter()


def get_source_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SourceService:
    return SourceService(SourceRepository(session))


@router.get("/", response_model=SourcesGroupedResponse)
async def list_sources(
    _: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
    redis_pool: Annotated[ConnectionPool, Depends(get_redis_pool)],
) -> SourcesGroupedResponse:
    return await service.list_grouped(redis_pool)


@router.post("/", response_model=SourceItem, status_code=201)
async def create_source(
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    request: CreateSourceRequest,
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceItem:
    return await service.create_source(request)


@router.put("/{source_id}", response_model=SourceItem)
async def update_source(
    source_id: str,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    request: UpdateSourceRequest,
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceItem:
    return await service.update_source(source_id, request)


@router.delete("/{source_id}", response_model=DeleteSuccessResponse)
async def delete_source(
    source_id: str,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> DeleteSuccessResponse:
    await service.delete_source(source_id)
    return DeleteSuccessResponse()


@router.get("/{source_id}/files", response_model=SourceFilesResponse)
async def list_source_files(
    source_id: str,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceFilesResponse:
    return await service.list_files(source_id)


@router.put("/{source_id}/files", response_model=UploadSourceFilesResponse)
async def upload_source_files(
    source_id: str,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[SourceService, Depends(get_source_service)],
    files: Annotated[list[UploadFile], File(...)],
) -> UploadSourceFilesResponse:
    return await service.upload_files(source_id, files)


@router.delete("/{source_id}/files", response_model=DeleteSuccessResponse)
async def delete_source_file(
    source_id: str,
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    request: DeleteSourceFileRequest,
    service: Annotated[SourceService, Depends(get_source_service)],
) -> DeleteSuccessResponse:
    await service.delete_file(source_id, request.pathname)
    return DeleteSuccessResponse()
