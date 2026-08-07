from __future__ import annotations

import enum
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from app.trade_workspace.ai.response_validator import RebuildResponseValidator
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.session_decision import (
    SessionDecisionV2,
    SessionDecisionV2Decision,
)
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

RECENT_ACTIVITY_LIMIT = 3


class SessionActivityType(str, enum.Enum):
    SESSION_CREATED = "SESSION_CREATED"
    INITIAL_ANALYSIS_COMPLETED = "INITIAL_ANALYSIS_COMPLETED"
    BUY_CONFIRMED = "BUY_CONFIRMED"
    WAIT_CONFIRMED = "WAIT_CONFIRMED"
    SKIP_CONFIRMED = "SKIP_CONFIRMED"
    WAIT_UPDATE_COMPLETED = "WAIT_UPDATE_COMPLETED"
    POSITION_UPDATE_COMPLETED = "POSITION_UPDATE_COMPLETED"
    SESSION_CLOSED = "SESSION_CLOSED"
    SESSION_ARCHIVED = "SESSION_ARCHIVED"


@dataclass(frozen=True, slots=True)
class LatestAnalysisSummary:
    analysis_type: AnalysisRequestV2Type
    completed_at: datetime
    has_result: bool = True

    def payload(self) -> dict[str, object]:
        return {
            "analysis_type": self.analysis_type,
            "completed_at": self.completed_at,
            "has_result": self.has_result,
        }


@dataclass(frozen=True, slots=True)
class SessionRecentActivityItem:
    type: SessionActivityType
    occurred_at: datetime
    analysis_type: AnalysisRequestV2Type | None = None
    decision: SessionDecisionV2Decision | None = None

    def payload(self) -> dict[str, object]:
        return {
            "type": self.type,
            "occurred_at": self.occurred_at,
            "analysis_type": self.analysis_type,
            "decision": self.decision,
        }


@dataclass(frozen=True, slots=True)
class SessionSummaryReadModel:
    latest_analysis: LatestAnalysisSummary | None
    recent_activity: tuple[SessionRecentActivityItem, ...]


@dataclass(frozen=True, slots=True)
class _ActivityCandidate:
    item: SessionRecentActivityItem
    priority: int
    source_id: str


_ANALYSIS_ACTIVITY_TYPES = {
    AnalysisRequestV2Type.INITIAL_ANALYSIS: SessionActivityType.INITIAL_ANALYSIS_COMPLETED,
    AnalysisRequestV2Type.WAIT_UPDATE: SessionActivityType.WAIT_UPDATE_COMPLETED,
    AnalysisRequestV2Type.POSITION_UPDATE: SessionActivityType.POSITION_UPDATE_COMPLETED,
}

_DECISION_ACTIVITY_TYPES = {
    SessionDecisionV2Decision.BUY: SessionActivityType.BUY_CONFIRMED,
    SessionDecisionV2Decision.WAIT: SessionActivityType.WAIT_CONFIRMED,
    SessionDecisionV2Decision.SKIP: SessionActivityType.SKIP_CONFIRMED,
}


