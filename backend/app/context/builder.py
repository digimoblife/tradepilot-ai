"""Context Summary Builder (TP-0902)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.history_selector import (
    HistoryEvent,
    MaterialHistorySelector,
)
from app.models.analysis import Analysis
from app.models.enums import (
    AcceptanceStatus,
    AnalysisType,
)
from app.models.session_event import SessionEvent
from app.models.trade_action import TradeAction
from app.models.trade_session import TradeSession
from app.models.trade_state import TradeState
from app.repositories.analysis import AnalysisRepository
from app.repositories.trade_session import TradeSessionRepository
from app.validation.context_summary import ContextSummaryValidationResult, validate_context_summary


@dataclass(frozen=True, slots=True)
class ContextSummaryBuildResult:
    session_id: uuid.UUID
    source_cutoff: datetime
    payload: Mapping[str, object]
    validation_result: ContextSummaryValidationResult
    selected_event_ids: tuple[uuid.UUID, ...]


class ContextSummaryBuilderError(Exception):
    code: str = "CONTEXT_SUMMARY_BUILDER_ERROR"
    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class ContextSummarySessionNotFoundError(ContextSummaryBuilderError):
    code: str = "CONTEXT_SUMMARY_SESSION_NOT_FOUND_OR_NOT_OWNED"


class ContextSummaryValidationFailedError(ContextSummaryBuilderError):
    code: str = "CONTEXT_SUMMARY_VALIDATION_FAILED"


class ContextSummaryBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._session_repo = TradeSessionRepository(session)
        self._analysis_repo = AnalysisRepository(session)
        self._history_selector = MaterialHistorySelector()

    async def build(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        source_cutoff: datetime | None = None,
        maximum_events: int = 50,
    ) -> ContextSummaryBuildResult:
        ts = await self._session_repo.get_by_id_for_user(session_id, owner_id)
        if ts is None:
            raise ContextSummarySessionNotFoundError(
                message="Trade Session not found or not owned",
            )
        trade_state = await self._session.get(TradeState, session_id)

        history_inputs = await self._load_history_events(session_id, owner_id)
        selection = self._history_selector.select(
            events=history_inputs, maximum_events=maximum_events,
        )

        latest_analysis = None
        for at in AnalysisType:
            a = await self._analysis_repo.get_latest_accepted_by_type_for_user(
                session_id, owner_id, at.value,
            )
            if a is not None:
                latest_analysis = a

        cutoff = source_cutoff or datetime.now(timezone.utc)
        payload = _build_payload(ts, trade_state, latest_analysis, cutoff)

        canonical_state = _canonical_state_dict(trade_state)
        domain_result = validate_context_summary(payload, canonical_state)

        if not domain_result.valid:
            raise ContextSummaryValidationFailedError(
                message=f"Context Summary domain validation failed: {len(domain_result.issues)} issue(s)",
            )
        return ContextSummaryBuildResult(
            session_id=session_id, source_cutoff=cutoff, payload=payload,
            validation_result=ContextSummaryValidationResult(valid=True, issues=domain_result.issues),
            selected_event_ids=tuple(e.event_id for e in selection.selected_events),
        )

    async def _load_history_events(
        self, session_id: uuid.UUID, owner_id: uuid.UUID,
    ) -> list[HistoryEvent]:
        query = await self._session.execute(
            select(SessionEvent)
            .where(SessionEvent.session_id == session_id)
            .order_by(SessionEvent.occurred_at, SessionEvent.id)
        )
        session_events = query.unique().scalars().all()
        events: list[HistoryEvent] = []
        for se in session_events:
            action_type = None
            is_confirmed = False
            if se.related_action_id is not None:
                action = await self._session.get(TradeAction, se.related_action_id)
                if action is not None:
                    action_type = action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type)
                    is_confirmed = True
            analysis_type = None
            is_accepted = False
            if se.related_analysis_id is not None:
                analysis = await self._session.get(Analysis, se.related_analysis_id)
                if analysis is not None:
                    analysis_type = analysis.analysis_type.value if hasattr(analysis.analysis_type, "value") else str(analysis.analysis_type)
                    is_accepted = analysis.acceptance_status == AcceptanceStatus.ACCEPTED
            payload = {}
            if se.compact_summary:
                try:
                    payload = json.loads(se.compact_summary)
                except (json.JSONDecodeError, ValueError):
                    payload = {}
            events.append(HistoryEvent(
                event_id=se.id,
                event_type=se.event_type.value if hasattr(se.event_type, "value") else str(se.event_type),
                occurred_at=se.occurred_at, created_at=se.created_at,
                related_action_id=se.related_action_id,
                related_analysis_id=se.related_analysis_id,
                analysis_type=analysis_type, action_type=action_type,
                payload=payload,
                price=float(se.price) if se.price is not None else None,
                quantity=float(se.quantity) if se.quantity is not None else None,
                is_confirmed_action=is_confirmed, is_accepted_analysis=is_accepted,
            ))
        return events


# ---------------------------------------------------------------------------
# Schema-compliant payload builder
# ---------------------------------------------------------------------------


def _build_payload(
    session: TradeSession, trade_state: TradeState | None,
    latest_analysis: Analysis | None, source_cutoff: datetime,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    pos_status = _ps(trade_state)
    is_closed = _is_closed_status(session)
    closing_reason = _closing_reason(session)

    return {
        "context_id": str(uuid.uuid4()),
        "session_id": str(session.id),
        "ticker": session.ticker,
        "company_name": session.company_name,
        "currency": _ev(session.currency),
        "session_status": _ev(session.lifecycle_status),
        "generated_at": now.isoformat(),
        "source_cutoff_timestamp": source_cutoff.isoformat(),
        "context_version": "1.0.0",
        "current_position": {
            "position_exists": pos_status != "NOT_OPENED",
            "position_status": pos_status,
            "entry_price": _d(trade_state.entry_price) if trade_state else None,
            "entry_timestamp": _ts(trade_state.entry_at) if trade_state else None,
            "original_quantity": _d(trade_state.original_quantity) if trade_state else None,
            "remaining_quantity": _d(trade_state.remaining_quantity) if trade_state else None,
            "average_exit_price": _d(trade_state.average_exit_price) if trade_state else None,
            "current_price": None, "active_stop_loss": _d(trade_state.active_stop_loss) if trade_state else None,
            "active_target": _d(trade_state.active_target) if trade_state else None,
            "realized_profit_loss": _d(trade_state.realized_pnl) if trade_state else None,
            "realized_return_percentage": None, "unrealized_profit_loss": None,
            "unrealized_return_percentage": None, "holding_duration_days": None, "last_confirmed_at": None,
        },
        "thesis_context": {
            "thesis_status": _ev(trade_state.thesis_status) if trade_state else "INTACT",
            "original_thesis": None, "thesis_evolution": [],
            "latest_thesis_summary": latest_analysis.payload.get("executive_summary") if latest_analysis and latest_analysis.payload else None,
        },
        "active_levels": {
            "entry_reference": {"price": _d(trade_state.entry_price)} if trade_state and trade_state.entry_price is not None else None,
            "active_stop_loss": {"price": _d(trade_state.active_stop_loss)} if trade_state and trade_state.active_stop_loss is not None else None,
            "active_target": {"price": _d(trade_state.active_target)} if trade_state and trade_state.active_target is not None else None,
            "proposed_stop_loss": None, "proposed_target": None,
            "maximum_acceptable_entry": None, "chase_limit": None,
            "invalidation_level": None, "supports": [], "resistances": [],
            "last_updated_at": now.isoformat(),
        },
        "latest_market_context": {"bid": None, "offer": None, "last_price": None, "spread": None, "market_change": None, "market_timestamp": None, "available": False},
        "latest_orderbook_context": {"summary": None, "orderbook_timestamp": None, "available": False},
        "latest_chart_context": {"chart_summary": None, "chart_timestamp": None, "chart_types_available": [], "chart_limitations": [], "available": False},
        "latest_ai_assessment": {
            "analysis_id": str(latest_analysis.id) if latest_analysis else None,
            "analysis_type": _ev(latest_analysis.analysis_type) if latest_analysis else None,
            "analysis_timestamp": _ts(latest_analysis.accepted_at) if latest_analysis and latest_analysis.accepted_at else None,
            "bias": None, "confidence": None, "setup_quality": None, "position_health": None,
            "bullish_probability": None, "target_probability": None, "downside_probability": None,
            "risk_level": None, "recommended_action": None,
            "summary": latest_analysis.payload.get("executive_summary") if latest_analysis and latest_analysis.payload else None,
        },
        "active_trading_plan": {
            "current_action": None, "action_rationale": None,
            "entry_condition": None, "hold_condition": None,
            "reduce_risk_condition": None, "exit_condition": None,
            "cancel_setup_condition": None, "next_checkpoint": None,
            "levels_to_monitor": [], "requires_user_confirmation": False,
            "last_updated_at": now.isoformat(),
        },
        "important_history": [],
        "user_confirmed_actions": [],
        "unresolved_items": {"warnings": [], "missing_evidence": [], "unresolved_questions": [], "pending_confirmations": []},
        "closing_context": {
            "available": is_closed, "closing_reason": closing_reason,
            "closed_at": None, "average_exit_price": _d(trade_state.average_exit_price) if trade_state else None,
            "gross_profit_loss": _d(trade_state.realized_pnl) if trade_state else None,
            "gross_return_percentage": None, "net_profit_loss": None, "net_return_percentage": None,
            "trade_grade": None, "main_lesson": None, "summary": None,
        },
        "context_quality": {
            "quality": "STANDARD", "complete_enough_for_analysis": True,
            "canonical_state_included": True, "latest_analysis_included": latest_analysis is not None,
            "latest_evidence_included": False, "history_compressed": False,
            "stale": False, "limitations": [],
        },
        "summary": None,
    }


def _ps(trade_state: TradeState | None) -> str:
    if trade_state is None:
        return "NOT_OPENED"
    return trade_state.position_status.value if hasattr(trade_state.position_status, "value") else str(trade_state.position_status)


def _is_closed_status(session: TradeSession) -> bool:
    st = _ev(session.lifecycle_status)
    return st in ("CLOSED_TAKE_PROFIT", "CLOSED_STOP_LOSS", "CLOSED_MANUAL")


def _closing_reason(session: TradeSession) -> str | None:
    st = _ev(session.lifecycle_status)
    if st == "CLOSED_TAKE_PROFIT":
        return "TAKE_PROFIT"
    if st == "CLOSED_STOP_LOSS":
        return "STOP_LOSS"
    if st == "CLOSED_MANUAL":
        return "MANUAL_EXIT"
    return None


def _d(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _ts(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _ev(value: Any) -> str:
    if hasattr(value, "value"):
        return value.value  # type: ignore[no-any-return]
    return str(value)


def _canonical_state_dict(trade_state: TradeState | None) -> dict[str, object]:
    if trade_state is None:
        return {"position": {}}
    return {
        "position": {
            "entry_price": trade_state.entry_price,
            "original_quantity": trade_state.original_quantity,
            "remaining_quantity": trade_state.remaining_quantity,
            "active_stop_loss": trade_state.active_stop_loss,
            "active_target": trade_state.active_target,
        },
        "position_status": _ev(trade_state.position_status),
        "thesis_status": _ev(trade_state.thesis_status),
    }



