"""Partitioned Gemini generation helpers for INITIAL_ANALYSIS."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence

from jsonschema import Draft202012Validator, ValidationError

from app.ai.providers.gemini import (
    build_initial_analysis_transport_schema,
    load_initial_analysis_response_schema,
)
from app.ai.providers.models import ProviderImage
from app.validation import ValidationCategory, ValidationIssue, ValidationSeverity
from app.validation.json_schema import _deduplicate, _error_to_issues, _issue_sort_key

_SCHEMA_ROOT = Path("schemas/production/v1")


@dataclass(frozen=True, slots=True)
class InitialAnalysisPartition:
    name: str
    top_level_keys: tuple[str, ...]
    prompt_suffix: str
    image_indexes: tuple[int, ...]


PARTITIONS: tuple[InitialAnalysisPartition, ...] = (
    InitialAnalysisPartition(
        name="MARKET_EVIDENCE",
        top_level_keys=(
            "metadata",
            "evidence_summary",
            "market_snapshot",
            "executive_summary",
            "orderbook_analysis",
        ),
        prompt_suffix=(
            "Produce only the market and evidence partition of the INITIAL_ANALYSIS JSON.\n"
            "Allowed top-level keys: metadata, evidence_summary, market_snapshot, "
            "executive_summary, orderbook_analysis.\n"
            "metadata.analysis_type must be exactly INITIAL_ANALYSIS.\n"
            "metadata.language must be exactly id.\n"
            "metadata.schema.schema_name must be exactly initial_analysis.\n"
            "metadata.schema.schema_version must be exactly 1.0.0.\n"
            "metadata.prompt_version must be exactly 1.0.0.\n"
            "Do not include any other top-level keys."
        ),
        image_indexes=(0,),
    ),
    InitialAnalysisPartition(
        name="CHART_ANALYSIS",
        top_level_keys=(
            "chart_3_month_analysis",
            "chart_6_month_analysis",
            "combined_chart_analysis",
        ),
        prompt_suffix=(
            "Produce only the chart-analysis partition of the INITIAL_ANALYSIS JSON.\n"
            "Allowed top-level keys: chart_3_month_analysis, chart_6_month_analysis, "
            "combined_chart_analysis.\n"
            "Do not include any other top-level keys."
        ),
        image_indexes=(1, 2),
    ),
    InitialAnalysisPartition(
        name="TRADE_THESIS",
        top_level_keys=(
            "price_levels",
            "entry_plan",
            "stop_loss_plan",
            "target_plan",
            "initial_thesis",
        ),
        prompt_suffix=(
            "Produce only the trade-thesis partition of the INITIAL_ANALYSIS JSON.\n"
            "Allowed top-level keys: price_levels, entry_plan, stop_loss_plan, target_plan, "
            "initial_thesis.\n"
            "If entry_recommended, stop_loss_recommended, and target_recommended are all true, "
            "target_plan.risk_reward_ratio must equal "
            "(target_plan.target_price - reference_entry) / (reference_entry - stop_loss_plan.stop_loss_price), "
            "where reference_entry is entry_plan.entry_price for EXACT_PRICE and "
            "entry_plan.entry_zone_low for PRICE_ZONE. Use null when the ratio cannot be safely calculated.\n"
            "Do not include any other top-level keys."
        ),
        image_indexes=(),
    ),
    InitialAnalysisPartition(
        name="DECISION_ASSESSMENT",
        top_level_keys=(
            "trading_plan",
            "ai_assessment",
            "warnings_and_missing_information",
        ),
        prompt_suffix=(
            "Produce only the decision-assessment partition of the INITIAL_ANALYSIS JSON.\n"
            "Allowed top-level keys: trading_plan, ai_assessment, "
            "warnings_and_missing_information.\n"
            "If trading_plan.current_action is WAIT, DO_NOT_ENTER, or CANCEL_SETUP, "
            "trading_plan.requires_user_confirmation must be false. Use true only when "
            "trading_plan.current_action is ENTER_IF_CONFIRMED.\n"
            "Do not include any other top-level keys."
        ),
        image_indexes=(),
    ),
)
_PARTITION_BY_NAME = {partition.name: partition for partition in PARTITIONS}


@dataclass(frozen=True, slots=True)
class PartitionSchemas:
    provider_schema: dict[str, object]
    validation_schema: dict[str, object]


def get_partition(name: str) -> InitialAnalysisPartition:
    return _PARTITION_BY_NAME[name]


def build_partition_schemas(
    schema_package_root: str | Path = _SCHEMA_ROOT,
) -> dict[str, PartitionSchemas]:
    package_root = Path(schema_package_root)
    canonical_schema = load_initial_analysis_response_schema(schema_package_root)
    transport_schema = build_initial_analysis_transport_schema(canonical_schema)
    raw_schema = json.loads((package_root / "initial_analysis.schema.json").read_text(encoding="utf-8"))
    validation_schema = _resolve_schema_node(
        raw_schema,
        schema_path=package_root / "initial_analysis.schema.json",
        package_root=package_root,
        document=raw_schema,
    )

    schemas: dict[str, PartitionSchemas] = {}
    for partition in PARTITIONS:
        provider_base = transport_schema if partition.name == "CHART_ANALYSIS" else canonical_schema
        schemas[partition.name] = PartitionSchemas(
            provider_schema=_derive_partition_schema(provider_base, partition.top_level_keys),
            validation_schema=_derive_partition_schema(validation_schema, partition.top_level_keys),
        )
    return schemas


def build_partition_user_prompt(
    *,
    base_user_prompt: str,
    partition_name: str,
    validated_context: Mapping[str, Mapping[str, object]],
) -> str:
    partition = get_partition(partition_name)
    lines = [
        base_user_prompt.rstrip(),
        "",
        partition.prompt_suffix,
        "Return one JSON object only.",
        "No additional top-level properties are allowed.",
    ]

    if validated_context:
        context_payload = _merge_available_partition_context(validated_context)
        lines.extend(
            [
                "",
                "Use this validated prior-partition context exactly as reference:",
                json.dumps(context_payload, ensure_ascii=False, indent=2),
            ]
        )

    return "\n".join(lines).strip()


def select_partition_images(
    *,
    partition_name: str,
    images: Sequence[ProviderImage],
) -> tuple[ProviderImage, ...]:
    partition = get_partition(partition_name)
    selected: list[ProviderImage] = []
    for index in partition.image_indexes:
        if index < len(images):
            selected.append(images[index])
    return tuple(selected)


def validate_partition_payload(
    *,
    payload: Mapping[str, object],
    partition_name: str,
    schemas: Mapping[str, PartitionSchemas],
) -> tuple[bool, tuple[ValidationIssue, ...]]:
    partition = get_partition(partition_name)
    schema = schemas[partition_name].validation_schema

    payload_keys = set(payload.keys())
    allowed_keys = set(partition.top_level_keys)
    unexpected = sorted(payload_keys - allowed_keys)
    issues: list[ValidationIssue] = []
    for key in unexpected:
        issues.append(
            ValidationIssue(
                code="SCHEMA_UNKNOWN_PROPERTY",
                category=ValidationCategory.ADDITIONAL_PROPERTY,
                severity=ValidationSeverity.ERROR,
                path=f"/{key}",
                message=f"Additional properties are not allowed ('{key}' was unexpected)",
                expected="no additional properties allowed",
                actual=payload.get(key),
            )
        )

    validator = Draft202012Validator(schema)
    for error in validator.iter_errors(dict(payload)):
        issues.extend(_partition_error_to_issues(error))

    deduped = _deduplicate(issues)
    deduped.sort(key=_issue_sort_key)
    return len(deduped) == 0, tuple(deduped)


def merge_partition_payloads(
    payloads_by_partition: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    missing = [partition.name for partition in PARTITIONS if partition.name not in payloads_by_partition]
    if missing:
        raise ValueError(f"Missing required INITIAL_ANALYSIS partition(s): {', '.join(missing)}")

    merged: dict[str, object] = {}
    for partition in PARTITIONS:
        payload = payloads_by_partition[partition.name]
        for key in partition.top_level_keys:
            if key not in payload:
                raise ValueError(f"Partition {partition.name} is missing required top-level key: {key}")
            if key in merged:
                raise ValueError(f"Duplicate INITIAL_ANALYSIS top-level key during merge: {key}")
            merged[key] = copy.deepcopy(payload[key])

        extra = sorted(set(payload) - set(partition.top_level_keys))
        if extra:
            raise ValueError(
                f"Partition {partition.name} contains overlapping or unexpected top-level key(s): {', '.join(extra)}"
            )

    return merged


def decimalize_json_numbers_for_validation(value: object) -> object:
    """Return a validation-only copy with JSON floats converted to Decimal."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, list):
        return [decimalize_json_numbers_for_validation(item) for item in value]
    if isinstance(value, dict):
        return {
            key: decimalize_json_numbers_for_validation(item)
            for key, item in value.items()
        }
    return value


