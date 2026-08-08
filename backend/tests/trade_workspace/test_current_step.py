from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.current_step import CurrentStepService

INITIAL_EVIDENCE_TYPES = (
    EvidenceUploadV2Type.ORDERBOOK,
    EvidenceUploadV2Type.CHART_3_MONTH,
    EvidenceUploadV2Type.CHART_6_MONTH,
    EvidenceUploadV2Type.FOREIGN_FLOW_1W,
)

NOW = datetime(2026, 8, 5, tzinfo=timezone.utc)


def _session(
    status: TradeSessionV2Status,
    *,
    archived: bool = False,
) -> TradeSessionV2:
    return TradeSessionV2(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        ticker="BBRI",
        company_name="Bank BRI",
        status=status,
        archived_at=NOW if archived else None,
    )


def _request(
    trade_session: TradeSessionV2,
    analysis_type: AnalysisRequestV2Type,
    status: AnalysisRequestV2Status,
    *,
    request_id: uuid.UUID | None = None,
    created_at: datetime = NOW,
) -> AnalysisRequestV2:
    return AnalysisRequestV2(
        id=request_id or uuid.uuid4(),
        session_id=trade_session.id,
        analysis_type=analysis_type,
        status=status,
        provider="gemini",
        model="test-model",
        prompt_version="v1",
        input_snapshot={},
        created_at=created_at,
        current_price=(
            Decimal("1200")
            if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
            else None
        ),
        observation_period=(
            AnalysisRequestV2ObservationPeriod.MORNING
            if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
            else None
        ),
        observation_at=(
            NOW if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS else None
        ),
        error_code="PRIVATE_FAILURE",
        error_message="must not leak",
    )


def _evidence(
    trade_session: TradeSessionV2,
    evidence_type: EvidenceUploadV2Type,
    *,
    request: AnalysisRequestV2 | None = None,
    update: bool = False,
) -> EvidenceUploadV2:
    return EvidenceUploadV2(
        id=uuid.uuid4(),
        session_id=trade_session.id,
        analysis_request_id=request.id if request else None,
        evidence_type=evidence_type,
        observation_period=(AnalysisRequestV2ObservationPeriod.MORNING if update else None),
        current_price=Decimal("1200") if update else None,
        observation_timestamp=NOW if update else None,
        file_path="stored/safe.png",
        original_filename="safe.png",
        mime_type="image/png",
        size_bytes=10,
        uploaded_at=NOW,
    )


def _position(
    trade_session: TradeSessionV2,
    status: PositionV2Status = PositionV2Status.OPEN,
) -> PositionV2:
    return PositionV2(
        id=uuid.uuid4(),
        session_id=trade_session.id,
        entry_price=Decimal("1000"),
        entry_at=NOW,
        quantity=Decimal("1"),
        stop_loss=Decimal("900"),
        target_price=Decimal("1200"),
        status=status,
    )


def _derive(
    trade_session: TradeSessionV2,
    *,
    evidence: tuple[EvidenceUploadV2, ...] = (),
    requests: tuple[AnalysisRequestV2, ...] = (),
    positions: tuple[PositionV2, ...] = (),
    closure: object | None = None,
) -> dict[str, object]:
    return CurrentStepService.derive(
        trade_session=trade_session,
        evidence=evidence,
        requests=requests,
        positions=positions,
        closure=closure,  # type: ignore[arg-type]
    ).payload()


@pytest.mark.parametrize(
    ("status", "archived", "code", "mode", "read_only"),
    [
        (TradeSessionV2Status.WAITING, True, "INCONSISTENT", "INCONSISTENT", True),
        (TradeSessionV2Status.CLOSED, True, "ARCHIVED_CLOSED", "READ_ONLY", True),
        (TradeSessionV2Status.CLOSED_SKIPPED, True, "ARCHIVED_SKIPPED", "READ_ONLY", True),
        (TradeSessionV2Status.CLOSED, False, "TERMINAL_CLOSED", "READ_ONLY", True),
        (TradeSessionV2Status.CLOSED_SKIPPED, False, "TERMINAL_SKIPPED", "READ_ONLY", True),
    ],
)
def test_terminal_and_archive_precedence(status, archived, code, mode, read_only) -> None:
    trade_session = _session(status, archived=archived)
    request = _request(
        trade_session,
        AnalysisRequestV2Type.WAIT_UPDATE,
        AnalysisRequestV2Status.PROCESSING,
    )
    payload = _derive(trade_session, requests=(request,))
    assert (payload["code"], payload["mode"], payload["read_only"]) == (
        code,
        mode,
        read_only,
    )
    assert payload["workflow_actions"] == []


