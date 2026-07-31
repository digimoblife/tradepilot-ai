from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.queue.analysis_request_queue import AnalysisRequestQueue

pytestmark = pytest.mark.database

CLOSE_TIMESTAMP = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)


class RecordingTransport:
    async def publish(self, payload: bytes) -> None:
        pass


async def _seed_user_and_session(
    engine: AsyncEngine,
    *,
    status: TradeSessionV2Status = TradeSessionV2Status.OPEN_POSITION,
    position_status: PositionV2Status | None = PositionV2Status.OPEN,
    owner: tuple[uuid.UUID, str] | None = None,
    entry_price: Decimal = Decimal("1200.000000"),
    quantity: Decimal = Decimal("10.000000"),
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID | None, str]:
    if owner is None:
        user_id, email = uuid.uuid4(), f"p92-{uuid.uuid4()}@example.test"
        create_user = True
    else:
        user_id, email = owner
        create_user = False
    session_id = uuid.uuid4()
    position_id = uuid.uuid4() if position_status is not None else None
    async with engine.begin() as connection:
        if create_user:
            await connection.execute(
                User.__table__.insert().values(
                    id=user_id, email=email, password_hash=hash_password("testpass123")
                )
            )
        await connection.execute(
            TradeSessionV2.__table__.insert().values(
                id=session_id,
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                status=status,
            )
        )
        if position_id is not None:
            await connection.execute(
                PositionV2.__table__.insert().values(
                    id=position_id,
                    session_id=session_id,
                    entry_price=entry_price,
                    entry_at=datetime(2026, 7, 29, 2, tzinfo=timezone.utc),
                    quantity=quantity,
                    stop_loss=Decimal("1100.000000"),
                    target_price=Decimal("1400.000000"),
                    note="Open position note",
                    status=position_status,
                )
            )
    return user_id, session_id, position_id, email


def _build_app(engine: AsyncEngine) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)
    app.state.rebuild_analysis_queue = AnalysisRequestQueue(RecordingTransport())

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_db() -> AsyncSession:
        async with session_maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db_session] = _override_db
    return app


async def _login(client: AsyncClient, email: str) -> None:
    res = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_close_api_success(engine: AsyncEngine) -> None:
    user_id, session_id, position_id, email = await _seed_user_and_session(engine)
    app = _build_app(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)

        payload = {
            "close_price": "1350.000000",
            "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
            "close_reason": "Target price reached",
            "note": "Took profit",
        }
        res = await client.post(f"/api/v2/trade-sessions/{session_id}/close", json=payload)
        assert res.status_code == 201
        data = res.json()

        assert data["session_id"] == str(session_id)
        assert data["position_id"] == str(position_id)
        assert Decimal(str(data["close_price"])) == Decimal("1350.000000")
        assert data["close_reason"] == "Target price reached"
        assert data["note"] == "Took profit"
        # Price diff = +150; (1350 - 1200) * 10 = 1500
        assert Decimal(str(data["realized_profit_loss"])) == Decimal("1500.000000")
        assert data["position_status"] == "CLOSED"
        assert data["session_status"] == "CLOSED"

    # Verify DB state directly
    async_session = async_sessionmaker(engine, expire_on_commit=False)()
    async with async_session:
        # Check Closure count and exact values
        closure_count = await async_session.scalar(
            select(func.count(TradeClosureV2.id)).where(TradeClosureV2.session_id == session_id)
        )
        assert closure_count == 1

        closure = await async_session.scalar(
            select(TradeClosureV2).where(TradeClosureV2.session_id == session_id)
        )
        assert closure is not None
        assert closure.position_id == position_id
        assert closure.close_price == Decimal("1350.000000")
        assert closure.close_reason == "Target price reached"
        assert closure.realized_profit_loss == Decimal("1500.000000")

        # Check Position (facts preserved, status closed)
        pos = await async_session.scalar(
            select(PositionV2).where(PositionV2.id == position_id)
        )
        assert pos is not None
        assert pos.status == PositionV2Status.CLOSED
        assert pos.entry_price == Decimal("1200.000000")
        assert pos.quantity == Decimal("10.000000")
        assert pos.stop_loss == Decimal("1100.000000")
        assert pos.target_price == Decimal("1400.000000")

        # Check Session
        session_row = await async_session.scalar(
            select(TradeSessionV2).where(TradeSessionV2.id == session_id)
        )
        assert session_row is not None
        assert session_row.status == TradeSessionV2Status.CLOSED
        assert session_row.closed_at is not None


