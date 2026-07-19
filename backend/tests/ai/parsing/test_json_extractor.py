"""Tests for JSON object extraction (TP-0705)."""

import pytest

from app.ai.parsing import (
    ExtractionEmptyError,
    ExtractionMultipleObjectsError,
    ExtractionObjectNotFoundError,
    extract_json_object,
)


class TestPlainJSON:
    def test_compact_object(self) -> None:
        result = extract_json_object('{"a":1}')
        assert result == '{"a":1}'

    def test_formatted_object(self) -> None:
        raw = '{\n  "a": 1,\n  "b": 2\n}'
        result = extract_json_object(raw)
        assert result == raw

    def test_surrounding_whitespace(self) -> None:
        result = extract_json_object('  \n  {"a":1}  \n  ')
        assert result == '{"a":1}'

    def test_nested_object(self) -> None:
        raw = '{"outer": {"inner": 1}}'
        result = extract_json_object(raw)
        assert result == raw

    def test_nested_array(self) -> None:
        raw = '{"items": [1, 2, {"nested": 3}]}'
        result = extract_json_object(raw)
        assert result == raw

    def test_braces_inside_string(self) -> None:
        raw = '{"msg": "text with {braces} here"}'
        result = extract_json_object(raw)
        assert result == raw

    def test_escaped_quotes(self) -> None:
        raw = '{"text": "He said \\"hello\\""}'
        result = extract_json_object(raw)
        assert result == raw

    def test_escaped_backslashes(self) -> None:
        raw = '{"path": "C:\\\\example\\\\file"}'
        result = extract_json_object(raw)
        assert result == raw


class TestMarkdownFences:
    def test_json_fence(self) -> None:
        raw = '```json\n{"a": 1}\n```'
        result = extract_json_object(raw)
        assert result == '{"a": 1}'

    def test_generic_fence(self) -> None:
        raw = '```\n{"a": 1}\n```'
        result = extract_json_object(raw)
        assert result == '{"a": 1}'

    def test_whitespace_around_fence(self) -> None:
        raw = '  \n  ```json\n{"a": 1}\n```  \n  '
        result = extract_json_object(raw)
        assert result == '{"a": 1}'

    def test_commentary_before_fenced(self) -> None:
        raw = 'Here is the result:\n\n```json\n{"a": 1}\n```'
        result = extract_json_object(raw)
        assert result == '{"a": 1}'

    def test_commentary_after_fenced(self) -> None:
        raw = '```json\n{"a": 1}\n```\n\nHope this helps.'
        result = extract_json_object(raw)
        assert result == '{"a": 1}'


class TestCommentary:
    def test_leading_commentary(self) -> None:
        result = extract_json_object('Here is:\n{"a": 1}')
        assert result == '{"a": 1}'

    def test_trailing_commentary(self) -> None:
        result = extract_json_object('{"a": 1}\n\nThanks!')
        assert result == '{"a": 1}'

    def test_both_leading_and_trailing(self) -> None:
        result = extract_json_object('Start\n{"a": 1}\nEnd')
        assert result == '{"a": 1}'


class TestMultipleObjects:
    def test_two_adjacent_objects(self) -> None:
        with pytest.raises(ExtractionMultipleObjectsError):
            extract_json_object('{"a":1}\n{"b":2}')

    def test_objects_separated_by_text(self) -> None:
        with pytest.raises(ExtractionMultipleObjectsError):
            extract_json_object('First: {"a":1}\nSecond: {"b":2}')

    def test_two_fenced_objects(self) -> None:
        raw = '```json\n{"a":1}\n```\n```json\n{"b":2}\n```'
        with pytest.raises(ExtractionMultipleObjectsError):
            extract_json_object(raw)


class TestInvalidOutput:
    def test_empty_string(self) -> None:
        with pytest.raises(ExtractionEmptyError):
            extract_json_object("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(ExtractionEmptyError):
            extract_json_object("   \n  \n  ")

    def test_no_json(self) -> None:
        with pytest.raises(ExtractionObjectNotFoundError):
            extract_json_object("Just some text without braces")

    def test_incomplete_object(self) -> None:
        with pytest.raises(ExtractionObjectNotFoundError):
            extract_json_object('{"a": 1')

    def test_unmatched_braces(self) -> None:
        with pytest.raises(ExtractionObjectNotFoundError):
            extract_json_object('{"a": 1')
