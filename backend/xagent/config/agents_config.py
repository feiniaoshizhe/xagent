"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 15:41
Description:
FilePath: agents_config
"""
from pydantic import BaseModel,Field


class AgentConfig(BaseModel):
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    model: str | None = Field(default=None, description="Agent model")
    tools: list[str] |  None = Field(default=None, description="Agent tools")

    skills: list[str] | None = Field(default=None, description="Agent skills")
