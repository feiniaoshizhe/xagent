"""Business logic for sources."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath
import re
import uuid

from fastapi import UploadFile
from redis.asyncio import ConnectionPool, Redis

from app.core.errors import ApiError
from app.models.source import SourceModel, SourceType
from app.repository.repository import SourceRepository
from app.domain.sources.schemas import (
    CreateSourceRequest,
    SourceFileItem,
    SourceFilesResponse,
    SourceItem,
    SourceSection,
    SourcesGroupedResponse,
    UpdateSourceRequest,
    UploadSourceFilesResponse,
    UploadedSourceFileResult,
)
from app.services.storage import LocalStorageService
from app.common.settings import settings

ALLOWED_EXTENSIONS = (".md", ".mdx", ".txt", ".yml", ".yaml", ".json")
MAX_FILE_SIZE = 8 * 1024 * 1024
LAST_SOURCE_SYNC_KEY = "sources:last-sync"


class SourceService:
    def __init__(
        self,
        repository: SourceRepository,
        storage: LocalStorageService | None = None,
    ) -> None:
        self._repository = repository
        self._storage = storage or LocalStorageService()

    async def list_grouped(
        self,
        redis_pool: ConnectionPool | None = None,
    ) -> SourcesGroupedResponse:
        all_sources = await self._repository.list_all()
        youtube_enabled = bool(settings.youtube_api_key)
        github = [SourceItem.model_validate(item) for item in all_sources if item.type == SourceType.GITHUB]
        youtube = (
            [SourceItem.model_validate(item) for item in all_sources if item.type == SourceType.YOUTUBE]
            if youtube_enabled
            else []
        )
        files = [SourceItem.model_validate(item) for item in all_sources if item.type == SourceType.FILE]
        snapshot_repo = settings.github_snapshot_repo or None
        return SourcesGroupedResponse(
            total=len(github) + len(youtube) + len(files),
            last_sync_at=await self._get_last_sync_at(redis_pool),
            youtube_enabled=youtube_enabled,
            snapshot_repo=snapshot_repo,
            snapshot_branch=settings.github_snapshot_branch or "main",
            snapshot_repo_url=f"https://github.com/{snapshot_repo}" if snapshot_repo else None,
            github=SourceSection(count=len(github), sources=github),
            youtube=SourceSection(count=len(youtube), sources=youtube),
            file=SourceSection(count=len(files), sources=files),
        )

    async def create_source(self, request: CreateSourceRequest) -> SourceItem:
        payload = self._build_payload(request.type, request.model_dump(), None)
        payload["id"] = str(uuid.uuid4())
        source = await self._repository.create(payload)
        return SourceItem.model_validate(source)

    async def update_source(
        self,
        source_id: int,
        request: UpdateSourceRequest,
    ) -> SourceItem:
        source = await self._get_source_or_404(source_id)
        merged = {
            "label": source.label,
            "base_path": source.base_path,
            "repo": source.repo,
            "branch": source.branch,
            "content_path": source.content_path,
            "output_path": source.output_path,
            "readme_only": source.readme_only,
            "channel_id": source.channel_id,
            "handle": source.handle,
            "max_videos": source.max_videos,
        }
        merged.update(request.model_dump(exclude_unset=True))
        payload = self._build_payload(source.type, merged, source)
        payload["updated_at"] = datetime.now(UTC)
        updated = await self._repository.update(source, payload)
        return SourceItem.model_validate(updated)

    async def delete_source(self, source_id: int) -> None:
        source = await self._get_source_or_404(source_id)
        await self._repository.delete(source)
        if source.type == SourceType.FILE:
            await self._storage.delete_prefix(self._source_prefix(source.id))

    async def list_files(self, source_id: int) -> SourceFilesResponse:
        source = await self._get_file_source_or_400(source_id)
        files = await self._storage.list_files(self._source_prefix(source.id))
        return SourceFilesResponse(
            files=[
                SourceFileItem(
                    pathname=item.pathname,
                    filename=item.filename,
                    size=item.size,
                    uploaded_at=item.uploaded_at,
                )
                for item in files
            ],
        )

    async def upload_files(
        self,
        source_id: int,
        files: list[UploadFile],
    ) -> UploadSourceFilesResponse:
        await self._get_file_source_or_400(source_id)
        if not files:
            raise ApiError(400, "No files provided", error="Bad Request")

        results: list[UploadedSourceFileResult] = []
        for file in files:
            filename = file.filename or ""
            if not filename:
                results.append(UploadedSourceFileResult(filename="unknown", error="Missing filename"))
                continue
            if not self._is_allowed_file(filename):
                results.append(
                    UploadedSourceFileResult(
                        filename=filename,
                        error=f"File type not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}",
                    ),
                )
                continue
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                results.append(
                    UploadedSourceFileResult(filename=filename, error="File exceeds 8MB limit"),
                )
                continue
            pathname = f"{self._source_prefix(source_id)}{filename}"
            await self._storage.put_file(pathname, content, file.content_type)
            results.append(
                UploadedSourceFileResult(
                    filename=filename,
                    pathname=pathname,
                    size=len(content),
                ),
            )
        return UploadSourceFilesResponse(files=results)

    async def delete_file(self, source_id: int, pathname: str) -> None:
        await self._get_file_source_or_400(source_id)
        prefix = self._source_prefix(source_id)
        if not pathname.startswith(prefix):
            raise ApiError(
                403,
                "File does not belong to this source",
                error="Forbidden",
                data={
                    "why": "The pathname is outside the source attachment prefix.",
                    "fix": f"Use a pathname starting with {prefix}.",
                },
            )
        await self._storage.delete_file(pathname)

    async def _get_source_or_404(self, source_id: int) -> SourceModel:
        source = await self._repository.get_by_id(source_id)
        if source is None:
            raise ApiError(
                404,
                "Source not found",
                error="Not Found",
                data={
                    "why": "No source exists with this ID.",
                    "fix": "Verify the source ID from the sources list.",
                },
            )
        return source

    async def _get_file_source_or_400(self, source_id: int) -> SourceModel:
        source = await self._get_source_or_404(source_id)
        if source.type != SourceType.FILE:
            raise ApiError(
                400,
                "Source is not a file source",
                error="Bad Request",
                data={
                    "why": "The requested source does not support file attachments.",
                    "fix": "Use a source with type=file.",
                },
            )
        return source

    async def _get_last_sync_at(self, redis_pool: ConnectionPool | None) -> int | None:
        if redis_pool is None:
            return None
        async with Redis(connection_pool=redis_pool) as redis:
            value = await redis.get(LAST_SOURCE_SYNC_KEY)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _build_payload(
        self,
        source_type: SourceType,
        raw_payload: dict[str, object],
        source: SourceModel | None,
    ) -> dict[str, object]:
        label = self._normalize_text(raw_payload.get("label"))
        if not label:
            raise ApiError(
                400,
                "Validation error",
                error="Bad Request",
                data={"why": "label is required", "fix": "Provide a non-empty source label."},
            )

        payload: dict[str, object] = {
            "type": source_type,
            "label": label,
            "base_path": self._normalize_text(raw_payload.get("base_path")) or self._default_base_path(source_type),
            "repo": None,
            "branch": None,
            "content_path": None,
            "output_path": self._normalize_text(raw_payload.get("output_path")) or self._slugify(label),
            "readme_only": None,
            "channel_id": None,
            "handle": None,
            "max_videos": None,
        }

        if source_type == SourceType.GITHUB:
            repo = self._normalize_text(raw_payload.get("repo"))
            if not repo or not re.fullmatch(r"[^/\s]+/[^/\s]+", repo):
                raise ApiError(
                    400,
                    "Validation error",
                    error="Bad Request",
                    data={
                        "why": "repo is required for github source",
                        "fix": "Provide repo in owner/repo format.",
                    },
                )
            payload.update(
                {
                    "repo": repo,
                    "branch": self._normalize_text(raw_payload.get("branch")) or "main",
                    "content_path": self._normalize_text(raw_payload.get("content_path")),
                    "readme_only": bool(raw_payload.get("readme_only") or False),
                },
            )
        elif source_type == SourceType.YOUTUBE:
            channel_id = self._normalize_text(raw_payload.get("channel_id"))
            if not channel_id:
                raise ApiError(
                    400,
                    "Validation error",
                    error="Bad Request",
                    data={
                        "why": "channelId is required for youtube source",
                        "fix": "Provide a YouTube channel ID.",
                    },
                )
            payload.update(
                {
                    "channel_id": channel_id,
                    "handle": self._normalize_text(raw_payload.get("handle")),
                    "max_videos": int(raw_payload.get("max_videos") or 50),
                },
            )

        if source is None:
            payload["created_at"] = datetime.now(UTC)
        return payload

    def _default_base_path(self, source_type: SourceType) -> str:
        return {
            SourceType.GITHUB: "/docs",
            SourceType.YOUTUBE: "/youtube",
            SourceType.FILE: "/files",
        }[source_type]

    def _normalize_text(self, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return str(value)
        stripped = value.strip()
        return stripped or None

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", value.lower().strip())
        slug = re.sub(r"[\s_-]+", "-", slug)
        return slug.strip("-") or "source"

    def _is_allowed_file(self, filename: str) -> bool:
        return filename.lower().endswith(ALLOWED_EXTENSIONS)

    def _source_prefix(self, source_id: int) -> str:
        return f"{PurePosixPath('sources', str(source_id)).as_posix()}/"
