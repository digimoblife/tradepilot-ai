"""JSON Schema validation service using cached Draft 2020-12 validators.

Normalizes ``jsonschema`` errors into stable ``ValidationIssue`` objects.
"""

from __future__ import annotations

from typing import cast

from jsonschema import ValidationError

from app.schemas.registry import LocalSchemaRegistry, RegisteredSchema
from app.validation.issues import (
    JsonSchemaValidationResult,
    JsonValue,
    ValidationCategory,
    ValidationIssue,
    ValidationSeverity,
)
from app.validation.json_pointer import build_json_pointer, escape_token

# ---------------------------------------------------------------------------
# Stable issue-code mapping
# ---------------------------------------------------------------------------

_ERROR_CODE_MAP: dict[str, str] = {
    "required": "SCHEMA_REQUIRED_FIELD_MISSING",
    "additionalProperties": "SCHEMA_UNKNOWN_PROPERTY",
    "type": "SCHEMA_TYPE_MISMATCH",
    "format": "SCHEMA_FORMAT_INVALID",
    "enum": "SCHEMA_ENUM_INVALID",
    "const": "SCHEMA_CONST_MISMATCH",
    "minimum": "SCHEMA_RANGE_INVALID",
    "maximum": "SCHEMA_RANGE_INVALID",
    "exclusiveMinimum": "SCHEMA_RANGE_INVALID",
    "exclusiveMaximum": "SCHEMA_RANGE_INVALID",
    "multipleOf": "SCHEMA_MULTIPLE_OF_INVALID",
    "minLength": "SCHEMA_STRING_LENGTH_INVALID",
    "maxLength": "SCHEMA_STRING_LENGTH_INVALID",
    "pattern": "SCHEMA_PATTERN_INVALID",
    "minItems": "SCHEMA_ARRAY_LENGTH_INVALID",
    "maxItems": "SCHEMA_ARRAY_LENGTH_INVALID",
    "uniqueItems": "SCHEMA_ARRAY_DUPLICATE_ITEM",
    "oneOf": "SCHEMA_CONDITIONAL_INVALID",
    "anyOf": "SCHEMA_CONDITIONAL_INVALID",
    "allOf": "SCHEMA_CONDITIONAL_INVALID",
    "if": "SCHEMA_CONDITIONAL_INVALID",
    "then": "SCHEMA_CONDITIONAL_INVALID",
    "else": "SCHEMA_CONDITIONAL_INVALID",
    "not": "SCHEMA_CONDITIONAL_INVALID",
}

_CATEGORY_MAP: dict[str, ValidationCategory] = {
    "required": ValidationCategory.REQUIRED,
    "additionalProperties": ValidationCategory.ADDITIONAL_PROPERTY,
    "type": ValidationCategory.TYPE,
    "format": ValidationCategory.FORMAT,
    "enum": ValidationCategory.ENUM,
    "const": ValidationCategory.ENUM,
    "minimum": ValidationCategory.RANGE,
    "maximum": ValidationCategory.RANGE,
    "exclusiveMinimum": ValidationCategory.RANGE,
    "exclusiveMaximum": ValidationCategory.RANGE,
    "multipleOf": ValidationCategory.RANGE,
    "minLength": ValidationCategory.RANGE,
    "maxLength": ValidationCategory.RANGE,
    "pattern": ValidationCategory.FORMAT,
    "minItems": ValidationCategory.RANGE,
    "maxItems": ValidationCategory.RANGE,
    "uniqueItems": ValidationCategory.SCHEMA,
    "oneOf": ValidationCategory.CONDITIONAL,
    "anyOf": ValidationCategory.CONDITIONAL,
    "allOf": ValidationCategory.CONDITIONAL,
    "if": ValidationCategory.CONDITIONAL,
    "then": ValidationCategory.CONDITIONAL,
    "else": ValidationCategory.CONDITIONAL,
    "not": ValidationCategory.CONDITIONAL,
}


