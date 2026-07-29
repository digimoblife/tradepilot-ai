"""Deterministic conversion of application values to JSON-native values."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Mapping
from uuid import UUID


def to_json_safe(value: object, *, path: str = "$") -> object:
    """Convert supported application values without silently stringifying unknowns."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return to_json_safe(value.value, path=path)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise TypeError(f"Naive datetime is not JSON-safe at {path}")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(f"Non-string mapping key is not JSON-safe at {path}")
            result[key] = to_json_safe(nested, path=f"{path}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
    raise TypeError(f"Unsupported JSON value {type(value).__name__} at {path}")
