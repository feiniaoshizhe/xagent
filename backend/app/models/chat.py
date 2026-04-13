"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/13 14:32
Description:
FilePath: chat
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


class ChatMode(str, Enum):
    """Chat modes."""

    CHAT = "chat"
    ADMIN = "admin"


class ChatModel(Base):
    """Chat session metadata."""

    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[ChatMode] = mapped_column(
        SQLEnum(ChatMode, native_enum=False),
        nullable=False,
        default=ChatMode.CHAT,
    )
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    share_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class MessageRole(str, Enum):
    """Supported message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageFeedback(str, Enum):
    """Feedback values."""

    POSITIVE = "positive"
    NEGATIVE = "negative"

class MessageSource(str, Enum):
    """Message source values."""

    WEB = "web"
    API = "api"

class MessageModel(Base):
    """Persisted message."""

    __tablename__ = "messages"

    chat_id: Mapped[str] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole, native_enum=False),
        nullable=False,
    )
    parts: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    feedback: Mapped[MessageFeedback | None] = mapped_column(
        SQLEnum(MessageFeedback, native_enum=False),
        nullable=True,
    )
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[MessageSource | None] = mapped_column(
        SQLEnum(MessageSource, native_enum=False),
        nullable=True,
    )

