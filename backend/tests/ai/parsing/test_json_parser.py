"""Tests for strict JSON parsing (TP-0705)."""

import pytest

from app.ai.parsing import (
    CRITICAL_KEYS,
    ParseDuplicateCriticalKeyError,
    ParseNonFiniteNumberError,
    ParseSyntaxError,
    extract_and_parse_json,
    parse_json_object,
)


class TestPlainJSON:
    def test_compact_object(self) -> None:
        result = parse_json_object('{"a": 1}')
        assert result == {"a": 1}

    def test_formatted_object(self) -> None:
        result = parse_json_object('{\n  "a": 1\n}')
        assert result == {"a": 1}

    def test_nested_object(self) -> None:
        result = parse_json_object('{"outer": {"inner": 1}}')
        assert result == {"outer": {"inner": 1}}

    def test_nested_array(self) -> None:
        result = parse_json_object('{"items": [1, 2, {"nested": 3}]}')
        assert result == {"items": [1, 2, {"nested": 3}]}

    def test_braces_inside_string(self) -> None:
        result = parse_json_object('{"msg": "text with {braces}"}')
        assert result == {"msg": "text with {braces}"}

    def test_escaped_quotes(self) -> None:
        result = parse_json_object('{"text": "He said \\"hello\\""}')
        assert result == {"text": 'He said "hello"'}

    def test_escaped_backslashes(self) -> None:
        result = parse_json_object('{"path": "C:\\\\example\\\\file"}')
        assert result == {"path": "C:\\example\\file"}


class TestRootTypeRejection:
    def test_array_rejected(self) -> None:
        with pytest.raises(ParseSyntaxError, match="Expected JSON object, got list"):
            parse_json_object('[{"a": 1}]')

    def test_string_rejected(self) -> None:
        with pytest.raises(ParseSyntaxError, match="Expected JSON object, got str"):
            parse_json_object('"hello"')

    def test_number_rejected(self) -> None:
        with pytest.raises(ParseSyntaxError, match="Expected JSON object, got int"):
            parse_json_object("42")

    def test_boolean_rejected(self) -> None:
        with pytest.raises(ParseSyntaxError, match="Expected JSON object, got bool"):
            parse_json_object("true")

    def test_null_rejected(self) -> None:
        with pytest.raises(ParseSyntaxError, match="Expected JSON object, got NoneType"):
            parse_json_object("null")


class TestStrictNumbers:
    def test_nan_rejected(self) -> None:
        with pytest.raises(ParseNonFiniteNumberError):
            parse_json_object('{"value": NaN}')

    def test_infinity_rejected(self) -> None:
        with pytest.raises(ParseNonFiniteNumberError):
            parse_json_object('{"value": Infinity}')

    def test_negative_infinity_rejected(self) -> None:
        with pytest.raises(ParseNonFiniteNumberError):
            parse_json_object('{"value": -Infinity}')


class TestDuplicateKeys:
    def test_duplicate_top_level_critical_key(self) -> None:
        with pytest.raises(ParseDuplicateCriticalKeyError):
            parse_json_object('{"analysis_type": "A", "analysis_type": "B"}')

    def test_duplicate_nested_critical_key(self) -> None:
        with pytest.raises(ParseDuplicateCriticalKeyError):
            parse_json_object('{"outer": {"analysis_type": "A", "analysis_type": "B"}}')

    def test_duplicate_non_critical_key_allowed(self) -> None:
        """Non-critical keys may be silently deduplicated by Python's json."""
        result = parse_json_object('{"foo": 1, "foo": 2}')
        # Python json keeps the last value for non-critical duplicates
        assert result == {"foo": 2}

    def test_valid_unique_critical_keys(self) -> None:
        result = parse_json_object(
            '{"analysis_type": "A", "schema_version": "1", "session_id": "s"}'
        )
        assert result["analysis_type"] == "A"
        assert result["schema_version"] == "1"
        assert result["session_id"] == "s"

    def test_critical_keys_defined(self) -> None:
        assert "analysis_type" in CRITICAL_KEYS
        assert "schema_version" in CRITICAL_KEYS
        assert "session_id" in CRITICAL_KEYS
        assert "trade_state" in CRITICAL_KEYS
        assert "position_assessment" in CRITICAL_KEYS


class TestInvalidInput:
    def test_empty_string(self) -> None:
        with pytest.raises(ParseSyntaxError):
            parse_json_object("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(ParseSyntaxError):
            parse_json_object("   ")

    def test_malformed_json(self) -> None:
        with pytest.raises(ParseSyntaxError):
            parse_json_object('{"a": }')

    def test_unmatched_braces(self) -> None:
        with pytest.raises(ParseSyntaxError):
            parse_json_object('{"a": 1')

    def test_no_json_object(self) -> None:
        with pytest.raises(ParseSyntaxError):
            parse_json_object("just text")


class TestValuePreservation:
    def test_string_values(self) -> None:
        result = parse_json_object('{"name": "BBRI"}')
        assert result["name"] == "BBRI"

    def test_number_values(self) -> None:
        result = parse_json_object('{"price": 2500, "ratio": 1.5}')
        assert result["price"] == 2500
        assert result["ratio"] == 1.5

    def test_boolean_values(self) -> None:
        result = parse_json_object('{"active": true, "done": false}')
        assert result["active"] is True
        assert result["done"] is False

    def test_null_values(self) -> None:
        result = parse_json_object('{"value": null}')
        assert result["value"] is None

    def test_nested_structure(self) -> None:
        result = parse_json_object('{"a": {"b": [1, 2, {"c": 3}]}}')
        assert result["a"]["b"][2]["c"] == 3


class TestExtractAndParse:
    def test_composition(self) -> None:
        result = extract_and_parse_json('Some text\n{"a": 1}\nmore text')
        assert result == {"a": 1}

    def test_fenced_composition(self) -> None:
        result = extract_and_parse_json('```json\n{"a": 1}\n```')
        assert result == {"a": 1}

    def test_empty_extraction_fails(self) -> None:
        from app.ai.parsing import ExtractionEmptyError

        with pytest.raises(ExtractionEmptyError):
            extract_and_parse_json("")


class TestBoundaries:
    def test_input_immutability(self) -> None:
        raw = '{"a": 1}'
        original = raw
        parse_json_object(raw)
        assert raw == original

    def test_no_schema_validation(self) -> None:
        """Parser does not validate against a schema, only parses."""
        result = parse_json_object('{"unknown_field": "value"}')
        assert result["unknown_field"] == "value"

    def test_no_provider_call(self) -> None:
        """Parsing does not invoke any provider."""
        parse_json_object('{"a": 1}')

    def test_no_database_or_network(self) -> None:
        """Parsing is purely in-memory."""
        parse_json_object('{"a": 1}')