def _safe_actual(value: object) -> JsonValue:
    """Return a JSON-safe representation of *value* for diagnostics."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_actual(v) for v in value[:5]]
    if isinstance(value, dict):
        return {str(k): _safe_actual(v) for k, v in list(value.items())[:5]}
    return str(type(value).__name__)


# ---------------------------------------------------------------------------
# Required: extract missing properties structurally
# ---------------------------------------------------------------------------


def _get_required_set(error: ValidationError) -> list[str]:
    """Get the list of required property names from a required error."""
    val = error.validator_value if hasattr(error, "validator_value") else None
    if isinstance(val, list):
        return [str(v) for v in val]
    return []


def _find_missing_properties(
    instance: object,
    required: list[str],
) -> list[str]:
    """Return required keys absent from *instance* when it is a mapping.

    If *instance* is not a mapping all required keys are considered missing.
    """
    if isinstance(instance, dict):
        return sorted(r for r in required if r not in instance)
    return sorted(required)


def _error_to_required_issues(error: ValidationError) -> list[ValidationIssue]:
    """Produce one ``ValidationIssue`` per missing required property."""
    required_set = _get_required_set(error)
    if not required_set:
        return []

    missing = _find_missing_properties(error.instance, required_set)
    if not missing:
        return []

    issues: list[ValidationIssue] = []
    base = list(error.absolute_path)
    for prop in missing:
        parts = base + [prop]
        full_path = build_json_pointer(parts)
        issues.append(
            ValidationIssue(
                code="SCHEMA_REQUIRED_FIELD_MISSING",
                category=ValidationCategory.REQUIRED,
                severity=ValidationSeverity.ERROR,
                path=full_path,
                message=f"'{prop}' is a required property",
                expected=prop,
                actual=None,
            )
        )
    return issues


# ---------------------------------------------------------------------------
# Additional properties: structural key comparison
# ---------------------------------------------------------------------------


def _get_allowed_properties(schema: object) -> set[str]:
    """Return the set of allowed property names from a schema node."""
    allowed: set[str] = set()
    if isinstance(schema, dict):
        props = schema.get("properties")
        if isinstance(props, dict):
            allowed.update(props.keys())
        pat = schema.get("patternProperties")
        if isinstance(pat, dict):
            allowed.update(pat.keys())
    return allowed


def _error_to_additional_issues(error: ValidationError) -> list[ValidationIssue]:
    """Produce one ``ValidationIssue`` per unexpected property."""
    instance = error.instance if hasattr(error, "instance") else {}
    schema = error.schema if hasattr(error, "schema") else {}

    allowed = _get_allowed_properties(schema)
    if not isinstance(instance, dict) or not allowed:
        return _fallback_additional_issues(error)

    extra_keys = sorted(k for k in instance if k not in allowed)
    if not extra_keys:
        return _fallback_additional_issues(error)

    issues: list[ValidationIssue] = []
    base = list(error.absolute_path)
    for key in extra_keys:
        parts = base + [key]
        full_path = build_json_pointer(parts)
        issues.append(
            ValidationIssue(
                code="SCHEMA_UNKNOWN_PROPERTY",
                category=ValidationCategory.ADDITIONAL_PROPERTY,
                severity=ValidationSeverity.ERROR,
                path=full_path,
                message=f"Additional properties are not allowed ('{key}' was unexpected)",
                expected="no additional properties allowed",
                actual=_safe_actual(instance.get(key)),
            )
        )
    return issues


def _fallback_additional_issues(error: ValidationError) -> list[ValidationIssue]:
    """Fallback: extract property name from English message text."""
    extra = _extract_additional_property_from_message(error)
    if extra:
        path = build_json_pointer(list(error.absolute_path))
        path = path + "/" + escape_token(extra) if path else "/" + escape_token(extra)
        return [
            ValidationIssue(
                code="SCHEMA_UNKNOWN_PROPERTY",
                category=ValidationCategory.ADDITIONAL_PROPERTY,
                severity=ValidationSeverity.ERROR,
                path=path,
                message=f"Additional properties are not allowed ('{extra}' was unexpected)",
                expected="no additional properties allowed",
                actual=_safe_actual(_try_get_instance_value(error.instance, extra)),
            )
        ]
    return [
        _build_single_issue(error),
    ]


def _try_get_instance_value(instance: object, key: str) -> object:
    """Safely retrieve a key from a mapping."""
    if isinstance(instance, dict):
        return instance.get(key)
    return None


def _extract_additional_property_from_message(error: ValidationError) -> str | None:
    """Parse the extra property name from ``additionalProperties`` message."""
    try:
        if hasattr(error, "message"):
            msg: str = cast(str, error.message)
            for token in msg.split():
                raw = token.strip("(").strip(")")
                if raw.startswith("'") and raw.endswith("'") and len(raw) > 2:
                    return raw[1:-1]
                if raw.startswith('"') and raw.endswith('"') and len(raw) > 2:
                    return raw[1:-1]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Single-issue converters (all other validator types)
# ---------------------------------------------------------------------------


def _build_single_issue(error: ValidationError) -> ValidationIssue:
    """Convert a single ``jsonschema.ValidationError`` to a ``ValidationIssue``."""
    validator = error.validator if error.validator else ""
    code = _ERROR_CODE_MAP.get(validator, f"SCHEMA_{validator.upper()}_INVALID")
    category = _CATEGORY_MAP.get(validator, ValidationCategory.SCHEMA)
    path = build_json_pointer(list(error.absolute_path))

    expected: JsonValue = None
    actual: JsonValue = None

    if validator == "type":
        expected = _val(error, "validator_value")
        actual = _safe_actual(error.instance) if hasattr(error, "instance") else None
    elif validator == "format":
        expected = _val(error, "validator_value") or cast(str, error.message)
        actual = _safe_actual(error.instance) if hasattr(error, "instance") else None
    elif validator == "enum":
        expected = list(error.validator_value) if hasattr(error, "validator_value") else None
        actual = _safe_actual(error.instance) if hasattr(error, "instance") else None
    elif validator == "const":
        expected = _val(error, "validator_value")
        actual = _safe_actual(error.instance) if hasattr(error, "instance") else None
    elif validator in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
        expected = _range_expected(error, validator)
        actual = _safe_actual(error.instance) if hasattr(error, "instance") else None
    elif validator in ("minLength", "maxLength", "pattern"):
        expected = _range_expected(error, validator)
        actual = _safe_actual(error.instance) if hasattr(error, "instance") else None
    elif validator in ("minItems", "maxItems"):
        expected = _range_expected(error, validator)
        actual = _safe_actual(error.instance) if hasattr(error, "instance") else None
    elif validator in ("required", "additionalProperties"):
        expected = "no additional properties allowed"
        actual = _safe_actual(error.instance) if hasattr(error, "instance") else None
    else:
        expected = cast(JsonValue, error.schema)
        actual = _safe_actual(error.instance) if hasattr(error, "instance") else None

    return ValidationIssue(
        code=code,
        category=category,
        severity=ValidationSeverity.ERROR,
        path=path,
        message=error.message,
        expected=expected,
        actual=actual,
    )


def _val(error: ValidationError, attr: str) -> JsonValue:
    """Safely get an attribute as JsonValue."""
    v = getattr(error, attr, None)
    return cast(JsonValue, v) if v is not None else None


def _range_expected(error: ValidationError, validator: str) -> str | None:
    v = getattr(error, "validator_value", None)
    return f"{validator}: {v}" if v is not None else None


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------


def _error_to_issues(error: ValidationError) -> list[ValidationIssue]:
    """Dispatch to the correct converter based on validator type."""
    validator = error.validator if error.validator else ""
    if validator == "required":
        issues = _error_to_required_issues(error)
        if issues:
            return issues
        return [_build_single_issue(error)]
    if validator == "additionalProperties":
        issues = _error_to_additional_issues(error)
        if issues:
            return issues
        return [_build_single_issue(error)]
    return [_build_single_issue(error)]


# ---------------------------------------------------------------------------
# Sorting key
# ---------------------------------------------------------------------------


def _issue_sort_key(issue: ValidationIssue) -> tuple[str, str, str, str]:
    return (issue.path, issue.category.value, issue.code, issue.message)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _deduplication_key(issue: ValidationIssue) -> tuple[str, str, str, str]:
    return (issue.code, issue.path, str(issue.expected), str(issue.actual))


def _deduplicate(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[ValidationIssue] = []
    for issue in issues:
        key = _deduplication_key(issue)
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class JsonSchemaValidationService:
    """Validates payloads against production schemas using cached validators.

    Parameters
    ----------
    registry:
        An already-constructed ``LocalSchemaRegistry`` with compiled validators.
    """

    def __init__(self, registry: LocalSchemaRegistry) -> None:
        self._registry = registry

    def validate_by_name(
        self,
        payload: object,
        schema_name: str,
        schema_version: str,
    ) -> JsonSchemaValidationResult:
        """Validate *payload* against the schema identified by name and version."""
        registered = self._registry.get(schema_name, schema_version)
        return self._validate(payload, registered)

    def validate_by_analysis_type(
        self,
        payload: object,
        analysis_type: str,
    ) -> JsonSchemaValidationResult:
        """Validate *payload* against the schema mapped from an analysis type."""
        registered = self._registry.get_by_analysis_type(analysis_type)
        return self._validate(payload, registered)

    def validate_by_schema_id(
        self,
        payload: object,
        schema_id: str,
    ) -> JsonSchemaValidationResult:
        """Validate *payload* against the schema identified by ``$id``."""
        registered = self._registry.get_by_schema_id(schema_id)
        return self._validate(payload, registered)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _validate(
        self, payload: object, registered: RegisteredSchema
    ) -> JsonSchemaValidationResult:
        validator = registered.validator
        errors = list(validator.iter_errors(payload))

        raw_issues: list[ValidationIssue] = []
        for e in errors:
            raw_issues.extend(_error_to_issues(e))
        deduped = _deduplicate(raw_issues)
        deduped.sort(key=_issue_sort_key)

        return JsonSchemaValidationResult(
            valid=len(deduped) == 0,
            schema_name=registered.manifest_entry.name,
            schema_version=registered.manifest_entry.version,
            schema_id=registered.manifest_entry.schema_id,
            issues=tuple(deduped),
        )
