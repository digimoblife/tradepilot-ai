from __future__ import annotations

import json
import uuid
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.ai.initial_analysis_partitioning import (
    PARTITIONS,
    build_partition_schemas,
    build_partition_user_prompt,
    decimalize_json_numbers_for_validation,
    merge_partition_payloads,
    select_partition_images,
    validate_partition_payload,
)
from app.ai.providers import ProviderImage
from app.validation import UnifiedValidationService


def _schema_root() -> Path:
    return Path(__file__).resolve().parents[3] / "schemas" / "production" / "v1"


def _valid_v2_payload() -> dict[str, object]:
    fixture = (
        Path(__file__).resolve().parents[3]
        / "schemas"
        / "fixtures"
        / "valid"
        / "v1"
        / "initial_analysis_v2.valid.json"
    )
    return json.loads(fixture.read_text(encoding="utf-8"))


def _partition_payloads() -> dict[str, dict[str, object]]:
    payload = _valid_v2_payload()
    findings = payload["evidence_findings"]
    trade_plan = payload["trade_plan"]
    return {
        "MARKET_EVIDENCE": {
            "metadata": payload["metadata"],
            "market_facts": payload["market_facts"],
            "evidence_findings": {
                "orderbook": findings["orderbook"],
                "broker_summary": findings["broker_summary"],
                "foreign_flow": findings["foreign_flow"],
                "limitations": findings["limitations"],
            },
        },
        "CHART_ANALYSIS": {
            "evidence_findings": {
                "chart_3_month": findings["chart_3_month"],
                "chart_6_month": findings["chart_6_month"],
            },
            "trade_plan": {
                "nearest_support": trade_plan["nearest_support"],
                "nearest_resistance": trade_plan["nearest_resistance"],
            },
        },
        "TRADE_THESIS": {
            "trade_plan": {
                "entry_zone_low": trade_plan["entry_zone_low"],
                "entry_zone_high": trade_plan["entry_zone_high"],
                "chase_limit": trade_plan["chase_limit"],
                "stop_loss": trade_plan["stop_loss"],
                "target_1": trade_plan["target_1"],
                "target_2": trade_plan["target_2"],
                "invalidation": trade_plan["invalidation"],
                "risk_reward": trade_plan["risk_reward"],
            },
            "scenarios": payload["scenarios"],
        },
        "DECISION_ASSESSMENT": {
            "decision": payload["decision"],
            "probabilities": payload["probabilities"],
            "next_actions": payload["next_actions"],
        },
    }


def _images() -> tuple[ProviderImage, ProviderImage, ProviderImage]:
    buf = BytesIO()
    Image.new("RGB", (1, 1), (255, 255, 255)).save(buf, format="PNG")
    png_bytes = buf.getvalue()
    Image.open(BytesIO(png_bytes)).verify()
    size = len(png_bytes)
    return (
        ProviderImage(uuid.uuid4(), "image/png", "user/session/file-1.png", size, 1, 1),
        ProviderImage(uuid.uuid4(), "image/png", "user/session/file-2.png", size, 1, 1),
        ProviderImage(uuid.uuid4(), "image/png", "user/session/file-3.png", size, 1, 1),
    )


class TestPartitionSchemas:
    def test_each_partition_schema_contains_only_allowed_top_level_keys(self) -> None:
        schemas = build_partition_schemas(_schema_root())
        for partition in PARTITIONS:
            schema = schemas[partition.name].provider_schema
            assert tuple(schema["properties"].keys()) == partition.top_level_keys
            assert tuple(schema["required"]) == partition.top_level_keys

    def test_partition_ownership_is_non_overlapping_by_nested_path(self) -> None:
        seen: set[str] = set()
        for partition in PARTITIONS:
            for path in partition.required_paths:
                assert path not in seen
                seen.add(path)

        assert "trade_plan.nearest_support" in seen
        assert "trade_plan.stop_loss" in seen
        assert "decision" in seen

    def test_partition_validation_rejects_unexpected_nested_fields(self) -> None:
        schemas = build_partition_schemas(_schema_root())
        payload = dict(_partition_payloads()["CHART_ANALYSIS"])
        payload["trade_plan"] = {
            **payload["trade_plan"],
            "stop_loss": 2750,
        }

        is_valid, issues = validate_partition_payload(
            payload=payload,
            partition_name="CHART_ANALYSIS",
            schemas=schemas,
        )

        assert is_valid is False
        assert any(issue.code == "SCHEMA_UNKNOWN_PROPERTY" for issue in issues)

    def test_images_are_routed_only_to_market_and_chart_partitions(self) -> None:
        images = _images()
        assert [img.storage_reference for img in select_partition_images(partition_name="MARKET_EVIDENCE", images=images)] == ["user/session/file-1.png"]
        assert [img.storage_reference for img in select_partition_images(partition_name="CHART_ANALYSIS", images=images)] == [
            "user/session/file-2.png",
            "user/session/file-3.png",
        ]
        assert select_partition_images(partition_name="TRADE_THESIS", images=images) == ()
        assert select_partition_images(partition_name="DECISION_ASSESSMENT", images=images) == ()

    def test_prompts_reflect_compact_v2_responsibilities(self) -> None:
        prompts = {
            partition.name: build_partition_user_prompt(
                base_user_prompt="Base prompt.",
                partition_name=partition.name,
                validated_context={},
            )
            for partition in PARTITIONS
        }

        assert "metadata; market_facts" in prompts["MARKET_EVIDENCE"]
        assert "limitations must list only missing or unreadable evidence/data constraints" in prompts["MARKET_EVIDENCE"]
        assert "trade_plan.nearest_support" in prompts["CHART_ANALYSIS"]
        assert "trade_plan.entry_zone_low" in prompts["TRADE_THESIS"]
        assert "decision.recommendation must be BUY, WAIT, SKIP, or UNCERTAIN" in prompts["DECISION_ASSESSMENT"]


