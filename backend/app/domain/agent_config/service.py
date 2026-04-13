"""Business logic for agent config."""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from redis.asyncio import ConnectionPool, Redis

from app.models import AgentConfigModel, CitationFormat, ResponseStyle
from app.repository.repository import AgentConfigRepository
from app.domain.agent_config.schemas import AgentConfigResponse, UpdateAgentConfigRequest
from app.common.settings import settings

AGENT_CONFIG_CACHE_KEY = "agent:config-cache"


class AgentConfigService:
    def __init__(self, repository: AgentConfigRepository) -> None:
        self._repository = repository

    async def get_active_or_default(
        self,
        redis_pool: ConnectionPool | None = None,
    ) -> AgentConfigResponse:
        cached = await self._get_cached(redis_pool)
        if cached is not None:
            return cached

        active = await self._repository.get_active()
        response = self._to_response(active) if active else self._default_config()
        await self._set_cached(redis_pool, response)
        return response

    async def update_active(
        self,
        request: UpdateAgentConfigRequest,
        redis_pool: ConnectionPool | None = None,
    ) -> AgentConfigResponse:
        active = await self._repository.get_active()
        defaults = self._default_config()
        payload = {
            "name": "default",
            "additional_prompt": request.additional_prompt,
            "response_style": request.response_style or defaults.response_style,
            "language": request.language or defaults.language,
            "default_model": request.default_model,
            "max_steps_multiplier": request.max_steps_multiplier or defaults.max_steps_multiplier,
            "temperature": request.temperature or defaults.temperature,
            "search_instructions": request.search_instructions,
            "citation_format": request.citation_format or defaults.citation_format,
            "is_active": True,
            "updated_at": datetime.now(UTC),
        }

        if active is None:
            payload["id"] = str(uuid.uuid4())
            payload["created_at"] = datetime.now(UTC)
            active = await self._repository.create_active(payload)
        else:
            active = await self._repository.update_active(active, payload)

        await self.invalidate_cache(redis_pool)
        return self._to_response(active)

    async def reset_active(
        self,
        redis_pool: ConnectionPool | None = None,
    ) -> AgentConfigResponse:
        defaults = self._default_config()
        active = await self._repository.get_active()
        payload = {
            "name": defaults.name,
            "additional_prompt": defaults.additional_prompt,
            "response_style": defaults.response_style,
            "language": defaults.language,
            "default_model": defaults.default_model,
            "max_steps_multiplier": defaults.max_steps_multiplier,
            "temperature": defaults.temperature,
            "search_instructions": defaults.search_instructions,
            "citation_format": defaults.citation_format,
            "is_active": True,
            "updated_at": datetime.now(UTC),
        }
        if active is None:
            payload["id"] = str(uuid.uuid4())
            payload["created_at"] = datetime.now(UTC)
            active = await self._repository.create_active(payload)
        else:
            active = await self._repository.update_active(active, payload)

        await self.invalidate_cache(redis_pool)
        return self._to_response(active)

    async def invalidate_cache(self, redis_pool: ConnectionPool | None = None) -> None:
        if redis_pool is None:
            return
        async with Redis(connection_pool=redis_pool) as redis:
            await redis.delete(AGENT_CONFIG_CACHE_KEY)

    async def _get_cached(
        self,
        redis_pool: ConnectionPool | None,
    ) -> AgentConfigResponse | None:
        if redis_pool is None:
            return None
        async with Redis(connection_pool=redis_pool) as redis:
            payload = await redis.get(AGENT_CONFIG_CACHE_KEY)
        if not payload:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return AgentConfigResponse.model_validate_json(payload)

    async def _set_cached(
        self,
        redis_pool: ConnectionPool | None,
        response: AgentConfigResponse,
    ) -> None:
        if redis_pool is None:
            return
        async with Redis(connection_pool=redis_pool) as redis:
            await redis.set(
                AGENT_CONFIG_CACHE_KEY,
                response.model_dump_json(by_alias=True),
                ex=settings.agent_config_cache_ttl_seconds,
            )

    def _default_config(self) -> AgentConfigResponse:
        return AgentConfigResponse(
            id="default",
            name="default",
            additional_prompt=None,
            response_style=ResponseStyle.CONCISE,
            language="en",
            default_model=None,
            max_steps_multiplier=1.0,
            temperature=0.7,
            search_instructions=None,
            citation_format=CitationFormat.INLINE,
            is_active=True,
        )

    def _to_response(self, model: AgentConfigModel) -> AgentConfigResponse:
        return AgentConfigResponse(
            id=model.id,
            name=model.name,
            additional_prompt=model.additional_prompt,
            response_style=model.response_style or ResponseStyle.CONCISE,
            language=model.language or "en",
            default_model=model.default_model,
            max_steps_multiplier=model.max_steps_multiplier or 1.0,
            temperature=model.temperature or 0.7,
            search_instructions=model.search_instructions,
            citation_format=model.citation_format or CitationFormat.INLINE,
            is_active=model.is_active,
        )
