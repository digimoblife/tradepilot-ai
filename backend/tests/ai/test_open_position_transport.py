"""Offline tests for the compact Gemini Open Position transport contract."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.ai.providers.gemini import GeminiNormalizationError
from app.ai.providers.models import ProviderRequest, ProviderResponse
from app.ai.providers.open_position_transport import normalize_open_position_update_transport_payload
from app.ai.providers.router import _normalize_payload
from app.ai.providers.selection import _load_gemini_response_schemas
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry

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
    assert "entry_at" not in json.dumps(normalized)


def test_missing_optional_values_do_not_fabricate_facts_but_unusable_output_is_blocked() -> None:
    payload = _transport()
    payload.pop("market_facts")
    payload["position_assessment"].pop("current_price")
    with pytest.raises(GeminiNormalizationError, match="current_price"):
        normalize_open_position_update_transport_payload(payload, application_metadata=_metadata())


def test_router_normalizes_open_position_before_canonical_validation() -> None:
    request = ProviderRequest(request_id=uuid.uuid4(), analysis_type="OPEN_POSITION_UPDATE", prompt_version="1.0.0", user_prompt="open", expected_schema_name="open_position_update", expected_schema_version="1.0.0", metadata=_metadata())
    response = ProviderResponse(provider="gemini", model="gemini-3.1-flash-lite", raw_output="{}", request_id=request.request_id)
    normalized = _normalize_payload(request=request, response=response, parsed=_transport())
    assert normalized["metadata"]["schema"]["schema_name"] == "open_position_update"
    assert _canonical(normalized) == []
