"""
Local filesystem-backed storage used by step 1 APIs
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import shutil

import aiofiles

from app.core.errors import ApiError
from app.common.settings import settings


@dataclass(slots=True)
class StoredFile:
    """Stored file metadata."""

    pathname: str
    filename: str
    size: int
    uploaded_at: datetime


class LocalStorageService:
    """Store source attachments under a local root directory."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = (root or settings.storage_root).resolve()

    def _resolve(self, pathname: str) -> Path:
        normalized = PurePosixPath(pathname)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ApiError(
                400,
                "Invalid storage path",
                data={
                    "why": "Storage path must stay inside the configured storage root.",
                    "fix": "Use a relative path such as sources/{id}/file.md.",
                },
            )
        resolved = (self._root / Path(*normalized.parts)).resolve()
        if not str(resolved).startswith(str(self._root)):
            raise ApiError(
                400,
                "Invalid storage path",
                data={
                    "why": "Resolved path escaped the configured storage root.",
                    "fix": "Use a safe relative storage path.",
                },
            )
        return resolved

    async def list_files(self, prefix: str) -> list[StoredFile]:
        """List files under a prefix."""

        prefix_path = self._resolve(prefix)
        if not prefix_path.exists():
            return []

        files: list[StoredFile] = []
        prefix_value = PurePosixPath(prefix).as_posix().rstrip("/") + "/"
        for file_path in sorted(prefix_path.rglob("*")):
            if not file_path.is_file():
                continue
            stat = file_path.stat()
            pathname = file_path.relative_to(self._root).as_posix()
            files.append(
                StoredFile(
                    pathname=pathname,
                    filename=pathname.removeprefix(prefix_value),
                    size=stat.st_size,
                    uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                ),
            )
        return files

    async def put_file(
        self,
        path: str,
        content: bytes,
        content_type: str | None = None,
    ) -> None:
        """Persist a file."""

        del content_type
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target, "wb") as handle:
            await handle.write(content)

    async def delete_file(self, path: str) -> None:
        """Delete a single file if present."""

        target = self._resolve(path)
        if target.exists():
            target.unlink()

    async def delete_prefix(self, prefix: str) -> None:
        """Delete a directory tree if present."""

        target = self._resolve(prefix)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)

storage = LocalStorageService()
