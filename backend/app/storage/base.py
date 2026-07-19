"""Provider-independent storage contract for evidence file persistence."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredFile:
    """Result of a successful file store operation."""

    file_reference: str
    generated_filename: str
    original_filename: str
    checksum_sha256: str
    size_bytes: int


class FileStorage(Protocol):
    """Provider-independent interface for evidence file storage."""

    def store(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        original_filename: str,
        content: bytes,
    ) -> StoredFile:
        """Store file bytes and return metadata."""

    def read(self, *, file_reference: str) -> bytes:
        """Read stored file bytes by reference."""

    def delete(self, *, file_reference: str) -> None:
        """Delete a stored file by reference."""


# ---------------------------------------------------------------------------
# Stable storage errors
# ---------------------------------------------------------------------------


class StorageError(Exception):
    """Base exception for all storage-layer errors."""

    code: str = "STORAGE_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class StorageInvalidPathError(StorageError):
    """Raised when a file reference is unsafe or malformed."""

    code: str = "STORAGE_INVALID_PATH"


class StorageFileNotFoundError(StorageError):
    """Raised when a stored file cannot be found."""

    code: str = "STORAGE_FILE_NOT_FOUND"


class StorageWriteError(StorageError):
    """Raised when a file write operation fails."""

    code: str = "STORAGE_WRITE_FAILED"


class StorageReadError(StorageError):
    """Raised when a file read operation fails."""

    code: str = "STORAGE_READ_FAILED"