class TestPartitionMerge:
    def test_deterministic_merge_creates_full_v2_payload(self) -> None:
        merged = merge_partition_payloads(_partition_payloads())

        assert merged == _valid_v2_payload()
        validation = UnifiedValidationService(schema_package_root=str(_schema_root())).validate(
            decimalize_json_numbers_for_validation(merged),
            expected_analysis_type="INITIAL_ANALYSIS",
        )
        assert validation.valid is True

    def test_decision_critical_fields_remain_present(self) -> None:
        merged = merge_partition_payloads(_partition_payloads())

        assert merged["decision"]["recommendation"] == "WAIT"
        assert merged["decision"]["bias"] == "BULLISH"
        assert merged["decision"]["confidence"] == 72
        assert merged["trade_plan"]["entry_zone_low"] == 2780
        assert merged["trade_plan"]["chase_limit"] == 2820
        assert merged["trade_plan"]["stop_loss"] == 2750
        assert merged["trade_plan"]["target_1"] == 2850
        assert merged["trade_plan"]["target_2"] == 2900
        assert merged["trade_plan"]["invalidation"] == 2750
        assert merged["probabilities"]["bullish"] == 58
        assert merged["next_actions"]["monitoring"]

    def test_v1_narrative_fields_are_removed_from_v2(self) -> None:
        merged = merge_partition_payloads(_partition_payloads())
        removed = {
            "executive_summary",
            "orderbook_analysis",
            "chart_3_month_analysis",
            "chart_6_month_analysis",
            "combined_chart_analysis",
            "price_levels",
            "entry_plan",
            "stop_loss_plan",
            "target_plan",
            "initial_thesis",
            "trading_plan",
            "ai_assessment",
            "warnings_and_missing_information",
        }

        assert removed.isdisjoint(merged)

    def test_schema_caps_array_sizes(self) -> None:
        schema = json.loads((_schema_root() / "initial_analysis_v2.schema.json").read_text())
        assert schema["$defs"]["findingArray"]["maxItems"] == 3

    def test_validation_decimalizes_json_floats_without_mutating_payload(self) -> None:
        payload = {"market_facts": {"close_or_last": 5125.5}, "signals": [1.25, {"price": 99.9}]}

        validation_payload = decimalize_json_numbers_for_validation(payload)

        assert payload["market_facts"]["close_or_last"] == 5125.5
        assert validation_payload["market_facts"]["close_or_last"] == Decimal("5125.5")
        assert validation_payload["signals"][0] == Decimal("1.25")
        assert validation_payload["signals"][1]["price"] == Decimal("99.9")

    def test_overlapping_nested_fields_are_rejected(self) -> None:
        payloads = _partition_payloads()
        payloads["TRADE_THESIS"]["trade_plan"]["nearest_support"] = 2780

        with pytest.raises(ValueError, match="Duplicate INITIAL_ANALYSIS field"):
            merge_partition_payloads(payloads)

    def test_missing_partition_is_rejected(self) -> None:
        payloads = _partition_payloads()
        payloads.pop("DECISION_ASSESSMENT")

        with pytest.raises(ValueError, match="Missing required INITIAL_ANALYSIS partition"):
            merge_partition_payloads(payloads)

    def test_flexible_validation_keeps_schema_drift_non_blocking_when_requested(self) -> None:
        payload = _valid_v2_payload()
        payload["decision"].pop("bias")

        validation = UnifiedValidationService(schema_package_root=str(_schema_root())).validate(
            decimalize_json_numbers_for_validation(payload),
            expected_analysis_type="INITIAL_ANALYSIS",
            continue_on_schema_errors=True,
        )

        assert validation.valid is False
        assert any(issue.code == "SCHEMA_REQUIRED_FIELD_MISSING" for issue in validation.issues)
