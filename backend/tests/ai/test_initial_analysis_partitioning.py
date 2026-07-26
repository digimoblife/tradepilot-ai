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
    build_partition_user_prompt,
    build_partition_schemas,
    get_partition,
    decimalize_json_numbers_for_validation,
    merge_partition_payloads,
    select_partition_images,
    validate_partition_payload,
)
from app.ai.providers import ProviderImage
from app.ai.providers.gemini import normalize_initial_analysis_transport_payload
from app.validation import UnifiedValidationService


def _schema_root() -> Path:
    return Path(__file__).resolve().parents[3] / "schemas" / "production" / "v1"


def _valid_initial_analysis_payload() -> dict[str, object]:
    fixture_path = (
        Path(__file__).resolve().parents[3]
        / "schemas"
        / "fixtures"
        / "valid"
        / "v1"
        / "initial_analysis.valid.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    market_snapshot = payload["market_snapshot"]
    market_snapshot["previous_close"] = market_snapshot["last"]
    market_snapshot["change"] = 0
    market_snapshot["change_percentage"] = 0
    market_snapshot["best_bid"] = market_snapshot["best_offer"]
    market_snapshot["spread"] = 0
    market_snapshot["spread_percentage"] = 0
    return payload


def _transport_initial_analysis_payload() -> dict[str, object]:
    payload = _valid_initial_analysis_payload()
    for section_name in ("chart_3_month_analysis", "chart_6_month_analysis"):
        section = payload[section_name]
        section["nearest_support"] = (
            section["nearest_support"]["price"] if section["nearest_support"] is not None else None
        )
        section["nearest_resistance"] = (
            section["nearest_resistance"]["price"] if section["nearest_resistance"] is not None else None
        )
        section.pop("structure_status", None)
        section.pop("volume_condition", None)
        section.pop("supports_setup", None)
    return payload


def _partition_payloads() -> dict[str, dict[str, object]]:
    canonical = _valid_initial_analysis_payload()
    transport = _transport_initial_analysis_payload()
    return {
        "MARKET_EVIDENCE": {
            key: canonical[key] for key in get_partition("MARKET_EVIDENCE").top_level_keys
        },
        "CHART_ANALYSIS": {
            key: transport[key] for key in get_partition("CHART_ANALYSIS").top_level_keys
        },
        "TRADE_THESIS": {
            key: canonical[key] for key in get_partition("TRADE_THESIS").top_level_keys
        },
        "DECISION_ASSESSMENT": {
            key: canonical[key] for key in get_partition("DECISION_ASSESSMENT").top_level_keys
        },
    }


def _normalized_partition_payloads() -> dict[str, dict[str, object]]:
    payloads = _partition_payloads()
    chart_payload = normalize_initial_analysis_transport_payload(payloads["CHART_ANALYSIS"])
    payloads["CHART_ANALYSIS"] = chart_payload
    return payloads


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

    def test_chart_partition_uses_reduced_provider_level_types(self) -> None:
        schemas = build_partition_schemas(_schema_root())
        chart_schema = schemas["CHART_ANALYSIS"].provider_schema
        chart = chart_schema["properties"]["chart_3_month_analysis"]
        assert chart["properties"]["nearest_support"] == {
            "oneOf": [{"type": "number"}, {"type": "null"}]
        }
        assert chart["properties"]["nearest_resistance"] == {
            "oneOf": [{"type": "number"}, {"type": "null"}]
        }

    def test_partition_validation_rejects_unexpected_top_level_keys(self) -> None:
        schemas = build_partition_schemas(_schema_root())
        payload = dict(_partition_payloads()["MARKET_EVIDENCE"])
        payload["chart_3_month_analysis"] = {}

        is_valid, issues = validate_partition_payload(
            payload=payload,
            partition_name="MARKET_EVIDENCE",
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

    def test_trade_thesis_prompt_includes_authoritative_risk_reward_formula(self) -> None:
        prompt = build_partition_user_prompt(
            base_user_prompt="Base prompt.",
            partition_name="TRADE_THESIS",
            validated_context={},
        )

        assert "target_plan.risk_reward_ratio must equal" in prompt
        assert "(target_plan.target_price - reference_entry)" in prompt
        assert "entry_plan.entry_price for EXACT_PRICE" in prompt
        assert "entry_plan.entry_zone_low for PRICE_ZONE" in prompt


class TestPartitionMerge:
    def test_deterministic_merge_creates_full_canonical_payload(self) -> None:
        merged = merge_partition_payloads(_normalized_partition_payloads())

        validation = UnifiedValidationService(schema_package_root=str(_schema_root())).validate(
            decimalize_json_numbers_for_validation(merged),
            expected_analysis_type="INITIAL_ANALYSIS",
        )
        assert validation.valid is True

    def test_validation_decimalizes_json_floats_without_mutating_payload(self) -> None:
        payload = {"market_snapshot": {"last": 5125.5}, "signals": [1.25, {"price": 99.9}]}

        validation_payload = decimalize_json_numbers_for_validation(payload)

        assert payload["market_snapshot"]["last"] == 5125.5
        assert validation_payload["market_snapshot"]["last"] == Decimal("5125.5")
        assert validation_payload["signals"][0] == Decimal("1.25")
        assert validation_payload["signals"][1]["price"] == Decimal("99.9")

    def test_overlapping_keys_are_rejected(self) -> None:
        payloads = _normalized_partition_payloads()
        payloads["TRADE_THESIS"]["market_snapshot"] = payloads["MARKET_EVIDENCE"]["market_snapshot"]

        with pytest.raises(ValueError, match="overlapping or unexpected"):
            merge_partition_payloads(payloads)

    def test_missing_partition_is_rejected(self) -> None:
        payloads = _normalized_partition_payloads()
        payloads.pop("DECISION_ASSESSMENT")

        with pytest.raises(ValueError, match="Missing required INITIAL_ANALYSIS partition"):
            merge_partition_payloads(payloads)