@pytest.mark.asyncio
async def test_close_realized_calculations(engine: AsyncEngine) -> None:
    # 1. Losing close: entry 1200, close 1050, qty 10 -> diff -150 -> PnL = -1500.00
    user_id, s_losing, p_losing, email_losing = await _seed_user_and_session(engine)
    # 2. Break-even close: entry 1200, close 1200, qty 10 -> diff 0 -> PnL = 0.00
    user_id, s_even, p_even, email_even = await _seed_user_and_session(engine, owner=(user_id, email_losing))
    # 3. Fractional decimal: entry 123.456000, close 150.000000, qty 12.500000 -> PnL = 331.800000
    user_id, s_frac, p_frac, email_frac = await _seed_user_and_session(
        engine,
        owner=(user_id, email_losing),
        entry_price=Decimal("123.456000"),
        quantity=Decimal("12.500000"),
    )

    app = _build_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email_losing)

        # Losing Close
        res_l = await client.post(
            f"/api/v2/trade-sessions/{s_losing}/close",
            json={
                "close_price": "1050.000000",
                "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
                "close_reason": "Stop loss hit",
            },
        )
        assert res_l.status_code == 201
        assert Decimal(str(res_l.json()["realized_profit_loss"])) == Decimal("-1500.000000")

        # Break-even Close
        res_e = await client.post(
            f"/api/v2/trade-sessions/{s_even}/close",
            json={
                "close_price": "1200.000000",
                "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
                "close_reason": "Exit at cost",
            },
        )
        assert res_e.status_code == 201
        assert Decimal(str(res_e.json()["realized_profit_loss"])) == Decimal("0.000000")

        # Fractional Decimal Close
        res_f = await client.post(
            f"/api/v2/trade-sessions/{s_frac}/close",
            json={
                "close_price": "150.000000",
                "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
                "close_reason": "Partial target reached",
            },
        )
        assert res_f.status_code == 201
        # (150.000000 - 123.456000) * 12.500000 = 26.544000 * 12.500000 = 331.800000
        assert Decimal(str(res_f.json()["realized_profit_loss"])) == Decimal("331.800000")


@pytest.mark.asyncio
async def test_close_timezone_and_fact_preservation(engine: AsyncEngine) -> None:
    user_id, session_id, position_id, email = await _seed_user_and_session(engine)
    app = _build_app(engine)

    # Timezone with +07:00 offset (2026-07-31T17:00:00+07:00 == 2026-07-31T10:00:00Z)
    offset_time_str = "2026-07-31T17:00:00+07:00"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)

        res = await client.post(
            f"/api/v2/trade-sessions/{session_id}/close",
            json={
                "close_price": "1300.00",
                "close_timestamp": offset_time_str,
                "close_reason": "Timezone test",
            },
        )
        assert res.status_code == 201

    async_session = async_sessionmaker(engine, expire_on_commit=False)()
    async with async_session:
        closure = await async_session.scalar(
            select(TradeClosureV2).where(TradeClosureV2.session_id == session_id)
        )
        assert closure is not None
        # Check UTC instant is preserved
        expected_utc = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
        assert closure.close_at == expected_utc

        # Check Position entry facts untouched
        pos = await async_session.scalar(
            select(PositionV2).where(PositionV2.id == position_id)
        )
        assert pos is not None
        assert pos.entry_price == Decimal("1200.000000")
        assert pos.entry_at == datetime(2026, 7, 29, 2, tzinfo=timezone.utc)
        assert pos.quantity == Decimal("10.000000")
        assert pos.stop_loss == Decimal("1100.000000")
        assert pos.target_price == Decimal("1400.000000")
        assert pos.note == "Open position note"
        assert pos.status == PositionV2Status.CLOSED
        assert pos.closed_at == expected_utc


@pytest.mark.asyncio
async def test_close_api_rejections_and_atomicity(engine: AsyncEngine) -> None:
    user_id, session_id, position_id, email = await _seed_user_and_session(engine)
    other_user_id, other_session_id, _, other_email = await _seed_user_and_session(engine)
    app = _build_app(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)

        # 1. Non-existent session -> 404
        res = await client.post(
            f"/api/v2/trade-sessions/{uuid.uuid4()}/close",
            json={
                "close_price": "1300.00",
                "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
                "close_reason": "Close test",
            },
        )
        assert res.status_code == 404

        # 2. Other user's session -> 404
        res = await client.post(
            f"/api/v2/trade-sessions/{other_session_id}/close",
            json={
                "close_price": "1300.00",
                "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
                "close_reason": "Close test",
            },
        )
        assert res.status_code == 404

        # 3. Invalid close price <= 0 -> 422
        res = await client.post(
            f"/api/v2/trade-sessions/{session_id}/close",
            json={
                "close_price": "-100.00",
                "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
                "close_reason": "Close test",
            },
        )
        assert res.status_code == 422

        # 4. Blank close reason -> 422
        res = await client.post(
            f"/api/v2/trade-sessions/{session_id}/close",
            json={
                "close_price": "1300.00",
                "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
                "close_reason": "   ",
            },
        )
        assert res.status_code == 422

        # 5. Successful CLOSE
        res = await client.post(
            f"/api/v2/trade-sessions/{session_id}/close",
            json={
                "close_price": "1350.00",
                "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
                "close_reason": "Close test",
            },
        )
        assert res.status_code == 201

        # 6. Duplicate CLOSE -> 409
        res_dup = await client.post(
            f"/api/v2/trade-sessions/{session_id}/close",
            json={
                "close_price": "1350.00",
                "close_timestamp": CLOSE_TIMESTAMP.isoformat(),
                "close_reason": "Close again",
            },
        )
        assert res_dup.status_code == 409

        # 7. Submitting Position Update to closed session -> 409
        res_post_upd = await client.post(
            f"/api/v2/trade-sessions/{session_id}/position-updates"
        )
        assert res_post_upd.status_code == 409

        # 8. History remains readable -> 200
        res_read = await client.get(
            f"/api/v2/trade-sessions/{session_id}/position-updates"
        )
        assert res_read.status_code == 200
