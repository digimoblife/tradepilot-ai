"""Trade Session Service (TP-0501).

Creates a Trade Session in DRAFT with its initial empty canonical Trade State.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Currency, PositionStatus, ThesisStatus, TradeSessionStatus
from app.models.trade_session import TradeSession, normalize_currency, normalize_ticker
from app.models.trade_state import TradeState
from app.repositories.trade_session import TradeSessionRepository


class TradeSessionServiceError(ValueError):
    """Base error for Trade Session service operations."""


class InvalidTickerError(TradeSessionServiceError):
    """Raised when the ticker is empty or invalid after normalization."""


class UnsupportedCurrencyError(TradeSessionServiceError):
    """Raised when the currency is not a supported canonical value."""


_SUPPORTED_CURRENCIES = frozenset({c.value for c in Currency})


class TradeSessionService:
    """Service for creating Trade Sessions with initial canonical Trade State."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TradeSessionRepository(session)

    async def create_session(
        self,
        *,
        owner_id: uuid.UUID,
        ticker: str,
        currency: str = "IDR",
        title: str | None = None,
    ) -> TradeSession:
        """Create a Trade Session in DRAFT with an empty canonical Trade State.

        Parameters
        ----------
        owner_id:
            The authenticated user's UUID.
        ticker:
            The stock ticker (case-insensitive, whitespace-trimmed).
        currency:
            The trading currency (default ``"IDR"``).
        title:
            Optional session title.

        Returns
        -------
        TradeSession
            The newly created session (attached to the DB session, not committed).

        Raises
        ------
        InvalidTickerError
            If the normalized ticker is empty.
        UnsupportedCurrencyError
            If the currency is not a supported canonical value.
        """
        # Normalize
        normalized_ticker = normalize_ticker(ticker)
        if not normalized_ticker:
            raise InvalidTickerError("Ticker must not be empty after normalization")

        normalized_currency = normalize_currency(currency)
        if normalized_currency not in _SUPPORTED_CURRENCIES:
            raise UnsupportedCurrencyError(
                f"Unsupported currency: {currency}. "
                f"Supported: {', '.join(sorted(_SUPPORTED_CURRENCIES))}"
            )

        # Generate IDs explicitly for atomic creation
        session_id = uuid.uuid4()
        state_id = session_id  # TradeState uses session_id as PK

        ts = TradeSession(
            id=session_id,
            owner_id=owner_id,
            ticker=normalized_ticker,
            currency=normalized_currency,
            title=title,
            lifecycle_status=TradeSessionStatus.DRAFT,
            stable_status=TradeSessionStatus.DRAFT,
        )

        trade_state = TradeState(
            session_id=state_id,
            position_status=PositionStatus.NOT_OPENED,
            thesis_status=ThesisStatus.INTACT,
        )

        self._session.add(ts)
        self._session.add(trade_state)
        await self._session.flush()

        return ts
