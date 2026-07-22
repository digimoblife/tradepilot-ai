"""Tests for structured logging (TP-1601).

Covers: structured output format, contextual fields, secret redaction,
nested redaction, production prompt omission, missing optional context,
backend logging initialisation.
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
    _collect_extra,
    _is_secret_key,
    _redact,
    _should_skip_in_production,
    configure_logging,
    get_logger,
    is_production,
)

# Save / restore env var that influences is_production
_ENV_KEY = "TRADEPILOT_LOG_PRODUCTION"


# ===================================================================
# Fixtures
# ===================================================================


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
    logger = logging.getLogger("test_logger")
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
    def test_valid_json_output(self, capture_log: Any) -> None:
        _, buf = capture_log
        logger = logging.getLogger("test_logger")
        logger.info("hello world")
        record = _parse_log(buf)
        assert record["message"] == "hello world"
        assert record["level"] == "INFO"
        assert record["logger"] == "test_logger"
        assert "timestamp" in record

    def test_timestamp_iso8601(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info("t")
        record = _parse_log(buf)
        ts = record["timestamp"]
        assert isinstance(ts, str)
        # ISO-8601 with timezone
        assert "+" in ts or ts.endswith("Z")

    def test_sort_keys(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info("m")
        text = buf.getvalue().strip()
        # JSON with sorted keys: "level" before "logger" before "message" before "timestamp"
        parsed = json.loads(text)
        keys = list(parsed.keys())
        assert keys == sorted(keys)


# ===================================================================
# 2. Required contextual fields
# ===================================================================


class TestContextualFields:
    @pytest.mark.parametrize("field", sorted(CONTEXTUAL_FIELDS))
    def test_field_appears_when_provided(self, field: str, capture_log: Any) -> None:
        _, buf = capture_log
        logger = logging.getLogger("test_logger")
        logger.info("ctx", extra={field: "test-value"})
        record = _parse_log(buf)
        assert record.get(field) == "test-value"

    def test_multiple_fields(self, capture_log: Any) -> None:
        _, buf = capture_log
        logger = logging.getLogger("test_logger")
        logger.info(
            "multi",
            extra={
                "request_id": "req-1",
                "session_id": "ses-2",
                "provider": "gemini",
                "model": "gemini-2.0-flash",
                "attempt": 2,
                "duration": 1.5,
            },
        )
        record = _parse_log(buf)
        assert record["request_id"] == "req-1"
        assert record["session_id"] == "ses-2"
        assert record["provider"] == "gemini"
        assert record["model"] == "gemini-2.0-flash"
        assert record["attempt"] == 2
        assert record["duration"] == 1.5


# ===================================================================
# 3. Secret redaction
# ===================================================================


class TestSecretRedaction:
    def test_api_key_redacted(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info("secret", extra={"api_key": "sk-1234567890abcdef"})
        record = _parse_log(buf)
        assert record["api_key"] == REDACTED

    def test_password_redacted(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info("pw", extra={"password": "hunter2"})
        record = _parse_log(buf)
        assert record["password"] == REDACTED

    @pytest.mark.parametrize(
        "secret_key",
        [
            "token",
            "access_token",
            "refresh_token",
            "authorization",
            "private_key",
            "secret",
            "api_secret",
        ],
    )
    def test_all_secret_patterns(self, secret_key: str, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info("secret", extra={secret_key: "sensitive-value"})
        record = _parse_log(buf)
        assert record[secret_key] == REDACTED

    def test_non_secret_unaffected(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info("safe", extra={"safe_field": "hello"})
        record = _parse_log(buf)
        assert record["safe_field"] == "hello"


# ===================================================================
# 4. Nested secret redaction
# ===================================================================


class TestNestedRedaction:
    def test_nested_dict_value_redacted(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info(
            "nested",
            extra={
                "credentials": {
                    "api_key": "sk-xxx",
                    "username": "admin",
                }
            },
        )
        record = _parse_log(buf)
        creds = record["credentials"]
        assert isinstance(creds, dict)
        assert creds["api_key"] == REDACTED
        assert creds["username"] == "admin"

    def test_nested_list_of_dicts(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info(
            "list_nested",
            extra={
                "providers": [
                    {"name": "gemini", "api_key": "key1"},
                    {"name": "deepseek", "api_key": "key2"},
                ]
            },
        )
        record = _parse_log(buf)
        providers = record["providers"]
        assert len(providers) == 2
        assert providers[0]["api_key"] == REDACTED
        assert providers[1]["api_key"] == REDACTED
        assert providers[0]["name"] == "gemini"

    def test_deeply_nested(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info(
            "deep",
            extra={
                "config": {
                    "auth": {"token": "tkn"},
                    "safe": {"key": "ok"},
                }
            },
        )
        record = _parse_log(buf)
        assert record["config"]["auth"]["token"] == REDACTED
        assert record["config"]["safe"]["key"] == "ok"


# ===================================================================
# 5. Production prompt omission
# ===================================================================


class TestProductionPromptOmission:
    def test_prompt_omitted_in_production(self) -> None:
        buf = StringIO()
        formatter = StructuredFormatter(production=True)
        handler = logging.StreamHandler(buf)
        handler.setFormatter(formatter)
        logger = logging.getLogger("test_prod")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("prompt test", extra={"user_prompt": "analyze this chart"})
        record = json.loads(buf.getvalue().strip())
        assert "user_prompt" not in record
        logger.removeHandler(handler)

    def test_prompt_included_non_production(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info(
            "prompt", extra={"user_prompt": "analyze this chart"}
        )
        record = _parse_log(buf)
        assert record["user_prompt"] == "analyze this chart"

    @pytest.mark.parametrize("key", ["system_prompt", "raw_output", "prompt_text"])
    def test_all_prompt_keys_omitted(self, key: str) -> None:
        buf = StringIO()
        formatter = StructuredFormatter(production=True)
        handler = logging.StreamHandler(buf)
        handler.setFormatter(formatter)
        logger = logging.getLogger("test_prod")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("prod", extra={key: "some content"})
        record = json.loads(buf.getvalue().strip())
        assert key not in record
        logger.removeHandler(handler)

    def test_empty_prompt_not_skipped(self) -> None:
        buf = StringIO()
        formatter = StructuredFormatter(production=True)
        handler = logging.StreamHandler(buf)
        handler.setFormatter(formatter)
        logger = logging.getLogger("test_prod")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        logger.info("empty prompt", extra={"user_prompt": ""})
        record = json.loads(buf.getvalue().strip())
        assert record["user_prompt"] == ""
        logger.removeHandler(handler)


# ===================================================================
# 6. Missing optional context
# ===================================================================


class TestMissingContext:
    def test_no_extra_does_not_crash(self, capture_log: Any) -> None:
        _, buf = capture_log
        logging.getLogger("test_logger").info("no extra")
        record = _parse_log(buf)
        assert record["message"] == "no extra"

    def test_partial_context(self, capture_log: Any) -> None:
        _, buf = capture_log
        logger = logging.getLogger("test_logger")
        logger.info("partial", extra={"session_id": "s1"})
        record = _parse_log(buf)
        assert record["session_id"] == "s1"
        # Other contextual fields should be absent
        for field in CONTEXTUAL_FIELDS:
            if field != "session_id":
                assert field not in record, f"{field} should not be present"


# ===================================================================
# 7. Backend logging initialisation
# ===================================================================


class TestBackendInit:
    def test_configure_logging(self) -> None:
        configure_logging(level="DEBUG", production=False)
        root = logging.getLogger()
        root.info("init test")
        # After configure, handler should be set; try logging directly
        found_structured = False
        for h in root.handlers:
            if isinstance(h.formatter, StructuredFormatter):
                found_structured = True
        assert found_structured, "StructuredFormatter should be installed"

    def test_configure_logging_production(self) -> None:
        configure_logging(level="INFO", production=True)
        root = logging.getLogger()
        found_prod = False
        for h in root.handlers:
            if isinstance(h.formatter, StructuredFormatter) and h.formatter._production:
                found_prod = True
        assert found_prod

    def test_is_production_default_false(self) -> None:
        assert not is_production()

    def test_is_production_via_env(self) -> None:
        os.environ[_ENV_KEY] = "true"
        assert is_production()


# ===================================================================
# 8. ContextAdapter
# ===================================================================


class TestContextAdapter:
    def test_bound_context_appears(self, capture_log: Any) -> None:
        _, buf = capture_log
        log = ContextAdapter(
            logging.getLogger("test_logger"),
            {"session_id": "ses-bound"},
        )
        log.info("bound context")
        record = _parse_log(buf)
        assert record["session_id"] == "ses-bound"

    def test_extra_merges_with_bound(self, capture_log: Any) -> None:
        _, buf = capture_log
        log = ContextAdapter(
            logging.getLogger("test_logger"),
            {"session_id": "ses-bound"},
        )
        log.info("merged", extra={"provider": "gemini"})
        record = _parse_log(buf)
        assert record["session_id"] == "ses-bound"
        assert record["provider"] == "gemini"

    def test_extra_overrides_bound(self, capture_log: Any) -> None:
        _, buf = capture_log
        log = ContextAdapter(
            logging.getLogger("test_logger"),
            {"session_id": "original"},
        )
        log.info("override", extra={"session_id": "override"})
        record = _parse_log(buf)
        assert record["session_id"] == "override"

    def test_get_logger_helper(self, capture_log: Any) -> None:
        _, buf = capture_log
        log = get_logger("test_logger", analysis_job_id="job-1")
        log.info("via get_logger")
        record = _parse_log(buf)
        assert record["analysis_job_id"] == "job-1"


# ===================================================================
# 9. Helper unit tests
# ===================================================================


class TestHelpers:
    def test_is_secret_key(self) -> None:
        assert _is_secret_key("api_key")
        assert _is_secret_key("API_KEY")
        assert _is_secret_key("my_password_here")
        assert not _is_secret_key("safe_field")
        assert not _is_secret_key("")

    def test_redact_flat(self) -> None:
        data = {"api_key": "secret", "name": "hello"}
        result = _redact(data)
        assert result["api_key"] == REDACTED
        assert result["name"] == "hello"

    def test_redact_nested(self) -> None:
        data = {"outer": {"api_key": "secret", "inner": {"token": "t"}}}
        result = _redact(data)
        assert result["outer"]["api_key"] == REDACTED
        assert result["outer"]["inner"]["token"] == REDACTED

    def test_redact_list(self) -> None:
        data = [{"api_key": "k1"}, {"password": "p2"}]
        result = _redact(data)
        assert result[0]["api_key"] == REDACTED
        assert result[1]["password"] == REDACTED

    def test_should_skip_in_production(self) -> None:
        assert _should_skip_in_production("user_prompt", "analyze")
        assert _should_skip_in_production("raw_output", "{}")
        assert not _should_skip_in_production("safe_field", "value")
        assert not _should_skip_in_production("user_prompt", "")

    def test_collect_extra_skips_standard(self) -> None:
        record = logging.LogRecord(
            "n",
            logging.INFO,
            "/f.py",
            1,
            "msg",
            (),
            None,
        )
        record.custom_field = "hello"  # type: ignore[attr-defined]
        extra = _collect_extra(record)
        assert extra.get("custom_field") == "hello"
        # Standard fields should not appear
        assert "name" not in extra
        assert "msg" not in extra
        assert "levelno" not in extra


# ===================================================================
# 10. Exception handling
# ===================================================================


class TestExceptionHandling:
    def test_exception_info_included(self, capture_log: Any) -> None:
        _, buf = capture_log
        logger = logging.getLogger("test_logger")
        try:
            raise ValueError("test error")
        except ValueError:
            logger.exception("something failed")
        record = _parse_log(buf)
        assert record["message"] == "something failed"
        assert "exception" in record
        assert "ValueError" in record["exception"]
        assert "test error" in record["exception"]
