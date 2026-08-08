from __future__ import annotations

import uuid
from pathlib import Path
from typing import Iterable

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_session import TradeSessionV2Status

INITIAL_EVIDENCE_TYPES = (
    EvidenceUploadV2Type.ORDERBOOK,
    EvidenceUploadV2Type.CHART_3_MONTH,
    EvidenceUploadV2Type.CHART_6_MONTH,
    EvidenceUploadV2Type.FOREIGN_FLOW_1W,
)


def request_is_active(status: AnalysisRequestV2Status) -> bool:
    return status in {
        AnalysisRequestV2Status.PENDING,
        AnalysisRequestV2Status.PROCESSING,
    }


def request_is_retryable(status: AnalysisRequestV2Status) -> bool:
    return status in {
        AnalysisRequestV2Status.FAILED,
        AnalysisRequestV2Status.PENDING,
    }


def initial_evidence_session_is_eligible(status: TradeSessionV2Status) -> bool:
    return status is TradeSessionV2Status.DRAFT


def has_unassigned_initial_evidence(evidence: Iterable[EvidenceUploadV2]) -> bool:
    return any(
        item.evidence_type in INITIAL_EVIDENCE_TYPES
        and item.analysis_request_id is None
        and item.observation_period is None
        for item in evidence
    )


def initial_evidence_set_is_complete(evidence: Iterable[EvidenceUploadV2]) -> bool:
    rows = tuple(evidence)
    grouped = {
        evidence_type: [item for item in rows if item.evidence_type is evidence_type]
        for evidence_type in INITIAL_EVIDENCE_TYPES
    }
    return all(
        len(items) == 1
        and items[0].analysis_request_id is None
        and items[0].observation_period is None
        for items in grouped.values()
    ) and len(rows) == len(INITIAL_EVIDENCE_TYPES)


def linked_initial_evidence_is_valid(
    *,
    session_id: uuid.UUID,
    request_id: uuid.UUID,
    evidence: Iterable[EvidenceUploadV2],
) -> bool:
    linked = tuple(item for item in evidence if item.analysis_request_id == request_id)
    grouped = {
        evidence_type: [item for item in linked if item.evidence_type is evidence_type]
        for evidence_type in INITIAL_EVIDENCE_TYPES
    }
    return (
        len(linked) == len(INITIAL_EVIDENCE_TYPES)
        and all(item.session_id == session_id for item in linked)
        and all(
            len(items) == 1 and items[0].observation_period is None
            for items in grouped.values()
        )
    )


def wait_update_session_is_eligible(status: TradeSessionV2Status) -> bool:
    return status is TradeSessionV2Status.WAITING


def single_open_position(positions: Iterable[PositionV2]) -> PositionV2 | None:
    rows = tuple(positions)
    if len(rows) != 1 or rows[0].status is not PositionV2Status.OPEN:
        return None
    return rows[0]


def open_position_session_is_eligible(status: TradeSessionV2Status) -> bool:
    return status is TradeSessionV2Status.OPEN_POSITION


def update_evidence_is_ready(
    item: EvidenceUploadV2,
    *,
    require_relative_path: bool,
) -> bool:
    return (
        item.evidence_type is EvidenceUploadV2Type.ORDERBOOK
        and item.analysis_request_id is None
        and item.current_price is not None
        and item.observation_period is not None
        and item.observation_timestamp is not None
        and bool(item.file_path.strip())
        and (not require_relative_path or not Path(item.file_path).is_absolute())
    )


def wait_retry_evidence_is_valid(
    *,
    session_id: uuid.UUID,
    request: AnalysisRequestV2,
    evidence: Iterable[EvidenceUploadV2],
) -> bool:
    linked = tuple(item for item in evidence if item.analysis_request_id == request.id)
    if len(linked) not in (1, 2):
        return False
    orderbooks = [item for item in linked if item.evidence_type is EvidenceUploadV2Type.ORDERBOOK]
    broker_flows = [
        item for item in linked if item.evidence_type is EvidenceUploadV2Type.BROKER_FLOW_1D
    ]
    if len(orderbooks) != 1 or len(broker_flows) != len(linked) - 1:
        return False
    orderbook = orderbooks[0]
    return (
        all(item.session_id == session_id for item in linked)
        and orderbook.current_price is not None
        and orderbook.observation_period is not None
        and orderbook.observation_timestamp is not None
        and orderbook.current_price == request.current_price
        and orderbook.observation_period is request.observation_period
        and orderbook.observation_timestamp == request.observation_at
        and all(bool(item.file_path.strip()) for item in linked)
        and all(not Path(item.file_path).is_absolute() for item in linked)
    )
