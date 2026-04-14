"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 17:11
Description:
FilePath: schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict

from app.models.schemas.node import Node, Edge

class AgentFlowDetail(BaseModel):

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, title="描述")
    nodes: List[Node] = Field(..., title="节点")
    edges: List[Edge] = Field(..., title="边")
    viewport: Optional[Dict[str, Any]] = Field(default=None, title="视图信息")
    data: Optional[Dict[str, Any]] = Field(default=None, title="数据")
    is_template: bool = Field(default=False, title="是否模板")
    tags: Optional[List[str]] = Field(default=None, title="标签")


    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )

class AgentFlowCreate(AgentFlowDetail):
    pass

class AgentFlowUpdate(AgentFlowDetail):

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    viewport: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    is_template: Optional[bool] = None
    tags: Optional[List[str]] = None


class AgentFlowResponse(AgentFlowCreate):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )
    id: int = Field(..., title="ID")
    created_at: datetime = Field(..., title="创建时间")
    updated_at: Optional[datetime] = Field(None, title="更新时间")

class AgentFlowListResponse(BaseModel):
    items: List[AgentFlowResponse]
    total: int
