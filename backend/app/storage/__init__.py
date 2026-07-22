"""TradePilot AI evidence storage layer."""

from typing import Any

from app.storage.base import (
    FileStorage,
    StorageError,
    StorageFileNotFoundError,
    StorageInvalidPathError,
    StorageReadError,
    StorageWriteError,
    StoredFile,
)
from app.storage.local import LocalFileStorage


def create_file_storage(config: Any | None = None) -> LocalFileStorage:
    """Build a ``LocalFileStorage`` from application configuration.

    Use this factory wherever a production storage instance is needed
    to ensure the same root path is used by all callers.
    """
    from pathlib import Path

    if config is None:
        from app.config import AppConfig

        config = AppConfig()
    return LocalFileStorage(root=Path(config.storage_root))

__all__ = [
    "FileStorage",
    "LocalFileStorage",
    "StorageError",
    "StorageFileNotFoundError",
    "StorageInvalidPathError",
    "StorageReadError",
    "StorageWriteError",
    "StoredFile",
    "create_file_storage",
]
