"""Structured logging for the worker application.

Provides JSON-formatted log output suitable for production ingestion,
with automatic secret redaction, production prompt omission, and
support for structured contextual fields (``request_id``, ``session_id``,
``analysis_job_id``, ``provider``, ``model``, ``schema``, ``attempt``,
``validation_result``, ``duration``).

Usage::

    from app.logging import configure_logging, get_logger

    configure_logging(level="INFO", production=True)
    log = get_logger(__name__, session_id="abc-123")
    log.info("Job processed", extra={"job_id": "def-456"})
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, MutableMapping

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECRET_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "password",
        "secret",
        "token",
        "authorization",
        "private_key",
        "access_key",
        "refresh_token",
    }
)

PROMPT_KEYS: frozenset[str] = frozenset(
    {
        "user_prompt",
        "system_prompt",
        "raw_output",
        "prompt_text",
    }
)

CONTEXTUAL_FIELDS: frozenset[str] = frozenset(
    {
        "request_id",
        "session_id",
        "analysis_job_id",
        "provider",
        "model",
        "schema",
        "attempt",
        "validation_result",
        "duration",
    }
)

REDACTED = "[REDACTED]"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENV_PRODUCTION = "production"


def _is_secret_key(key: str) -> bool:
    """Return True when *key* (lower-cased) contains any secret substring."""
    lower = key.lower()
    return any(sk in lower for sk in SECRET_KEYS)


def _is_prompt_key(key: str) -> bool:
    """Return True when *key* matches a known prompt-content field."""
    return key.lower() in PROMPT_KEYS


def _redact(obj: object, key_hint: str = "") -> object:
    """Recursively redact sensitive values.

    Dict values whose key matches a secret pattern are replaced with
    ``REDACTED``.  Nested dicts and lists are traversed.
    """
    if isinstance(obj, dict):
        return {
            k: REDACTED if _is_secret_key(k) else _redact(v, key_hint=k) for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(item, key_hint) for item in obj]
    return obj


def _should_skip_in_production(key: str, value: object) -> bool:
    """Return True when the key-value pair should be omitted in production.

    Prompt-content fields (raw prompts, raw AI output) are omitted so that
    sensitive analysis instructions are never written to the log stream.
    """
    if _is_prompt_key(key) and isinstance(value, str) and len(value) > 0:
        return True
    return False


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------


class StructuredFormatter(logging.Formatter):
    """JSON log formatter with secret redaction and production prompt omission.

    Parameters
    ----------
    production:
        When ``True``, prompt-content fields are stripped from the output.
    """

    def __init__(self, production: bool = False) -> None:
        super().__init__()
        self._production = production

    def format(self, record: logging.LogRecord) -> str:
        # Standard fields
        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Exception info
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)

        # Structured contextual fields from ``extra``
        extra = _collect_extra(record)
        redacted = _redact(extra)

        for field in CONTEXTUAL_FIELDS:
            value = redacted.get(field)
            if value is not None:
                entry[field] = value

        # Additional non-contextual extra fields (attached as ``extra``)
        for key, value in redacted.items():
            if key not in CONTEXTUAL_FIELDS and not key.startswith("_"):
                if self._production and _should_skip_in_production(key, value):
                    continue
                entry[key] = value

        return json.dumps(entry, default=str, sort_keys=True)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802
        # We handle timestamps ourselves via record.created
        return ""


def _collect_extra(record: logging.LogRecord) -> dict[str, Any]:
    """Collect user-supplied ``extra`` fields from a LogRecord.

    ``extra`` fields are attributes on the record that are not part of the
    standard set.
    """
    standard = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }
    extra: dict[str, Any] = {}
    for key in dir(record):
        if key.startswith("_") or key in standard:
            continue
        try:
            val = getattr(record, key)
        except Exception:
            continue
        if isinstance(val, (str, int, float, bool, dict, list, type(None))):
            extra[key] = val
    return extra


# ---------------------------------------------------------------------------
# Logger adapter
# ---------------------------------------------------------------------------


class ContextAdapter(logging.LoggerAdapter):
    """A logger adapter that attaches bound context to every log call.

    Usage::

        log = ContextAdapter(logging.getLogger(__name__), {"session_id": "abc"})
        log.info("message")                          # session_id attached
        log.info("message", extra={"provider": "x"})  # merged
    """

    def process(
        self,
        msg: str,
        kwargs: MutableMapping[str, object],
    ) -> tuple[str, MutableMapping[str, object]]:
        extra = dict(self.extra)
        extra.update(kwargs.get("extra", {}))
        kwargs["extra"] = extra
        return msg, kwargs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_logger(name: str, **context: object) -> ContextAdapter:
    """Return a structured logger with *context* bound to every call.

    Example::

        log = get_logger(__name__, session_id="abc-123")
        log.info("Processing job")             # includes session_id
        log.info("Provider called", extra={"provider": "gemini"})
    """
    return ContextAdapter(logging.getLogger(name), context)


def configure_logging(
    level: str = "INFO",
    production: bool = False,
) -> None:
    """Configure root logger with structured JSON output.

    Parameters
    ----------
    level:
        Log level string (e.g. ``"DEBUG"``, ``"INFO"``).
    production:
        When ``True``, prompt-content fields are stripped from log records.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter(production=production))

    root = logging.getLogger()
    # Remove any pre-existing handlers to avoid duplicate output
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Silence overly verbose third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def is_production() -> bool:
    """Return the production flag, checking env var override first.

    The ``TRADEPILOT_LOG_PRODUCTION`` environment variable, when set to
    ``1``, ``true``, or ``yes`` (case-insensitive), overrides the
    programmatic ``production`` flag passed to :func:`configure_logging`.
    """
    val = os.environ.get("TRADEPILOT_LOG_PRODUCTION", "").lower()
    return val in ("1", "true", "yes")
