"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 17:07
Description:
FilePath: agent_run_repository
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.routes.dependencies import get_db_session


class AgentRunRepository:

    def __init__(self, session: AsyncSession = Depends(get_db_session)) -> None:
        self.session = session