def test_normal_action_matrix_and_inconsistent_states() -> None:
    draft = _session(TradeSessionV2Status.DRAFT)
    assert _derive(draft)["workflow_actions"] == ["SUBMIT_INITIAL_EVIDENCE"]
    initial = tuple(_evidence(draft, item) for item in INITIAL_EVIDENCE_TYPES)
    assert _derive(draft, evidence=initial)["code"] == "INITIAL_ANALYSIS"

    analyzed = _session(TradeSessionV2Status.ANALYZED)
    assert _derive(analyzed)["workflow_actions"] == ["BUY", "WAIT", "SKIP"]
    assert _derive(analyzed, positions=(_position(analyzed),))["code"] == "INCONSISTENT"

    waiting = _session(TradeSessionV2Status.WAITING)
    assert _derive(waiting)["workflow_actions"] == ["BUY", "WAIT", "SKIP"]
    wait_input = _evidence(waiting, EvidenceUploadV2Type.ORDERBOOK, update=True)
    assert _derive(waiting, evidence=(wait_input,))["workflow_actions"] == [
        "BUY",
        "WAIT",
        "SKIP",
        "SUBMIT_WAIT_UPDATE",
    ]

    open_session = _session(TradeSessionV2Status.OPEN_POSITION)
    assert _derive(open_session, positions=(_position(open_session),))["workflow_actions"] == [
        "CLOSE"
    ]
    position_input = _evidence(open_session, EvidenceUploadV2Type.ORDERBOOK, update=True)
    assert _derive(
        open_session,
        evidence=(position_input,),
        positions=(_position(open_session),),
    )["workflow_actions"] == ["SUBMIT_POSITION_UPDATE", "CLOSE"]
    assert _derive(open_session)["code"] == "INCONSISTENT"
    assert _derive(_session(TradeSessionV2Status.ANALYZING))["code"] == "INCONSISTENT"


def test_active_request_is_processing_without_actions_or_error_leakage() -> None:
    trade_session = _session(TradeSessionV2Status.WAITING)
    request = _request(
        trade_session,
        AnalysisRequestV2Type.WAIT_UPDATE,
        AnalysisRequestV2Status.PROCESSING,
    )
    payload = _derive(trade_session, requests=(request,))
    assert payload["code"] == "PROCESSING"
    assert payload["workflow_actions"] == []
    assert payload["active_request"] == {
        "id": str(request.id),
        "analysis_type": "WAIT_UPDATE",
        "status": "PROCESSING",
    }
    assert "error_code" not in payload["active_request"]
    assert "error_message" not in payload["active_request"]


def test_latest_relevant_request_is_deterministic_and_supersedes_failure() -> None:
    trade_session = _session(TradeSessionV2Status.WAITING)
    failed = _request(
        trade_session,
        AnalysisRequestV2Type.WAIT_UPDATE,
        AnalysisRequestV2Status.FAILED,
        request_id=uuid.UUID(int=1),
        created_at=NOW - timedelta(seconds=1),
    )
    completed = _request(
        trade_session,
        AnalysisRequestV2Type.WAIT_UPDATE,
        AnalysisRequestV2Status.COMPLETED,
        request_id=uuid.UUID(int=2),
    )
    assert _derive(trade_session, requests=(completed, failed))["code"] == "WAIT_UPDATE"

    same_time_processing = _request(
        trade_session,
        AnalysisRequestV2Type.WAIT_UPDATE,
        AnalysisRequestV2Status.PROCESSING,
        request_id=uuid.UUID(int=3),
    )
    assert (
        _derive(trade_session, requests=(completed, same_time_processing))["code"] == "PROCESSING"
    )

    older_active = _request(
        trade_session,
        AnalysisRequestV2Type.WAIT_UPDATE,
        AnalysisRequestV2Status.PENDING,
        request_id=uuid.UUID(int=4),
        created_at=NOW - timedelta(seconds=2),
    )
    assert _derive(trade_session, requests=(completed, older_active))["code"] == "PROCESSING"


def test_other_session_request_cannot_affect_current_step() -> None:
    trade_session = _session(TradeSessionV2Status.WAITING)
    other_session = _session(TradeSessionV2Status.WAITING)
    foreign_request = _request(
        other_session,
        AnalysisRequestV2Type.WAIT_UPDATE,
        AnalysisRequestV2Status.PROCESSING,
    )
    payload = _derive(trade_session, requests=(foreign_request,))
    assert payload["code"] == "WAIT_UPDATE"
    assert payload["workflow_actions"] == ["BUY", "WAIT", "SKIP"]


def test_failed_retry_contract_matches_supported_retry_services() -> None:
    draft = _session(TradeSessionV2Status.DRAFT)
    initial_request = _request(
        draft,
        AnalysisRequestV2Type.INITIAL_ANALYSIS,
        AnalysisRequestV2Status.FAILED,
    )
    linked_initial = tuple(
        _evidence(draft, item, request=initial_request) for item in INITIAL_EVIDENCE_TYPES
    )
    initial_payload = _derive(
        draft,
        evidence=linked_initial,
        requests=(initial_request,),
    )
    assert initial_payload["workflow_actions"] == ["RETRY_INITIAL_ANALYSIS"]
    assert initial_payload["failed_request"]["retry_allowed"] is True

    waiting = _session(TradeSessionV2Status.WAITING)
    wait_request = _request(
        waiting,
        AnalysisRequestV2Type.WAIT_UPDATE,
        AnalysisRequestV2Status.FAILED,
    )
    wait_evidence = _evidence(
        waiting,
        EvidenceUploadV2Type.ORDERBOOK,
        request=wait_request,
        update=True,
    )
    wait_payload = _derive(waiting, evidence=(wait_evidence,), requests=(wait_request,))
    assert wait_payload["workflow_actions"] == ["RETRY_WAIT_UPDATE"]
    assert wait_payload["failed_request"]["retry_allowed"] is True

    open_session = _session(TradeSessionV2Status.OPEN_POSITION)
    position_request = _request(
        open_session,
        AnalysisRequestV2Type.POSITION_UPDATE,
        AnalysisRequestV2Status.FAILED,
    )
    position_payload = _derive(
        open_session,
        requests=(position_request,),
        positions=(_position(open_session),),
    )
    assert position_payload["workflow_actions"] == []
    assert position_payload["failed_request"]["retry_allowed"] is False
