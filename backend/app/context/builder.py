"""Context Summary Builder (TP-0902)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

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
    EvidenceType,
)
from app.models.evidence import Evidence
from app.models.session_event import SessionEvent
from app.models.trade_action import TradeAction
from app.models.trade_session import TradeSession
from app.models.trade_state import TradeState
from app.repositories.analysis import AnalysisRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.trade_session import TradeSessionRepository
from app.schemas.registry import LocalSchemaRegistry
from app.validation.context_summary import ContextSummaryValidationResult, validate_context_summary
from app.validation.json_schema import JsonSchemaValidationService
from app.validation.issues import ValidationIssue

_SCHEMAS_ROOT = Path("schemas/production/v1")


@dataclass(frozen=True, slots=True)
class ContextSummaryBuildResult:
    session_id: uuid.UUID
    source_cutoff: datetime
    payload: Mapping[str, object]
    validation_result: ContextSummaryValidationResult
    selected_event_ids: tuple[uuid.UUID, ...]
    schema_issues: tuple[ValidationIssue, ...] = ()


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


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class ContextSummaryBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._session_repo = TradeSessionRepository(session)
        self._analysis_repo = AnalysisRepository(session)
        self._evidence_repo = EvidenceRepository(session)
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

        # 1. Load history
        history_inputs = await self._load_history_events(session_id, owner_id)
        selection = self._history_selector.select(
            events=history_inputs,
            maximum_events=maximum_events,
        )

        # 2. Load analyses — original + latest
        orig_analysis = await self._find_original_analysis(session_id, owner_id)
        latest_analysis = await self._find_latest_accepted(session_id, owner_id)

        # 3. Load active evidence
        all_active = await self._evidence_repo.list_active_for_session_for_user(
            session_id,
            owner_id,
        )
        chart_evidence = [
            e
            for e in all_active
            if e.evidence_type
            in (
                EvidenceType.CHART_THREE_MONTH,
                EvidenceType.CHART_SIX_MONTH,
            )
        ]

        # 4. Derive source cutoff from included sources
        cutoff = _derive_cutoff(
            source_cutoff,
            ts,
            trade_state,
            latest_analysis,
            chart_evidence,
        )

        # 5. Build payload
        payload = _build_payload(
            session=ts,
            trade_state=trade_state,
            latest_analysis=latest_analysis,
            orig_analysis=orig_analysis,
            chart_evidence=chart_evidence,
            source_cutoff=cutoff,
        )

        # 6. JSON Schema validation
        registry = _load_schema_registry()
        schema_validator = JsonSchemaValidationService(registry)
        schema_result = schema_validator.validate_by_name(
            payload,
            "context_summary",
            "1.0.0",
        )

        # 7. Domain validation
        canonical_state = _canonical_state_dict(trade_state)
        domain_result = validate_context_summary(payload, canonical_state)

        all_issues = list(schema_result.issues) + list(domain_result.issues)
        if not schema_result.valid or not domain_result.valid:
            details = "; ".join(f"{i.code}:{i.path}" for i in all_issues[:10])
            raise ContextSummaryValidationFailedError(
                message=f"Validation failed: {len(all_issues)} issue(s) [{details}]",
            )
        return ContextSummaryBuildResult(
            session_id=session_id,
            source_cutoff=cutoff,
            payload=payload,
            validation_result=ContextSummaryValidationResult(
                valid=True,
                issues=tuple(domain_result.issues),
            ),
            selected_event_ids=tuple(e.event_id for e in selection.selected_events),
            schema_issues=tuple(schema_result.issues),
        )

    async def _find_original_analysis(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Analysis | None:
        return await self._analysis_repo.get_latest_accepted_by_type_for_user(
            session_id,
            owner_id,
            AnalysisType.INITIAL_ANALYSIS.value,
        )

    async def _find_latest_accepted(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Analysis | None:
        result: Analysis | None = None
        for at in AnalysisType:
            a = await self._analysis_repo.get_latest_accepted_by_type_for_user(
                session_id,
                owner_id,
                at.value,
            )
            if a is not None and (result is None or a.created_at > result.created_at):
                result = a
        return result

    async def _load_history_events(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
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
                    action_type = _ev(action.action_type)
                    is_confirmed = True
            analysis_type = None
            is_accepted = False
            if se.related_analysis_id is not None:
                analysis = await self._session.get(Analysis, se.related_analysis_id)
                if analysis is not None:
                    analysis_type = _ev(analysis.analysis_type)
                    is_accepted = analysis.acceptance_status == AcceptanceStatus.ACCEPTED
            events.append(
                HistoryEvent(
                    event_id=se.id,
                    event_type=_ev(se.event_type),
                    occurred_at=se.occurred_at,
                    created_at=se.created_at,
                    related_action_id=se.related_action_id,
                    related_analysis_id=se.related_analysis_id,
                    analysis_type=analysis_type,
                    action_type=action_type,
                    payload={},
                    price=float(se.price) if se.price is not None else None,
                    quantity=float(se.quantity) if se.quantity is not None else None,
                    is_confirmed_action=is_confirmed,
                    is_accepted_analysis=is_accepted,
                )
            )
        return events


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------


def _build_payload(
    session: TradeSession,
    trade_state: TradeState | None,
    latest_analysis: Analysis | None,
    orig_analysis: Analysis | None,
    chart_evidence: Sequence[Evidence],
    source_cutoff: datetime,
) -> dict[str, Any]:
    pos_status = _ps(trade_state)
    is_closed = _is_closed_status(session)

    context_id = _deterministic_id(session.id, source_cutoff)

    return {
        "context_id": context_id,
        "session_id": str(session.id),
        "ticker": session.ticker,
        "company_name": session.company_name,
        "currency": _ev(session.currency),
        "session_status": _ev(session.lifecycle_status),
        "generated_at": source_cutoff.isoformat(),
        "source_cutoff_timestamp": source_cutoff.isoformat(),
        "context_version": "1.0.0",
        "current_position": _build_current_position(trade_state),
        "thesis_context": _build_thesis_context(
            trade_state,
            latest_analysis,
            orig_analysis,
        ),
        "active_levels": _build_active_levels(trade_state, latest_analysis),
        "latest_market_context": {
            "available": False,
            "trading_date": None,
            "market_timestamp": None,
            "update_period": None,
            "open": None,
            "high": None,
            "low": None,
            "last_or_close": None,
            "average": None,
            "change_percentage": None,
            "best_bid": None,
            "best_offer": None,
            "summary": "Not available",
        },
        "latest_orderbook_context": {
            "available": False,
            "evidence_id": None,
            "market_timestamp": None,
            "buyer_strength": "UNKNOWN",
            "seller_pressure": "UNKNOWN",
            "best_bid": None,
            "best_offer": None,
            "bid_support": None,
            "offer_resistance": None,
            "supports_current_plan": None,
            "key_observations": [],
            "conclusion": "Not available",
            "limitations": ["Not available"],
        },
        "latest_chart_context": _build_chart_context(chart_evidence),
        "latest_ai_assessment": _build_ai_assessment(latest_analysis),
        "active_trading_plan": _build_trading_plan(latest_analysis),
        "important_history": [],
        "user_confirmed_actions": [],
        "unresolved_items": _build_unresolved(latest_analysis),
        "closing_context": _build_closing_context(session, trade_state),
        "context_quality": _build_quality(latest_analysis, chart_evidence),
        "summary": "Not available",
    }


def _build_current_position(ts: TradeState | None) -> dict[str, Any]:
    if ts is None:
        return {
            k: None
            for k in (
                "position_exists",
                "position_status",
                "entry_price",
                "entry_timestamp",
                "original_quantity",
                "remaining_quantity",
                "average_exit_price",
                "current_price",
                "active_stop_loss",
                "active_target",
                "realized_profit_loss",
                "realized_return_percentage",
                "unrealized_profit_loss",
                "unrealized_return_percentage",
                "holding_duration_days",
                "last_confirmed_at",
            )
        } | {"position_exists": False, "position_status": "NOT_OPENED"}
    ps = _ev(ts.position_status)
    return {
        "position_exists": ps != "NOT_OPENED",
        "position_status": ps,
        "entry_price": _d(ts.entry_price),
        "entry_timestamp": _ts(ts.entry_at),
        "original_quantity": _d(ts.original_quantity),
        "remaining_quantity": _d(ts.remaining_quantity),
        "average_exit_price": _d(ts.average_exit_price),
        "current_price": None,
        "active_stop_loss": _d(ts.active_stop_loss),
        "active_target": _d(ts.active_target),
        "realized_profit_loss": _d(ts.realized_pnl),
        "realized_return_percentage": None,
        "unrealized_profit_loss": None,
        "unrealized_return_percentage": None,
        "holding_duration_days": None,
        "last_confirmed_at": None,
    }


def _extract_thesis_text(payload: dict[str, object] | None) -> str | None:
    """Extract a thesis narrative string from an analysis payload."""
    if not payload:
        return None
    # Check various thesis-related fields across analysis types
    es = payload.get("executive_summary")
    if isinstance(es, str):
        return es
    it = payload.get("initial_thesis")
    if isinstance(it, dict):
        val = it.get("summary")
        if isinstance(val, str):
            return val
    sa = payload.get("setup_assessment")
    if isinstance(sa, dict):
        for key in ("current_thesis_summary", "original_thesis_summary"):
            val = sa.get(key)
            if isinstance(val, str):
                return val
    ta = payload.get("thesis_assessment")
    if isinstance(ta, dict):
        val = ta.get("summary")
        if isinstance(val, str):
            return val
    if isinstance(es, dict):
        val = es.get("summary")
        if isinstance(val, str):
            return val
    return None


def _build_thesis_context(
    ts: TradeState | None,
    latest: Analysis | None,
    orig: Analysis | None,
) -> dict[str, Any]:
    original_thesis = _extract_thesis_text(orig.payload if orig else None)
    current_thesis = _extract_thesis_text(latest.payload if latest else None)
    return {
        "original_thesis": original_thesis,
        "current_thesis": current_thesis,
        "status": _ev(ts.thesis_status) if ts else "INTACT",
        "remains_valid": True,
        "support_condition": "Not available",
        "invalidation_condition": "Not available",
        "invalidation_price": None,
        "strengthening_factors": [],
        "weakening_factors": [],
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _price_level(
    price: object, label: str = "Active level", summary: str = "Not available"
) -> dict[str, object]:
    return {"price": price, "label": label, "summary": summary}


def _build_active_levels(
    ts: TradeState | None,
    latest: Analysis | None,
) -> dict[str, Any]:
    last_updated = _ts(datetime.now(timezone.utc))
    pending_sl = None
    pending_tg = None
    if latest and latest.payload:
        p = latest.payload
        pending_sl = p.get("proposed_stop_loss") or p.get("stop_loss_proposal")
        pending_tg = p.get("proposed_target") or p.get("target_proposal")
    return {
        "supports": [],
        "resistances": [],
        "entry_reference": _price_level(_d(ts.entry_price))
        if ts and ts.entry_price is not None
        else None,
        "maximum_acceptable_entry": None,
        "active_stop_loss": _price_level(_d(ts.active_stop_loss))
        if ts and ts.active_stop_loss is not None
        else None,
        "active_target": _price_level(_d(ts.active_target))
        if ts and ts.active_target is not None
        else None,
        "proposed_stop_loss": pending_sl,
        "proposed_target": pending_tg,
        "invalidation_level": None,
        "last_updated_at": last_updated,
    }


def _build_chart_context(charts: Sequence[Evidence]) -> dict[str, Any]:
    has_3m = any(_ev(e.evidence_type) == "CHART_THREE_MONTH" for e in charts)
    has_6m = any(_ev(e.evidence_type) == "CHART_SIX_MONTH" for e in charts)
    ts_3m = next(
        (_ts(e.uploaded_at) for e in charts if _ev(e.evidence_type) == "CHART_THREE_MONTH"), None
    )
    ts_6m = next(
        (_ts(e.uploaded_at) for e in charts if _ev(e.evidence_type) == "CHART_SIX_MONTH"), None
    )
    return {
        "available": len(charts) > 0,
        "chart_3_month_available": has_3m,
        "chart_6_month_available": has_6m,
        "using_historical_context": False,
        "latest_chart_timestamp": ts_3m or ts_6m,
        "short_term_trend": "UNKNOWN",
        "medium_term_trend": "UNKNOWN",
        "structure_status": "UNKNOWN",
        "nearest_support": None,
        "nearest_resistance": None,
        "breakout_status": "UNKNOWN",
        "breakdown_status": "UNKNOWN",
        "supports_current_plan": None,
        "conclusion": "Not available",
        "limitations": ["Not available"],
    }


def _n(val: Any, fallback: str = "Not available") -> str:
    """Return a string value or fallback — schema doesn't allow None/empty for string fields."""
    if val is None or val == "None" or (isinstance(val, str) and val.lower() == "none"):
        return fallback
    s = str(val)
    if not s:
        return fallback
    return s


