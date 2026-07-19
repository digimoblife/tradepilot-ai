"""Material History Selector (TP-0901).

Selects important historical events for longitudinal Trade Session memory.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Sequence

# ---------------------------------------------------------------------------
# Event materiality classification
# ---------------------------------------------------------------------------


class _MaterialClass(IntEnum):
    MANDATORY_CONFIRMED = 0
    MANDATORY_LIFECYCLE = 1
    MATERIAL_ANALYSIS = 2
    ROUTINE = 3


# ---------------------------------------------------------------------------
# Input/Output models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HistoryEvent:
    """A single event in the session timeline."""

    event_id: uuid.UUID
    event_type: str
    occurred_at: datetime
    created_at: datetime | None = None
    related_action_id: uuid.UUID | None = None
    related_analysis_id: uuid.UUID | None = None
    analysis_type: str | None = None
    action_type: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    price: float | None = None
    quantity: float | None = None
    is_confirmed_action: bool = False
    is_accepted_analysis: bool = False


@dataclass(frozen=True, slots=True)
class MaterialHistorySelection:
    """Result of selecting material history events."""

    selected_events: tuple[HistoryEvent, ...]
    original_event_count: int
    selected_event_count: int
    compressed_event_count: int
    maximum_events: int


# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class MaterialHistoryError(Exception):
    code: str = "MATERIAL_HISTORY_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class MaterialHistoryInvalidLimitError(MaterialHistoryError):
    code: str = "MATERIAL_HISTORY_INVALID_LIMIT"


class MaterialHistoryMandatoryOverflowError(MaterialHistoryError):
    code: str = "MATERIAL_HISTORY_MANDATORY_OVERFLOW"


# ---------------------------------------------------------------------------
# Event types that represent confirmed user actions
# ---------------------------------------------------------------------------

_CONFIRMED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "POSITION_OPENED",
        "STOP_LOSS_CHANGED",
        "TARGET_CHANGED",
        "PARTIAL_EXIT",
        "FULL_EXIT",
    }
)

# Event types that are lifecycle events (always material)
_LIFECYCLE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "SESSION_CREATED",
        "EVIDENCE_UPLOADED",
        "ANALYSIS_REQUESTED",
        "SESSION_ARCHIVED",
    }
)

# Action types that represent confirmed user actions (to match related_action)
_CONFIRMED_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "POSITION_OPENED",
        "STOP_LOSS_CONFIRMED",
        "STOP_LOSS_CHANGED",
        "TARGET_CONFIRMED",
        "TARGET_CHANGED",
        "PARTIAL_EXIT",
        "FULL_EXIT",
        "SESSION_CANCELLED",
        "SESSION_ARCHIVED",
    }
)

# Analysis types considered material by default
_MATERIAL_ANALYSIS_TYPES: frozenset[str] = frozenset(
    {
        "INITIAL_ANALYSIS",
        "CLOSING_ANALYSIS",
    }
)


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------


class MaterialHistorySelector:
    """Deterministic, read-only selector of material session history."""

    def select(
        self,
        *,
        events: Sequence[HistoryEvent],
        maximum_events: int,
    ) -> MaterialHistorySelection:
        if maximum_events < 1:
            raise MaterialHistoryInvalidLimitError(
                message=f"maximum_events must be >= 1, got {maximum_events}",
            )

        if not events:
            return MaterialHistorySelection(
                selected_events=(),
                original_event_count=0,
                selected_event_count=0,
                compressed_event_count=0,
                maximum_events=maximum_events,
            )

        # 1. Sort chronologically
        sorted_events = sorted(
            events,
            key=lambda e: (
                e.occurred_at,
                e.created_at or e.occurred_at,
                e.event_id,
            ),
        )

        # 2. Classify
        mandatory: list[HistoryEvent] = []
        material: list[HistoryEvent] = []
        routine: list[HistoryEvent] = []

        for ev in sorted_events:
            cls = self._classify(ev)
            if cls == _MaterialClass.MANDATORY_CONFIRMED:
                mandatory.append(ev)
            elif cls == _MaterialClass.MANDATORY_LIFECYCLE:
                mandatory.append(ev)
            elif cls == _MaterialClass.MATERIAL_ANALYSIS:
                material.append(ev)
            else:
                routine.append(ev)

        # 3. Compress routine events
        compressed_routine = self._compress_routine(routine)

        # 4. Build combined list
        combined = mandatory + material + compressed_routine

        remaining = maximum_events
        if len(combined) <= remaining:
            return MaterialHistorySelection(
                selected_events=tuple(combined),
                original_event_count=len(events),
                selected_event_count=len(combined),
                compressed_event_count=len(routine) - len(compressed_routine),
                maximum_events=maximum_events,
            )

        # 5. Remove optional events in priority order
        if len(mandatory) > remaining:
            raise MaterialHistoryMandatoryOverflowError(
                message=(
                    f"Mandatory events ({len(mandatory)}) exceed maximum_events ({remaining})"
                ),
            )

        # Remove material analysis events first (from the end = oldest)
        keep = mandatory[:]
        remaining -= len(keep)

        # Add most recent material analyses
        for ev in reversed(material):
            if remaining <= 0:
                break
            keep.append(ev)
            remaining -= 1

        # Re-sort
        keep.sort(key=lambda e: (e.occurred_at, e.created_at or e.occurred_at, e.event_id))

        return MaterialHistorySelection(
            selected_events=tuple(keep),
            original_event_count=len(events),
            selected_event_count=len(keep),
            compressed_event_count=len(routine) + len(material) - (len(keep) - len(mandatory)),
            maximum_events=maximum_events,
        )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    @staticmethod
    def _classify(event: HistoryEvent) -> _MaterialClass:
        if event.is_confirmed_action:
            return _MaterialClass.MANDATORY_CONFIRMED
        if event.related_action_id is not None and event.action_type in _CONFIRMED_ACTION_TYPES:
            return _MaterialClass.MANDATORY_CONFIRMED
        if event.event_type in _CONFIRMED_EVENT_TYPES:
            return _MaterialClass.MANDATORY_CONFIRMED
        if event.event_type in _LIFECYCLE_EVENT_TYPES:
            return _MaterialClass.MANDATORY_LIFECYCLE
        if event.is_accepted_analysis:
            if event.analysis_type in _MATERIAL_ANALYSIS_TYPES:
                return _MaterialClass.MATERIAL_ANALYSIS
            if event.analysis_type == "INITIAL_ANALYSIS":
                return _MaterialClass.MATERIAL_ANALYSIS
            # Check for thesis changes in the payload
            payload = event.payload or {}
            if _has_thesis_change(payload):
                return _MaterialClass.MATERIAL_ANALYSIS
        return _MaterialClass.ROUTINE

    # ------------------------------------------------------------------
    # Compression
    # ------------------------------------------------------------------

    @staticmethod
    def _compress_routine(routine: list[HistoryEvent]) -> list[HistoryEvent]:
        if len(routine) <= 1:
            return routine

        result: list[HistoryEvent] = []
        previous = routine[0]
        result.append(previous)

        for current in routine[1:]:
            if _is_materially_different(previous, current):
                result.append(current)
                previous = current

        # Always keep the last routine event for continuity
        if result[-1] is not routine[-1]:
            result.append(routine[-1])

        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_thesis_change(payload: dict[str, Any]) -> bool:
    """Check if an analysis payload contains a thesis status change."""
    if not payload:
        return False
    prev = payload.get("previous_thesis_status")
    curr = payload.get("current_thesis_status")
    if prev is not None and curr is not None and prev != curr:
        return True
    return False


def _is_materially_different(prev: HistoryEvent, curr: HistoryEvent) -> bool:
    """Determine if two routine events are materially different."""
    # Different event types are material
    if prev.event_type != curr.event_type:
        return True

    if prev.analysis_type != curr.analysis_type:
        return True

    # Check payload for changes in key fields
    prev_payload = prev.payload or {}
    curr_payload = curr.payload or {}

    # Thesis status change
    if _has_thesis_change(curr_payload):
        return True

    # Support/resistance changes
    if _level_changed(prev_payload, curr_payload, "support"):
        return True
    if _level_changed(prev_payload, curr_payload, "resistance"):
        return True

    return False


def _level_changed(
    prev: dict[str, Any],
    curr: dict[str, Any],
    key: str,
) -> bool:
    """Check if support/resistance level changed between two events."""
    prev_val = prev.get(key) or prev.get(f"{key}_level")
    curr_val = curr.get(key) or curr.get(f"{key}_level")
    if prev_val is None and curr_val is None:
        return False
    if prev_val != curr_val:
        return True
    return False
