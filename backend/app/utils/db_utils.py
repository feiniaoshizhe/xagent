"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 15:06
Description:
FilePath: db_utils
"""

import os

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from app.common.settings import settings


async def create_database() -> None:
    """Create a database."""
    engine = create_async_engine(str(settings.db_url.with_path("/mysql")))

    async with engine.connect() as conn:
        database_existance = await conn.execute(
            text(
                "SELECT 1 FROM INFORMATION_SCHEMA.SCHEMATA"  # noqa: S608
                f" WHERE SCHEMA_NAME='{settings.db_base}';",
            )
        )
        database_exists = database_existance.scalar() == 1

    if database_exists:
        await drop_database()

    async with engine.connect() as conn:
        await conn.execute(
            text(
                f'CREATE DATABASE {settings.db_base};'
            )
        )

async def drop_database() -> None:
    """Drop current database."""
    engine = create_async_engine(str(settings.db_url.with_path("/mysql")))
    async with engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE {settings.db_base};'))

