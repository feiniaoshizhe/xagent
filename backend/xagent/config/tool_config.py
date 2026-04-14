"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 15:50
Description:
FilePath: tool_config
"""
from pydantic import BaseModel, ConfigDict, Field


class ToolConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="Tool name")

