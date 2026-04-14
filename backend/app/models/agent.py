"""
Author: xuyoushun
Email: xuyoushun@bestpay.com.cn
Date: 2026/4/14 10:46
Description:
FilePath: agent
"""
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any

from sqlalchemy import (
    Boolean,
    Text,
    String,
    JSON,
    DateTime,
    Integer,
    ForeignKey, Float
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.schemas.node import Node, Edge


class RunStatus(str, Enum):
    IDLE = "IDLE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

class TradingMode(str, Enum):
    ONE_TIME = "one-time"
    CONTINUOUS = "continuous"
    ADVISORY = "advisory"

class ApiKey(Base):
    __tablename__ = "api_keys"

    # API key details
    provider: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)  # e.g., "ANTHROPIC_API_KEY"
    key_value: Mapped[str] = mapped_column(Text, nullable=False)  # The actual API key (encrypted in production)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Enable/disable without deletion

    # Optional metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # Human-readable description
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Track usage

class AgentFlow(Base):

    __tablename__ = "agent_flows"

    # 元数据
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # React Flow 状态字段
    nodes: Mapped[List[Node]] = mapped_column(JSON, nullable=False, comment="节点信息")  # Store React Flow nodes as JSON
    edges: Mapped[List[Edge]] = mapped_column(JSON, nullable=False, comment="边信息")  # Store React Flow edges as JSON
    viewport: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="视图状态")  # Store viewport state (zoom, x, y)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="节点数据")  # Store node internal states (tickers, models, etc.)

    # 拓展字段
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)  # Mark as template for reuse
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # Store tags for categorization

class AgentFlowRun(Base):
    __tablename__ = "agent_flow_runs"

    flow_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_flows.id"), nullable=False,
                     index=True)

    # Run execution tracking
    status: Mapped[RunStatus] = mapped_column(SQLEnum(RunStatus), nullable=False, default=RunStatus.IDLE)  # IDLE, IN_PROGRESS, COMPLETE, ERROR
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Run configuration
    trading_mode: Mapped[TradingMode] = mapped_column(SQLEnum(TradingMode), nullable=False, default=TradingMode.ONE_TIME)  # one-time, continuous, advisory
    schedule: Mapped[str | None] = mapped_column(String(50), nullable=True)  # hourly, daily, weekly (for continuous mode)
    duration: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 1day, 1week, 1month (for continuous mode)

    # Run data
    request_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Store the request parameters (tickers, agents, models, etc.)
    initial_portfolio = mapped_column(JSON, nullable=True)  # Store initial portfolio state
    final_portfolio = mapped_column(JSON, nullable=True)  # Store final portfolio state
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Store the output/results from the run
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # Store error details if run failed

    # Metadata
    run_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # Sequential run number for this flow




class AgentFlowRunCycle(Base):
    """Individual analysis cycles within a trading session"""
    __tablename__ = "agent_flow_run_cycles"

    flow_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_flow_runs.id"), nullable=False, index=True)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3, etc. within the run

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Analysis results
    analyst_signals = mapped_column(JSON, nullable=True)  # All agent decisions/signals
    trading_decisions = mapped_column(JSON, nullable=True)  # Portfolio manager decisions
    executed_trades = mapped_column(JSON, nullable=True)  # Actual trades executed (paper trading)

    # Portfolio state after this cycle
    portfolio_snapshot = mapped_column(JSON, nullable=True)  # Cash, positions, performance metrics

    # Performance metrics for this cycle
    performance_metrics = mapped_column(JSON, nullable=True)  # Returns, sharpe ratio, etc.

    # Execution tracking
    status: Mapped[RunStatus] = mapped_column(SQLEnum(RunStatus), nullable=False, default=RunStatus.IN_PROGRESS)  # IN_PROGRESS, COMPLETED, ERROR
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # Store error details if cycle failed

    # Cost tracking
    llm_calls_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)  # Number of LLM calls made
    api_calls_count: Mapped[int] = mapped_column(Integer, nullable=True,  default=0)  # Number of financial API calls made
    estimated_cost: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Estimated cost in USD

    # Metadata
    trigger_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)  # scheduled, manual, market_event, etc.
    market_conditions = mapped_column(JSON, nullable=True)  # Market data snapshot at cycle start

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
