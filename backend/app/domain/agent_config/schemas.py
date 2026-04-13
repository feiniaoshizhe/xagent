"""Schemas for agent config APIs."""

from pydantic import Field

from app.core.schema import CustomModel
from app.models import CitationFormat, ResponseStyle


class AgentConfigResponse(CustomModel):
    id: str
    name: str
    additional_prompt: str | None = None
    response_style: ResponseStyle
    language: str
    default_model: str | None = None
    max_steps_multiplier: float
    temperature: float
    search_instructions: str | None = None
    citation_format: CitationFormat
    is_active: bool


class UpdateAgentConfigRequest(CustomModel):
    additional_prompt: str | None = None
    response_style: ResponseStyle | None = None
    language: str | None = None
    default_model: str | None = None
    max_steps_multiplier: float | None = Field(default=None, ge=0.5, le=3.0)
    temperature: float | None = Field(default=None, ge=0, le=2)
    search_instructions: str | None = None
    citation_format: CitationFormat | None = None
