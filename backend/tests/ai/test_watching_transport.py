"""Offline tests for the compact Gemini Watching transport contract."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.ai.providers.gemini import GeminiNormalizationError
from app.ai.providers.models import ProviderRequest, ProviderResponse
from app.ai.providers.router import _normalize_payload
from app.ai.providers.selection import _load_gemini_response_schemas
from app.ai.providers.watching_transport import (
    normalize_watching_update_transport_payload,
)
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry


ROOT = Path("schemas/production/v1")


def _transport_payload() -> dict[str, object]:
    return {
        "decision": {
            "recommendation": "WAIT",
            "bias": "NEUTRAL",
            "confidence": 50,
            "setup_quality": "FAIR",
            "risk_level": "MODERATE",
            "summary": "Menunggu konfirmasi.",
        },
        "evidence_findings": {
            "orderbook": ["Bid support belum cukup."],
            "chart": ["Tren belum terkonfirmasi."],
            "limitations": ["Data terbatas."],
        },
        "trade_plan": {
            "rationale": "Belum ada konfirmasi.",
            "wait_condition": "Tunggu data berikutnya.",
            "monitoring": ["Pantau harga."],
            "entry_zone_low": 100,
            "entry_zone_high": 105,
        },
        "probabilities": {"bullish": 30, "target": 20, "downside": 50},
        "scenarios": {
            "bullish": "Konfirmasi naik.",
            "neutral": "Bergerak sideways.",
            "bearish": "Menembus support.",
        },
        "next_action": {
            "action": "WAIT",
            "reasons": ["Konfirmasi belum cukup."],
            "wait_condition": "Tunggu evidence.",
            "monitoring": ["Pantau support."],
        },
        "market_facts": {"current_price": 999, "summary": "Transport observation."},
        "warnings": ["Transport warning."],
    }


def _application_metadata() -> dict[str, object]:
    return {
        "canonical_analysis_id": "11111111-1111-4111-8111-111111111111",
        "session_id": "22222222-2222-4222-8222-222222222222",
        "ticker": "BBRI",
        "company_name": "Bank Rakyat Indonesia",
        "canonical_analysis_timestamp": "2026-07-28T12:00:00+00:00",
        "prompt_version": "1.0.0",
        "provider_model": "gemini-3.1-flash-lite",
        "evidence_ids": ["33333333-3333-4333-8333-333333333333"],
        "canonical_facts": {
            "ticker": "BBRI",
            "currency": "IDR",
            "lifecycle_status": "WATCHING",
            "market_snapshot": {"last": 101, "currency": "IDR"},
        },
    }


def _walk(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def test_transport_schema_is_compact_and_self_contained() -> None:
    document = json.loads(
        (ROOT / "watching_update_gemini_transport_v1.schema.json").read_text()
    )
    forbidden = {"$ref", "$defs", "allOf", "oneOf", "anyOf"}
    assert not forbidden.intersection(key for key, _ in _walk(document))
    assert set(document["required"]) == {
        "decision",
        "evidence_findings",
        "trade_plan",
        "probabilities",
        "scenarios",
        "next_action",
    }


def test_watching_registration_uses_transport_and_other_stages_remain_registered() -> None:
    schemas = _load_gemini_response_schemas(ROOT)
    assert set(schemas) == {
        "initial_analysis_v2",
        "watching_update",
        "open_position_update",
        "closing_analysis",
        "partial_exit_review",
    }
    assert set(schemas["watching_update"]["properties"]) == {
        "metadata",
        "decision",
        "market_facts",
        "evidence_findings",
        "trade_plan",
        "probabilities",
        "scenarios",
        "next_action",
        "warnings",
    }
    assert "metadata" in schemas["initial_analysis_v2"]["properties"]
    assert all(key not in json.dumps(schemas["watching_update"]) for key in ("$ref", "$defs"))


def test_transport_normalizes_to_valid_canonical_watching_payload() -> None:
    payload = normalize_watching_update_transport_payload(
        _transport_payload(), application_metadata=_application_metadata()
    )
    registry = LocalSchemaRegistry(load_production_manifest(ROOT), ROOT)
    errors = list(registry.get("watching_update", "1.0.0").validator.iter_errors(payload))
    assert errors == []
    assert payload["metadata"]["session_id"] == _application_metadata()["session_id"]
    assert payload["market_snapshot"]["last"] == 101
    assert payload["warnings_and_missing_information"]["warnings"][-1].startswith(
        "Transport Watching output"
    )


def test_router_normalizes_gemini_watching_transport_before_canonical_validation() -> None:
    request = ProviderRequest(
        request_id=uuid.uuid4(),
        analysis_type="WATCHING_UPDATE",
        prompt_version="1.0.0",
        user_prompt="watch",
        expected_schema_name="watching_update",
        expected_schema_version="1.0.0",
        metadata=_application_metadata(),
    )
    response = ProviderResponse(
        provider="gemini",
        model="gemini-3.1-flash-lite",
        raw_output="{}",
        request_id=request.request_id,
    )
    normalized = _normalize_payload(
        request=request,
        response=response,
        parsed=_transport_payload(),
    )
    assert normalized["metadata"]["schema"]["schema_name"] == "watching_update"


def test_transport_cannot_override_application_identity_or_execution_authority() -> None:
    metadata = _application_metadata()
    payload = _transport_payload()
    payload["metadata"] = {"session_id": "attacker"}
    payload["next_action"] = {
        "action": "ENTER_IF_CONFIRMED",
        "reasons": [],
        "wait_condition": "now",
        "monitoring": [],
    }
    normalized = normalize_watching_update_transport_payload(
        payload, application_metadata=metadata
    )
    assert normalized["metadata"]["session_id"] == metadata["session_id"]
    assert normalized["metadata"]["ticker"] == "BBRI"
    assert normalized["trading_plan"]["requires_user_confirmation"] is False
    assert "execution" not in json.dumps(normalized).lower()


def test_missing_required_transport_field_fails_before_canonical_validation() -> None:
    payload = _transport_payload()
    del payload["scenarios"]
    with pytest.raises(GeminiNormalizationError, match="scenarios"):
        normalize_watching_update_transport_payload(
            payload, application_metadata=_application_metadata()
        )


def test_missing_application_metadata_fails_clearly() -> None:
    with pytest.raises(GeminiNormalizationError, match="canonical metadata"):
        normalize_watching_update_transport_payload(
            _transport_payload(), application_metadata={}
        )
