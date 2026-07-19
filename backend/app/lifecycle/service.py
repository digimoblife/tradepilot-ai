"""Session Lifecycle Service (TP-0502).

Enforces canonical Trade Session lifecycle transitions.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.lifecycle.transitions import TERMINAL_STATUSES, is_transition_allowed
from app.models.enums import TradeSessionStatus
from app.models.trade_session import TradeSession
from app.repositories.trade_session import TradeSessionRepository


class InvalidSessionTransitionError(Exception):
    """Raised when an invalid lifecycle transition is requested."""

    code = "SESSION_TRANSITION_INVALID"

    def __init__(
        self,
        current_status: TradeSessionStatus,
        target_status: TradeSessionStatus,
        message: str | None = None,
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status
        msg = message or (
            f"Transition from {current_status.value} to {target_status.value} is not allowed"
        )
        super().__init__(msg)


class SessionLifecycleService:
    """Service for transitioning Trade Session lifecycle statuses."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TradeSessionRepository(session)

    async def transition(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        target_status: TradeSessionStatus,
    ) -> TradeSession:
        """Transition the session to *target_status*.

        Parameters
        ----------
        session_id:
            The session to transition.
        owner_id:
            The authenticated owner.
        target_status:
            The desired target lifecycle status.

        Returns
        -------
        TradeSession
            The updated session (attached to the DB session, not committed).

        Raises
        ------
        InvalidSessionTransitionError
            If the transition is not allowed by the canonical lifecycle.
        """
        ts = await self._repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise InvalidSessionTransitionError(
                current_status=TradeSessionStatus.DRAFT,
                target_status=target_status,
                message=f"Session {session_id} not found for user {owner_id}",
            )

        current = ts.lifecycle_status

        # Validate the transition
        if current == TradeSessionStatus.ARCHIVED and target_status != TradeSessionStatus.ARCHIVED:
            # Can only restore from archived
            raise InvalidSessionTransitionError(current, target_status)

        if not is_transition_allowed(current, target_status):
            raise InvalidSessionTransitionError(current, target_status)

        # Handle ANALYZING: preserve stable_status
        if target_status == TradeSessionStatus.ANALYZING:
            ts.stable_status = current

        # Handle terminal states: update both lifecycle and stable
        if target_status in TERMINAL_STATUSES and target_status != TradeSessionStatus.CANCELLED:
            ts.stable_status = target_status

        if (
            target_status == TradeSessionStatus.ANALYZING
            or target_status in TERMINAL_STATUSES
        ):
            ts.lifecycle_status = target_status
        else:
            ts.lifecycle_status = target_status
            # Non-transient, non-terminal statuses update stable_status
            if target_status not in (TradeSessionStatus.ANALYZING, TradeSessionStatus.ARCHIVED):
                ts.stable_status = target_status

        await self._session.flush()
        return ts