def _build_ai_assessment(analysis: Analysis | None) -> dict[str, Any]:
    if analysis is None:
        return {
            "analysis_id": None,
            "analysis_type": None,
            "analysis_timestamp": None,
            "bias": "NEUTRAL",
            "confidence": None,
            "setup_quality": None,
            "position_health": None,
            "bullish_probability": None,
            "target_probability": None,
            "downside_probability": None,
            "risk_level": "UNKNOWN",
            "recommended_action": "NO_ACTION",
            "summary": "Not available",
        }
    p = analysis.payload or {}
    return {
        "analysis_id": str(analysis.id),
        "analysis_type": _ev(analysis.analysis_type),
        "analysis_timestamp": _ts(analysis.accepted_at),
        "bias": _n(p.get("bias"), "NEUTRAL"),
        "confidence": p.get("confidence"),
        "setup_quality": p.get("setup_quality"),
        "position_health": p.get("position_health"),
        "bullish_probability": p.get("bullish_probability"),
        "target_probability": p.get("target_probability"),
        "downside_probability": p.get("downside_probability"),
        "risk_level": _n(p.get("risk_level"), "UNKNOWN"),
        "recommended_action": _n(p.get("recommended_action"), "NO_ACTION"),
        "summary": _n(p.get("executive_summary")),
    }


