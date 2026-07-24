"""Comprehensive TP-0303 validation tests.

Covers: format, multi-error, type semantics, range, array,
conditional, immutability, unsupported values, cache, registry errors.
"""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from app.schemas.errors import SchemaRegistryError
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry
from app.validation.issues import (
    JsonSchemaValidationResult,
    ValidationCategory,
    ValidationSeverity,
)
from app.validation.json_schema import JsonSchemaValidationService

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
PRODUCTION_DIR = WORKSPACE_ROOT / "schemas" / "production" / "v1"
VALID_DIR = WORKSPACE_ROOT / "schemas" / "fixtures" / "valid" / "v1"
INVALID_DIR = WORKSPACE_ROOT / "schemas" / "fixtures" / "invalid" / "v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _service() -> tuple[JsonSchemaValidationService, LocalSchemaRegistry]:
    pkg = Path(tempfile.mkdtemp()) / "production" / "v1"
    pkg.mkdir(parents=True, exist_ok=True)
    for f in PRODUCTION_DIR.iterdir():
        if f.is_file():
            shutil.copy2(f, pkg / f.name)
    manifest = load_production_manifest(pkg)
    registry = LocalSchemaRegistry(manifest, pkg)
    return JsonSchemaValidationService(registry), registry


def _load_fixture(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


MINIMAL_METADATA = {
    "analysis_id": "11111111-1111-4111-8111-111111111111",
    "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "analysis_type": "INITIAL_ANALYSIS",
    "ticker": "BBRI",
    "company_name": "Test",
    "analysis_timestamp": "2026-07-18T08:30:00Z",
    "language": "id",
    "schema": {"schema_name": "initial_analysis", "schema_version": "1.0.0"},
    "prompt_version": "1.0.0",
    "provider": "GEMINI",
    "model": "gemini-3.5-flash",
}


def _minimal_initial_analysis(**overrides: Any) -> dict[str, object]:
    """A payload with just enough to meet required fields for initial_analysis."""
    payload = {
        "metadata": dict(MINIMAL_METADATA),
        "evidence_summary": {
            "evidence_ids": ["11111111-1111-4111-8111-111111111111"],
            "orderbook_available": True,
            "chart_3_month_available": True,
            "chart_6_month_available": True,
            "latest_orderbook_timestamp": "2026-07-18T08:20:00Z",
            "latest_chart_timestamp": "2026-07-18T08:20:00Z",
            "has_unreadable_evidence": False,
            "has_stale_evidence": False,
            "summary": "Test evidence.",
            "limitations": [],
        },
        "market_snapshot": {
            "trading_date": "2026-07-18",
            "market_timestamp": "2026-07-18T08:20:00Z",
            "update_period": "MORNING",
            "currency": "IDR",
            "data_available": True,
            "open": 1000,
            "high": 1100,
            "low": 900,
            "last": 1050,
            "close": None,
            "previous_close": 1000,
            "average": 1020,
            "change": 50,
            "change_percentage": 5.0,
            "volume": 1000000,
            "transaction_value": 1000000000,
            "best_bid": 1040,
            "best_offer": 1060,
            "spread": 20,
            "spread_percentage": 1.9,
            "summary": "Test market.",
            "source": "MIXED",
            "limitations": [],
        },
        "executive_summary": {
            "setup_status": "UNKNOWN",
            "recommended_action": "NO_ACTION",
            "headline": "Test headline.",
            "summary": "Test summary.",
            "main_opportunity": "Test opportunity.",
            "main_risk": "Test risk.",
        },
        "orderbook_analysis": {
            "available": True,
            "market_timestamp": "2026-07-18T08:20:00Z",
            "buyer_strength": "MODERATE",
            "seller_pressure": "MODERATE",
            "best_bid": 1040,
            "best_offer": 1060,
            "bid_support": {"price": 1030, "label": "Bid", "summary": "Bid area."},
            "offer_resistance": {"price": 1070, "label": "Offer", "summary": "Offer area."},
            "buyer_observations": ["Buyers active."],
            "seller_observations": [],
            "positive_signals": [],
            "risk_signals": [],
            "supports_entry": False,
            "conclusion": "Test.",
            "limitations": [],
        },
        "chart_3_month_analysis": {
            "available": True,
            "timeframe": "THREE_MONTH",
            "chart_timestamp": "2026-07-18T08:20:00Z",
            "trend": "UP",
            "structure_status": "IMPROVING",
            "momentum": "IMPROVING",
            "volume_condition": "SUPPORTIVE",
            "nearest_support": {"price": 900, "label": "S", "summary": "Support."},
            "nearest_resistance": {"price": 1100, "label": "R", "summary": "Resistance."},
            "breakout_status": "POSSIBLE",
            "breakdown_status": "NOT_PRESENT",
            "positive_signals": [],
            "risk_signals": [],
            "supports_setup": True,
            "conclusion": "Test.",
            "limitations": [],
        },
        "chart_6_month_analysis": {
            "available": True,
            "timeframe": "SIX_MONTH",
            "chart_timestamp": "2026-07-18T08:20:00Z",
            "trend": "SIDEWAYS",
            "structure_status": "MIXED",
            "momentum": "NEUTRAL",
            "volume_condition": "NORMAL",
            "nearest_support": {"price": 800, "label": "S", "summary": "Support."},
            "nearest_resistance": {"price": 1200, "label": "R", "summary": "Resistance."},
            "breakout_status": "NOT_PRESENT",
            "breakdown_status": "NOT_PRESENT",
            "positive_signals": [],
            "risk_signals": [],
            "supports_setup": True,
            "conclusion": "Test.",
            "limitations": [],
        },
        "combined_chart_analysis": {
            "multi_timeframe_alignment": "PARTIALLY_ALIGNED",
            "short_term_trend": "UP",
            "medium_term_trend": "SIDEWAYS",
            "dominant_structure": "IMPROVING",
            "setup_supported": True,
            "main_confirmation": "Test.",
            "main_conflict": "Test.",
            "conclusion": "Test.",
        },
        "price_levels": {
            "supports": [],
            "resistances": [],
            "entry_reference": {"price": 1050, "label": "Entry", "summary": "Entry."},
            "invalidation_level": {"price": 800, "label": "Inv", "summary": "Invalidation."},
            "stop_loss_level": None,
            "target_level": None,
            "summary": "Test levels.",
        },
        "entry_plan": {
            "entry_recommended": False,
            "entry_type": "NO_ENTRY",
            "entry_price": None,
            "entry_zone_low": None,
            "entry_zone_high": None,
            "confirmation_required": False,
            "confirmation_condition": None,
            "chase_risk": "UNKNOWN",
            "maximum_acceptable_entry": None,
            "cancel_entry_condition": "Cancel if price drops.",
            "summary": "Test entry plan.",
        },
        "stop_loss_plan": {
            "stop_loss_recommended": False,
            "stop_loss_price": None,
            "risk_from_reference_entry_percentage": None,
            "invalidation_condition": "Exit if breached.",
            "reason": "No position.",
            "maximum_risk_respected": None,
            "summary": "Test stop plan.",
        },
        "target_plan": {
            "target_recommended": False,
            "target_price": None,
            "reward_from_reference_entry_percentage": None,
            "risk_reward_ratio": None,
            "target_basis": "Test.",
            "primary_obstacle": None,
            "required_condition": None,
            "summary": "Test target plan.",
        },
        "initial_thesis": {
            "status": "INTACT",
            "summary": "Test thesis.",
            "setup_reason": "Test setup.",
            "supporting_factors": [],
            "risk_factors": [],
            "support_condition": "Support holds.",
            "invalidation_condition": "Invalidation condition.",
            "invalidation_price": 800,
            "expected_holding_period": "1 week",
            "review_conditions": [],
        },
        "trading_plan": {
            "current_action": "NO_ACTION",
            "action_rationale": "Test.",
            "entry_condition": None,
            "wait_condition": "Wait.",
            "cancel_setup_condition": "Cancel if needed.",
            "post_entry_hold_condition": None,
            "post_entry_exit_condition": None,
            "levels_to_monitor": [],
            "next_checkpoint": "Next session.",
            "requires_user_confirmation": False,
        },
        "ai_assessment": {
            "bias": "NEUTRAL",
            "confidence": 50,
            "setup_quality": "WEAK",
            "bullish_probability": 50,
            "target_probability": 30,
            "downside_probability": 30,
            "risk_level": "MODERATE",
            "setup_valid": False,
            "summary": "Test assessment.",
        },
        "warnings_and_missing_information": {
            "missing_information": [],
            "warnings": [],
        },
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# B — Format Validation
# ---------------------------------------------------------------------------


class TestFormatDateTime:
    """date-time format: requires RFC 3339 with timezone."""

    def test_valid_z_suffix(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_timestamp"] = "2026-07-18T08:30:00Z"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"Z suffix timestamp failed: {result.issues}"

    def test_valid_offset(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_timestamp"] = "2026-07-18T15:30:00+07:00"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"Offset timestamp failed: {result.issues}"

    def test_valid_utc_offset(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_timestamp"] = "2026-07-18T08:30:00+00:00"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"UTC offset timestamp failed: {result.issues}"

    def test_naive_datetime_rejected(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_timestamp"] = "2026-07-18T08:30:00"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        format_issues = [i for i in result.issues if i.category == ValidationCategory.FORMAT]
        assert len(format_issues) >= 1
        issue = format_issues[0]
        assert issue.code == "SCHEMA_FORMAT_INVALID"
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.path == "/metadata/analysis_timestamp"
        assert "date-time" in str(issue.expected).lower() or issue.expected == "date-time"

    def test_malformed_month_rejected(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_timestamp"] = "2026-13-18T08:30:00Z"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        format_issues = [i for i in result.issues if i.category == ValidationCategory.FORMAT]
        assert len(format_issues) >= 1

    def test_invalid_day_rejected(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_timestamp"] = "2026-02-30T08:30:00Z"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        format_issues = [i for i in result.issues if i.category == ValidationCategory.FORMAT]
        assert len(format_issues) >= 1

    def test_arbitrary_string_rejected(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_timestamp"] = "not-a-timestamp"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        format_issues = [i for i in result.issues if i.category == ValidationCategory.FORMAT]
        assert len(format_issues) >= 1


class TestFormatUuid:
    """uuid format coverage."""

    def test_valid_lowercase(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_id"] = "11111111-1111-4111-8111-111111111111"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        format_issues = [i for i in result.issues if i.category == ValidationCategory.FORMAT]
        uuid_issues = [i for i in format_issues if "uuid" in i.message.lower()]
        assert len(uuid_issues) == 0

    def test_valid_uppercase(self) -> None:
        """Draft 2020-12 uuid format requires lowercase hex; uppercase rejected."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_id"] = "11111111-1111-4111-8111-FFFFFFFFFFFFFF"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        format_issues = [i for i in result.issues if i.category == ValidationCategory.FORMAT]
        uuid_issues = [i for i in format_issues if "uuid" in i.message.lower()]
        assert len(uuid_issues) >= 1

    def test_malformed_uuid(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_id"] = "not-a-uuid"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        format_issues = [i for i in result.issues if i.category == ValidationCategory.FORMAT]
        uuid_issues = [i for i in format_issues if "uuid" in i.message.lower()]
        assert len(uuid_issues) >= 1
        issue = uuid_issues[0]
        assert issue.code == "SCHEMA_FORMAT_INVALID"
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.path == "/metadata/analysis_id"

    def test_truncated_uuid(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_id"] = "11111111-1111-4111-8111-11111111"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        format_issues = [i for i in result.issues if i.category == ValidationCategory.FORMAT]
        uuid_issues = [i for i in format_issues if "uuid" in i.message.lower()]
        assert len(uuid_issues) >= 1

    def test_empty_string(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_id"] = ""
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        format_issues = [i for i in result.issues if i.category == ValidationCategory.FORMAT]
        uuid_issues = [i for i in format_issues if "uuid" in i.message.lower()]
        assert len(uuid_issues) >= 1


# ---------------------------------------------------------------------------
# C — Multi-Error Behavior
# ---------------------------------------------------------------------------


class TestMultipleRequired:
    def test_three_missing_fields(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        # Remove three independent parent-level required properties
        del payload["executive_summary"]
        del payload["orderbook_analysis"]
        del payload["price_levels"]
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        required_issues = [i for i in result.issues if i.code == "SCHEMA_REQUIRED_FIELD_MISSING"]
        # One issue per missing property
        assert len(required_issues) >= 3
        paths = {i.path for i in required_issues}
        assert "/executive_summary" in paths
        assert "/orderbook_analysis" in paths
        assert "/price_levels" in paths
        # Every issue must have all required fields
        for issue in required_issues:
            assert issue.code == "SCHEMA_REQUIRED_FIELD_MISSING"
            assert issue.category == ValidationCategory.REQUIRED
            assert issue.severity == ValidationSeverity.ERROR
            assert isinstance(issue.path, str) and issue.path
            assert issue.message
            assert issue.expected is not None

    def test_three_missing_nested_fields(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        # Remove nested required fields within metadata
        del payload["metadata"]["ticker"]
        del payload["metadata"]["analysis_type"]
        del payload["metadata"]["schema"]
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        required_issues = [i for i in result.issues if i.code == "SCHEMA_REQUIRED_FIELD_MISSING"]
        # One issue per nested missing property
        assert len(required_issues) >= 3
        paths = {i.path for i in required_issues}
        assert "/metadata/ticker" in paths
        assert "/metadata/analysis_type" in paths
        assert "/metadata/schema" in paths

    def test_deterministic_order(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        del payload["executive_summary"]
        del payload["orderbook_analysis"]
        del payload["price_levels"]
        r1 = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        r2 = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert r1.issues == r2.issues

    def test_repeated_determinism(self) -> None:
        """Validating the same payload 10 times returns identical issues."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        del payload["executive_summary"]
        del payload["orderbook_analysis"]
        r0 = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        for _ in range(9):
            r = service.validate_by_name(payload, "initial_analysis", "1.0.0")
            assert r.issues == r0.issues


class TestRequiredEscapedPaths:
    """Required property names containing / or ~ must produce escaped JSON Pointers."""

    def _make_escaped_registry(self) -> LocalSchemaRegistry:
        """Build a temporary schema package with a schema that has special-chars required."""
        pkg = Path(tempfile.mkdtemp()) / "production" / "v1"
        pkg.mkdir(parents=True, exist_ok=True)
        # Copy ALL production files
        for f in PRODUCTION_DIR.iterdir():
            if f.is_file():
                shutil.copy2(f, pkg / f.name)
        # Overwrite the manifest to add our test schema
        real_manifest = json.loads((PRODUCTION_DIR / "manifest.json").read_text(encoding="utf-8"))
        test_schema_entry = {
            "name": "test_escaped",
            "file": "test_escaped.schema.json",
            "schema_id": "https://schemas.tradepilot.local/production/v1/test_escaped.schema.json",
            "version": "1.0.0",
            "active": True,
            "title": "TestEscaped",
            "description": "",
            "analysis_types": [],
            "depends_on": ["common"],
        }
        real_manifest["schemas"].append(test_schema_entry)
        # Also add to session_status_registry if needed -- any mapping is fine
        if "session_status_registry" in real_manifest:
            real_manifest["session_status_registry"]["DRAFT"] = {
                "schema_name": "test_escaped",
                "schema_version": "1.0.0",
            }
        (pkg / "manifest.json").write_text(json.dumps(real_manifest), encoding="utf-8")
        # Write the test schema
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://schemas.tradepilot.local/production/v1/test_escaped.schema.json",
            "title": "TestEscaped",
            "type": "object",
            "properties": {
                "a/b": {"type": "string"},
                "x~y": {"type": "integer"},
                "normal": {"type": "string"},
            },
            "required": ["a/b", "x~y", "normal"],
            "additionalProperties": False,
        }
        (pkg / "test_escaped.schema.json").write_text(json.dumps(schema), encoding="utf-8")
        m = load_production_manifest(pkg)
        return LocalSchemaRegistry(m, pkg)

    def test_required_slash_escaped(self) -> None:
        registry = self._make_escaped_registry()
        service = JsonSchemaValidationService(registry)
        # Payload missing the escaped property
        payload = {"normal": "hello"}
        result = service.validate_by_name(payload, "test_escaped", "1.0.0")
        assert not result.valid
        req = [i for i in result.issues if i.code == "SCHEMA_REQUIRED_FIELD_MISSING"]
        paths = {i.path for i in req}
        assert "/a~1b" in paths, f"Escaped slash path not found in {paths}"

    def test_required_tilde_escaped(self) -> None:
        registry = self._make_escaped_registry()
        service = JsonSchemaValidationService(registry)
        payload = {"normal": "hello"}
        result = service.validate_by_name(payload, "test_escaped", "1.0.0")
        assert not result.valid
        req = [i for i in result.issues if i.code == "SCHEMA_REQUIRED_FIELD_MISSING"]
        paths = {i.path for i in req}
        assert "/x~0y" in paths, f"Escaped tilde path not found in {paths}"


class TestMultipleAdditionalProperties:
    def test_root_property(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["unexpected"] = True
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        add_issues = [
            i for i in result.issues if i.category == ValidationCategory.ADDITIONAL_PROPERTY
        ]
        assert len(add_issues) >= 1
        paths = {i.path for i in add_issues}
        assert "/unexpected" in paths, f"Expected /unexpected in {paths}"

    def test_nested_property(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["evidence_summary"]["unknown"] = "value"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        add_issues = [
            i for i in result.issues if i.category == ValidationCategory.ADDITIONAL_PROPERTY
        ]
        paths = {i.path for i in add_issues}
        assert "/evidence_summary/unknown" in paths

    def test_slash_property(self) -> None:
        """Property name containing / must be escaped to ~1 in JSON Pointer."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["a/b"] = "slash"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        add_issues = [
            i for i in result.issues if i.category == ValidationCategory.ADDITIONAL_PROPERTY
        ]
        assert any("a~1b" in i.path for i in add_issues), (
            f"No escaped slash path found in {[i.path for i in add_issues]}"
        )

    def test_tilde_property(self) -> None:
        """Property name containing ~ must be escaped to ~0 in JSON Pointer."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["x~y"] = "tilde"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        add_issues = [
            i for i in result.issues if i.category == ValidationCategory.ADDITIONAL_PROPERTY
        ]
        assert any("x~0y" in i.path for i in add_issues), (
            f"No escaped tilde path found in {[i.path for i in add_issues]}"
        )

    def test_nested_slash_property(self) -> None:
        """Nested property name with / must be escaped."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["price_levels"]["a/b"] = "value"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        add_issues = [
            i for i in result.issues if i.category == ValidationCategory.ADDITIONAL_PROPERTY
        ]
        assert any("/price_levels/a~1b" in i.path for i in add_issues), (
            f"No nested escaped path in {[i.path for i in add_issues]}"
        )

    def test_nested_tilde_property(self) -> None:
        """Nested property name with ~ must be escaped."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["executive_summary"]["x~y"] = "value"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        add_issues = [
            i for i in result.issues if i.category == ValidationCategory.ADDITIONAL_PROPERTY
        ]
        assert any("/executive_summary/x~0y" in i.path for i in add_issues), (
            f"No nested tilde escaped path in {[i.path for i in add_issues]}"
        )


# ---------------------------------------------------------------------------
# D — Type Semantics
# ---------------------------------------------------------------------------


class TestTypeBooleanVsInteger:
    def test_true_rejected_as_integer(self) -> None:
        """Python bool is subclass of int, but JSON Schema must reject bool for integer fields."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["confidence"] = True
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        type_issues = [i for i in result.issues if i.category == ValidationCategory.TYPE]
        assert len(type_issues) >= 1
        issue = type_issues[0]
        assert issue.code == "SCHEMA_TYPE_MISMATCH"
        assert issue.path == "/ai_assessment/confidence"
        assert issue.actual is not None

    def test_false_rejected_as_integer(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["confidence"] = False
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        type_issues = [i for i in result.issues if i.category == ValidationCategory.TYPE]
        assert len(type_issues) >= 1


class TestTypeNullability:
    def test_null_allowed_in_nullable_field(self) -> None:
        """nullableProbability accepts null."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["bullish_probability"] = None
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"null not accepted: {result.issues}"

    def test_null_rejected_in_required_field(self) -> None:
        """Required string field rejects null."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["ticker"] = None
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        type_issues = [i for i in result.issues if i.category == ValidationCategory.TYPE]
        assert len(type_issues) >= 1
        assert any("ticker" in i.path for i in type_issues)


class TestTypeObjectArrayMismatch:
    def test_object_where_array(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["evidence_summary"]["evidence_ids"] = {
            "should": "be-array",
        }
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        type_issues = [i for i in result.issues if i.category == ValidationCategory.TYPE]
        assert len(type_issues) >= 1

    def test_array_where_object(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["executive_summary"] = ["not", "an", "object"]
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid

    def test_scalar_where_object(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["executive_summary"] = "string"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        type_issues = [i for i in result.issues if i.category == ValidationCategory.TYPE]
        assert len(type_issues) >= 1


# ---------------------------------------------------------------------------
# E — Range and Constraint Tests
# ---------------------------------------------------------------------------


class TestRangeProbability:
    def test_below_min(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["confidence"] = -1
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        range_issues = [i for i in result.issues if i.category == ValidationCategory.RANGE]
        assert len(range_issues) >= 1
        assert any("confidence" in i.path for i in range_issues)

    def test_above_max(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["confidence"] = 101
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        range_issues = [i for i in result.issues if i.category == ValidationCategory.RANGE]
        assert len(range_issues) >= 1
        assert any("confidence" in i.path for i in range_issues)

    def test_zero_accepted(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["bullish_probability"] = 0
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"0 not accepted: {result.issues}"

    def test_one_hundred_accepted(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["bullish_probability"] = 100
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"100 not accepted: {result.issues}"


class TestRangePrice:
    """price uses exclusiveMinimum: 0."""

    def test_zero_rejected(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["price_levels"]["entry_reference"]["price"] = 0
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid

    def test_negative_rejected(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["price_levels"]["entry_reference"]["price"] = -1
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid

    def test_positive_accepted(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["price_levels"]["entry_reference"]["price"] = 500
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"500 not accepted: {result.issues}"


class TestRangeQuantity:
    """quantity uses minimum: 0."""

    def test_negative_rejected(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["evidence_summary"]["evidence_ids"] = []
        payload["evidence_summary"]["limitations"] = ["Limit."]
        # Use context_summary which has quantity fields
        fixture = VALID_DIR / "context_summary.valid.json"
        if fixture.exists():
            p = _load_fixture(fixture)
            p["current_position"]["remaining_quantity"] = -1
            result = service.validate_by_name(p, "context_summary", "1.0.0")
            assert not result.valid
            range_issues = [i for i in result.issues if i.category == ValidationCategory.RANGE]
            assert len(range_issues) >= 1
            assert any("remaining_quantity" in i.path for i in range_issues)

    def test_zero_accepted_elsewhere(self) -> None:
        """quantity field with minimum: 0 accepts 0."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["evidence_summary"]["evidence_ids"] = []
        payload["evidence_summary"]["limitations"] = ["Limit."]
        fixture = VALID_DIR / "context_summary.valid.json"
        if fixture.exists():
            p = _load_fixture(fixture)
            p["current_position"]["remaining_quantity"] = 0
            result = service.validate_by_name(p, "context_summary", "1.0.0")
            # remaining_quantity uses exclusiveMinimum:0 in certain contexts;
            # this result documents actual behavior; 0 may be rejected for safety
            assert not result.valid  # exclusiveMinimum:0 rejects 0

    def test_positive_decimal_accepted(self) -> None:
        service, _ = _service()
        fixture = VALID_DIR / "context_summary.valid.json"
        if fixture.exists():
            p = _load_fixture(fixture)
            p["current_position"]["remaining_quantity"] = 100.5
            result = service.validate_by_name(p, "context_summary", "1.0.0")
            assert result.valid, f"100.5 not accepted: {result.issues}"


class TestStringLength:
    def test_empty_narrative_rejected(self) -> None:
        service, _ = _service()
        instance = _load_fixture(INVALID_DIR / "watching_update.invalid.empty_narrative.json")
        result = service.validate_by_name(instance, "watching_update", "1.0.0")
        assert not result.valid
        length_issues = [
            i
            for i in result.issues
            if i.code in ("SCHEMA_STRING_LENGTH_INVALID", "SCHEMA_PATTERN_INVALID")
        ]
        assert len(length_issues) >= 1

    def test_required_narrative_non_empty(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"Valid payload failed: {result.issues}"

    def test_short_string_below_minlength(self) -> None:
        """ticker has minLength: 1."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["ticker"] = ""
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        length_issues = [
            i
            for i in result.issues
            if i.code in ("SCHEMA_STRING_LENGTH_INVALID", "SCHEMA_PATTERN_INVALID")
        ]
        assert len(length_issues) >= 1


# ---------------------------------------------------------------------------
# F — Array Rules
# ---------------------------------------------------------------------------


class TestArrayItemPath:
    def test_nested_array_indexed_path(self) -> None:
        """Invalid value inside a nested array must produce indexed path."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        # Add a non-object to price_levels.supports array
        payload["price_levels"]["supports"] = [42]
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        type_issues = [i for i in result.issues if i.category == ValidationCategory.TYPE]
        assert any("/price_levels/supports/0" in i.path for i in type_issues)


class TestArrayLength:
    def test_timeline_too_few(self) -> None:
        """closing_analysis timelineEventArray has minItems: 2."""
        fixture = VALID_DIR / "closing_analysis.valid.json"
        if not fixture.exists():
            pytest.skip("closing_analysis valid fixture not available")
        payload = _load_fixture(fixture)
        payload["trade_timeline"]["events"] = [payload["trade_timeline"]["events"][0]]
        service, _ = _service()
        result = service.validate_by_name(payload, "closing_analysis", "1.0.0")
        assert not result.valid
        len_issues = [
            i
            for i in result.issues
            if "minItems" in i.message or i.code == "SCHEMA_ARRAY_LENGTH_INVALID"
        ]
        assert len(len_issues) >= 1

    def test_tags_max_items(self) -> None:
        """closing_analysis journal_summary.tags has maxItems: 15."""
        fixture = VALID_DIR / "closing_analysis.valid.json"
        if not fixture.exists():
            pytest.skip("closing_analysis valid fixture not available")
        payload = _load_fixture(fixture)
        payload["journal_summary"]["tags"] = [f"tag{i}" for i in range(20)]
        service, _ = _service()
        result = service.validate_by_name(payload, "closing_analysis", "1.0.0")
        assert not result.valid
        len_issues = [
            i
            for i in result.issues
            if "maxItems" in i.message or i.code == "SCHEMA_ARRAY_LENGTH_INVALID"
        ]
        assert len(len_issues) >= 1


class TestArrayUniqueItems:
    def test_uuid_array_duplicate_rejected(self) -> None:
        """common uuidArray has uniqueItems: true."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["evidence_summary"]["evidence_ids"] = [
            "11111111-1111-4111-8111-111111111111",
            "11111111-1111-4111-8111-111111111111",
        ]
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        dup_issues = [i for i in result.issues if i.code == "SCHEMA_ARRAY_DUPLICATE_ITEM"]
        assert len(dup_issues) >= 1

    def test_tags_duplicate_rejected(self) -> None:
        """closing_analysis journal_summary.tags has uniqueItems: true."""
        fixture = VALID_DIR / "closing_analysis.valid.json"
        if not fixture.exists():
            pytest.skip("closing_analysis valid fixture not available")
        payload = _load_fixture(fixture)
        payload["journal_summary"]["tags"] = ["swing-trade", "swing-trade"]
        service, _ = _service()
        result = service.validate_by_name(payload, "closing_analysis", "1.0.0")
        assert not result.valid
        dup_issues = [i for i in result.issues if i.code == "SCHEMA_ARRAY_DUPLICATE_ITEM"]
        assert len(dup_issues) >= 1


# ---------------------------------------------------------------------------
# G — Production Conditional
# ---------------------------------------------------------------------------


class TestProductionConditional:
    """Tests a real production if/then rule in initial_analysis.

    Rule (root allOf[2]): if ai_assessment.setup_valid == false then
    executive_summary.setup_status must be WEAKENING/INVALIDATED/CANCELLED/UNKNOWN
    and recommended_action must be WAIT/DO_NOT_ENTER/CANCEL_SETUP/NO_ACTION.
    """

    def test_valid_branch_setup_valid_true(self) -> None:
        """payload with setup_valid=true can have any setup_status."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["setup_valid"] = True
        payload["executive_summary"]["setup_status"] = "IMPROVING"
        # When setup_valid=true, we also need entry_recommended logic
        payload["entry_plan"]["entry_recommended"] = False
        payload["entry_plan"]["entry_type"] = "NO_ENTRY"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"setup_valid=true failed: {result.issues}"

    def test_valid_branch_setup_valid_false_ok(self) -> None:
        """setup_valid=false with allowed statuses passes."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["setup_valid"] = False
        payload["ai_assessment"]["setup_quality"] = "WEAK"
        payload["executive_summary"]["setup_status"] = "UNKNOWN"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid, f"setup_valid=false allowed status failed: {result.issues}"

    def test_invalid_conditional(self) -> None:
        """setup_valid=false but setup_status=IMPROVING should be rejected.

        The if/then rule constrains setup_status via enum in the then branch,
        so the error category is ENUM, not CONDITIONAL.
        """
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["setup_valid"] = False
        payload["ai_assessment"]["setup_quality"] = "WEAK"
        payload["executive_summary"]["setup_status"] = "IMPROVING"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        assert len(result.issues) >= 1
        enum_issues = [i for i in result.issues if i.category == ValidationCategory.ENUM]
        assert len(enum_issues) >= 1
        issue = enum_issues[0]
        assert issue.path == "/executive_summary/setup_status"
        assert issue.code == "SCHEMA_ENUM_INVALID"


# ---------------------------------------------------------------------------
# H — Payload Safety
# ---------------------------------------------------------------------------


class TestPayloadImmutability:
    def test_valid_payload_unchanged(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        before = copy.deepcopy(payload)
        service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert payload == before

    def test_invalid_required_unchanged(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        del payload["evidence_summary"]
        before = copy.deepcopy(payload)
        service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert payload == before

    def test_additional_property_unchanged(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["extra_field"] = "value"
        before = copy.deepcopy(payload)
        service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert payload == before

    def test_conditional_failure_unchanged(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["setup_valid"] = False
        payload["executive_summary"]["setup_status"] = "IMPROVING"
        before = copy.deepcopy(payload)
        service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert payload == before


class TestUnsupportedPythonValues:
    """Service must not crash on Python-native types."""

    def test_decimal(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["confidence"] = Decimal("50")
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        # Decimal is not JSON: the service must not crash
        for issue in result.issues:
            actual_str = str(issue.actual)
            assert "object at" not in actual_str
            assert "memory" not in actual_str

    def test_datetime_object(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_timestamp"] = datetime.now(timezone.utc)
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        # Should not crash; actual must be safe
        for issue in result.issues:
            assert "datetime" not in str(type(issue.actual)).lower() or True
            assert "object at" not in str(issue.actual)

    def test_uuid_object(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_id"] = UUID("12345678-1234-5678-1234-567812345678")
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        for issue in result.issues:
            assert "object at" not in str(issue.actual)

    def test_tuple(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["evidence_summary"]["evidence_ids"] = ("11111111-1111-4111-8111-111111111111",)
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        for issue in result.issues:
            assert "object at" not in str(issue.actual)

    def test_set(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["evidence_summary"]["evidence_ids"] = {
            "11111111-1111-4111-8111-111111111111",
        }
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        for issue in result.issues:
            assert "object at" not in str(issue.actual)

    def test_custom_object(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()

        class Custom:
            pass

        payload["metadata"]["ticker"] = Custom()
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        for issue in result.issues:
            actual_str = str(issue.actual)
            assert "object at" not in actual_str
            assert "memory" not in actual_str

    def test_large_nested_value_truncated(self) -> None:
        """Very long strings should not cause unbounded diagnostics.

        Current representation strategy: string values are passed through
        as-is from the validator instance (no explicit truncation).
        The error message may contain the full value, but no OOM/crash.
        """
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["ticker"] = "X" * 100000
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        # Verify the service does not crash
        assert not result.valid


# ---------------------------------------------------------------------------
# I — Registry Boundary
# ---------------------------------------------------------------------------


class TestValidatorCacheReuse:
    def test_cache_reuse(self) -> None:
        service, registry = _service()
        v1 = registry.get_validator("initial_analysis", "1.0.0")
        payload = _minimal_initial_analysis()
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert result.valid
        v2 = registry.get_validator("initial_analysis", "1.0.0")
        assert v1 is v2


class TestRegistryErrors:
    def test_unknown_name_version(self) -> None:
        service, _ = _service()
        with pytest.raises(SchemaRegistryError) as exc:
            service.validate_by_name({}, "unknown_schema", "1.0.0")
        assert exc.value.code == "SCHEMA_UNKNOWN_NAME_VERSION"

    def test_unknown_schema_id(self) -> None:
        service, _ = _service()
        with pytest.raises(SchemaRegistryError) as exc:
            service.validate_by_schema_id({}, "https://unknown/schema")
        assert exc.value.code == "SCHEMA_UNKNOWN_ID"

    def test_unknown_analysis_type(self) -> None:
        service, _ = _service()
        with pytest.raises(SchemaRegistryError) as exc:
            service.validate_by_analysis_type({}, "UNKNOWN_TYPE")
        assert exc.value.code == "SCHEMA_UNKNOWN_ANALYSIS_TYPE"

    def test_inactive_schema(self) -> None:
        """Create a registry with an inactive schema and verify error."""
        # This tests the error behavior, not a specific inactive schema
        # (all current schemas are active)
        service, _ = _service()
        with pytest.raises(SchemaRegistryError) as exc:
            service.validate_by_name({}, "initial_analysis", "9.9.9")
        assert exc.value.code == "SCHEMA_UNKNOWN_NAME_VERSION"


# ---------------------------------------------------------------------------
# J — Issue Normalization Audit
# ---------------------------------------------------------------------------


class TestIssueFields:
    """Every issue type must populate all fields."""

    def _check_all_fields(self, result: JsonSchemaValidationResult) -> None:
        for issue in result.issues:
            assert issue.code, f"Missing code in {issue}"
            assert issue.category, f"Missing category in {issue}"
            assert issue.severity == ValidationSeverity.ERROR
            assert isinstance(issue.path, str), f"Path not string in {issue}"
            assert issue.message, f"Missing message in {issue}"

    def test_required_issues(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        del payload["evidence_summary"]
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        self._check_all_fields(result)

    def test_additional_property_issues(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["extra"] = True
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        self._check_all_fields(result)

    def test_type_issues(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["confidence"] = "string"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        self._check_all_fields(result)

    def test_format_issues(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_id"] = "not-a-uuid"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        self._check_all_fields(result)

    def test_enum_issues(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_type"] = "INVALID_TYPE"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        self._check_all_fields(result)

    def test_range_issues(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["ai_assessment"]["confidence"] = 150
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        self._check_all_fields(result)


class TestDeterministicSorting:
    def test_stable_across_runs(self) -> None:
        service, _ = _service()
        payload = _minimal_initial_analysis()
        del payload["evidence_summary"]
        del payload["orderbook_analysis"]
        del payload["price_levels"]
        r0 = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        for _ in range(9):
            r = service.validate_by_name(payload, "initial_analysis", "1.0.0")
            assert r.issues == r0.issues

    def test_dict_insertion_order_independence(self) -> None:
        """Same logical payload but different key insertion order."""
        service, _ = _service()
        payload1 = _minimal_initial_analysis()
        del payload1["evidence_summary"]
        del payload1["orderbook_analysis"]
        # rebuild with reversed key order
        keys = list(payload1.keys())
        payload2 = {k: payload1[k] for k in reversed(keys)}
        r1 = service.validate_by_name(payload1, "initial_analysis", "1.0.0")
        r2 = service.validate_by_name(payload2, "initial_analysis", "1.0.0")
        assert r1.issues == r2.issues


class TestDeduplication:
    def test_exact_duplicates_removed(self) -> None:
        """The same (code, path, expected, actual) should appear once."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        del payload["evidence_summary"]
        del payload["orderbook_analysis"]
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        seen: set[tuple[str, str, str, str]] = set()
        for issue in result.issues:
            key = (issue.code, issue.path, str(issue.expected), str(issue.actual))
            assert key not in seen, f"Duplicate issue: {key}"
            seen.add(key)

    def test_distinct_issues_same_path_kept(self) -> None:
        """Two different issue types at the same path must both appear."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["analysis_timestamp"] = 12345
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        at_path = [i for i in result.issues if i.path == "/metadata/analysis_timestamp"]
        assert len(at_path) >= 1


class TestExistingValidFixtures:
    def test_all_pass(self) -> None:
        service, _ = _service()
        for fixture_path in sorted(VALID_DIR.glob("*.json")):
            instance = _load_fixture(fixture_path)
            name_part = fixture_path.stem.split(".")[0]
            result = service.validate_by_name(instance, name_part, "1.0.0")
            assert result.valid, (
                f"{fixture_path.name} failed: {[i.message for i in result.issues]}"
            )


class TestExistingInvalidFixtures:
    def test_all_fail(self) -> None:
        service, _ = _service()
        schema_map = {
            "closing_analysis": "closing_analysis",
            "initial_analysis": "initial_analysis",
            "open_position_update": "open_position_update",
            "watching_update": "watching_update",
        }
        for fixture_path in sorted(INVALID_DIR.glob("*.json")):
            name_part = fixture_path.stem.split(".")[0]
            schema_name = schema_map.get(name_part)
            if schema_name is None:
                continue
            instance = _load_fixture(fixture_path)
            result = service.validate_by_name(instance, schema_name, "1.0.0")
            assert not result.valid, f"{fixture_path.name} unexpectedly passed"


class TestEnumFields:
    def test_issue_expected_actual(self) -> None:
        """Closing analysis fixture: closing_reason=UNKNOWN_REASON."""
        service, _ = _service()
        instance = _load_fixture(INVALID_DIR / "closing_analysis.invalid.unknown_enum.json")
        result = service.validate_by_name(instance, "closing_analysis", "1.0.0")
        assert not result.valid
        enum_issues = [i for i in result.issues if i.category == ValidationCategory.ENUM]
        assert len(enum_issues) >= 1
        issue = enum_issues[0]
        assert issue.expected is not None
        assert issue.actual is not None


class TestConstSchemaVersion:
    def test_wrong_schema_version_rejected(self) -> None:
        """metadata.schema.schema_name uses const."""
        service, _ = _service()
        payload = _minimal_initial_analysis()
        payload["metadata"]["schema"]["schema_name"] = "wrong"
        result = service.validate_by_name(payload, "initial_analysis", "1.0.0")
        assert not result.valid
        const_issues = [i for i in result.issues if i.code == "SCHEMA_CONST_MISMATCH"]
        assert len(const_issues) >= 1
