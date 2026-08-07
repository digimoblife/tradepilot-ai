"""Offline tests for the compact Gemini Open Position transport contract."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from app.ai.providers.gemini import GeminiNormalizationError
from app.ai.providers.models import ProviderRequest, ProviderResponse
from app.ai.providers.open_position_transport import (
    _market_numeric,
    normalize_open_position_update_transport_payload,
)
from app.ai.providers.router import _normalize_payload
from app.ai.providers.selection import _load_gemini_response_schemas
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry
from app.validation.state_consistency import validate_state_consistency
from app.validation.market_snapshot import validate_market_snapshot
from app.calculations.decimal_utils import CurrencyCode
from app.json_safe import to_json_safe

ROOT = Path("schemas/production/v1")


def _metadata() -> dict[str, object]:
    return {
        "canonical_analysis_id": "11111111-1111-4111-8111-111111111111",
        "session_id": "22222222-2222-4222-8222-222222222222",
        "ticker": "BBRI",
        "company_name": "Bank Rakyat Indonesia",
        "canonical_analysis_timestamp": "2026-07-29T00:00:00Z",
        "prompt_version": "1.0.0",
        "provider_model": "gemini-3.1-flash-lite",
        "evidence_ids": ["33333333-3333-4333-8333-333333333333"],
        "canonical_facts": {
            "ticker": "BBRI", "company_name": "Bank Rakyat Indonesia", "currency": "IDR",
            "current_price": "4120", "current_price_source": "USER_CONFIRMED_ORDERBOOK_INPUT",
            "entry_price": "4100", "entry_at": "2026-07-29T02:16:48Z",
            "remaining_quantity": "100", "active_stop_loss": "3900", "active_target": "4500",
        },
    }


def _transport() -> dict[str, object]:
    return {
        "decision": {"bias": "BULLISH", "confidence": 70, "summary": "Posisi masih sehat.", "recommendation": "HOLD"},
        "market_facts": {"open": 4150, "high": 4250, "low": 4100, "current_price": 4200, "average": 4180, "best_bid": 4195, "best_offer": 4200, "change_percentage": 1.2, "summary": "Pasar positif."},
        "evidence_findings": {"orderbook": ["Bid bertahan."], "chart": ["Tidak ada chart baru."], "limitations": ["Chart terbaru tidak tersedia."]},
        "position_assessment": {"health": "HEALTHY", "summary": "Posisi sehat.", "current_price": 4200, "target_realism": "REALISTIC", "target_obstacle": "Offer tebal.", "target_condition": "Buyer menyerap offer.", "target_summary": "Target masih realistis.", "unrealized_return_percentage": 2.4},
        "trade_plan": {"current_action": "HOLD", "rationale": "Pertahankan posisi.", "monitoring": ["Pantau bid."], "hold_condition": "Harga di atas stop.", "exit_condition": "Jika stop terpicu."},
        "probabilities": {"bullish": 65, "target": 60, "downside": 20},
        "scenarios": {"bullish": "Buyer menguat.", "base": "Bergerak sideways.", "bearish": "Support ditembus."},
        "next_action": {"monitoring": ["Pantau orderbook."], "checkpoint": "Evidence berikutnya", "rationale": "Tunggu konfirmasi."},
        "warnings": ["Snapshot dapat berubah cepat."],
    }


def _canonical(payload: dict[str, object]) -> list[object]:
    registry = LocalSchemaRegistry(load_production_manifest(ROOT), ROOT)
    return list(registry.get("open_position_update", "1.0.0").validator.iter_errors(payload))


def _walk(value: object, depth: int = 0):
    yield depth, value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child, depth + 1)


def test_open_position_transport_schema_is_compact_and_self_contained() -> None:
    document = json.loads((ROOT / "open_position_update_gemini_transport_v1.schema.json").read_text())
    keys = {key for _, value in _walk(document) if isinstance(value, dict) for key in value}
    assert not {"$ref", "$defs", "allOf", "oneOf", "anyOf"}.intersection(keys)
    assert max(depth for depth, _ in _walk(document)) <= 6
    assert set(document["required"]) == {"decision", "evidence_findings", "position_assessment", "trade_plan", "probabilities", "next_action"}


def test_transport_loads_and_gemini_conversion_succeeds() -> None:
    schemas = _load_gemini_response_schemas(ROOT)
    assert "open_position_update" in schemas
    assert "open_position_update_gemini_transport_v1" not in schemas
    assert all("$ref" not in json.dumps(schema) for schema in schemas.values())


def test_only_open_position_uses_transport_and_other_stages_remain_unchanged() -> None:
    schemas = _load_gemini_response_schemas(ROOT)
    assert set(schemas["open_position_update"]["properties"]) == {"metadata", "decision", "market_facts", "evidence_findings", "position_assessment", "trade_plan", "probabilities", "scenarios", "next_action", "warnings"}
    assert set(schemas["watching_update"]["properties"]) == {"metadata", "decision", "market_facts", "evidence_findings", "trade_plan", "probabilities", "scenarios", "next_action", "warnings"}
    assert "position_assessment" not in schemas["initial_analysis_v2"]["properties"]
    assert "position_assessment" not in schemas["partial_exit_review"]["properties"]
    assert "position_assessment" not in schemas["closing_analysis"]["properties"]


def test_complete_transport_maps_to_valid_canonical_payload_and_preserves_metadata() -> None:
    normalized = normalize_open_position_update_transport_payload(_transport(), application_metadata=_metadata())
    assert _canonical(normalized) == []
    assert normalized["metadata"]["ticker"] == "BBRI"
    assert normalized["metadata"]["company_name"] == "Bank Rakyat Indonesia"
    assert normalized["target_assessment"]["realism"] == "REALISTIC"
    assert normalized["target_assessment"]["target_probability"] == 60
    assert normalized["ai_assessment"]["downside_probability"] == 20
    assert "bullish: Buyer menguat." in normalized["thesis_assessment"]["summary"]
    assert normalized["warnings_and_missing_information"]["warnings"][-1].startswith("Output Gemini")


def test_application_position_facts_override_provider_values() -> None:
    payload = _transport()
    payload["position_assessment"] = {"health": "AT_RISK", "summary": "Provider mencoba mengubah fakta.", "current_price": 4200}
    normalized = normalize_open_position_update_transport_payload(payload, application_metadata=_metadata())
    position = normalized["position_assessment"]
    assert position["entry_price"] == 4100
    assert position["active_stop_loss"] == 3900
    assert position["active_target"] == 4500
    assert position["remaining_quantity"] == 100
    assert position["current_price"] == Decimal("4120")
    assert "entry_at" not in json.dumps(to_json_safe(normalized))


def test_application_current_price_is_canonical_when_provider_omits_or_disagrees() -> None:
    payload = _transport()
    payload["market_facts"].pop("current_price")
    payload["position_assessment"].pop("current_price")
    normalized = normalize_open_position_update_transport_payload(payload, application_metadata=_metadata())
    assert normalized["market_snapshot"]["last"] == Decimal("4120")
    assert normalized["position_assessment"]["current_price"] == Decimal("4120")


def test_missing_application_current_price_blocks_normalization_without_entry_fallback() -> None:
    metadata = _metadata()
    facts = metadata["canonical_facts"]
    assert isinstance(facts, dict)
    facts.pop("current_price")
    with pytest.raises(GeminiNormalizationError, match="application context"):
        normalize_open_position_update_transport_payload(_transport(), application_metadata=metadata)


def test_no_revision_keeps_confirmed_levels_and_canonical_proposals_null() -> None:
    normalized = normalize_open_position_update_transport_payload(
        _transport(), application_metadata=_metadata()
    )
    assert normalized["position_assessment"]["active_stop_loss"] == 3900
    assert normalized["position_assessment"]["active_target"] == 4500
    assert normalized["stop_loss_assessment"]["revised_stop_proposed"] is False
    assert normalized["stop_loss_assessment"]["proposed_stop_loss"] is None
    assert normalized["target_assessment"]["revised_target_proposed"] is False
    assert normalized["target_assessment"]["proposed_target"] is None
    assert _canonical(normalized) == []


def test_explicit_stop_and_target_revisions_are_canonical_recommendations_only() -> None:
    payload = _transport()
    payload["trade_plan"].update(
        {
            "stop_revision_proposed": True,
            "proposed_stop_loss": 3950,
            "target_revision_proposed": True,
            "proposed_target": 4600,
        }
    )
    normalized = normalize_open_position_update_transport_payload(payload, application_metadata=_metadata())
    assert normalized["stop_loss_assessment"]["revised_stop_proposed"] is True
    assert normalized["stop_loss_assessment"]["proposed_stop_loss"] == 3950
    assert normalized["target_assessment"]["revised_target_proposed"] is True
    assert normalized["target_assessment"]["proposed_target"] == 4600
    assert normalized["position_assessment"]["active_stop_loss"] == 3900
    assert normalized["position_assessment"]["active_target"] == 4500
    assert _canonical(normalized) == []


def test_inconsistent_or_equal_revision_proposals_are_normalized_safely() -> None:
    payload = _transport()
    payload["trade_plan"].update(
        {
            "stop_revision_proposed": False,
            "proposed_stop_loss": 3950,
            "target_revision_proposed": True,
            "proposed_target": 4500,
        }
    )
    normalized = normalize_open_position_update_transport_payload(payload, application_metadata=_metadata())
    assert normalized["stop_loss_assessment"]["proposed_stop_loss"] is None
    assert normalized["target_assessment"]["proposed_target"] is None
    assert any("diabaikan" in warning for warning in normalized["warnings_and_missing_information"]["warnings"])
    assert any("sama dengan fakta confirmed" in warning for warning in normalized["warnings_and_missing_information"]["warnings"])
    assert _canonical(normalized) == []


def test_revision_intent_without_numeric_proposal_is_unusable() -> None:
    payload = _transport()
    payload["trade_plan"]["stop_revision_proposed"] = True
    with pytest.raises(GeminiNormalizationError, match="proposed_stop_loss"):
        normalize_open_position_update_transport_payload(payload, application_metadata=_metadata())


def test_domain_state_consistency_runs_after_normalization() -> None:
    normalized = normalize_open_position_update_transport_payload(
        _transport(), application_metadata=_metadata()
    )
    result = validate_state_consistency(
        normalized,
        {
            "session_id": _metadata()["session_id"],
            "ticker": "BBRI",
            "position": {
                "entry_price": 4100,
                "remaining_quantity": 100,
                "active_stop_loss": 3900,
                "active_target": 4500,
            },
        },
    )
    assert result.valid


def test_spread_percentage_uses_canonical_decimal_precision_and_domain_accepts_it() -> None:
    payload = _transport()
    payload["market_facts"]["best_bid"] = 4095
    payload["market_facts"]["best_offer"] = 4100
    payload["market_facts"]["current_price"] = 4100
    normalized = normalize_open_position_update_transport_payload(payload, application_metadata=_metadata())
    spread_percentage = normalized["market_snapshot"]["spread_percentage"]
    assert isinstance(spread_percentage, Decimal)
    assert spread_percentage == Decimal("0.12")
    assert spread_percentage != 0.12195121951219512
    assert validate_market_snapshot(normalized["market_snapshot"]).valid
    assert _canonical(normalized) == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.0, Decimal("0.00")), (-0.72, Decimal("-0.72")), (Decimal("0.121951"), Decimal("0.12")), ("0.121951", Decimal("0.12"))],
)
def test_market_numeric_precision_and_sign_are_deterministic(
    value: object, expected: Decimal
) -> None:
    assert _market_numeric(value, kind="percentage", currency=CurrencyCode.IDR) == expected


def test_market_numeric_null_is_preserved_and_invalid_values_are_rejected() -> None:
    assert _market_numeric(None, kind="percentage", currency=CurrencyCode.IDR) is None
    for invalid in (float("nan"), float("inf"), float("-inf"), True):
        with pytest.raises(GeminiNormalizationError):
            _market_numeric(invalid, kind="percentage", currency=CurrencyCode.IDR)


def test_market_numeric_price_volume_and_position_authority_remain_canonical() -> None:
    payload = _transport()
    payload["market_facts"].update({"open": 4100.4, "high": 4200.5, "low": 4000.4, "average": "4150.5"})
    normalized = normalize_open_position_update_transport_payload(payload, application_metadata=_metadata())
    market = normalized["market_snapshot"]
    assert market["open"] == Decimal("4100")
    assert market["high"] == Decimal("4201")
    assert market["low"] == Decimal("4000")
    assert market["average"] == Decimal("4151")
    assert normalized["position_assessment"]["entry_price"] == 4100
    assert normalized["position_assessment"]["active_stop_loss"] == 3900
    assert normalized["position_assessment"]["active_target"] == 4500


def test_missing_optional_values_do_not_fabricate_facts_but_unusable_output_is_blocked() -> None:
    payload = _transport()
    payload.pop("market_facts")
    payload["position_assessment"].pop("current_price")
    normalized = normalize_open_position_update_transport_payload(payload, application_metadata=_metadata())
    assert normalized["market_snapshot"]["last"] == Decimal("4120")


def test_router_normalizes_open_position_before_canonical_validation() -> None:
    request = ProviderRequest(request_id=uuid.uuid4(), analysis_type="OPEN_POSITION_UPDATE", prompt_version="1.0.0", user_prompt="open", expected_schema_name="open_position_update", expected_schema_version="1.0.0", metadata=_metadata())
    response = ProviderResponse(provider="gemini", model="gemini-3.1-flash-lite", raw_output="{}", request_id=request.request_id)
    normalized = _normalize_payload(request=request, response=response, parsed=_transport())
    assert normalized["metadata"]["schema"]["schema_name"] == "open_position_update"
    assert _canonical(normalized) == []