def _build_trading_plan(analysis: Analysis | None) -> dict[str, Any]:
    plan = {
        "current_action": "NO_ACTION",
        "action_rationale": "Not available",
        "entry_condition": "Not available",
        "hold_condition": "Not available",
        "reduce_risk_condition": "Not available",
        "exit_condition": "Not available",
        "cancel_setup_condition": "Not available",
        "next_checkpoint": "Not available",
        "levels_to_monitor": [],
        "requires_user_confirmation": False,
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if analysis and analysis.payload:
        p = analysis.payload
        plan["current_action"] = _n(p.get("recommended_action"), "NO_ACTION")
        plan["action_rationale"] = _n(p.get("action_rationale"))
        plan["next_checkpoint"] = _n(p.get("next_checkpoint"))
    return plan


def _build_unresolved(analysis: Analysis | None) -> dict[str, Any]:
    return {
        "warnings": [],
        "missing_information": [],
        "items_requiring_review": [],
        "stale_context": False,
        "pending_entry_proposal": None,
        "pending_stop_loss_proposal": None,
        "pending_target_proposal": None,
        "pending_user_confirmations": [],
    }


def _build_closing_context(
    session: TradeSession,
    ts: TradeState | None,
) -> dict[str, Any]:
    is_closed = _is_closed_status(session)
    if not is_closed:
        return {
            "available": False,
            "closing_reason": None,
            "closed_at": None,
            "average_exit_price": None,
            "gross_profit_loss": None,
            "gross_return_percentage": None,
            "net_profit_loss": None,
            "net_return_percentage": None,
            "trade_grade": None,
            "main_lesson": None,
            "summary": None,
        }
    avg_exit = _d(ts.average_exit_price) if ts and ts.average_exit_price is not None else None
    gross_pnl = _d(ts.realized_pnl) if ts and ts.realized_pnl is not None else 0
    return {
        "available": True,
        "closing_reason": _closing_reason(session) or "MANUAL_EXIT",
        "closed_at": _ts(ts.entry_at)
        if ts and ts.entry_at
        else datetime.now(timezone.utc).isoformat(),
        "average_exit_price": avg_exit or _d(ts.entry_price) if ts else 0,
        "gross_profit_loss": gross_pnl,
        "gross_return_percentage": 0,
        "net_profit_loss": None,
        "net_return_percentage": None,
        "trade_grade": "C",
        "main_lesson": "Not available",
        "summary": "Not available",
    }


def _build_quality(
    latest: Analysis | None,
    charts: Sequence[Evidence],
) -> dict[str, Any]:
    limitations: list[str] = []
    if latest and latest.payload:
        p = latest.payload
        for key in ("limitations", "warnings", "data_limitations"):
            val = p.get(key)
            if isinstance(val, list):
                limitations.extend(str(v) for v in val if v)
    for ev in charts:
        if ev.text_content:
            limitations.append(f"Chart limitation: {ev.text_content[:200]}")
    return {
        "quality": "MODERATE",  # Valid enum: HIGH, MODERATE, LOW, INSUFFICIENT
        "complete_enough_for_analysis": True,
        "canonical_state_included": True,
        "latest_analysis_included": latest is not None,
        "latest_evidence_included": len(charts) > 0,
        "history_compressed": False,
        "stale": False,
        "limitations": limitations,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deterministic_id(session_id: uuid.UUID, cutoff: datetime) -> str:
    raw = f"{session_id}-{cutoff.isoformat()}"
    hex_digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"{hex_digest[:8]}-{hex_digest[8:12]}-4{hex_digest[13:16]}-{hex_digest[16:20]}-{hex_digest[20:32]}"


def _derive_cutoff(
    explicit: datetime | None,
    session: TradeSession,
    trade_state: TradeState | None,
    latest_analysis: Analysis | None,
    charts: Sequence[Evidence],
) -> datetime:
    if explicit is not None:
        return explicit
    candidates: list[datetime] = []
    if trade_state and trade_state.entry_at:
        candidates.append(trade_state.entry_at)
    if latest_analysis and latest_analysis.accepted_at:
        candidates.append(latest_analysis.accepted_at)
    for ev in charts:
        if ev.market_timestamp:
            candidates.append(ev.market_timestamp)
        if ev.uploaded_at:
            candidates.append(ev.uploaded_at)
    if candidates:
        return max(candidates)
    return session.created_at


def _ps(trade_state: TradeState | None) -> str:
    if trade_state is None:
        return "NOT_OPENED"
    return _ev(trade_state.position_status)


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


def _d(value: Any) -> object:
    """Convert a Decimal/numeric to a number for schema compliance."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _ds(value: Any) -> str | None:
    """Convert a Decimal/numeric to a string for domain validation."""
    if value is None:
        return None
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
            "entry_price": _ds(trade_state.entry_price),
            "original_quantity": _ds(trade_state.original_quantity),
            "remaining_quantity": _ds(trade_state.remaining_quantity),
            "active_stop_loss": _ds(trade_state.active_stop_loss),
            "active_target": _ds(trade_state.active_target),
        },
        "position_status": _ev(trade_state.position_status),
        "thesis_status": _ev(trade_state.thesis_status),
    }


def _load_schema_registry() -> LocalSchemaRegistry:
    from app.schemas.manifest import load_production_manifest

    manifest = load_production_manifest(_SCHEMAS_ROOT)
    return LocalSchemaRegistry(manifest, _SCHEMAS_ROOT)
