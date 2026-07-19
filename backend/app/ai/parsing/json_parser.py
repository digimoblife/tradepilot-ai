"""Strict JSON parser (TP-0705).

Parses extracted JSON text into a Python dictionary with strict rules:
rejects NaN, Infinity, -Infinity, duplicate critical keys,
and non-object root values.
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Critical keys that must never be duplicated
# ---------------------------------------------------------------------------

CRITICAL_KEYS: frozenset[str] = frozenset(
    {
        "analysis_type",
        "schema_version",
        "session_id",
        "trade_state",
        "position_assessment",
    }
)

# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class ParseError(Exception):
    """Base for all JSON parse errors."""

    code: str = "JSON_PARSE_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class ParseSyntaxError(ParseError):
    code: str = "JSON_SYNTAX_INVALID"


class ParseNonFiniteNumberError(ParseError):
    code: str = "JSON_NON_FINITE_NUMBER"


class ParseDuplicateCriticalKeyError(ParseError):
    code: str = "JSON_DUPLICATE_CRITICAL_KEY"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_json_object(json_text: str) -> dict[str, object]:
    """Parse *json_text* into a Python dict with strict validation.

    Raises ``ParseError`` subclasses for invalid root types,
    duplicate critical keys, non-finite numbers, or syntax errors.
    """
    if not json_text or not json_text.strip():
        raise ParseSyntaxError(message="JSON text is empty")

    try:
        parsed = json.loads(
            json_text,
            object_pairs_hook=_check_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except json.JSONDecodeError as exc:
        raise ParseSyntaxError(message=str(exc)) from exc
    except (ParseDuplicateCriticalKeyError, ParseNonFiniteNumberError):
        raise
    except Exception as exc:
        raise ParseSyntaxError(message=str(exc)) from exc

    if not isinstance(parsed, dict):
        raise ParseSyntaxError(
            message=f"Expected JSON object, got {type(parsed).__name__}",
        )

    # noinspection PyTypeChecker
    return parsed


# ---------------------------------------------------------------------------
# Convenience composition
# ---------------------------------------------------------------------------


def extract_and_parse_json(raw_output: str) -> dict[str, object]:
    """Convenience: extract + parse in one call."""
    from app.ai.parsing.json_extractor import extract_json_object

    json_text = extract_json_object(raw_output)
    return parse_json_object(json_text)


# ---------------------------------------------------------------------------
# Internal hooks
# ---------------------------------------------------------------------------


def _check_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    """``object_pairs_hook`` that rejects duplicate critical keys."""
    seen: set[str] = set()
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in CRITICAL_KEYS and key in seen:
            raise ParseDuplicateCriticalKeyError(
                message=f"Duplicate critical key: {key!r}",
            )
        seen.add(key)
        result[key] = value
    return result


def _reject_non_finite(value: str) -> float:
    """``parse_constant`` that rejects NaN, Infinity, -Infinity."""
    raise ParseNonFiniteNumberError(
        message=f"Non-finite JSON number not allowed: {value!r}",
    )
