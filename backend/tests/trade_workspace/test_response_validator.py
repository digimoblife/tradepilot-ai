from __future__ import annotations

from copy import deepcopy

import pytest

from app.trade_workspace.ai.response_validator import (
    RebuildResponseValidator,
    ResponseValidationError,
    UnsupportedResponseAnalysisTypeError,
    critical_validation_error,
)
from app.trade_workspace.models.analysis_request import AnalysisRequestV2Type


def _initial_response() -> dict[str, object]:
    return {
        "summary": "Ringkasan",
        "orderbook_analysis": "Orderbook cukup kuat",
        "three_month_chart_analysis": "Tren naik",
        "six_month_chart_analysis": "Tren menengah positif",
        "support": {"low": 100, "high": 101, "note": "Support"},
        "resistance": {"low": 110, "high": 111, "note": "Resistance"},
        "entry_area": {"low": 102, "high": 104, "note": "Area entry"},
        "stop_recommendation": {"level": 99, "note": "Stop"},
        "target_recommendation": {"level": 115, "note": "Target"},
        "probabilities": {"upside": 0.6, "downside": 0.4},
        "risks": ["Volatilitas"],
        "trading_plan": "Rencana bertahap",
        "conclusion": "WAIT",
    }


def _wait_response() -> dict[str, object]:
    return {
        "update_summary": "Ringkasan update",
        "current_price": 105,
        "orderbook_assessment": "Bid masih mendukung",
        "change_from_previous_analysis": "Belum berubah banyak",
        "current_entry_condition": "Tunggu konfirmasi",
        "upside_probability": 0.6,
        "downside_probability": 0.4,
        "key_risks": ["Volatilitas"],
        "recommended_action": "WAIT",
        "next_plan": "Pantau orderbook",
        "conclusion": "WAIT",
    }


def _position_response() -> dict[str, object]:
    return {
        "update_summary": "Ringkasan posisi",
        "current_price": 105,
        "position_condition": "Posisi masih terjaga",
        "orderbook_assessment": "Likuiditas cukup",
        "change_from_previous_analysis": "Momentum stabil",
        "target_realism": "Target masih realistis",
        "downside_risk": "Risiko terbatas",
        "target_probability": 0.6,
        "trading_plan": "Pertahankan posisi",
        "monitoring_points": ["Support"],
        "warnings": ["Pantau volatilitas"],
        "conclusion": "HOLD",
    }


@pytest.mark.parametrize(
    ("analysis_type", "response"),
    [
        (AnalysisRequestV2Type.INITIAL_ANALYSIS, _initial_response()),
        (AnalysisRequestV2Type.WAIT_UPDATE, _wait_response()),
        (AnalysisRequestV2Type.POSITION_UPDATE, _position_response()),
    ],
)
def test_valid_rebuild_responses_pass(
    analysis_type: AnalysisRequestV2Type,
    response: dict[str, object],
) -> None:
    result = RebuildResponseValidator().validate(analysis_type, response)

    assert result.is_valid is True
    assert result.warnings == ()


@pytest.mark.parametrize(
    ("analysis_type", "response", "missing"),
    [
        (AnalysisRequestV2Type.INITIAL_ANALYSIS, _initial_response(), "summary"),
        (AnalysisRequestV2Type.WAIT_UPDATE, _wait_response(), "current_price"),
        (AnalysisRequestV2Type.POSITION_UPDATE, _position_response(), "target_realism"),
    ],
)
def test_missing_critical_sections_fail_without_mutating_response(
    analysis_type: AnalysisRequestV2Type,
    response: dict[str, object],
    missing: str,
) -> None:
    original = deepcopy(response)
    response.pop(missing)
    candidate = deepcopy(response)

    result = RebuildResponseValidator().validate(analysis_type, response)

    assert result.is_valid is False
    assert f"critical_section_unusable:{missing}" in result.warnings
    assert response == candidate
    assert missing not in response
    assert original != response


@pytest.mark.parametrize(
    "value",
    [None, [], "", {"summary": ""}],
)
def test_null_non_object_empty_and_unusable_responses_fail(value: object) -> None:
    result = RebuildResponseValidator().validate(
        AnalysisRequestV2Type.INITIAL_ANALYSIS,
        value,
    )

    assert result.is_valid is False


def test_zero_is_usable_additional_properties_and_optional_drift_are_allowed() -> None:
    response = _wait_response()
    response["current_price"] = 0
    response["optional_extra"] = {"not_in_schema": True}
    response["key_risks"] = [None]

    result = RebuildResponseValidator().validate(AnalysisRequestV2Type.WAIT_UPDATE, response)

    assert result.is_valid is True
    assert response["current_price"] == 0


def test_unsupported_type_is_rejected_and_validation_error_identifies_sections() -> None:
    with pytest.raises(UnsupportedResponseAnalysisTypeError):
        RebuildResponseValidator().validate("CLOSING_ANALYSIS", {})

    result = RebuildResponseValidator().validate(
        AnalysisRequestV2Type.INITIAL_ANALYSIS,
        {"summary": "only summary"},
    )
    error = critical_validation_error(AnalysisRequestV2Type.INITIAL_ANALYSIS, result)

    assert isinstance(error, ResponseValidationError)
    assert "INITIAL_ANALYSIS" in str(error)
    assert "orderbook_analysis" in str(error)
    assert "api_key" not in str(error)
