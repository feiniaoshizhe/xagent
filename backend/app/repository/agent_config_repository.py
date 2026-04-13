"""Database access for agent config."""
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.dependencies import get_db_session
from app.models.agent_config import AgentConfigModel


class AgentConfigRepository:

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def get_active(self) -> AgentConfigModel | None:
        result = await self.session.execute(
            select(AgentConfigModel).where(AgentConfigModel.is_active.is_(True)).limit(1),
        )
        return result.scalar_one_or_none()

    async def create_active(self, payload: dict[str, object]) -> AgentConfigModel:
        instance = AgentConfigModel(**payload)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update_active(
        self,
        config: AgentConfigModel,
        payload: dict[str, object],
    ) -> AgentConfigModel:
        for key, value in payload.items():
            setattr(config, key, value)
        await self.session.flush()
        await self.session.refresh(config)
        return config
