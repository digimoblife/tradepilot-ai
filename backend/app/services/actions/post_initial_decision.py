"""User-confirmed post-initial-analysis lifecycle decisions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context_summary import ContextSummary
from app.models.enums import ActionType, SessionEventType, TradeSessionStatus
from app.models.session_event import SessionEvent
from app.models.trade_action import TradeAction
from app.repositories.trade_session import TradeSessionRepository

_DECISION_SOURCES = frozenset(
    {
        TradeSessionStatus.INITIAL_ANALYZED,
        TradeSessionStatus.WATCHING,
    }
)


class PostInitialDecisionError(Exception):
    code = "POST_INITIAL_DECISION_ERROR"


class PostInitialDecisionInvalidStateError(PostInitialDecisionError):
    code = "POST_INITIAL_DECISION_INVALID_STATE"


class PostInitialDecisionNotFoundError(PostInitialDecisionError):
    code = "POST_INITIAL_DECISION_NOT_FOUND_OR_NOT_OWNED"


@dataclass(frozen=True, slots=True)
class PostInitialDecisionResult:
    session_id: uuid.UUID
    action: TradeAction
    session_status: TradeSessionStatus


class PostInitialDecisionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TradeSessionRepository(session)

    async def wait(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        idempotency_key: str,
        confirmed_at: datetime,
        note: str | None = None,
    ) -> PostInitialDecisionResult:
        return await self._confirm(
            session_id=session_id,
            owner_id=owner_id,
            idempotency_key=idempotency_key,
            confirmed_at=confirmed_at,
            action_type=ActionType.USER_WAITED,
            event_type=SessionEventType.USER_WAITED,
            target_status=TradeSessionStatus.WATCHING,
            summary="User chose to wait",
            note=note,
        )

    async def skip(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        idempotency_key: str,
        confirmed_at: datetime,
        reason: str | None = None,
        note: str | None = None,
    ) -> PostInitialDecisionResult:
        return await self._confirm(
            session_id=session_id,
            owner_id=owner_id,
            idempotency_key=idempotency_key,
            confirmed_at=confirmed_at,
            action_type=ActionType.SESSION_SKIPPED,
            event_type=SessionEventType.SESSION_SKIPPED,
            target_status=TradeSessionStatus.CLOSED_SKIPPED,
            summary=f"User skipped setup: {reason or 'no reason given'}",
            note=note or reason,
            payload={"reason": reason},
        )

    async def _confirm(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        idempotency_key: str,
        confirmed_at: datetime,
        action_type: ActionType,
        event_type: SessionEventType,
        target_status: TradeSessionStatus,
        summary: str,
        note: str | None,
        payload: dict[str, object] | None = None,
    ) -> PostInitialDecisionResult:
        ts = await self._repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise PostInitialDecisionNotFoundError(
                f"Session {session_id} not found for user {owner_id}"
            )

        existing = (
            (
                await self._session.execute(
                    select(TradeAction).where(
                        TradeAction.session_id == session_id,
                        TradeAction.idempotency_key == idempotency_key,
                    )
                )
            )
            .unique()
            .scalar_one_or_none()
        )
        if existing is not None:
            return PostInitialDecisionResult(
                session_id=session_id,
                action=existing,
                session_status=ts.lifecycle_status,
            )

        if ts.lifecycle_status not in _DECISION_SOURCES:
            raise PostInitialDecisionInvalidStateError(
                f"Cannot confirm decision: session is {ts.lifecycle_status.value}"
            )

        action = TradeAction(
            session_id=session_id,
            action_type=action_type,
            confirmed_at=confirmed_at,
            idempotency_key=idempotency_key,
            note=note,
            payload=payload or {},
        )
        self._session.add(action)

        ts.lifecycle_status = target_status
        ts.stable_status = target_status

        self._session.add(
            SessionEvent(
                session_id=session_id,
                event_type=event_type,
                occurred_at=confirmed_at,
                related_action_id=action.id,
                compact_summary=summary,
            )
        )

        await self._session.execute(
            update(ContextSummary)
            .where(ContextSummary.session_id == session_id, ContextSummary.is_stale == False)  # noqa: E712
            .values(is_stale=True)
        )
        await self._session.flush()

        return PostInitialDecisionResult(
            session_id=session_id,
            action=action,
            session_status=target_status,
        )
