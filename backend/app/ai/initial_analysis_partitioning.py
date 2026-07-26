"""Partitioned Gemini generation helpers for INITIAL_ANALYSIS."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence

from jsonschema import Draft202012Validator, ValidationError

from app.ai.providers.gemini import load_initial_analysis_response_schema
from app.ai.providers.models import ProviderImage
from app.validation import ValidationCategory, ValidationIssue, ValidationSeverity
from app.validation.json_schema import _deduplicate, _error_to_issues, _issue_sort_key

_SCHEMA_ROOT = Path("schemas/production/v1")


@dataclass(frozen=True, slots=True)
class InitialAnalysisPartition:
    name: str
    top_level_keys: tuple[str, ...]
    required_paths: tuple[str, ...]
    prompt_suffix: str
    image_indexes: tuple[int, ...]


PARTITIONS: tuple[InitialAnalysisPartition, ...] = (
    InitialAnalysisPartition(
        name="MARKET_EVIDENCE",
        top_level_keys=(
            "metadata",
            "market_facts",
            "evidence_findings",
        ),
        required_paths=(
            "metadata",
            "market_facts",
            "evidence_findings.orderbook",
            "evidence_findings.broker_summary",
            "evidence_findings.foreign_flow",
            "evidence_findings.limitations",
        ),
        prompt_suffix=(
            "Produce only the compact v2 MARKET_EVIDENCE partition.\n"
            "Allowed fields: metadata; market_facts; evidence_findings.orderbook; "
            "evidence_findings.broker_summary; evidence_findings.foreign_flow; "
            "evidence_findings.limitations.\n"
            "Do not include chart findings, trade_plan, decision, probabilities, scenarios, or next_actions.\n"
            "limitations must list only missing or unreadable evidence/data constraints.\n"
            "Do not write generic disclaimers about snapshots, AI uncertainty, market risk, or investment advice.\n"
            "metadata.schema_name must be initial_analysis_v2; schema_version and prompt_version must be 2.0.0.\n"
            "All user-facing string findings must be Bahasa Indonesia, not English.\n"
            "Use arrays with at most 3 items; each item maximum 20 words."
        ),
        image_indexes=(0,),
    ),
    InitialAnalysisPartition(
        name="CHART_ANALYSIS",
        top_level_keys=(
            "evidence_findings",
            "trade_plan",
        ),
        required_paths=(
            "evidence_findings.chart_3_month",
            "evidence_findings.chart_6_month",
            "trade_plan.nearest_support",
            "trade_plan.nearest_resistance",
        ),
        prompt_suffix=(
            "Produce only the compact v2 CHART_ANALYSIS partition.\n"
            "Allowed fields: evidence_findings.chart_3_month; evidence_findings.chart_6_month; "
            "trade_plan.nearest_support; trade_plan.nearest_resistance.\n"
            "Do not include orderbook, broker, foreign flow, decision, probabilities, scenarios, or entry/stop/target fields.\n"
            "All user-facing chart findings must be Bahasa Indonesia, not English.\n"
            "Use arrays with at most 3 items; each item maximum 20 words."
        ),
        image_indexes=(1, 2),
    ),
    InitialAnalysisPartition(
        name="TRADE_THESIS",
        top_level_keys=(
            "trade_plan",
            "scenarios",
        ),
        required_paths=(
            "trade_plan.entry_zone_low",
            "trade_plan.entry_zone_high",
            "trade_plan.chase_limit",
            "trade_plan.stop_loss",
            "trade_plan.target_1",
            "trade_plan.target_2",
            "trade_plan.invalidation",
            "trade_plan.risk_reward",
            "scenarios",
        ),
        prompt_suffix=(
            "Produce only the compact v2 TRADE_THESIS partition.\n"
            "Allowed fields: trade_plan.entry_zone_low; entry_zone_high; chase_limit; stop_loss; "
            "target_1; target_2; invalidation; risk_reward; scenarios.\n"
            "Do not include nearest support/resistance, evidence narratives, decision, probabilities, or next_actions.\n"
            "All user-facing scenario strings must be Bahasa Indonesia, not English.\n"
            "Each scenario must be one Indonesian sentence with maximum 25 words."
        ),
        image_indexes=(),
    ),
    InitialAnalysisPartition(
        name="DECISION_ASSESSMENT",
        top_level_keys=(
            "decision",
            "probabilities",
            "next_actions",
        ),
        required_paths=(
            "decision",
            "probabilities",
            "next_actions",
        ),
        prompt_suffix=(
            "Produce only the compact v2 DECISION_ASSESSMENT partition.\n"
            "Allowed fields: decision; probabilities; next_actions.\n"
            "decision.recommendation must be BUY, WAIT, SKIP, or UNCERTAIN.\n"
            "decision.summary maximum 50 words. next_actions arrays have at most 3 items, each maximum 20 words.\n"
            "All user-facing summary, reasons, risks, and monitoring strings must be Bahasa Indonesia, not English.\n"
            "Do not repeat detailed evidence or trade thesis narratives."
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
    raw_schema = json.loads((package_root / "initial_analysis_v2.schema.json").read_text(encoding="utf-8"))
    validation_schema = _resolve_schema_node(
        raw_schema,
        schema_path=package_root / "initial_analysis_v2.schema.json",
        package_root=package_root,
        document=raw_schema,
    )

    schemas: dict[str, PartitionSchemas] = {}
    for partition in PARTITIONS:
        schemas[partition.name] = PartitionSchemas(
            provider_schema=_derive_partition_schema(canonical_schema, partition.required_paths),
            validation_schema=_derive_partition_schema(validation_schema, partition.required_paths),
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
        allowed_roots = set(partition.top_level_keys)
        extra_roots = sorted(set(payload) - allowed_roots)
        if extra_roots:
            raise ValueError(
                f"Partition {partition.name} contains overlapping or unexpected top-level key(s): {', '.join(extra_roots)}"
            )
        for path in partition.required_paths:
            if not _has_path(payload, path):
                raise ValueError(f"Partition {partition.name} is missing required field path: {path}")
        _deep_merge_partition(merged, payload, partition.name)

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
        extra_roots = sorted(set(payload) - set(partition.top_level_keys))
        if extra_roots:
            raise ValueError(
                f"Partition {partition.name} contains unexpected context key(s): {', '.join(extra_roots)}"
            )
        _deep_merge_partition(merged, payload, partition.name)
    return merged


def _derive_partition_schema(
    schema: Mapping[str, object],
    field_paths: Sequence[str],
) -> dict[str, object]:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("INITIAL_ANALYSIS schema must be an object with properties and required")

    top_level_keys = tuple(dict.fromkeys(path.split(".", 1)[0] for path in field_paths))
    missing_keys = [key for key in top_level_keys if key not in properties]
    if missing_keys:
        raise ValueError(f"INITIAL_ANALYSIS schema missing partition key(s): {', '.join(missing_keys)}")

    derived = {
        "type": "object",
        "additionalProperties": False,
        "properties": {},
        "required": list(top_level_keys),
    }
    for key in top_level_keys:
        source = properties[key]
        nested_paths = [
            path.split(".", 1)[1]
            for path in field_paths
            if path.startswith(f"{key}.")
        ]
        if nested_paths and isinstance(source, Mapping):
            derived["properties"][key] = _derive_nested_object_schema(source, nested_paths)
        else:
            derived["properties"][key] = copy.deepcopy(source)
    if "$defs" in schema and isinstance(schema["$defs"], dict):
        derived["$defs"] = copy.deepcopy(schema["$defs"])
    return derived


def _derive_nested_object_schema(
    schema: Mapping[str, object],
    field_paths: Sequence[str],
) -> dict[str, object]:
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        raise ValueError("Nested INITIAL_ANALYSIS schema must include properties")
    nested_keys = tuple(dict.fromkeys(path.split(".", 1)[0] for path in field_paths))
    missing = [key for key in nested_keys if key not in properties]
    if missing:
        raise ValueError(f"Nested INITIAL_ANALYSIS schema missing key(s): {', '.join(missing)}")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {key: copy.deepcopy(properties[key]) for key in nested_keys},
        "required": list(nested_keys),
    }


def _has_path(payload: Mapping[str, object], path: str) -> bool:
    current: object = payload
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False
        current = current[part]
    return True


def _deep_merge_partition(
    merged: dict[str, object],
    payload: Mapping[str, object],
    partition_name: str,
) -> None:
    for key, value in payload.items():
        if key not in merged:
            merged[key] = copy.deepcopy(value)
            continue
        existing = merged[key]
        if isinstance(existing, dict) and isinstance(value, Mapping):
            for nested_key, nested_value in value.items():
                if nested_key in existing:
                    raise ValueError(
                        f"Duplicate INITIAL_ANALYSIS field during merge: {key}.{nested_key}"
                    )
                existing[nested_key] = copy.deepcopy(nested_value)
            continue
        raise ValueError(
            f"Duplicate INITIAL_ANALYSIS top-level key during merge: {key} from {partition_name}"
        )


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
