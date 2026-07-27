"""API tests for P6 Same-Ticker History endpoint.

Verifies cross-user rejection (HTTP 404), owner authorization,
and HTTP response structure.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.main import app

pytestmark = pytest.mark.database


async def _make_user(engine: AsyncEngine) -> tuple[uuid.UUID, str]:
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                "INSERT INTO users (email, password_hash) "
                "VALUES (:e, 'hash') RETURNING id"
            ),
            {"e": email},
        )
        return res.scalar_one(), email


async def _make_session(
    engine: AsyncEngine,
    owner_id: uuid.UUID,
    ticker: str,
    status: str = "CLOSED",
) -> uuid.UUID:
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status, created_at, updated_at) "
                "VALUES (:sid, :uid, :tk, :st, :st, :now, :now)"
            ),
            {"sid": session_id, "uid": owner_id, "tk": ticker, "st": status, "now": now},
        )
        await conn.execute(
            text(
                "INSERT INTO trade_states (session_id, position_status, entry_price, average_exit_price, realized_return) "
                "VALUES (:sid, :pst, 5000, 5500, 10.0)"
            ),
            {
                "sid": session_id,
                "pst": "CLOSED" if status.startswith("CLOSED") else "NOT_OPENED",
            },
        )
    return session_id


class TestSameTickerHistoryAPI:
    async def test_api_cross_user_isolation(self, engine: AsyncEngine) -> None:
        user1_id, email1 = await _make_user(engine)
        user2_id, email2 = await _make_user(engine)

        s_user1 = await _make_session(engine, user1_id, "BBRI", "DRAFT")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            from app.api.dependencies import get_current_user
            from app.auth import AuthenticatedUser
            from app.database.session import get_db_session

            async def _override_db():
                factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                async with factory() as session:
                    yield session

            def _override_user2():
                return AuthenticatedUser(id=user2_id, email=email2)

            app.dependency_overrides[get_db_session] = _override_db
            app.dependency_overrides[get_current_user] = _override_user2
            try:
                # User 2 tries to access User 1's session history
                res = await client.get(f"/api/trade-sessions/{s_user1}/same-ticker-history")
                assert res.status_code == 404
            finally:
                app.dependency_overrides.pop(get_current_user, None)
                app.dependency_overrides.pop(get_db_session, None)

    async def test_api_returns_same_ticker_history_summary(self, engine: AsyncEngine) -> None:
        user_id, email = await _make_user(engine)

        _prior1 = await _make_session(engine, user_id, "BBRI", "CLOSED")
        curr = await _make_session(engine, user_id, "BBRI", "DRAFT")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            from app.api.dependencies import get_current_user
            from app.auth import AuthenticatedUser
            from app.database.session import get_db_session

            async def _override_db():
                factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                async with factory() as session:
                    yield session

            def _override_owner():
                return AuthenticatedUser(id=user_id, email=email)

            app.dependency_overrides[get_db_session] = _override_db
            app.dependency_overrides[get_current_user] = _override_owner
            try:
                res = await client.get(f"/api/trade-sessions/{curr}/same-ticker-history")
                assert res.status_code == 200
                data = res.json()
                assert data["session_id"] == str(curr)
                assert data["ticker"] == "BBRI"
                assert data["historical_context_used"] is True
                assert data["historical_session_count"] == 1
                assert len(data["recent_outcomes"]) == 1
            finally:
                app.dependency_overrides.pop(get_current_user, None)
                app.dependency_overrides.pop(get_db_session, None)
