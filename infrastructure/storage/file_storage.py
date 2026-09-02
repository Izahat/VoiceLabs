"""Safe, streaming file storage for user media and generated assets."""

from __future__ import annotations

import hashlib
import mimetypes
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredFile:
    path: Path
    original_filename: str
    mime_type: str | None
    size_bytes: int
    sha256: str
    kind: str


class FileStorage:
    """Store media outside SQLite and return durable metadata for persistence."""

    CHUNK_SIZE = 1024 * 1024
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_suffix(filename: str) -> str:
        suffix = Path(filename or "upload.bin").suffix.lower()
        return suffix if suffix and len(suffix) <= 10 and suffix.isascii() else ".bin"

    @classmethod
    def _kind_for(cls, filename: str, mime_type: str | None) -> str:
        if mime_type and mime_type.startswith("video/"):
            return "video"
        if Path(filename).suffix.lower() in cls.VIDEO_EXTENSIONS:
            return "video"
        return "audio"

    def _destination(self, user_id: str, asset_id: str, filename: str) -> Path:
        destination = self.root / "users" / user_id / "assets" / f"{asset_id}{self._safe_suffix(filename)}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination

    async def save_upload(self, upload, *, user_id: str, asset_id: str) -> StoredFile:
        """Stream a FastAPI UploadFile into durable storage."""
        filename = Path(upload.filename or "upload.bin").name
        destination = self._destination(user_id, asset_id, filename)
        digest = hashlib.sha256()
        size = 0

        with destination.open("wb") as output:
            while chunk := await upload.read(self.CHUNK_SIZE):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)

        return StoredFile(
            path=destination,
            original_filename=filename,
            mime_type=upload.content_type or mimetypes.guess_type(filename)[0],
            size_bytes=size,
            sha256=digest.hexdigest(),
            kind=self._kind_for(filename, upload.content_type),
        )

    def save_existing(self, source: Path, *, user_id: str, asset_id: str, original_filename: str) -> StoredFile:
        """Copy a generated file into durable storage and calculate its checksum."""
        destination = self._destination(user_id, asset_id, original_filename)
        digest = hashlib.sha256()
        size = 0
        with source.open("rb") as input_file, destination.open("wb") as output:
            while chunk := input_file.read(self.CHUNK_SIZE):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)

        mime_type = mimetypes.guess_type(original_filename)[0]
        return StoredFile(
            path=destination,
            original_filename=Path(original_filename).name,
            mime_type=mime_type,
            size_bytes=size,
            sha256=digest.hexdigest(),
            kind=self._kind_for(original_filename, mime_type),
        )

    def delete(self, path: Path) -> None:
        """Delete only files contained inside this storage root."""
        resolved_root = self.root.resolve()
        resolved_path = path.resolve()
        if resolved_root not in resolved_path.parents:
            raise ValueError("Refusing to delete a file outside storage root")
        resolved_path.unlink(missing_ok=True)
