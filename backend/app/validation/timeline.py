"""Timeline ordering validation for trade lifecycle events."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence

from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

DOMAIN = ValidationCategory("DOMAIN")
CLOSING_TIMELINE_INVALID = "CLOSING_TIMELINE_INVALID"


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


def validate_timeline(
    entry_timestamp: str | None,
    final_exit_timestamp: str | None,
    *,
    timeline_events: Sequence[Mapping[str, object]] | None = None,
    partial_exit_timestamps: Sequence[str] | None = None,
    closed_at_timestamp: str | None = None,
) -> tuple[ValidationIssue, ...]:
    """Validate chronological ordering of trade lifecycle events.

    Enforces:
      - entry <= partial exits <= final exit <= closed_at
    """
    issues: list[ValidationIssue] = []

    def _parse(ts_str: str | None) -> datetime | None:
        if ts_str is None:
            return None
        try:
            return datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            return None

    entry_dt = _parse(entry_timestamp)
    final_dt = _parse(final_exit_timestamp)
    closed_dt = _parse(closed_at_timestamp)

    # Collect all partial exit timestamps
    partial_dts: list[datetime] = []
    if partial_exit_timestamps:
        for ts in partial_exit_timestamps:
            dt = _parse(ts)
            if dt is not None:
                partial_dts.append(dt)
    if timeline_events:
        for ev in timeline_events:
            ts_val = ev.get("timestamp")
            if isinstance(ts_val, str):
                dt = _parse(ts_val)
                if dt is not None:
                    partial_dts.append(dt)

    partial_dts.sort()

    # entry <= partial exits
    if entry_dt is not None:
        for i, pdt in enumerate(partial_dts):
            if pdt < entry_dt:
                issues.append(
                    _make_issue(
                        CLOSING_TIMELINE_INVALID,
                        "/timeline/events",
                        f"Timeline event at {pdt.isoformat()} is before "
                        "entry at {entry_dt.isoformat()}",
                        expected=f">= {entry_dt.isoformat()}",
                        actual=pdt.isoformat(),
                    )
                )

    # entry <= final exit
    if entry_dt is not None and final_dt is not None and final_dt < entry_dt:
        issues.append(
            _make_issue(
                CLOSING_TIMELINE_INVALID,
                "/closing_confirmation/exit_timestamp",
                f"Final exit at {final_dt.isoformat()} is before entry at {entry_dt.isoformat()}",
                expected=f">= {entry_dt.isoformat()}",
                actual=final_dt.isoformat(),
            )
        )

    # partial exits <= final exit
    if final_dt is not None:
        for i, pdt in enumerate(partial_dts):
            if pdt > final_dt:
                issues.append(
                    _make_issue(
                        CLOSING_TIMELINE_INVALID,
                        "/timeline/events",
                        (
                            f"Timeline event at {pdt.isoformat()} is after "
                            "final exit at {final_dt.isoformat()}"
                        ),
                        expected=f"<= {final_dt.isoformat()}",
                        actual=pdt.isoformat(),
                    )
                )

    # final exit <= closed_at
    if final_dt is not None and closed_dt is not None and final_dt > closed_dt:
        issues.append(
            _make_issue(
                CLOSING_TIMELINE_INVALID,
                "/closing_confirmation/exit_timestamp",
                (
                    f"Final exit at {final_dt.isoformat()} is after "
                    "closed timestamp at {closed_dt.isoformat()}"
                ),
                expected=f"<= {closed_dt.isoformat()}",
                actual=final_dt.isoformat(),
            )
        )

    return tuple(sorted(issues, key=_sort_key))
