"""Tests for worker structured logging (TP-1601).

Covers: structured output format, contextual fields, secret redaction,
nested redaction, production prompt omission, missing optional context,
worker logging initialisation.
"""

from __future__ import annotations

import json
import logging
import os
from io import StringIO
from typing import Any

import pytest

from app.logging import (
    CONTEXTUAL_FIELDS,
    REDACTED,
    ContextAdapter,
    StructuredFormatter,
    configure_logging,
    get_logger,
    is_production,
)

_ENV_KEY = "TRADEPILOT_LOG_PRODUCTION"


@pytest.fixture(autouse=True)
def _clean_env() -> Any:
    saved = os.environ.get(_ENV_KEY)
    if _ENV_KEY in os.environ:
        del os.environ[_ENV_KEY]
    yield
    if saved is not None:
        os.environ[_ENV_KEY] = saved
    elif _ENV_KEY in os.environ:
        del os.environ[_ENV_KEY]


@pytest.fixture
def capture_log() -> tuple[StructuredFormatter, StringIO]:
    buf = StringIO()
    formatter = StructuredFormatter(production=False)
    handler = logging.StreamHandler(buf)
    handler.setFormatter(formatter)
    logger = logging.getLogger("test_worker")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield formatter, buf
    logger.removeHandler(handler)


def _parse_log(buf: StringIO) -> dict[str, Any]:
    return json.loads(buf.getvalue().strip())


# ===================================================================
# 1. Structured output format
# ===================================================================


class TestStructuredFormat:
    def test_valid_json(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info("hello")
        record = _parse_log(buf)
        assert record["message"] == "hello"
        assert record["level"] == "INFO"
        assert record["logger"] == "test_worker"
        assert "timestamp" in record

    def test_timestamp_iso8601(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info("t")
        record = _parse_log(buf)
        assert isinstance(record["timestamp"], str)
        assert "+" in record["timestamp"] or record["timestamp"].endswith("Z")


# ===================================================================
# 2. Contextual fields
# ===================================================================


class TestContextualFields:
    @pytest.mark.parametrize("field", sorted(CONTEXTUAL_FIELDS))
    def test_field_appears_when_provided(self, field: str, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info("ctx", extra={field: "val"})
        record = _parse_log(buf)
        assert record.get(field) == "val"

    def test_missing_context_does_not_crash(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info("no extra")
        record = _parse_log(buf)
        assert record["message"] == "no extra"


# ===================================================================
# 3. Secret redaction
# ===================================================================


class TestSecretRedaction:
    def test_api_key_redacted(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info("s", extra={"api_key": "sk-xxx"})
        record = _parse_log(buf)
        assert record["api_key"] == REDACTED

    def test_password_redacted(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info("s", extra={"password": "hunter2"})
        record = _parse_log(buf)
        assert record["password"] == REDACTED

    def test_non_secret_unaffected(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info("safe", extra={"label": "hello"})
        record = _parse_log(buf)
        assert record["label"] == "hello"


# ===================================================================
# 4. Nested redaction
# ===================================================================


class TestNestedRedaction:
    def test_nested_dict(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info(
            "nested",
            extra={"creds": {"api_key": "sk-xxx", "user": "admin"}},
        )
        record = _parse_log(buf)
        assert record["creds"]["api_key"] == REDACTED
        assert record["creds"]["user"] == "admin"

    def test_list_of_dicts(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info(
            "list", extra={"items": [{"token": "t1"}, {"token": "t2"}]}
        )
        record = _parse_log(buf)
        assert record["items"][0]["token"] == REDACTED
        assert record["items"][1]["token"] == REDACTED


# ===================================================================
# 5. Production prompt omission
# ===================================================================


class TestProductionPromptOmission:
    def test_prompt_omitted(self) -> None:
        buf = StringIO()
        formatter = StructuredFormatter(production=True)
        handler = logging.StreamHandler(buf)
        handler.setFormatter(formatter)
        logger = logging.getLogger("test_prod")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("prod", extra={"user_prompt": "analyze"})
        record = json.loads(buf.getvalue().strip())
        assert "user_prompt" not in record
        logger.removeHandler(handler)

    def test_prompt_included_non_production(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_worker").info("dev", extra={"user_prompt": "analyze"})
        record = _parse_log(buf)
        assert record["user_prompt"] == "analyze"


# ===================================================================
# 6. Worker logging initialisation
# ===================================================================


class TestWorkerInit:
    def test_configure_logging(self) -> None:
        configure_logging(level="DEBUG", production=False)
        root = logging.getLogger()
        found = False
        for h in root.handlers:
            if isinstance(h.formatter, StructuredFormatter):
                found = True
        assert found

    def test_configure_logging_production(self) -> None:
        configure_logging(level="INFO", production=True)
        root = logging.getLogger()
        found = False
        for h in root.handlers:
            if isinstance(h.formatter, StructuredFormatter) and h.formatter._production:
                found = True
        assert found

    def test_is_production_default_false(self) -> None:
        assert not is_production()

    def test_is_production_via_env(self) -> None:
        os.environ[_ENV_KEY] = "true"
        assert is_production()


# ===================================================================
# 7. ContextAdapter
# ===================================================================


class TestContextAdapter:
    def test_bound_context(self, capture_log: Any) -> None:
        _, buf = capture_log
        log = ContextAdapter(
            logging.getLogger("test_worker"),
            {"session_id": "s1"},
        )
        log.log(logging.INFO, "bound")
        record = _parse_log(buf)
        assert record["session_id"] == "s1"

    def test_get_logger_helper(self, capture_log: Any) -> None:
        _, buf = capture_log
        log = get_logger("test_worker", request_id="req-1")
        log.log(logging.INFO, "helper")
        record = _parse_log(buf)
        assert record["request_id"] == "req-1"
