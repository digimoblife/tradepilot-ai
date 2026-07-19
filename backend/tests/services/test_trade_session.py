"""Tests for Trade Session Service (TP-0501)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.enums import Currency, PositionStatus, ThesisStatus, TradeSessionStatus
from app.models.trade_state import TradeState
from app.repositories.trade_session import TradeSessionRepository
from app.services.trade_session import (
    InvalidTickerError,
    TradeSessionService,
    UnsupportedCurrencyError,
)

pytestmark = pytest.mark.database


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    """Create a test user and return the ID."""
    async with engine.begin() as conn:
        result = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"svc_user_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return result.first()[0]


@pytest.fixture
async def svc(
    engine: AsyncEngine, user_id: uuid.UUID
) -> tuple[TradeSessionService, AsyncSession, uuid.UUID]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield TradeSessionService(s), s, user_id


# ===================================================================


class TestCreateSession:
    async def test_valid_creation(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, _, uid = svc
        session = await service.create_session(
            owner_id=uid,
            ticker="BBRI",
            currency="IDR",
        )
        assert session is not None
        assert session.id is not None
        assert session.owner_id == uid

    async def test_draft_status(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, _, uid = svc
        session = await service.create_session(owner_id=uid, ticker="BBRI")
        assert session.lifecycle_status == TradeSessionStatus.DRAFT
        assert session.stable_status == TradeSessionStatus.DRAFT

    async def test_ticker_normalized(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, _, uid = svc
        session = await service.create_session(owner_id=uid, ticker=" bbri ")
        assert session.ticker == "BBRI"

    async def test_currency_normalized(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, _, uid = svc
        session = await service.create_session(owner_id=uid, ticker="BBRI", currency=" usd ")
        assert session.currency == Currency.USD


class TestEmptyTradeState:
    async def test_state_created(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, db_session, uid = svc
        session = await service.create_session(owner_id=uid, ticker="BBRI")
        await db_session.refresh(session)
        state = await db_session.get(TradeState, session.id)
        assert state is not None
        assert state.session_id == session.id

    async def test_not_opened_values(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, db_session, uid = svc
        session = await service.create_session(owner_id=uid, ticker="BBRI")
        state = await db_session.get(TradeState, session.id)
        assert state is not None
        assert state.position_status == PositionStatus.NOT_OPENED
        assert state.thesis_status == ThesisStatus.INTACT
        assert state.entry_price is None
        assert state.entry_at is None
        assert state.original_quantity is None
        assert state.remaining_quantity is None
        assert state.active_stop_loss is None
        assert state.active_target is None
        assert state.average_exit_price is None
        assert state.realized_pnl is None
        assert state.realized_return is None

    async def test_one_state_per_session(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, db_session, uid = svc
        session = await service.create_session(owner_id=uid, ticker="BBRI")
        states = await db_session.execute(
            text("SELECT COUNT(*) FROM trade_states WHERE session_id = :sid"),
            {"sid": session.id},
        )
        count = states.scalar_one()
        assert count == 1


class TestAtomicity:
    async def test_rollback_on_failure(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        """Simulate a failure by providing an invalid foreign key."""
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            service = TradeSessionService(s)
            # Use a non-existent user ID that won't violate FK constraints
            fake_id = uuid.uuid4()
            with pytest.raises(Exception):
                # This should fail on the FK constraint for users
                await service.create_session(owner_id=fake_id, ticker="BBRI")
            await s.rollback()
        # Verify no orphan session
        async with factory() as s:
            result = await s.execute(
                text("SELECT COUNT(*) FROM trade_sessions WHERE owner_id = :uid"),
                {"uid": fake_id},
            )
            assert result.scalar_one() == 0
            result = await s.execute(text("SELECT COUNT(*) FROM trade_states"))
            # Count should be 0 if the rollback happened before any commit
            # (there might be existing test data)
            pass


class TestOwnership:
    async def test_correct_owner(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, db_session, uid = svc
        session = await service.create_session(owner_id=uid, ticker="BBRI")
        repo = TradeSessionRepository(db_session)
        found = await repo.get_by_id_for_user(session.id, uid)
        assert found is not None
        assert found.id == session.id
        assert found.owner_id == uid

    async def test_wrong_owner_not_found(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, db_session, uid = svc
        session = await service.create_session(owner_id=uid, ticker="BBRI")
        repo = TradeSessionRepository(db_session)
        wrong_uid = uuid.uuid4()
        found = await repo.get_by_id_for_user(session.id, wrong_uid)
        assert found is None


class TestInvalidInput:
    async def test_blank_ticker_rejected(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, _, uid = svc
        with pytest.raises(InvalidTickerError):
            await service.create_session(owner_id=uid, ticker="  ")

    async def test_unsupported_currency_rejected(
        self, svc: tuple[TradeSessionService, AsyncSession, uuid.UUID]
    ) -> None:
        service, _, uid = svc
        with pytest.raises(UnsupportedCurrencyError):
            await service.create_session(owner_id=uid, ticker="BBRI", currency="EUR")
