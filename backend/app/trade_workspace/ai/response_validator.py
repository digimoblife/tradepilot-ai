from __future__ import annotations

import enum
import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from numbers import Real
from typing import Any

from app.trade_workspace.models.analysis_request import AnalysisRequestV2Type


class ResponseValidationError(Exception):
    """Base error for compact rebuild response validation."""


class UnsupportedResponseAnalysisTypeError(ResponseValidationError):
    pass


@dataclass(frozen=True, slots=True)
class ResponseValidationResult:
    is_valid: bool
    warnings: tuple[str, ...] = ()


_CRITICAL_SECTIONS: dict[str, tuple[str, ...]] = {
    "INITIAL_ANALYSIS": (
        "summary",
        "orderbook_analysis",
        "three_month_chart_analysis",
        "six_month_chart_analysis",
        "support",
        "resistance",
        "entry_area",
        "stop_recommendation",
        "target_recommendation",
        "probabilities",
        "risks",
        "trading_plan",
        "conclusion",
    ),
    "WAIT_UPDATE": (
        "update_summary",
        "current_price",
        "orderbook_assessment",
        "change_from_previous_analysis",
        "current_entry_condition",
        "upside_probability",
        "downside_probability",
        "key_risks",
        "recommended_action",
        "next_plan",
        "conclusion",
    ),
    "POSITION_UPDATE": (
        "update_summary",
        "current_price",
        "position_condition",
        "orderbook_assessment",
        "change_from_previous_analysis",
        "target_realism",
        "downside_risk",
        "target_probability",
        "trading_plan",
        "monitoring_points",
        "warnings",
        "conclusion",
    ),
}


class RebuildResponseValidator:
    """Check only dashboard-critical content for the three rebuild responses."""

    def validate(
        self,
        analysis_type: AnalysisRequestV2Type | str,
        processed_response: object,
    ) -> ResponseValidationResult:
        type_value = _resolve_analysis_type(analysis_type)
        if not isinstance(processed_response, Mapping) or not processed_response:
            return ResponseValidationResult(is_valid=False, warnings=("response_unusable",))

        missing = tuple(
            section
            for section in _CRITICAL_SECTIONS[type_value]
            if section not in processed_response
            or not _is_usable(processed_response[section])
        )
        if missing:
            return ResponseValidationResult(
                is_valid=False,
                warnings=tuple(f"critical_section_unusable:{section}" for section in missing),
            )
        return ResponseValidationResult(is_valid=True)


def critical_validation_error(
    analysis_type: AnalysisRequestV2Type | str,
    result: ResponseValidationResult,
) -> ResponseValidationError:
    type_value = _resolve_analysis_type(analysis_type)
    sections = tuple(
        warning.removeprefix("critical_section_unusable:")
        for warning in result.warnings
        if warning.startswith("critical_section_unusable:")
    )
    if not sections:
        sections = ("response",)
    return ResponseValidationError(
        f"{type_value}: critical response sections unusable: {', '.join(sections)}"
    )


def _resolve_analysis_type(analysis_type: AnalysisRequestV2Type | str) -> str:
    try:
        value = analysis_type.value if isinstance(analysis_type, enum.Enum) else analysis_type
        resolved = AnalysisRequestV2Type(value)
    except (TypeError, ValueError) as exc:
        raise UnsupportedResponseAnalysisTypeError(
            "Unsupported rebuild response analysis type"
        ) from exc
    return resolved.value


def _is_usable(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return True
    if isinstance(value, Decimal):
        return value.is_finite()
    if isinstance(value, Real):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, (list, tuple, set)):
        return bool(value)
    return False
