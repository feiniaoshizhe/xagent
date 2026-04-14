"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 16:25
Description:
FilePath: node
"""
from typing import Optional, Dict, Any

from pydantic import BaseModel

class Node(BaseModel):
    """Node in the graph (ReactFlow format)"""
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]


class Edge(BaseModel):
    """Connection between nodes (ReactFlow format)"""
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    type: Optional[str] = None  # 'default' | 'conditional' | 'smoothstep'

    # Conditional routing data
    data: Optional[Dict[str, Any]] = None  # For storing conditional config
    label: Optional[str] = None  # Edge label to display

