"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 17:09
Description:
FilePath: view
"""

from fastapi import APIRouter, Depends, HTTPException

from app.repository.agent_flow_repository import AgentFlowRepository
from .schemas import *

router = APIRouter()


@router.post(
    "/",
    response_model=AgentFlowResponse,
    description="创建智能体Flow"
)
async def create_flow(
    request: AgentFlowCreate,
    _repo: AgentFlowRepository = Depends(),
) -> AgentFlowResponse:
    agent_flow = await _repo.create_flow_async(
        name=request.name,
        nodes=request.nodes,
        edges=request.edges,
        description=request.description,
        viewport=request.viewport,
        data=request.data,
        is_template=request.is_template,
        tags=request.tags
    )

    return AgentFlowResponse.model_validate(agent_flow)

@router.get(
    "/",
    description="查询智能体Flow",
    response_model=AgentFlowListResponse,
)
async def get_flows(
    is_template: bool = True,
    _repo: AgentFlowRepository = Depends(),
) -> AgentFlowListResponse:
    agent_flows = await _repo.query_async(
        is_template=is_template
    )
    return AgentFlowListResponse(
        items=[AgentFlowResponse.model_validate(agent_flow) for agent_flow in agent_flows],
        total=len(agent_flows)
    )

@router.get(
    "/{flow_id}",
    description="查询单个智能体Flow",
    response_model=AgentFlowResponse,
)
async def get_flow(
    flow_id: int,
    _repo: AgentFlowRepository = Depends(),
) -> AgentFlowResponse:
    try:

        flow = await _repo.get_flow_by_id_async(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return AgentFlowResponse.model_validate(flow)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve flow: {str(e)}")


@router.put(
    "/{flow_id}",
    description="更新智能体Flow",
    response_model=AgentFlowResponse,
)
async def update_flow(
    flow_id: int,
    request: AgentFlowUpdate,
    _repo: AgentFlowRepository = Depends(),
) -> AgentFlowResponse:
    """Update an existing flow"""
    try:
        agent_flow = await _repo.update_async(
            flow_id=flow_id,
            name=request.name,
            description=request.description,
            nodes=request.nodes,
            edges=request.edges,
            viewport=request.viewport,
            data=request.data,
            is_template=request.is_template,
            tags=request.tags
        )
        if not agent_flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return AgentFlowResponse.model_validate(agent_flow)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update flow: {str(e)}")


@router.delete(
    "/{flow_id}",
    description="删除智能体Flow",
)
async def delete_flow(
    flow_id: int,
    _repo: AgentFlowRepository = Depends(),
):
    """Delete a flow"""
    try:
        success = await _repo.delete_async(flow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Flow not found")
        return {"message": "Flow deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete flow: {str(e)}")


@router.post(
    "/{flow_id}/duplicate",
    description="复制智能体Flow",
    response_model=AgentFlowResponse
)
async def duplicate_flow(
    flow_id: int,
    new_name: str = None,
    _repo: AgentFlowRepository = Depends(),
):
    """Create a copy of an existing flow"""
    try:
        agent_flow = await _repo.duplicate_async(flow_id, new_name)
        if not agent_flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return AgentFlowResponse.model_validate(agent_flow)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to duplicate flow: {str(e)}")


@router.get(
    "/search/{name}",
    description="搜索智能体Flow",
    response_model=AgentFlowListResponse,
)
async def search_flows(
    name: str,
    _repo: AgentFlowRepository = Depends(),
):
    """Search flows by name"""
    try:
        agent_flows = await _repo.query_async(name)
        return AgentFlowListResponse(
            items=[AgentFlowResponse.model_validate(flow) for flow in agent_flows],
            total=len(agent_flows)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search flows: {str(e)}")
