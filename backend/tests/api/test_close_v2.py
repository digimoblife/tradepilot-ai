from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
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
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID | None, str]:
    if owner is None:
        user_id, email = uuid.uuid4(), f"p91-{uuid.uuid4()}@example.test"
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
                    entry_price=Decimal("1200.000000"),
                    entry_at=datetime(2026, 7, 29, 2, tzinfo=timezone.utc),
                    quantity=Decimal("10.000000"),
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
        # (1350 - 1200) * 10 = 1500
        assert Decimal(str(data["realized_profit_loss"])) == Decimal("1500.000000")
        assert data["position_status"] == "CLOSED"
        assert data["session_status"] == "CLOSED"

    # Verify DB state directly
    async_session = async_sessionmaker(engine, expire_on_commit=False)()
    async with async_session:
        # Check Closure
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
