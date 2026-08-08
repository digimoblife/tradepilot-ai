from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

SCHEMA_ROOT = Path(__file__).resolve().parents[3] / "schemas" / "rebuild" / "v1"


def _schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def _initial() -> dict[str, object]:
    return {
        "summary": "Ringkasan",
        "orderbook_analysis": "Orderbook mendukung.",
        "three_month_chart_analysis": "Tren tiga bulan.",
        "six_month_chart_analysis": "Tren enam bulan.",
        "foreign_flow_analysis": {
            "assessment": "ACCUMULATION",
            "analysis": "Akumulasi terlihat konsisten, tetapi tetap perlu konfirmasi.",
        },
        "support": {"low": 100, "high": 101, "note": "Support"},
        "resistance": {"low": 110, "high": 111, "note": "Resistance"},
        "entry_area": {"low": 102, "high": 104, "note": "Area entry"},
        "stop_recommendation": {"level": 99, "note": "Stop"},
        "target_recommendation": {"level": 115, "note": "Target"},
        "probabilities": {"upside": 60, "downside": 40},
        "risks": ["Volatilitas"],
        "trading_plan": "Pantau konfirmasi.",
        "conclusion": "WAIT",
    }


def _wait() -> dict[str, object]:
    return {
        "update_summary": "Ringkasan update",
        "current_price": 105,
        "orderbook_assessment": "Bid mendukung",
        "change_from_previous_analysis": "Belum banyak berubah",
        "current_entry_condition": "Tunggu konfirmasi",
        "upside_probability": 60,
        "downside_probability": 40,
        "key_risks": ["Volatilitas"],
        "recommended_action": "WAIT",
        "next_plan": "Pantau orderbook",
        "conclusion": "WAIT",
    }


def _position() -> dict[str, object]:
    return {
        "update_summary": "Ringkasan posisi",
        "current_price": 105,
        "position_condition": "Masih terjaga",
        "orderbook_assessment": "Likuiditas cukup",
        "change_from_previous_analysis": "Momentum stabil",
        "target_realism": "Masih realistis",
        "downside_risk": "Terbatas",
        "target_probability": 60,
        "trading_plan": "Pertahankan posisi",
        "monitoring_points": ["Support"],
        "warnings": ["Pantau volatilitas"],
        "conclusion": "HOLD",
    }


def test_initial_flow_is_strict_and_required() -> None:
    validator = Draft202012Validator(_schema("initial_analysis.schema.json"))
    validator.validate(_initial())

    historical = deepcopy(_initial())
    historical.pop("foreign_flow_analysis")
    with pytest.raises(ValidationError):
        validator.validate(historical)


@pytest.mark.parametrize(
    ("schema_name", "payload_factory"),
    [
        ("wait_update.schema.json", _wait),
        ("position_update.schema.json", _position),
    ],
)
def test_optional_broker_flow_validates_present_absent_and_null(
    schema_name: str,
    payload_factory: Callable[[], dict[str, object]],
) -> None:
    validator = Draft202012Validator(_schema(schema_name))
    payload = payload_factory()
    validator.validate(payload)

    payload["broker_flow_analysis"] = None
    validator.validate(payload)

    payload["broker_flow_analysis"] = {
        "assessment": "DISTRIBUTION",
        "analysis": "Distribusi terlihat, tetapi bukti satu hari dapat berisik.",
    }
    validator.validate(payload)

    payload["broker_flow_analysis"] = {
        "assessment": "BULLISH",
        "analysis": "Tidak valid",
    }
    with pytest.raises(ValidationError):
        validator.validate(payload)