def _merge_available_partition_context(
    payloads_by_partition: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    merged: dict[str, object] = {}
    for partition in PARTITIONS:
        payload = payloads_by_partition.get(partition.name)
        if payload is None:
            continue
        extra = sorted(set(payload) - set(partition.top_level_keys))
        if extra:
            raise ValueError(
                f"Partition {partition.name} contains unexpected context key(s): {', '.join(extra)}"
            )
        for key in partition.top_level_keys:
            if key in payload:
                if key in merged:
                    raise ValueError(f"Duplicate INITIAL_ANALYSIS context key: {key}")
                merged[key] = copy.deepcopy(payload[key])
    return merged


def _derive_partition_schema(
    schema: Mapping[str, object],
    top_level_keys: Sequence[str],
) -> dict[str, object]:
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise ValueError("INITIAL_ANALYSIS schema must be an object with properties and required")

    missing_keys = [key for key in top_level_keys if key not in properties]
    if missing_keys:
        raise ValueError(f"INITIAL_ANALYSIS schema missing partition key(s): {', '.join(missing_keys)}")

    derived = {
        "type": "object",
        "additionalProperties": False,
        "properties": {key: copy.deepcopy(properties[key]) for key in top_level_keys},
        "required": [key for key in required if key in top_level_keys],
    }
    if "$defs" in schema and isinstance(schema["$defs"], dict):
        derived["$defs"] = copy.deepcopy(schema["$defs"])
    filtered_all_of = _filter_root_all_of(schema.get("allOf"), set(top_level_keys))
    if filtered_all_of:
        derived["allOf"] = filtered_all_of
    return derived


def _partition_error_to_issues(error: ValidationError) -> list[ValidationIssue]:
    return _error_to_issues(error)


def _filter_root_all_of(value: object, allowed_keys: set[str]) -> list[object]:
    if not isinstance(value, list):
        return []
    filtered: list[object] = []
    for item in value:
        referenced = _root_property_names(item)
        if referenced and referenced <= allowed_keys:
            filtered.append(copy.deepcopy(item))
    return filtered


def _root_property_names(node: object) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            names.update(str(key) for key in properties.keys())
        for key, value in node.items():
            if key == "properties":
                continue
            names.update(_root_property_names(value))
    elif isinstance(node, list):
        for item in node:
            names.update(_root_property_names(item))
    return names


def _resolve_schema_node(
    node: object,
    *,
    schema_path: Path,
    package_root: Path,
    document: dict[str, object],
) -> object:
    if isinstance(node, list):
        return [
            _resolve_schema_node(
                item,
                schema_path=schema_path,
                package_root=package_root,
                document=document,
            )
            for item in node
        ]
    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        resolved, resolved_path, resolved_document = _resolve_schema_ref(
            str(node["$ref"]),
            schema_path=schema_path,
            package_root=package_root,
            document=document,
        )
        merged = dict(resolved)
        for key, value in node.items():
            if key != "$ref":
                merged[key] = value
        return _resolve_schema_node(
            merged,
            schema_path=resolved_path,
            package_root=package_root,
            document=resolved_document,
        )

    return {
        key: _resolve_schema_node(
            value,
            schema_path=schema_path,
            package_root=package_root,
            document=document,
        )
        for key, value in node.items()
    }


def _resolve_schema_ref(
    ref: str,
    *,
    schema_path: Path,
    package_root: Path,
    document: dict[str, object],
) -> tuple[dict[str, object], Path, dict[str, object]]:
    if ref.startswith("#/"):
        return _resolve_json_pointer(document, ref[1:]), schema_path, document

    path_part, _, pointer = ref.partition("#")
    if ref.startswith("https://schemas.tradepilot.local/production/v1/"):
        filename = path_part.rsplit("/", 1)[-1]
        target_path = package_root / filename
    else:
        target_path = (schema_path.parent / path_part).resolve()

    target_document = json.loads(target_path.read_text(encoding="utf-8"))
    if not pointer:
        return target_document, target_path, target_document
    return _resolve_json_pointer(target_document, pointer), target_path, target_document


def _resolve_json_pointer(document: dict[str, object], pointer: str) -> dict[str, object]:
    current: object = document
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise ValueError(f"Schema JSON pointer not found: #{pointer}")
        current = current[token]
    if not isinstance(current, dict):
        raise ValueError(f"Schema JSON pointer must resolve to an object: #{pointer}")
    return current
