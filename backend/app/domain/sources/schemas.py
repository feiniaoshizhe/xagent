"""Schemas for source APIs."""

from datetime import datetime

from pydantic import Field

from app.core.schema import BaseModel
from app.models import SourceType


class SourceItem(BaseModel):
    id: str
    type: SourceType
    label: str
    repo: str | None = None
    branch: str | None = None
    content_path: str | None = None
    output_path: str | None = None
    readme_only: bool | None = None
    channel_id: str | None = None
    handle: str | None = None
    max_videos: int | None = None
    base_path: str | None = None
    created_at: datetime
    updated_at: datetime


class SourceSection(BaseModel):
    count: int
    sources: list[SourceItem]


class SourcesGroupedResponse(BaseModel):
    total: int
    last_sync_at: int | None = None
    youtube_enabled: bool
    snapshot_repo: str | None = None
    snapshot_branch: str | None = None
    snapshot_repo_url: str | None = None
    github: SourceSection
    youtube: SourceSection
    file: SourceSection


class CreateSourceRequest(BaseModel):
    type: SourceType
    label: str = Field(min_length=1)
    base_path: str | None = None
    repo: str | None = None
    branch: str | None = None
    content_path: str | None = None
    output_path: str | None = None
    readme_only: bool | None = None
    channel_id: str | None = None
    handle: str | None = None
    max_videos: int | None = None


class UpdateSourceRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    base_path: str | None = None
    repo: str | None = None
    branch: str | None = None
    content_path: str | None = None
    output_path: str | None = None
    readme_only: bool | None = None
    channel_id: str | None = None
    handle: str | None = None
    max_videos: int | None = None


class SourceFileItem(BaseModel):
    pathname: str
    filename: str
    size: int
    uploaded_at: datetime


class SourceFilesResponse(BaseModel):
    files: list[SourceFileItem]


class UploadedSourceFileResult(BaseModel):
    filename: str
    pathname: str | None = None
    size: int | None = None
    error: str | None = None


class UploadSourceFilesResponse(BaseModel):
    files: list[UploadedSourceFileResult]


class DeleteSourceFileRequest(BaseModel):
    pathname: str = Field(min_length=1)


class DeleteSuccessResponse(BaseModel):
    success: bool = True
