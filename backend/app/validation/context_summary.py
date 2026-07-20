"""Context Summary Validator (TP-0311).

Validates a Context Summary against canonical Trade State: entry, quantity,
pending proposals, cutoff timestamp, and staleness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Mapping

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

DOMAIN = ValidationCategory("DOMAIN")

CONTEXT_ENTRY_MISMATCH = "CONTEXT_ENTRY_MISMATCH"
CONTEXT_ORIGINAL_QUANTITY_MISMATCH = "CONTEXT_ORIGINAL_QUANTITY_MISMATCH"
CONTEXT_REMAINING_QUANTITY_MISMATCH = "CONTEXT_REMAINING_QUANTITY_MISMATCH"
CONTEXT_PENDING_PROPOSAL_MISSING = "CONTEXT_PENDING_PROPOSAL_MISSING"
CONTEXT_PENDING_PROPOSAL_CHANGED = "CONTEXT_PENDING_PROPOSAL_CHANGED"
CONTEXT_PENDING_PROPOSAL_ACTIVATED = "CONTEXT_PENDING_PROPOSAL_ACTIVATED"
CONTEXT_CUTOFF_INVALID = "CONTEXT_CUTOFF_INVALID"
CONTEXT_STALE = "CONTEXT_STALE"
CONTEXT_NUMERIC_INPUT_INVALID = "CONTEXT_NUMERIC_INPUT_INVALID"


@dataclass(frozen=True, slots=True)
class ContextSummaryValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)


def _make_issue(
    code: str, path: str, message: str, expected: str | None = None, actual: str | None = None
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        category=DOMAIN,
        severity=ValidationSeverity.ERROR,
        path=path,
        message=message,
        expected=expected,
        actual=actual,
    )


def _sort_key(issue: ValidationIssue) -> tuple[str, str, str, str]:
    return (issue.path, issue.code, issue.category.value, issue.message)


def _d(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, float):
        value = str(value)
    return to_decimal(value)  # type: ignore[arg-type]


def _active_levels_price(levels: dict[str, object] | None, field: str) -> Decimal | None:
    """Extract a price value from an active_levels sub-object like ``{"price": 2840}``."""
    if levels is None:
        return None
    item = levels.get(field)
    if isinstance(item, dict):
        p = item.get("price")
        if p is not None:
            try:
                return _d(p)
            except InvalidDecimalError:
                pass
    return None


def validate_context_summary(
    context_summary: Mapping[str, object],
    canonical_state: Mapping[str, object],
    *,
    required_cutoff_timestamp: datetime | str | None = None,
) -> ContextSummaryValidationResult:
    """Validate a Context Summary against canonical Trade State.

    Parameters
    ----------
    context_summary:
        The Context Summary payload (already schema-validated).  Contains
        ``current_position``, ``active_levels``, ``source_cutoff_timestamp``.
    canonical_state:
        The authoritative canonical Trade State payload.  Contains
        ``session_id``, ``ticker``, ``position.entry_price``,
        ``position.original_quantity``, ``position.remaining_quantity``.
    required_cutoff_timestamp:
        The minimum required cutoff timestamp for the next analysis.
        If the Context Summary's cutoff is older, it is stale.
    """
    issues: list[ValidationIssue] = []

    # ------------------------------------------------------------------
    # 1. Canonical entry
    # ------------------------------------------------------------------
    ctx_pos = context_summary.get("current_position")
    ctx_position = ctx_pos if isinstance(ctx_pos, dict) else {}

    canon_pos_raw = canonical_state.get("position")
    canon_position = canon_pos_raw if isinstance(canon_pos_raw, dict) else {}

    for field_name, ctx_key, canon_key, issue_code in (
        ("entry_price", "entry_price", "entry_price", CONTEXT_ENTRY_MISMATCH),
        (
            "original_quantity",
            "original_quantity",
            "original_quantity",
            CONTEXT_ORIGINAL_QUANTITY_MISMATCH,
        ),
        (
            "remaining_quantity",
            "remaining_quantity",
            "remaining_quantity",
            CONTEXT_REMAINING_QUANTITY_MISMATCH,
        ),
    ):
        ctx_val = ctx_position.get(ctx_key)
        canon_val = canon_position.get(canon_key)

        if ctx_val is not None:
            try:
                d_ctx = _d(ctx_val)
            except InvalidDecimalError:
                issues.append(
                    _make_issue(
                        CONTEXT_NUMERIC_INPUT_INVALID,
                        f"/current_position/{ctx_key}",
                        f"Invalid numeric input for {ctx_key}: "
                        f"type={type(ctx_val).__name__}, value={ctx_val!r}",
                        expected="Decimal, int, or str",
                        actual=f"{type(ctx_val).__name__}: {ctx_val!r}",
                    )
                )
                continue

            if canon_val is not None:
                try:
                    d_canon = _d(canon_val)
                except InvalidDecimalError:
                    continue
                if d_ctx is not None and d_canon is not None and d_ctx != d_canon:
                    issues.append(
                        _make_issue(
                            issue_code,
                            f"/current_position/{ctx_key}",
                            f"Context {field_name} ({d_ctx}) != canonical ({d_canon})",
                            expected=str(d_canon),
                            actual=str(d_ctx),
                        )
                    )
            elif d_ctx is not None:
                # Context has value but canonical is None
                issues.append(
                    _make_issue(
                        issue_code,
                        f"/current_position/{ctx_key}",
                        f"Context {field_name} ({d_ctx}) is non-null but canonical is null",
                        expected="null",
                        actual=str(d_ctx),
                    )
                )

    # Short-circuit on numeric issues to avoid downstream problems
    if any(i.code == CONTEXT_NUMERIC_INPUT_INVALID for i in issues):
        return ContextSummaryValidationResult(
            valid=False, issues=tuple(sorted(issues, key=_sort_key))
        )

    # ------------------------------------------------------------------
    # 2. Pending proposals vs active levels
    # ------------------------------------------------------------------
    ctx_active_levels = context_summary.get("active_levels")
    active_levels = ctx_active_levels if isinstance(ctx_active_levels, dict) else {}

    # Canonical active stop/target from canonical_state.position
    canon_active_stop = canon_position.get("active_stop_loss")
    canon_active_target = canon_position.get("active_target")

    # Context's active_stop_loss and active_target
    ctx_active_stop_price = _active_levels_price(active_levels, "active_stop_loss")
    ctx_active_target_price = _active_levels_price(active_levels, "active_target")

    # Proposed stop/target from active_levels
    ctx_proposed_stop_price = _active_levels_price(active_levels, "proposed_stop_loss")
    ctx_proposed_target_price = _active_levels_price(active_levels, "proposed_target")

    # Proposals must not be incorrectly activated: if proposal equals active
    # and differs from canonical active, that's a problem.
    if canon_active_stop is not None:
        try:
            d_canon_stop = _d(canon_active_stop)
        except InvalidDecimalError:
            d_canon_stop = None
    else:
        d_canon_stop = None

    if canon_active_target is not None:
        try:
            d_canon_target = _d(canon_active_target)
        except InvalidDecimalError:
            d_canon_target = None
    else:
        d_canon_target = None

    # If context proposes a change that has not yet been confirmed, the
    # active value in context should still match the canonical active value.
    if (
        ctx_active_stop_price is not None
        and d_canon_stop is not None
        and ctx_active_stop_price != d_canon_stop
    ):
        # Check if the context's active stop matches a proposal (incorrectly activated)
        if (
            ctx_proposed_stop_price is not None
            and ctx_active_stop_price == ctx_proposed_stop_price
        ):
            issues.append(
                _make_issue(
                    CONTEXT_PENDING_PROPOSAL_ACTIVATED,
                    "/active_levels/active_stop_loss",
                    f"Proposed stop ({ctx_proposed_stop_price}) is presented as active "
                    f"but canonical active stop is ({d_canon_stop})",
                    expected=str(d_canon_stop),
                    actual=str(ctx_active_stop_price),
                )
            )

    if (
        ctx_active_target_price is not None
        and d_canon_target is not None
        and ctx_active_target_price != d_canon_target
    ):
        if (
            ctx_proposed_target_price is not None
            and ctx_active_target_price == ctx_proposed_target_price
        ):
            issues.append(
                _make_issue(
                    CONTEXT_PENDING_PROPOSAL_ACTIVATED,
                    "/active_levels/active_target",
                    f"Proposed target ({ctx_proposed_target_price}) is presented as active "
                    f"but canonical active target is ({d_canon_target})",
                    expected=str(d_canon_target),
                    actual=str(ctx_active_target_price),
                )
            )

    # ------------------------------------------------------------------
    # 3. Cutoff timestamp
    # ------------------------------------------------------------------
    cutoff_str = context_summary.get("source_cutoff_timestamp")
    if cutoff_str is not None and isinstance(cutoff_str, str):
        try:
            cutoff_dt = datetime.fromisoformat(cutoff_str)
        except (ValueError, TypeError):
            issues.append(
                _make_issue(
                    CONTEXT_CUTOFF_INVALID,
                    "/source_cutoff_timestamp",
                    f"Invalid cutoff timestamp: {cutoff_str!r}",
                )
            )
            cutoff_dt = None
    else:
        cutoff_dt = None

    # 4. Staleness check
    if cutoff_dt is not None and required_cutoff_timestamp is not None:
        if isinstance(required_cutoff_timestamp, str):
            try:
                req_dt = datetime.fromisoformat(required_cutoff_timestamp)
            except (ValueError, TypeError):
                req_dt = None
        else:
            req_dt = required_cutoff_timestamp

        if req_dt is not None and cutoff_dt < req_dt:
            issues.append(
                _make_issue(
                    CONTEXT_STALE,
                    "/source_cutoff_timestamp",
                    f"Context cutoff ({cutoff_str}) is older than required ({req_dt.isoformat()})",
                    expected=f">= {req_dt.isoformat()}",
                    actual=str(cutoff_str),
                )
            )

    issues.sort(key=_sort_key)
    return ContextSummaryValidationResult(
        valid=len(issues) == 0,
        issues=tuple(issues),
    )
