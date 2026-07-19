"""Unified Validation Service (TP-0312).

Orchestrates schema validation and applicable domain validators for an
analysis payload, returning a single normalized result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from app.schemas.errors import SchemaRegistryError
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry
from app.validation.context_summary import validate_context_summary
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity
from app.validation.json_schema import JsonSchemaValidationService
from app.validation.registry import get_domain_validators
from app.validation.state_consistency import validate_state_consistency
from app.validation.trade_state import validate_trade_state

# ---------------------------------------------------------------------------
# Unified result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UnifiedValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    errors: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    warnings: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        # Derive errors and warnings from issues if not explicitly provided
        if not self.errors and not self.warnings and self.issues:
            err = tuple(i for i in self.issues if i.severity == ValidationSeverity.ERROR)
            warn = tuple(i for i in self.issues if i.severity == ValidationSeverity.WARNING)
            object.__setattr__(self, "errors", err)
            object.__setattr__(self, "warnings", warn)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sort_key(issue: ValidationIssue) -> tuple[str, str, str, str]:
    return (issue.path, issue.code, issue.category.value, issue.message)


def _deduplicate(issues: Sequence[ValidationIssue]) -> tuple[ValidationIssue, ...]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[ValidationIssue] = []
    for issue in issues:
        key = (issue.code, issue.path, str(issue.expected), str(issue.actual))
        if key not in seen:
            seen.add(key)
            result.append(issue)
    result.sort(key=_sort_key)
    return tuple(result)


def _extract_issues(result: object) -> tuple[ValidationIssue, ...]:
    """Extract issues from a validator result that may be a dataclass with
    ``.issues`` or a plain ``tuple[ValidationIssue, ...]``."""
    if isinstance(result, tuple):
        return result
    if hasattr(result, "issues"):
        val = getattr(result, "issues", ())
        if isinstance(val, tuple):
            return val
        if isinstance(val, list):
            return tuple(val)
    return ()


# ---------------------------------------------------------------------------
# Unified service
# ---------------------------------------------------------------------------


class UnifiedValidationService:
    """Unified validation service orchestrating schema and domain validators.

    Requires a pre-built ``JsonSchemaValidationService`` (which in turn
    requires a ``LocalSchemaRegistry``).  Construction loads the production
    manifest and builds the registry once.
    """

    def __init__(
        self,
        schema_package_root: str | None = None,
    ) -> None:
        from pathlib import Path

        pkg_root = (
            Path(schema_package_root) if schema_package_root else Path("schemas/production/v1")
        )
        self._manifest = load_production_manifest(pkg_root)
        self._schema_registry = LocalSchemaRegistry(self._manifest, pkg_root)
        self._schema_service = JsonSchemaValidationService(self._schema_registry)

    # ------------------------------------------------------------------
    # Public validate method
    # ------------------------------------------------------------------

    def validate(
        self,
        payload: Mapping[str, object],
        expected_analysis_type: str,
        trade_state: Mapping[str, object] | None = None,
        session_status_before_job: str | None = None,
        context_summary: Mapping[str, object] | None = None,
    ) -> UnifiedValidationResult:
        """Validate *payload* against all applicable layers.

        Parameters
        ----------
        payload:
            The AI analysis payload (already parsed JSON).
        expected_analysis_type:
            The expected analysis type (e.g. ``"INITIAL_ANALYSIS"``).
        trade_state:
            Optional canonical Trade State payload for state-consistency checks.
        session_status_before_job:
            Optional session status before the analysis job.
        context_summary:
            Optional Context Summary payload for staleness and consistency checks.

        Returns
        -------
        UnifiedValidationResult
        """
        all_issues: list[ValidationIssue] = []

        # ----------------------------------------------------------
        # 1. Schema validation (TP-0303)
        # ----------------------------------------------------------
        schema_issues = self._run_schema_validation(payload, expected_analysis_type)
        all_issues.extend(schema_issues)

        # If schema has blocking errors, stop (domain validators need
        # schema-valid structure)
        schema_errors = [i for i in schema_issues if i.severity == ValidationSeverity.ERROR]
        if schema_errors:
            return self._build_result(all_issues)

        # ----------------------------------------------------------
        # 2. Domain validators (from registry)
        # ----------------------------------------------------------
        domain_validators = get_domain_validators(expected_analysis_type)
        for vfn, payload_key in domain_validators:
            try:
                target = payload.get(payload_key) if payload_key else payload
                if target is not None or payload_key is None:
                    result = vfn(target)
                    all_issues.extend(_extract_issues(result))
            except Exception:  # noqa: BLE001
                pass  # Isolated validator failure does not crash the pipeline

        # ----------------------------------------------------------
        # 3. Trade State validator (internal consistency)
        # ----------------------------------------------------------
        # Run only when the payload has trade_state data or position data
        if "position" in payload or "position_assessment" in payload:
            try:
                ts_result = validate_trade_state(payload)
                all_issues.extend(_extract_issues(ts_result))
            except Exception:  # noqa: BLE001
                pass

        # ----------------------------------------------------------
        # 4. Canonical state consistency (TP-0308)
        # ----------------------------------------------------------
        if trade_state is not None:
            try:
                sc_result = validate_state_consistency(payload, trade_state)
                all_issues.extend(_extract_issues(sc_result))
            except Exception:  # noqa: BLE001
                pass

        # ----------------------------------------------------------
        # 5. Lifecycle checks (deferred — no lifecycle validator yet)
        # ----------------------------------------------------------
        # session_status_before_job is accepted but lifecycle validation
        # is not yet implemented.  This hook is reserved for future use.

        # ----------------------------------------------------------
        # 6. Narrative checks (deferred — no narrative validator yet)
        # ----------------------------------------------------------

        # ----------------------------------------------------------
        # 7. Context Summary validation (TP-0311)
        # ----------------------------------------------------------
        if context_summary is not None:
            try:
                cs_result = validate_context_summary(context_summary, trade_state or {})
                all_issues.extend(_extract_issues(cs_result))
            except Exception:  # noqa: BLE001
                pass

        return self._build_result(all_issues)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_schema_validation(
        self,
        payload: Mapping[str, object],
        analysis_type: str,
    ) -> list[ValidationIssue]:
        """Run JSON Schema validation for the given analysis type."""
        try:
            # Look up the schema name/version from the manifest
            at_reg = self._manifest.analysis_type_registry.get(analysis_type)
            if at_reg is None:
                return [
                    ValidationIssue(
                        code="REGISTRY_ERROR",
                        category=ValidationCategory.SCHEMA,
                        severity=ValidationSeverity.ERROR,
                        path="",
                        message=f"Unknown analysis type: {analysis_type}",
                    )
                ]
            schema_name = at_reg.schema_name
            schema_version = at_reg.schema_version
            result = self._schema_service.validate_by_name(payload, schema_name, schema_version)
            return list(result.issues)
        except SchemaRegistryError as exc:
            return [
                ValidationIssue(
                    code="REGISTRY_ERROR",
                    category=ValidationCategory.SCHEMA,
                    severity=ValidationSeverity.ERROR,
                    path="",
                    message=str(exc),
                )
            ]
        except Exception:  # noqa: BLE001
            return [
                ValidationIssue(
                    code="INTERNAL_ERROR",
                    category=ValidationCategory.SCHEMA,
                    severity=ValidationSeverity.ERROR,
                    path="",
                    message="Unexpected schema validation error",
                )
            ]

    @staticmethod
    def _build_result(issues: list[ValidationIssue]) -> UnifiedValidationResult:
        deduped = _deduplicate(issues)
        errors = tuple(i for i in deduped if i.severity == ValidationSeverity.ERROR)
        warnings = tuple(i for i in deduped if i.severity != ValidationSeverity.ERROR)
        return UnifiedValidationResult(
            valid=len(errors) == 0,
            issues=deduped,
            errors=errors,
            warnings=warnings,
        )
