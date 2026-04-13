"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/13 14:30
Description:
FilePath: agent_config
"""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Boolean, Float, Text, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


class ResponseStyle(str, Enum):
    """Assistant response styles."""

    CONCISE = "concise"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"

class CitationFormat(str, Enum):
    """Citation rendering modes."""

    INLINE = "inline"
    FOOTNOTE = "footnote"

class LanguageType(str, Enum):
    """Supported languages."""
    ZH =  "zh"
    EN = "en"

class AgentConfigModel(Base):
    """
    Active assistant configuration.
    """

    __tablename__ = "agent_config"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    additional_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_style: Mapped[ResponseStyle | None] = mapped_column(
        SQLEnum(ResponseStyle, native_enum=False),
        nullable=True
    )
    language: Mapped[LanguageType] = mapped_column(
        SQLEnum(LanguageType, native_enum=False),
        nullable=True,
        default=LanguageType.ZH
    )
    default_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_steps_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    search_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_format: Mapped[CitationFormat | None] = mapped_column(
        SQLEnum(CitationFormat, native_enum=False),
        default=None,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


