from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from typing import Iterable

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2
from app.trade_workspace.models.position import PositionV2
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.decision_availability import available_decision_actions
from app.trade_workspace.services.eligibility import (
    has_unassigned_initial_evidence,
    initial_evidence_set_is_complete,
    linked_initial_evidence_is_valid,
    open_position_session_is_eligible,
    request_is_active,
    request_is_retryable,
    single_open_position,
    wait_retry_evidence_is_valid,
    wait_update_session_is_eligible,
)


class CurrentStepCode(str, enum.Enum):
    INITIAL_EVIDENCE = "INITIAL_EVIDENCE"
    INITIAL_ANALYSIS = "INITIAL_ANALYSIS"
    PROCESSING = "PROCESSING"
    DECISION = "DECISION"
    WAIT_UPDATE = "WAIT_UPDATE"
    POSITION_MONITORING = "POSITION_MONITORING"
    FAILED_REQUEST = "FAILED_REQUEST"
    TERMINAL_CLOSED = "TERMINAL_CLOSED"
    TERMINAL_SKIPPED = "TERMINAL_SKIPPED"
    ARCHIVED_CLOSED = "ARCHIVED_CLOSED"
    ARCHIVED_SKIPPED = "ARCHIVED_SKIPPED"
    INCONSISTENT = "INCONSISTENT"


class CurrentStepMode(str, enum.Enum):
    ACTIONABLE = "ACTIONABLE"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    READ_ONLY = "READ_ONLY"
    INCONSISTENT = "INCONSISTENT"


class WorkflowAction(str, enum.Enum):
    SUBMIT_INITIAL_EVIDENCE = "SUBMIT_INITIAL_EVIDENCE"
    REQUEST_INITIAL_ANALYSIS = "REQUEST_INITIAL_ANALYSIS"
    BUY = "BUY"
    WAIT = "WAIT"
    SKIP = "SKIP"
    SUBMIT_WAIT_UPDATE = "SUBMIT_WAIT_UPDATE"
    SUBMIT_POSITION_UPDATE = "SUBMIT_POSITION_UPDATE"
    CLOSE = "CLOSE"
    RETRY_INITIAL_ANALYSIS = "RETRY_INITIAL_ANALYSIS"
    RETRY_WAIT_UPDATE = "RETRY_WAIT_UPDATE"


@dataclass(frozen=True, slots=True)
class CurrentStepRequest:
    id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    status: AnalysisRequestV2Status

    def payload(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "analysis_type": self.analysis_type,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class CurrentStepFailedRequest(CurrentStepRequest):
    retry_allowed: bool

    def payload(self) -> dict[str, object]:
        return {**super().payload(), "retry_allowed": self.retry_allowed}


@dataclass(frozen=True, slots=True)
class CurrentStep:
    code: CurrentStepCode
    mode: CurrentStepMode
    workflow_actions: tuple[WorkflowAction, ...] = ()
    active_request: CurrentStepRequest | None = None
    failed_request: CurrentStepFailedRequest | None = None
    read_only: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "code": self.code,
            "mode": self.mode,
            "workflow_actions": list(self.workflow_actions),
            "active_request": (
                self.active_request.payload() if self.active_request is not None else None
            ),
            "failed_request": (
                self.failed_request.payload() if self.failed_request is not None else None
            ),
            "read_only": self.read_only,
        }


_RELEVANT_REQUEST_TYPE = {
    TradeSessionV2Status.DRAFT: AnalysisRequestV2Type.INITIAL_ANALYSIS,
    TradeSessionV2Status.ANALYZING: AnalysisRequestV2Type.INITIAL_ANALYSIS,
    TradeSessionV2Status.ANALYZED: AnalysisRequestV2Type.INITIAL_ANALYSIS,
    TradeSessionV2Status.WAITING: AnalysisRequestV2Type.WAIT_UPDATE,
    TradeSessionV2Status.OPEN_POSITION: AnalysisRequestV2Type.POSITION_UPDATE,
}


