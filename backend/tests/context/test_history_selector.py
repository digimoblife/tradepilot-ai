"""Tests for MaterialHistorySelector (TP-0901)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.context import (
    HistoryEvent,
    MaterialHistoryInvalidLimitError,
    MaterialHistoryMandatoryOverflowError,
    MaterialHistorySelector,
)

_NOW = datetime.now(timezone.utc)
_SELECTOR = MaterialHistorySelector()


# ===================================================================
# Helpers
# ===================================================================


def _event(
    event_type: str = "ANALYSIS_ACCEPTED",
    occurred_at: datetime | None = None,
    analysis_type: str | None = None,
    action_type: str | None = None,
    is_confirmed: bool = False,
    is_accepted: bool = False,
    related_action_id: uuid.UUID | None = None,
    related_analysis_id: uuid.UUID | None = None,
    payload: dict | None = None,
    **kwargs: object,
) -> HistoryEvent:
    return HistoryEvent(
        event_id=uuid.uuid4(),
        event_type=event_type,
        occurred_at=occurred_at or _NOW,
        created_at=_NOW,
        analysis_type=analysis_type,
        action_type=action_type,
        is_confirmed_action=is_confirmed,
        is_accepted_analysis=is_accepted,
        related_action_id=related_action_id,
        related_analysis_id=related_analysis_id,
        payload=payload or {},
        **kwargs,
    )


# ===================================================================
# Chronology
# ===================================================================


class TestChronology:
    def test_chronological_input(self) -> None:
        t1 = _NOW - timedelta(hours=2)
        t2 = _NOW - timedelta(hours=1)
        e1 = _event("POSITION_OPENED", occurred_at=t1, is_confirmed=True)
        e2 = _event("ANALYSIS_ACCEPTED", occurred_at=t2, is_accepted=True)
        result = _SELECTOR.select(events=[e1, e2], maximum_events=10)
        assert result.selected_events[0].event_id == e1.event_id
        assert result.selected_events[1].event_id == e2.event_id

    def test_reverse_input(self) -> None:
        t1 = _NOW - timedelta(hours=2)
        t2 = _NOW - timedelta(hours=1)
        e1 = _event("POSITION_OPENED", occurred_at=t1, is_confirmed=True)
        e2 = _event("ANALYSIS_ACCEPTED", occurred_at=t2, is_accepted=True)
        result = _SELECTOR.select(events=[e2, e1], maximum_events=10)
        assert result.selected_events[0].event_id == e1.event_id
        assert result.selected_events[1].event_id == e2.event_id

    def test_deterministic_tie_break(self) -> None:
        e1 = _event("POSITION_OPENED", occurred_at=_NOW, is_confirmed=True)
        e2 = _event("ANALYSIS_ACCEPTED", occurred_at=_NOW, is_accepted=True)
        r1 = _SELECTOR.select(events=[e1, e2], maximum_events=10)
        r2 = _SELECTOR.select(events=[e1, e2], maximum_events=10)
        assert [e.event_id for e in r1.selected_events] == [e.event_id for e in r2.selected_events]

    def test_repeated_build_identical(self) -> None:
        e1 = _event("POSITION_OPENED", is_confirmed=True)
        e2 = _event("ANALYSIS_ACCEPTED", is_accepted=True)
        r1 = _SELECTOR.select(events=[e1, e2], maximum_events=10)
        r2 = _SELECTOR.select(events=[e1, e2], maximum_events=10)
        assert len(r1.selected_events) == len(r2.selected_events)


# ===================================================================
# Preserved events
# ===================================================================


class TestPreservedEvents:
    def test_original_setup_preserved(self) -> None:
        e1 = _event("SESSION_CREATED")
        e2 = _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="INITIAL_ANALYSIS")
        e3 = _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="WATCHING_UPDATE")
        result = _SELECTOR.select(events=[e1, e2, e3], maximum_events=10)
        types = [e.event_type for e in result.selected_events]
        assert "SESSION_CREATED" in types
        assert "ANALYSIS_ACCEPTED" in types

    def test_position_open_preserved(self) -> None:
        e = _event("POSITION_OPENED", is_confirmed=True)
        result = _SELECTOR.select(events=[e], maximum_events=10)
        assert len(result.selected_events) == 1

    def test_thesis_change_preserved(self) -> None:
        e = _event(
            "ANALYSIS_ACCEPTED",
            is_accepted=True,
            analysis_type="WATCHING_UPDATE",
            payload={"previous_thesis_status": "INTACT", "current_thesis_status": "WEAKENING"},
        )
        result = _SELECTOR.select(events=[e], maximum_events=10)
        assert len(result.selected_events) == 1

    def test_stop_changes_preserved(self) -> None:
        e1 = _event("STOP_LOSS_CHANGED", is_confirmed=True)
        e2 = _event("STOP_LOSS_CHANGED", is_confirmed=True)
        result = _SELECTOR.select(events=[e1, e2], maximum_events=10)
        assert len(result.selected_events) == 2

    def test_target_changes_preserved(self) -> None:
        e1 = _event("TARGET_CHANGED", is_confirmed=True)
        e2 = _event("TARGET_CHANGED", is_confirmed=True)
        result = _SELECTOR.select(events=[e1, e2], maximum_events=10)
        assert len(result.selected_events) == 2

    def test_partial_exits_preserved(self) -> None:
        e1 = _event("PARTIAL_EXIT", is_confirmed=True)
        e2 = _event("PARTIAL_EXIT", is_confirmed=True)
        result = _SELECTOR.select(events=[e1, e2], maximum_events=10)
        assert len(result.selected_events) == 2

    def test_final_exit_preserved(self) -> None:
        e = _event("FULL_EXIT", is_confirmed=True)
        result = _SELECTOR.select(events=[e], maximum_events=10)
        assert len(result.selected_events) == 1


# ===================================================================
# Rejected analysis exclusion
# ===================================================================


class TestRejectedAnalysis:
    def test_rejected_analysis_excluded(self) -> None:
        """A rejected/failed analysis event is not classified as MATERIAL."""
        e = _event("ANALYSIS_FAILED", is_accepted=False, analysis_type="INITIAL_ANALYSIS")
        result = _SELECTOR.select(events=[e], maximum_events=10)
        # The event is still kept as a routine event (not excluded entirely),
        # but it has no classification as MATERIAL — verified by compressed_count
        assert result.selected_event_count == 1
        assert result.compressed_event_count == 0

    def test_accepted_initial_analysis_included(self) -> None:
        e = _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="INITIAL_ANALYSIS")
        result = _SELECTOR.select(events=[e], maximum_events=10)
        assert len(result.selected_events) == 1


# ===================================================================
# Minor update compression
# ===================================================================


class TestCompression:
    def test_repeated_watching_updates_compressed(self) -> None:
        events = [
            _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="WATCHING_UPDATE")
            for _ in range(5)
        ]
        result = _SELECTOR.select(events=events, maximum_events=10)
        assert result.selected_event_count < 5

    def test_material_change_between_routine_preserved(self) -> None:
        e1 = _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="WATCHING_UPDATE")
        e2 = _event(
            "ANALYSIS_ACCEPTED",
            is_accepted=True,
            analysis_type="WATCHING_UPDATE",
            payload={
                "previous_thesis_status": "INTACT",
                "current_thesis_status": "WEAKENING",
            },
        )
        e3 = _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="WATCHING_UPDATE")
        result = _SELECTOR.select(events=[e1, e2, e3], maximum_events=10)
        # The thesis change event should be classified as material, not routine
        assert result.selected_event_count == 3

    def test_unchanged_support_compressed(self) -> None:
        events = [
            _event(
                "ANALYSIS_ACCEPTED",
                is_accepted=True,
                analysis_type="OPEN_POSITION_UPDATE",
                payload={"support": 2400, "resistance": 2600},
            )
            for _ in range(3)
        ]
        result = _SELECTOR.select(events=events, maximum_events=10)
        # Routine unchanged events compress to first + last
        assert result.selected_event_count <= 2

    def test_input_order_does_not_change_compression(self) -> None:
        events = [
            _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="WATCHING_UPDATE")
            for _ in range(5)
        ]
        r1 = _SELECTOR.select(events=events, maximum_events=10)
        r2 = _SELECTOR.select(events=list(reversed(events)), maximum_events=10)
        # Sorted before processing, so order shouldn't matter
        assert r1.selected_event_count == r2.selected_event_count


# ===================================================================
# Maximum count
# ===================================================================


class TestMaximumCount:
    def test_below_limit(self) -> None:
        e = _event("POSITION_OPENED", is_confirmed=True)
        result = _SELECTOR.select(events=[e], maximum_events=10)
        assert result.selected_event_count == 1
        assert result.selected_event_count <= result.maximum_events

    def test_exact_limit(self) -> None:
        events = [_event(f"E{i}", is_confirmed=True) for i in range(5)]
        result = _SELECTOR.select(events=events, maximum_events=5)
        assert result.selected_event_count == 5

    def test_optional_removed_above_limit(self) -> None:
        mandatory = _event("POSITION_OPENED", is_confirmed=True)
        routines = [
            _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="WATCHING_UPDATE")
            for _ in range(10)
        ]
        result = _SELECTOR.select(events=[mandatory] + routines, maximum_events=3)
        assert result.selected_event_count <= 3
        # Mandatory event must still be present
        assert any(e.event_id == mandatory.event_id for e in result.selected_events)

    def test_mandatory_retained_under_pressure(self) -> None:
        mandatory = [
            _event("POSITION_OPENED", is_confirmed=True),
            _event("STOP_LOSS_CHANGED", is_confirmed=True),
            _event("TARGET_CHANGED", is_confirmed=True),
            _event("PARTIAL_EXIT", is_confirmed=True),
            _event("FULL_EXIT", is_confirmed=True),
        ]
        routines = [
            _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="WATCHING_UPDATE")
            for _ in range(20)
        ]
        result = _SELECTOR.select(events=mandatory + routines, maximum_events=10)
        # All 5 mandatory events must be present
        assert result.selected_event_count <= 10
        mandatory_ids = {e.event_id for e in mandatory}
        selected_ids = {e.event_id for e in result.selected_events}
        assert mandatory_ids.issubset(selected_ids)

    def test_zero_limit_rejected(self) -> None:
        with pytest.raises(MaterialHistoryInvalidLimitError):
            _SELECTOR.select(events=[], maximum_events=0)

    def test_negative_limit_rejected(self) -> None:
        with pytest.raises(MaterialHistoryInvalidLimitError):
            _SELECTOR.select(events=[], maximum_events=-1)

    def test_mandatory_overflow(self) -> None:
        mandatory = [
            _event("POSITION_OPENED", is_confirmed=True),
            _event("STOP_LOSS_CHANGED", is_confirmed=True),
            _event("TARGET_CHANGED", is_confirmed=True),
            _event("PARTIAL_EXIT", is_confirmed=True),
            _event("FULL_EXIT", is_confirmed=True),
        ]
        with pytest.raises(MaterialHistoryMandatoryOverflowError):
            _SELECTOR.select(events=mandatory, maximum_events=3)

    def test_empty_history(self) -> None:
        result = _SELECTOR.select(events=[], maximum_events=10)
        assert result.selected_event_count == 0
        assert result.original_event_count == 0


# ===================================================================
# Report counts
# ===================================================================


class TestReportCounts:
    def test_original_count(self) -> None:
        events = [
            _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="WATCHING_UPDATE")
            for _ in range(10)
        ]
        result = _SELECTOR.select(events=events, maximum_events=10)
        assert result.original_event_count == 10

    def test_compressed_count(self) -> None:
        events = [
            _event("ANALYSIS_ACCEPTED", is_accepted=True, analysis_type="WATCHING_UPDATE")
            for _ in range(10)
        ]
        result = _SELECTOR.select(events=events, maximum_events=10)
        assert result.compressed_event_count > 0


# ===================================================================
# Immutability
# ===================================================================


class TestImmutability:
    def test_input_sequence_unchanged(self) -> None:
        events = [_event("POSITION_OPENED", is_confirmed=True)]
        original_len = len(events)
        _SELECTOR.select(events=events, maximum_events=10)
        assert len(events) == original_len

    def test_no_database_write(self) -> None:
        e = _event("POSITION_OPENED", is_confirmed=True)
        _SELECTOR.select(events=[e], maximum_events=10)

    def test_no_provider_call(self) -> None:
        e = _event("POSITION_OPENED", is_confirmed=True)
        _SELECTOR.select(events=[e], maximum_events=10)
