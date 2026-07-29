from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

import pytest

from app.json_safe import to_json_safe
from app.jobs.processor import AnalysisProcessor
from app.models.enums import ProviderType


class _Kind(Enum):
    VALUE = "value"


def test_open_position_metadata_persists_datetime_as_utc_iso() -> None:
    processor = object.__new__(AnalysisProcessor)
    entry_at = datetime(2026, 7, 29, 9, 16, 48, 123456, tzinfo=timezone.utc)

    record = processor._create_provider_request_record(
        job_id=uuid.uuid4(),
        provider=ProviderType.GEMINI,
        provider_model="gemini-3.1-flash-lite",
        attempt_number=1,
        prompt_name="OPEN_POSITION_UPDATE",
        prompt_version="1.0.0",
        schema_name="open_position_update",
        schema_version="1.0.0",
        system_prompt=None,
        user_prompt="prompt",
        images=(),
        metadata={
            "canonical_facts": {
                "entry_at": entry_at,
                "entry_price": Decimal("4100.00"),
                "position_status": _Kind.VALUE,
            }
        },
    )

    assert record.request_metadata == {
        "canonical_facts": {
            "entry_at": "2026-07-29T09:16:48.123456Z",
            "entry_price": "4100.00",
            "position_status": "value",
        }
    }
    json.dumps(record.request_metadata, allow_nan=False)


def test_json_safe_conversion_is_recursive_and_idempotent() -> None:
    value = {
        "timestamp": "2026-07-29T02:16:48Z",
        "date": date(2026, 7, 29),
        "id": uuid.UUID("4edbc9f8-3049-4240-af3f-651383f65c30"),
        "items": [datetime(2026, 7, 29, 2, 16, 48, tzinfo=timezone.utc), 100, True, None],
    }

    converted = to_json_safe(value)

    assert converted["timestamp"] == value["timestamp"]
    assert converted["date"] == "2026-07-29"
    assert converted["id"] == "4edbc9f8-3049-4240-af3f-651383f65c30"
    assert converted["items"] == ["2026-07-29T02:16:48Z", 100, True, None]
    json.dumps(converted, allow_nan=False)


def test_json_safe_preserves_primitives_and_rejects_unknown_objects() -> None:
    primitives = {"string": "x", "integer": 1, "float": 1.5, "boolean": False, "null": None}
    assert to_json_safe(primitives) == primitives

    with pytest.raises(TypeError, match="Unsupported JSON value"):
        to_json_safe(object())


def test_naive_datetime_is_rejected_without_losing_timezone_contract() -> None:
    with pytest.raises(TypeError, match="Naive datetime"):
        to_json_safe(datetime(2026, 7, 29, 2, 16, 48))
