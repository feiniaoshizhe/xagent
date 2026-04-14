"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 15:58
Description:
FilePath: agent_flow_repository
"""
from typing import List

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentFlow
from app.models.schemas.node import Node, Edge
from app.routes.dependencies import get_db_session


class AgentFlowRepository:

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session


    async def create_flow_async(
        self,
        name: str,
        nodes: List[Node],
        edges: List[Edge],
        description: str = None,
        viewport: dict = None,
        data: dict = None,
        is_template: bool = False,
        tags: List[str] = None
    ) -> AgentFlow:
        flow = AgentFlow(
            name=name,
            nodes=nodes,
            edges=edges,
            description=description,
            viewport=viewport,
            data=data,
            is_template=is_template,
            tags=tags
        )
        self.session.add(flow)
        await self.session.commit()
        await self.session.refresh(flow)
        return  flow

    async def get_flow_by_id_async(self, flow_id: int) -> AgentFlow | None:
        stmt = select(AgentFlow).where(AgentFlow.id == flow_id)
        result = await self.session.execute(stmt)
        return result.scalars().one_or_none()

    async def query_async(
        self,
        name: str = None,
        is_template: bool = True,
    ) -> List[AgentFlow]:

        stmt = (
            select(AgentFlow)
            .where(
                AgentFlow.is_template == is_template,
                AgentFlow.is_deleted == False
            )
            .order_by(AgentFlow.updated_at.desc())
        )

        if name:
            stmt = stmt.where(AgentFlow.name.like(f"%{name}%"))

        result = await self.session.execute(stmt)
        return result.scalars().all()


    async def update_async(
        self,
        flow_id: int,
        name: str = None,
        description: str = None,
        nodes: List[Node] = None,
        edges: List[Edge] = None,
        viewport: dict = None,
        data: dict = None,
        is_template: bool = None,
        tags: List[str] = None
    ) -> AgentFlow | None:
        agent_flow = await self.get_flow_by_id_async(flow_id)
        if not agent_flow:
            return None

        if name is not None:
            agent_flow.name = name
        if description is not None:
            agent_flow.description = description
        if nodes is not None:
            agent_flow.nodes = nodes
        if edges is not None:
            agent_flow.edges = edges
        if viewport is not None:
            agent_flow.viewport = viewport
        if data is not None:
            agent_flow.data = data
        if is_template is not None:
            agent_flow.is_template = is_template
        if tags is not None:
            agent_flow.tags = tags

        await self.session.commit()
        await self.session.refresh(agent_flow)

        return agent_flow

    async def delete_async(self, flow_id: int) -> bool:
        agent_flow = await self.get_flow_by_id_async(flow_id)
        if not agent_flow:
            return False

        await self.session.delete(agent_flow)
        await self.session.commit()
        return True

    async def duplicate_async(
        self,
        flow_id: int,
        new_name: str | None = None
    ) -> AgentFlow | None:
        original_flow = await self.get_flow_by_id_async(flow_id)
        if not original_flow:
            return None

        return await self.create_flow_async(
            name=new_name or f"{original_flow.name} (Copy)",
            nodes=original_flow.nodes,
            edges=original_flow.edges,
            description=original_flow.description,
            viewport=original_flow.viewport,
            data=original_flow.data,
            is_template=False,
            tags=original_flow.tags
        )




