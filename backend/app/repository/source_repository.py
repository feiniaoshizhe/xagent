"""Database access for sources."""
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.dependencies import get_db_session
from app.models.source import SourceModel


class SourceRepository:
    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

    async def list_all(self) -> list[SourceModel]:
        result = await self.session.execute(
            select(SourceModel).order_by(SourceModel.label.asc()),
        )
        return list(result.scalars().all())

    async def get_by_id(self, source_id: int) -> SourceModel | None:
        return await self.session.get(SourceModel, source_id)

    async def create(self, payload: dict[str, object]) -> SourceModel:
        instance = SourceModel(**payload)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(
        self,
        source: SourceModel,
        payload: dict[str, object],
    ) -> SourceModel:
        for key, value in payload.items():
            setattr(source, key, value)
        await self.session.flush()
        await self.session.refresh(source)
        return source

    async def delete(self, source: SourceModel) -> None:
        await self.session.delete(source)
        await self.session.flush()
