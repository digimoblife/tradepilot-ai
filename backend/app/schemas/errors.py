"""Stable error types for the TradePilot AI schema package."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping


class SchemaPackageError(Exception):
    """Base exception for all schema-package errors."""

    def __init__(
        self,
        code: str,
        message: str,
        path: Path | None = None,
        location: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.path = path
        self.location = location
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.code, self.message]
        if self.path:
            parts.append(f"path={self.path}")
        if self.location:
            parts.append(f"location={self.location}")
        return " | ".join(parts)


class ManifestLoadError(SchemaPackageError):
    """Raised when the manifest file cannot be read or parsed."""


class ManifestValidationError(SchemaPackageError):
    """Raised when the manifest content fails structural or semantic validation."""
