"""Local filesystem-based evidence storage adapter."""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from app.storage.base import (
    FileStorage,
    StorageFileNotFoundError,
    StorageInvalidPathError,
    StorageReadError,
    StorageWriteError,
    StoredFile,
)

_safe_ext_pattern = re.compile(r"^[a-zA-Z0-9]+$")


class LocalFileStorage(FileStorage):
    """Stores evidence files on the local filesystem.

    Files are organised under a configurable root directory in a
    ``<user_id>/<session_id>/<generated_filename>`` hierarchy.
    """

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        original_filename: str,
        content: bytes,
    ) -> StoredFile:
        generated = self._generate_filename(original_filename)
        relative = Path(str(user_id)) / str(session_id) / generated
        full_path = self._root / relative

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageWriteError(
                message=f"Failed to create storage directory: {exc}",
            ) from exc

        try:
            full_path.write_bytes(content)
        except OSError as exc:
            raise StorageWriteError(message=f"Failed to write file: {exc}") from exc

        checksum = hashlib.sha256(content).hexdigest()
        size = len(content)

        return StoredFile(
            file_reference=str(relative),
            generated_filename=generated,
            original_filename=original_filename,
            checksum_sha256=checksum,
            size_bytes=size,
        )

    def read(self, *, file_reference: str) -> bytes:
        path = self._resolve_safe(file_reference)
        if not path.is_file():
            raise StorageFileNotFoundError(
                message=f"File not found: {file_reference}",
            )
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageReadError(
                message=f"Failed to read file: {exc}",
            ) from exc

    def delete(self, *, file_reference: str) -> None:
        path = self._resolve_safe(file_reference)
        if not path.is_file():
            raise StorageFileNotFoundError(
                message=f"File not found: {file_reference}",
            )
        try:
            path.unlink()
        except OSError as exc:
            raise StorageWriteError(
                message=f"Failed to delete file: {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_extension(original_filename: str) -> str:
        ext = Path(original_filename).suffix
        if ext:
            stem = ext[1:]
            if stem and _safe_ext_pattern.match(stem):
                return ext
        return ""

    @staticmethod
    def _generate_filename(original_filename: str) -> str:
        base = uuid.uuid4().hex
        ext = LocalFileStorage._safe_extension(original_filename)
        return f"{base}{ext}"

    def _resolve_safe(self, reference: str) -> Path:
        if not reference:
            raise StorageInvalidPathError(
                message="File reference must not be empty",
            )

        if "\x00" in reference:
            raise StorageInvalidPathError(
                message="File reference contains null characters",
            )

        p = Path(reference)
        if p.is_absolute():
            raise StorageInvalidPathError(
                message="Absolute file references are not allowed",
            )

        resolved = (self._root / reference).resolve()
        resolved_root = self._root.resolve()

        try:
            resolved.relative_to(resolved_root)
        except ValueError:
            raise StorageInvalidPathError(
                message=f"File reference {reference!r} escapes storage root",
            )

        return resolved
