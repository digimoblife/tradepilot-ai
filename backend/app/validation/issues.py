"""Normalized validation issue types for the TradePilot AI validation layer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ValidationCategory(StrEnum):
    SCHEMA = "SCHEMA"
    REQUIRED = "REQUIRED"
    TYPE = "TYPE"
    FORMAT = "FORMAT"
    ENUM = "ENUM"
    RANGE = "RANGE"
    ADDITIONAL_PROPERTY = "ADDITIONAL_PROPERTY"
    CONDITIONAL = "CONDITIONAL"
    REFERENCE = "REFERENCE"


class ValidationSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# JSON-compatible value type (recursive)
JsonValue = str | int | float | bool | None | list[Any] | dict[str, Any]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single normalized validation issue."""

    code: str
    category: ValidationCategory
    severity: ValidationSeverity
    path: str
    message: str
    expected: JsonValue | None = None
    actual: JsonValue | None = None


@dataclass(frozen=True, slots=True)
class JsonSchemaValidationResult:
    """Result of validating a payload against a JSON Schema."""

    valid: bool
    schema_name: str
    schema_version: str
    schema_id: str
    issues: tuple[ValidationIssue, ...]
