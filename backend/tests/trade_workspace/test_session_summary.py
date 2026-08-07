from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.session_decision import SessionDecisionV2Decision
from app.trade_workspace.models.trade_session import TradeSessionV2Status
from app.trade_workspace.services.session_summary import (
    RECENT_ACTIVITY_LIMIT,
    SessionActivityType,
    SessionSummaryService,
)


def _valid_result(analysis_type: AnalysisRequestV2Type) -> dict[str, object]:
    fields = {
        AnalysisRequestV2Type.INITIAL_ANALYSIS: (
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
        AnalysisRequestV2Type.WAIT_UPDATE: (
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
        AnalysisRequestV2Type.POSITION_UPDATE: (
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
    }[analysis_type]
    return {field: {"safe": True} for field in fields}


def _request(
    *,
    session_id: uuid.UUID,
    analysis_type: AnalysisRequestV2Type,
    completed_at: datetime | None,
    status: AnalysisRequestV2Status = AnalysisRequestV2Status.COMPLETED,
    result: object | None = None,
    request_id: uuid.UUID | None = None,
):
    return SimpleNamespace(
        id=request_id or uuid.uuid4(),
        session_id=session_id,
        analysis_type=analysis_type,
        status=status,
        completed_at=completed_at,
        processed_response=_valid_result(analysis_type) if result is None else result,
    )


def _session(
    *,
    session_id: uuid.UUID,
    created_at: datetime,
    archived_at: datetime | None = None,
    status: TradeSessionV2Status = TradeSessionV2Status.DRAFT,
):
    return SimpleNamespace(
        id=session_id,
        created_at=created_at,
        archived_at=archived_at,
        status=status,
    )


def _decision(*, session_id: uuid.UUID, decision: SessionDecisionV2Decision, created_at: datetime):
    return SimpleNamespace(
        id=uuid.uuid4(), session_id=session_id, decision=decision, created_at=created_at
    )


def test_selects_the_latest_valid_completed_analysis_across_v2_types() -> None:
    session_id = uuid.uuid4()
    start = datetime(2026, 8, 5, tzinfo=timezone.utc)
    summary = SessionSummaryService().build(
        trade_session=_session(session_id=session_id, created_at=start),
        requests=(
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                completed_at=start + timedelta(minutes=1),
            ),
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                completed_at=start + timedelta(minutes=2),
            ),
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                completed_at=start + timedelta(minutes=3),
            ),
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                completed_at=start + timedelta(minutes=4),
                status=AnalysisRequestV2Status.FAILED,
            ),
            _request(
                session_id=uuid.uuid4(),
                analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                completed_at=start + timedelta(minutes=5),
            ),
        ),
        decisions=(),
        closure=None,
    )

    assert summary.latest_analysis is not None
    assert summary.latest_analysis.analysis_type is AnalysisRequestV2Type.POSITION_UPDATE
    assert summary.latest_analysis.completed_at == start + timedelta(minutes=3)
    assert summary.latest_analysis.has_result is True


def test_malformed_newest_completed_result_falls_back_to_older_valid_result() -> None:
    session_id = uuid.uuid4()
    start = datetime(2026, 8, 5, tzinfo=timezone.utc)
    summary = SessionSummaryService().build(
        trade_session=_session(session_id=session_id, created_at=start),
        requests=(
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                completed_at=start + timedelta(minutes=1),
            ),
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                completed_at=start + timedelta(minutes=2),
                result={},
            ),
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                completed_at=None,
            ),
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                completed_at=start + timedelta(minutes=3),
                status=AnalysisRequestV2Status.PROCESSING,
            ),
        ),
        decisions=(),
        closure=None,
    )

    assert summary.latest_analysis is not None
    assert summary.latest_analysis.analysis_type is AnalysisRequestV2Type.INITIAL_ANALYSIS


