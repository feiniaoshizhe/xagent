"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/13 14:31
Description:
FilePath: source
"""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Boolean, Integer, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


class SourceType(str, Enum):
    """Supported source types."""

    GITHUB = "github"
    YOUTUBE = "youtube"
    FILE = "file"


class SourceModel(Base):
    """Knowledge source configuration."""

    __tablename__ = "sources"

    type: Mapped[SourceType] = mapped_column(
        SQLEnum(SourceType, native_enum=False),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    base_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    repo: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    readme_only: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    channel_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    handle: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_videos: Mapped[int | None] = mapped_column(Integer, nullable=True)


