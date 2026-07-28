"""Service for creating and updating evaluation records (P7).

Handles deterministic prediction recording from accepted analyses, user decision tracking,
and outcome completion on session closure or skip.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.enums import AcceptanceStatus, TradeSessionStatus
from app.models.evaluation_record import CompletenessStatus, EvaluationRecord
from app.models.trade_session import TradeSession
from app.models.trade_state import TradeState
from app.repositories.evaluation_record import EvaluationRecordRepository


class EvaluationRecordService:
    """Deterministic service for evaluation records creation and enrichment."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session
        self._repo = EvaluationRecordRepository(db_session)

    async def record_prediction_from_analysis(
        self,
        analysis: Analysis,
        session: TradeSession,
    ) -> EvaluationRecord | None:
        """Create an evaluation record from an accepted analysis."""

        # Guard: Only accepted analyses generate prediction data
        status_val = (
            analysis.acceptance_status.value
            if hasattr(analysis.acceptance_status, "value")
            else str(analysis.acceptance_status)
        )
        if status_val != AcceptanceStatus.ACCEPTED.value:
            return None

        # Check idempotency
        existing = await self._repo.get_by_session_and_analysis(session.id, analysis.id)
        if existing is not None:
            return existing

        payload = analysis.payload or {}
        decision_obj = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}

        prediction_data: dict[str, Any] = {
            "recommendation": payload.get("recommendation") or payload.get("recommendation_type") or decision_obj.get("recommendation"),
            "recommended_action": payload.get("recommended_action") or payload.get("suggested_action"),
            "confidence": payload.get("confidence") or payload.get("confidence_score") or decision_obj.get("confidence"),
            "bullish_probability": payload.get("bullish_probability"),
            "neutral_probability": payload.get("neutral_probability"),
            "bearish_probability": payload.get("bearish_probability"),
            "target_probability": payload.get("target_probability"),
            "downside_probability": payload.get("downside_probability"),
            "thesis_status": payload.get("thesis_status") or payload.get("thesis_state"),
            "setup_quality": payload.get("setup_quality") or payload.get("quality_score"),
            "proposed_entry": payload.get("proposed_entry") or payload.get("entry_plan"),
            "proposed_stop": payload.get("proposed_stop") or payload.get("stop_loss"),
            "proposed_targets": payload.get("proposed_targets") or payload.get("take_profit_targets"),
            "setup_change_classification": payload.get("setup_change_classification"),
        }

        # Count non-null prediction fields
        populated_count = sum(1 for v in prediction_data.values() if v is not None)
        completeness = (
            CompletenessStatus.PARTIAL.value
            if populated_count > 3
            else CompletenessStatus.INSUFFICIENT.value
        )

        record = EvaluationRecord(
            id=uuid.uuid4(),
            owner_id=session.owner_id,
            session_id=session.id,
            source_analysis_id=analysis.id,
            evidence_batch_id=None,
            ticker=session.ticker,
            analysis_type=analysis.analysis_type,
            prompt_name=analysis.prompt_name,
            prompt_version=analysis.prompt_version,
            schema_name=analysis.schema_name,
            schema_version=analysis.schema_version,
            provider=getattr(analysis, "provider", None) or "gemini",
            model=getattr(analysis, "model", None) or "gemini-2.5-flash",
            prediction_data=prediction_data,
            user_decision_data={},
            outcome_data={},
            completeness_status=completeness,
            legacy_source=False,
            validation_warning_count=0,
            quality_notes=[],
        )

        return await self._repo.create(record)

    async def record_user_decision(
        self,
        session: TradeSession,
        action_name: str,
        action_payload: dict[str, Any],
    ) -> EvaluationRecord | None:
        """Record user-confirmed action in the session's evaluation record."""
        record = await self._repo.get_latest_for_session(session.id)
        if record is None:
            # Create container evaluation record for user decision
            record = EvaluationRecord(
                id=uuid.uuid4(),
                owner_id=session.owner_id,
                session_id=session.id,
                source_analysis_id=None,
                evidence_batch_id=None,
                ticker=session.ticker,
                analysis_type="USER_ACTION",
                prediction_data={},
                user_decision_data={},
                outcome_data={},
                completeness_status=CompletenessStatus.PARTIAL.value,
                legacy_source=False,
                validation_warning_count=0,
                quality_notes=[],
            )
            record = await self._repo.create(record)

        decision_data = dict(record.user_decision_data)
        actions_list = list(decision_data.get("confirmed_actions", []))

        now_str = datetime.now(timezone.utc).isoformat()
        actions_list.append(
            {
                "action": action_name,
                "timestamp": action_payload.get("confirmed_at") or now_str,
                "payload": action_payload,
            }
        )
        decision_data["confirmed_actions"] = actions_list

        if action_name == "BUY":
            decision_data["user_action"] = "BUY"
            if action_payload.get("entry_price"):
                decision_data["actual_entry_price"] = str(action_payload["entry_price"])
            if action_payload.get("entry_timestamp"):
                decision_data["actual_entry_timestamp"] = str(action_payload["entry_timestamp"])
            if action_payload.get("quantity"):
                decision_data["quantity"] = str(action_payload["quantity"])
        elif action_name == "WAIT":
            decision_data["user_action"] = "WAIT"
        elif action_name == "SKIP":
            decision_data["user_action"] = "SKIP"
        elif action_name == "SELL":
            decision_data["user_action"] = "SELL"
            if action_payload.get("exit_price"):
                decision_data["actual_exit_price"] = str(action_payload["exit_price"])
            if action_payload.get("exit_timestamp"):
                decision_data["actual_exit_timestamp"] = str(action_payload["exit_timestamp"])
        elif action_name in ("CONFIRM_STOP", "CHANGE_STOP"):
            if action_payload.get("confirmed_stop_loss"):
                decision_data["confirmed_stop"] = str(action_payload["confirmed_stop_loss"])
        elif action_name in ("CONFIRM_TARGET", "CHANGE_TARGET"):
            if action_payload.get("confirmed_target"):
                decision_data["confirmed_target"] = str(action_payload["confirmed_target"])

        record.user_decision_data = decision_data
        record.updated_at = datetime.now(timezone.utc)
        return record

    async def record_outcome_on_closure(
        self,
        session: TradeSession,
        trade_state: TradeState | None,
    ) -> EvaluationRecord | None:
        """Complete outcome section when session is closed or skipped."""
        record = await self._repo.get_latest_for_session(session.id)
        if record is None:
            record = EvaluationRecord(
                id=uuid.uuid4(),
                owner_id=session.owner_id,
                session_id=session.id,
                source_analysis_id=None,
                evidence_batch_id=None,
                ticker=session.ticker,
                analysis_type="TERMINAL_OUTCOME",
                prediction_data={},
                user_decision_data={},
                outcome_data={},
                completeness_status=CompletenessStatus.PARTIAL.value,
                legacy_source=False,
                validation_warning_count=0,
                quality_notes=[],
            )
            record = await self._repo.create(record)

        outcome_data = dict(record.outcome_data)
        status_val = (
            session.lifecycle_status.value
            if hasattr(session.lifecycle_status, "value")
            else str(session.lifecycle_status)
        )

        outcome_data["session_status"] = status_val
        outcome_data["session_completed"] = status_val == TradeSessionStatus.CLOSED.value
        outcome_data["session_skipped"] = status_val == TradeSessionStatus.CLOSED_SKIPPED.value

        if trade_state is not None:
            if trade_state.realized_return is not None:
                outcome_data["realized_return"] = str(trade_state.realized_return)
            if trade_state.realized_pnl is not None:
                outcome_data["realized_pnl"] = str(trade_state.realized_pnl)
            if trade_state.entry_at is not None and trade_state.updated_at is not None:
                duration_hrs = (trade_state.updated_at - trade_state.entry_at).total_seconds() / 3600.0
                outcome_data["holding_duration_hours"] = f"{duration_hrs:.2f}"
            if trade_state.thesis_status is not None:
                outcome_data["thesis_status"] = (
                    trade_state.thesis_status.value
                    if hasattr(trade_state.thesis_status, "value")
                    else str(trade_state.thesis_status)
                )

        # Check agreement between AI recommendation and user action
        pred_rec = record.prediction_data.get("recommendation") or record.prediction_data.get("recommended_action")
        user_act = record.user_decision_data.get("user_action")
        if pred_rec and user_act:
            outcome_data["recommendation_user_agreement"] = (str(pred_rec).upper() == str(user_act).upper())

        # Determine overall completeness status
        if status_val == TradeSessionStatus.CLOSED_SKIPPED.value:
            record.completeness_status = CompletenessStatus.COMPLETE.value
        elif trade_state and trade_state.entry_price is not None and trade_state.average_exit_price is not None:
            record.completeness_status = CompletenessStatus.COMPLETE.value
        else:
            record.completeness_status = CompletenessStatus.PARTIAL.value

        record.outcome_data = outcome_data
        record.updated_at = datetime.now(timezone.utc)
        return record