def test_recent_activity_is_v2_only_bounded_and_deterministic() -> None:
    session_id = uuid.uuid4()
    start = datetime(2026, 8, 5, tzinfo=timezone.utc)
    archived_at = start + timedelta(minutes=6)
    closure = SimpleNamespace(
        id=uuid.UUID(int=9), session_id=session_id, close_at=start + timedelta(minutes=5)
    )
    requests = (
        _request(
            session_id=session_id,
            analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
            completed_at=start + timedelta(minutes=1),
            request_id=uuid.UUID(int=1),
        ),
        _request(
            session_id=session_id,
            analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
            completed_at=start + timedelta(minutes=2),
            request_id=uuid.UUID(int=2),
        ),
        _request(
            session_id=session_id,
            analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
            completed_at=start + timedelta(minutes=3),
            request_id=uuid.UUID(int=3),
        ),
    )
    decisions = (
        _decision(
            session_id=session_id,
            decision=SessionDecisionV2Decision.BUY,
            created_at=start + timedelta(minutes=4),
        ),
    )
    service = SessionSummaryService()
    first = service.build(
        trade_session=_session(
            session_id=session_id,
            created_at=start,
            archived_at=archived_at,
            status=TradeSessionV2Status.CLOSED,
        ),
        requests=requests,
        decisions=decisions,
        closure=closure,
    )
    second = service.build(
        trade_session=_session(
            session_id=session_id,
            created_at=start,
            archived_at=archived_at,
            status=TradeSessionV2Status.CLOSED,
        ),
        requests=requests,
        decisions=decisions,
        closure=closure,
    )

    assert len(first.recent_activity) == RECENT_ACTIVITY_LIMIT
    assert [item.type for item in first.recent_activity] == [
        SessionActivityType.SESSION_ARCHIVED,
        SessionActivityType.SESSION_CLOSED,
        SessionActivityType.BUY_CONFIRMED,
    ]
    assert first.recent_activity == second.recent_activity
    assert first.recent_activity[2].decision is SessionDecisionV2Decision.BUY
    assert first.recent_activity[0].payload() == {
        "type": SessionActivityType.SESSION_ARCHIVED,
        "occurred_at": archived_at,
        "analysis_type": None,
        "decision": None,
    }


def test_equal_completion_timestamps_use_stable_request_identifier_ordering() -> None:
    session_id = uuid.uuid4()
    completed_at = datetime(2026, 8, 5, tzinfo=timezone.utc)
    summary = SessionSummaryService().build(
        trade_session=_session(session_id=session_id, created_at=completed_at),
        requests=(
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                completed_at=completed_at,
                request_id=uuid.UUID(int=1),
            ),
            _request(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                completed_at=completed_at,
                request_id=uuid.UUID(int=2),
            ),
        ),
        decisions=(),
        closure=None,
    )

    assert summary.latest_analysis is not None
    assert summary.latest_analysis.analysis_type is AnalysisRequestV2Type.WAIT_UPDATE


def test_activity_uses_only_the_closed_v2_vocabulary() -> None:
    session_id = uuid.uuid4()
    created_at = datetime(2026, 8, 5, tzinfo=timezone.utc)
    analysis_cases = (
        (
            AnalysisRequestV2Type.INITIAL_ANALYSIS,
            SessionActivityType.INITIAL_ANALYSIS_COMPLETED,
        ),
        (AnalysisRequestV2Type.WAIT_UPDATE, SessionActivityType.WAIT_UPDATE_COMPLETED),
        (
            AnalysisRequestV2Type.POSITION_UPDATE,
            SessionActivityType.POSITION_UPDATE_COMPLETED,
        ),
    )
    decision_cases = (
        (SessionDecisionV2Decision.BUY, SessionActivityType.BUY_CONFIRMED),
        (SessionDecisionV2Decision.WAIT, SessionActivityType.WAIT_CONFIRMED),
        (SessionDecisionV2Decision.SKIP, SessionActivityType.SKIP_CONFIRMED),
    )

    for analysis_type, activity_type in analysis_cases:
        summary = SessionSummaryService().build(
            trade_session=_session(session_id=session_id, created_at=created_at),
            requests=(
                _request(
                    session_id=session_id,
                    analysis_type=analysis_type,
                    completed_at=created_at + timedelta(minutes=1),
                ),
            ),
            decisions=(),
            closure=None,
        )
        assert summary.recent_activity[0].type is activity_type

    for decision, activity_type in decision_cases:
        summary = SessionSummaryService().build(
            trade_session=_session(session_id=session_id, created_at=created_at),
            requests=(),
            decisions=(
                _decision(
                    session_id=session_id,
                    decision=decision,
                    created_at=created_at + timedelta(minutes=1),
                ),
            ),
            closure=None,
        )
        assert summary.recent_activity[0].type is activity_type


def test_non_terminal_archival_marker_does_not_create_archive_activity() -> None:
    session_id = uuid.uuid4()
    created_at = datetime(2026, 8, 5, tzinfo=timezone.utc)

    summary = SessionSummaryService().build(
        trade_session=_session(
            session_id=session_id,
            created_at=created_at,
            archived_at=created_at + timedelta(minutes=1),
            status=TradeSessionV2Status.WAITING,
        ),
        requests=(),
        decisions=(),
        closure=None,
    )

    assert [item.type for item in summary.recent_activity] == [
        SessionActivityType.SESSION_CREATED
    ]