class SessionSummaryService:
    """Build the bounded V2 summary read contract from aggregate rows."""

    def __init__(self, *, validator: RebuildResponseValidator | None = None) -> None:
        self._validator = validator or RebuildResponseValidator()

    def build(
        self,
        *,
        trade_session: TradeSessionV2,
        requests: Iterable[AnalysisRequestV2],
        decisions: Iterable[SessionDecisionV2],
        closure: TradeClosureV2 | None,
    ) -> SessionSummaryReadModel:
        completed = self._valid_completed_requests(
            session_id=trade_session.id,
            requests=requests,
        )
        return SessionSummaryReadModel(
            latest_analysis=self._latest_analysis(completed),
            recent_activity=self._recent_activity(
                trade_session=trade_session,
                completed_requests=completed,
                decisions=decisions,
                closure=closure,
            ),
        )

    def _valid_completed_requests(
        self,
        *,
        session_id: object,
        requests: Iterable[AnalysisRequestV2],
    ) -> tuple[AnalysisRequestV2, ...]:
        valid: list[AnalysisRequestV2] = []
        for request in requests:
            if request.session_id != session_id:
                continue
            if request.status is not AnalysisRequestV2Status.COMPLETED:
                continue
            if request.analysis_type not in _ANALYSIS_ACTIVITY_TYPES:
                continue
            if not isinstance(request.completed_at, datetime):
                continue
            try:
                result = self._validator.validate(
                    request.analysis_type,
                    request.processed_response,
                )
            except Exception:
                continue
            if result.is_valid:
                valid.append(request)
        return tuple(valid)

    @staticmethod
    def _latest_analysis(
        requests: tuple[AnalysisRequestV2, ...],
    ) -> LatestAnalysisSummary | None:
        if not requests:
            return None
        latest = max(requests, key=lambda item: (item.completed_at, str(item.id)))
        assert isinstance(latest.completed_at, datetime)
        return LatestAnalysisSummary(
            analysis_type=latest.analysis_type,
            completed_at=latest.completed_at,
        )

    def _recent_activity(
        self,
        *,
        trade_session: TradeSessionV2,
        completed_requests: tuple[AnalysisRequestV2, ...],
        decisions: Iterable[SessionDecisionV2],
        closure: TradeClosureV2 | None,
    ) -> tuple[SessionRecentActivityItem, ...]:
        candidates = [
            _ActivityCandidate(
                item=SessionRecentActivityItem(
                    type=SessionActivityType.SESSION_CREATED,
                    occurred_at=trade_session.created_at,
                ),
                priority=10,
                source_id=str(trade_session.id),
            )
        ]
        for request in completed_requests:
            assert isinstance(request.completed_at, datetime)
            candidates.append(
                _ActivityCandidate(
                    item=SessionRecentActivityItem(
                        type=_ANALYSIS_ACTIVITY_TYPES[request.analysis_type],
                        occurred_at=request.completed_at,
                        analysis_type=request.analysis_type,
                    ),
                    priority=40,
                    source_id=str(request.id),
                )
            )
        for decision in decisions:
            if decision.session_id != trade_session.id:
                continue
            activity_type = _DECISION_ACTIVITY_TYPES.get(decision.decision)
            if activity_type is None or not isinstance(decision.created_at, datetime):
                continue
            candidates.append(
                _ActivityCandidate(
                    item=SessionRecentActivityItem(
                        type=activity_type,
                        occurred_at=decision.created_at,
                        decision=decision.decision,
                    ),
                    priority=50,
                    source_id=str(decision.id),
                )
            )
        if (
            closure is not None
            and closure.session_id == trade_session.id
            and isinstance(closure.close_at, datetime)
        ):
            candidates.append(
                _ActivityCandidate(
                    item=SessionRecentActivityItem(
                        type=SessionActivityType.SESSION_CLOSED,
                        occurred_at=closure.close_at,
                    ),
                    priority=70,
                    source_id=str(closure.id),
                )
            )
        if (
            trade_session.archived_at is not None
            and trade_session.status
            in {TradeSessionV2Status.CLOSED, TradeSessionV2Status.CLOSED_SKIPPED}
        ):
            candidates.append(
                _ActivityCandidate(
                    item=SessionRecentActivityItem(
                        type=SessionActivityType.SESSION_ARCHIVED,
                        occurred_at=trade_session.archived_at,
                    ),
                    priority=80,
                    source_id=str(trade_session.id),
                )
            )
        ordered = sorted(
            candidates,
            key=lambda candidate: (
                candidate.item.occurred_at,
                candidate.priority,
                candidate.source_id,
            ),
            reverse=True,
        )
        return tuple(candidate.item for candidate in ordered[:RECENT_ACTIVITY_LIMIT])
