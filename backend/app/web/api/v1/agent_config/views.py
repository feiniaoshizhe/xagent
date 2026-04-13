"""Agent config API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import ConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, require_admin, require_authenticated_user
from app.core.db.dependencies import get_db_session
from app.repository.agent_config_repository import AgentConfigRepository
from app.domain.agent_config.schemas import AgentConfigResponse, UpdateAgentConfigRequest
from app.domain.agent_config.service import AgentConfigService
from app.services.redis.dependency import get_redis_pool

router = APIRouter()


def get_agent_config_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgentConfigService:
    return AgentConfigService(AgentConfigRepository(session))


@router.get("/", response_model=AgentConfigResponse)
async def get_agent_config(
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[AgentConfigService, Depends(get_agent_config_service)],
    redis_pool: Annotated[ConnectionPool, Depends(get_redis_pool)],
) -> AgentConfigResponse:
    return await service.get_active_or_default(redis_pool)


@router.put("/", response_model=AgentConfigResponse)
async def update_agent_config(
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    request: UpdateAgentConfigRequest,
    service: Annotated[AgentConfigService, Depends(get_agent_config_service)],
    redis_pool: Annotated[ConnectionPool, Depends(get_redis_pool)],
) -> AgentConfigResponse:
    return await service.update_active(request, redis_pool)


@router.post("/reset", response_model=AgentConfigResponse)
async def reset_agent_config(
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    service: Annotated[AgentConfigService, Depends(get_agent_config_service)],
    redis_pool: Annotated[ConnectionPool, Depends(get_redis_pool)],
) -> AgentConfigResponse:
    return await service.reset_active(redis_pool)


@router.get("/public", response_model=AgentConfigResponse)
async def get_public_agent_config(
    _: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AgentConfigService, Depends(get_agent_config_service)],
    redis_pool: Annotated[ConnectionPool, Depends(get_redis_pool)],
) -> AgentConfigResponse:
    return await service.get_active_or_default(redis_pool)