class CurrentStepService:
    """Derive one non-persisted workflow step from owner-scoped aggregate rows."""

    @staticmethod
    def derive(
        *,
        trade_session: TradeSessionV2,
        evidence: Iterable[EvidenceUploadV2],
        requests: Iterable[AnalysisRequestV2],
        positions: Iterable[PositionV2],
        closure: TradeClosureV2 | None,
    ) -> CurrentStep:
        evidence_rows = tuple(
            item for item in evidence if item.session_id == trade_session.id
        )
        request_rows = tuple(
            item for item in requests if item.session_id == trade_session.id
        )
        position_rows = tuple(
            item for item in positions if item.session_id == trade_session.id
        )
        if closure is not None and closure.session_id != trade_session.id:
            closure = None
        status = trade_session.status

        if trade_session.archived_at is not None:
            if status is TradeSessionV2Status.CLOSED:
                return _read_only(CurrentStepCode.ARCHIVED_CLOSED)
            if status is TradeSessionV2Status.CLOSED_SKIPPED:
                return _read_only(CurrentStepCode.ARCHIVED_SKIPPED)
            return _inconsistent(read_only=True)

        if status is TradeSessionV2Status.CLOSED:
            return _read_only(CurrentStepCode.TERMINAL_CLOSED)
        if status is TradeSessionV2Status.CLOSED_SKIPPED:
            return _read_only(CurrentStepCode.TERMINAL_SKIPPED)

        relevant_requests = _relevant_requests(status, request_rows)
        active_requests = tuple(
            item for item in relevant_requests if request_is_active(item.status)
        )
        if active_requests:
            active = max(active_requests, key=lambda item: (item.created_at, item.id))
            return CurrentStep(
                code=CurrentStepCode.PROCESSING,
                mode=CurrentStepMode.PROCESSING,
                active_request=CurrentStepRequest(
                    id=active.id,
                    analysis_type=active.analysis_type,
                    status=active.status,
                ),
            )
        latest = (
            max(relevant_requests, key=lambda item: (item.created_at, item.id))
            if relevant_requests
            else None
        )
        if latest is not None and latest.status is AnalysisRequestV2Status.FAILED:
            retry_action = _retry_action(
                trade_session=trade_session,
                request=latest,
                evidence=evidence_rows,
            )
            return CurrentStep(
                code=CurrentStepCode.FAILED_REQUEST,
                mode=CurrentStepMode.FAILED,
                workflow_actions=(retry_action,) if retry_action is not None else (),
                failed_request=CurrentStepFailedRequest(
                    id=latest.id,
                    analysis_type=latest.analysis_type,
                    status=latest.status,
                    retry_allowed=retry_action is not None,
                ),
            )

        if status is TradeSessionV2Status.DRAFT:
            if not has_unassigned_initial_evidence(evidence_rows):
                return _actionable(
                    CurrentStepCode.INITIAL_EVIDENCE,
                    WorkflowAction.SUBMIT_INITIAL_EVIDENCE,
                )
            if initial_evidence_set_is_complete(evidence_rows):
                return _actionable(
                    CurrentStepCode.INITIAL_ANALYSIS,
                    WorkflowAction.REQUEST_INITIAL_ANALYSIS,
                )
            return _inconsistent()

        if status is TradeSessionV2Status.ANALYZING:
            return _inconsistent()

        if status in {TradeSessionV2Status.ANALYZED, TradeSessionV2Status.WAITING}:
            if position_rows or closure is not None:
                return _inconsistent()
            decision_actions = tuple(
                WorkflowAction(action) for action in available_decision_actions(status)
            )
            if status is TradeSessionV2Status.ANALYZED:
                return CurrentStep(
                    code=CurrentStepCode.DECISION,
                    mode=CurrentStepMode.ACTIONABLE,
                    workflow_actions=decision_actions,
                )
            wait_actions = (
                (WorkflowAction.SUBMIT_WAIT_UPDATE,)
                if wait_update_session_is_eligible(status)
                else ()
            )
            return CurrentStep(
                code=CurrentStepCode.WAIT_UPDATE,
                mode=CurrentStepMode.ACTIONABLE,
                workflow_actions=decision_actions + wait_actions,
            )

        if status is TradeSessionV2Status.OPEN_POSITION:
            position = single_open_position(position_rows)
            if position is None:
                return _inconsistent()
            position_update_actions = (
                (WorkflowAction.SUBMIT_POSITION_UPDATE,)
                if open_position_session_is_eligible(status)
                else ()
            )
            close_actions = (WorkflowAction.CLOSE,) if closure is None else ()
            return CurrentStep(
                code=CurrentStepCode.POSITION_MONITORING,
                mode=CurrentStepMode.ACTIONABLE,
                workflow_actions=position_update_actions + close_actions,
            )

        return _inconsistent()


def _relevant_requests(
    status: TradeSessionV2Status,
    requests: tuple[AnalysisRequestV2, ...],
) -> tuple[AnalysisRequestV2, ...]:
    request_type = _RELEVANT_REQUEST_TYPE.get(status)
    if request_type is None:
        return ()
    return tuple(item for item in requests if item.analysis_type is request_type)


def _retry_action(
    *,
    trade_session: TradeSessionV2,
    request: AnalysisRequestV2,
    evidence: tuple[EvidenceUploadV2, ...],
) -> WorkflowAction | None:
    linked = [item for item in evidence if item.analysis_request_id == request.id]
    if request.analysis_type is AnalysisRequestV2Type.INITIAL_ANALYSIS:
        if trade_session.status is not TradeSessionV2Status.DRAFT:
            return None
        if request_is_retryable(request.status) and linked_initial_evidence_is_valid(
            session_id=trade_session.id,
            request_id=request.id,
            evidence=linked,
        ):
            return WorkflowAction.RETRY_INITIAL_ANALYSIS
        return None
    if request.analysis_type is AnalysisRequestV2Type.WAIT_UPDATE:
        if not wait_update_session_is_eligible(trade_session.status):
            return None
        if request_is_retryable(request.status) and wait_retry_evidence_is_valid(
            session_id=trade_session.id,
            request=request,
            evidence=linked,
        ):
            return WorkflowAction.RETRY_WAIT_UPDATE
    return None


def _actionable(code: CurrentStepCode, action: WorkflowAction) -> CurrentStep:
    return CurrentStep(
        code=code,
        mode=CurrentStepMode.ACTIONABLE,
        workflow_actions=(action,),
    )


def _read_only(code: CurrentStepCode) -> CurrentStep:
    return CurrentStep(code=code, mode=CurrentStepMode.READ_ONLY, read_only=True)


def _inconsistent(*, read_only: bool = False) -> CurrentStep:
    return CurrentStep(
        code=CurrentStepCode.INCONSISTENT,
        mode=CurrentStepMode.INCONSISTENT,
        read_only=read_only,
    )
