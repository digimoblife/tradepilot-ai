from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2
from app.trade_workspace.models.session_decision import SessionDecisionV2
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2


class SessionDetailAggregateNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class SessionDetailAggregate:
    payload: dict[str, object]


def _value(item: object, name: str) -> object:
    value = getattr(item, name)
    return value.value if hasattr(value, "value") else value


def _evidence(item: EvidenceUploadV2) -> dict[str, object]:
    return {
        "id": str(item.id),
        "evidence_type": _value(item, "evidence_type"),
        "original_filename": item.original_filename,
        "mime_type": item.mime_type,
        "size_bytes": item.size_bytes,
        "uploaded_at": item.uploaded_at,
    }


def _request(item: AnalysisRequestV2, *, evidence: EvidenceUploadV2 | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "request_id": str(item.id),
        "session_id": str(item.session_id),
        "status": _value(item, "status"),
        "analysis_type": _value(item, "analysis_type"),
        "observation_period": _value(item, "observation_period") if item.observation_period else None,
        "current_price": item.current_price,
        "observation_timestamp": item.observation_at,
        "processed_response": item.processed_response,
        "error_code": item.error_code,
        "error_message": item.error_message,
        "model": item.model,
        "prompt_version": item.prompt_version,
        "created_at": item.created_at,
        "started_at": item.started_at,
        "completed_at": item.completed_at,
    }
    if evidence is not None:
        result["evidence"] = _evidence(evidence)
    snapshot = item.input_snapshot or {}
    if isinstance(snapshot, dict) and "note" in snapshot:
        result["note"] = snapshot.get("note")
    return result


class SessionDetailAggregateService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, user_id: uuid.UUID, session_id: uuid.UUID) -> SessionDetailAggregate:
        trade_session = await self._session.scalar(
            select(TradeSessionV2).where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
        )
        if trade_session is None:
            raise SessionDetailAggregateNotFoundError

        evidence_rows = list((await self._session.scalars(
            select(EvidenceUploadV2)
            .where(
                EvidenceUploadV2.session_id == session_id,
                EvidenceUploadV2.evidence_type.in_(
                    [EvidenceUploadV2Type.ORDERBOOK, EvidenceUploadV2Type.CHART_3_MONTH, EvidenceUploadV2Type.CHART_6_MONTH]
                ),
            )
            .order_by(EvidenceUploadV2.uploaded_at.asc(), EvidenceUploadV2.id.asc())
        )).all())
        requests = list((await self._session.scalars(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type.in_(list(AnalysisRequestV2Type)),
            )
            .order_by(AnalysisRequestV2.created_at.asc(), AnalysisRequestV2.id.asc())
        )).all())
        decisions = list((await self._session.scalars(
            select(SessionDecisionV2)
            .where(SessionDecisionV2.session_id == session_id)
            .order_by(SessionDecisionV2.created_at.asc(), SessionDecisionV2.id.asc())
        )).all())
        position = await self._session.scalar(
            select(PositionV2).where(PositionV2.session_id == session_id)
        )
        closure = await self._session.scalar(
            select(TradeClosureV2).where(TradeClosureV2.session_id == session_id)
        )

        initial_types = {
            EvidenceUploadV2Type.ORDERBOOK,
            EvidenceUploadV2Type.CHART_3_MONTH,
            EvidenceUploadV2Type.CHART_6_MONTH,
        }
        initial_requests = [item for item in requests if item.analysis_type is AnalysisRequestV2Type.INITIAL_ANALYSIS]
        initial_request_ids = {item.id for item in initial_requests}
        initial_evidence = [
            _evidence(item)
            for item in evidence_rows
            if item.evidence_type in initial_types
            and (item.analysis_request_id is None or item.analysis_request_id in initial_request_ids)
        ]
        initial = _request(initial_requests[-1]) if initial_requests else None
        wait_requests = [item for item in requests if item.analysis_type is AnalysisRequestV2Type.WAIT_UPDATE]
        position_requests = [item for item in requests if item.analysis_type is AnalysisRequestV2Type.POSITION_UPDATE]
        evidence_by_request = {item.analysis_request_id: item for item in evidence_rows if item.analysis_request_id is not None}

        decision_rows = [
            {
                "decision_id": str(item.id),
                "decision": _value(item, "decision"),
                "reason": _value(item, "reason") if item.reason else None,
                "note": item.note,
                "created_at": item.created_at,
            }
            for item in decisions
        ]
        position_payload = None if position is None else {
            "id": str(position.id), "session_id": str(position.session_id), "status": _value(position, "status"),
            "entry_price": position.entry_price, "entry_timestamp": position.entry_at, "quantity": position.quantity,
            "stop_loss": position.stop_loss, "target_price": position.target_price, "note": position.note,
            "created_at": position.created_at, "closed_at": position.closed_at,
        }
        closure_payload = None if closure is None else {
            "closure_id": str(closure.id), "position_id": str(closure.position_id), "close_price": closure.close_price,
            "close_timestamp": closure.close_at, "close_reason": closure.close_reason, "note": closure.note,
            "realized_result": closure.realized_profit_loss, "created_at": closure.created_at,
        }
        return SessionDetailAggregate({
            "session": {
                "id": str(trade_session.id), "ticker": trade_session.ticker, "company_name": trade_session.company_name,
                "status": _value(trade_session, "status"), "initial_note": trade_session.note,
                "created_at": trade_session.created_at, "updated_at": trade_session.updated_at, "closed_at": trade_session.closed_at,
            },
            "initial_evidence": initial_evidence,
            "initial_analysis": initial,
            "decisions": decision_rows,
            "wait_updates": [_request(item, evidence=evidence_by_request.get(item.id)) for item in wait_requests],
            "position": position_payload,
            "position_updates": [_request(item, evidence=evidence_by_request.get(item.id)) for item in position_requests],
            "closure": closure_payload,
        })
