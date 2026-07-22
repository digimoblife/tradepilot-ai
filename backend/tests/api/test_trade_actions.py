"""Tests for Trade Action API (TP-1005)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.routes.trade_actions import router as ta_router
from app.auth import hash_password

pytestmark = pytest.mark.database

NOW = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)


# ===================================================================
# Helpers
# ===================================================================


async def _ensure_user_sessions_table(engine: AsyncEngine) -> None:
    """Create user_sessions matching migration 4a2b6c8d0e1f."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS user_sessions ("
                "id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                "token_hash VARCHAR(64) NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), last_used_at TIMESTAMPTZ, "
                "revoked_at TIMESTAMPTZ)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_sessions_token_hash ON user_sessions(token_hash)"
            )
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id)")
        )


async def _make_user(
    engine: AsyncEngine,
    email: str | None = None,
    password: str = "testpass123",
) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    pw_hash = hash_password(password)
    unique_email = email or f"ta_{uid.hex[:8]}@test.com"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, account_status) "
                "VALUES (:id, :e, :ph, 'ACTIVE')"
            ),
            {"id": uid, "e": unique_email, "ph": pw_hash},
        )
    return uid, unique_email


async def _make_watching_session(engine: AsyncEngine, uid: uuid.UUID) -> uuid.UUID:
    sid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions (id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:id, :oid, 'BBRI', 'WATCHING', 'WATCHING')"
            ),
            {"id": sid, "oid": uid},
        )
        await conn.execute(
            text(
                "INSERT INTO trade_states (session_id, position_status, thesis_status, state_version) "
                "VALUES (:sid, 'NOT_OPENED', 'INTACT', 1)"
            ),
            {"sid": sid},
        )
    return sid


async def _make_open_session(engine: AsyncEngine, uid: uuid.UUID) -> uuid.UUID:
    sid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions (id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:id, :oid, 'BBRI', 'OPEN_POSITION', 'OPEN_POSITION')"
            ),
            {"id": sid, "oid": uid},
        )
        await conn.execute(
            text(
                "INSERT INTO trade_states (session_id, position_status, thesis_status, "
                "entry_price, original_quantity, remaining_quantity, "
                "active_stop_loss, active_target, state_version, entry_at) "
                "VALUES (:sid, 'OPEN', 'INTACT', "
                "2500, 100, 100, 2400, 2800, 1, :now)"
            ),
            {"sid": sid, "now": NOW},
        )
    return sid


async def _login_user(client: AsyncClient, email: str) -> str:
    resp = await client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": "testpass123",
        },
    )
    assert resp.status_code == 200
    return resp.cookies.get("tradepilot_session")


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


def _build_app(db_session: AsyncSession) -> FastAPI:
    app = FastAPI()
    from app.auth.errors import AUTHENTICATION_INACTIVE, AuthenticationError
    from app.database.session import get_db_session

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request, exc: AuthenticationError):
        from fastapi.responses import JSONResponse

        if exc.code == AUTHENTICATION_INACTIVE:
            return JSONResponse(
                status_code=403, content={"detail": "Account is not active", "code": exc.code}
            )
        return JSONResponse(
            status_code=401,
            content={"detail": exc.message or "Authentication failed", "code": exc.code},
        )

    app.include_router(auth_router)
    app.include_router(ta_router)

    async def _override() -> AsyncSession:
        return db_session

    app.dependency_overrides[get_db_session] = _override
    return app


@pytest.fixture
async def client(engine: AsyncEngine, db_session: AsyncSession) -> AsyncClient:
    app = _build_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ===================================================================
# Authentication
# ===================================================================


class TestAuth:
    """All 8 endpoints require auth; test a representative sample."""

    async def test_anonymous_open_position(self, engine: AsyncEngine, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/actions/open-position",
            json={
                "session_id": str(uuid.uuid4()),
                "idempotency_key": "k1",
                "entry_price": "2800",
                "quantity": "100",
                "executed_at": NOW.isoformat(),
            },
        )
        assert resp.status_code == 401

    async def test_anonymous_cancel(self, engine: AsyncEngine, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/actions/cancel",
            json={
                "session_id": str(uuid.uuid4()),
                "idempotency_key": "k1",
                "cancelled_at": NOW.isoformat(),
            },
        )
        assert resp.status_code == 401


# ===================================================================
# Open Position
# ===================================================================


class TestOpenPosition:
    async def test_valid_open(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_watching_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/open-position",
            json={
                "session_id": str(sid),
                "idempotency_key": "op1",
                "entry_price": "2800",
                "quantity": "100",
                "executed_at": NOW.isoformat(),
                "stop_loss": "2700",
                "target": "3000",
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"]["action_type"] == "POSITION_OPENED"
        assert data["session_status"] == "OPEN_POSITION"
        assert data["trade_state"]["position_status"] == "OPEN"
        assert "2800" in data["trade_state"]["entry_price"]
        assert "2700" in data["trade_state"]["active_stop_loss"]
        assert "3000" in data["trade_state"]["active_target"]

    async def test_idempotency(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_watching_session(engine, uid)
        cookie = await _login_user(client, email)
        body = {
            "session_id": str(sid),
            "idempotency_key": "op_idem",
            "entry_price": "2800",
            "quantity": "100",
            "executed_at": NOW.isoformat(),
        }
        r1 = await client.post(
            "/api/actions/open-position", json=body, cookies={"tradepilot_session": cookie}
        )
        assert r1.status_code == 200
        r2 = await client.post(
            "/api/actions/open-position", json=body, cookies={"tradepilot_session": cookie}
        )
        assert r2.status_code == 200
        assert r1.json()["action"]["id"] == r2.json()["action"]["id"]

    async def test_cross_user_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_watching_session(engine, uid1)
        cookie = await _login_user(client, email2)
        resp = await client.post(
            "/api/actions/open-position",
            json={
                "session_id": str(sid),
                "idempotency_key": "op_cross",
                "entry_price": "2800",
                "quantity": "100",
                "executed_at": NOW.isoformat(),
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404


# ===================================================================
# Stop Loss
# ===================================================================


class TestStop:
    async def test_confirm_stop(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_open_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/confirm-stop",
            json={
                "session_id": str(sid),
                "idempotency_key": "st1",
                "stop_loss": "2350",
                "confirmed_at": NOW.isoformat(),
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert "2350" in resp.json()["trade_state"]["active_stop_loss"]

    async def test_change_stop(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_open_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/change-stop",
            json={
                "session_id": str(sid),
                "idempotency_key": "st_chg",
                "stop_loss": "2300",
                "confirmed_at": NOW.isoformat(),
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert "2300" in resp.json()["trade_state"]["active_stop_loss"]


# ===================================================================
# Target
# ===================================================================


class TestTarget:
    async def test_confirm_target(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_open_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/confirm-target",
            json={
                "session_id": str(sid),
                "idempotency_key": "tg1",
                "target": "2900",
                "confirmed_at": NOW.isoformat(),
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert "2900" in resp.json()["trade_state"]["active_target"]


# ===================================================================
# Partial Exit
# ===================================================================


class TestPartialExit:
    async def test_valid_partial(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_open_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/partial-exit",
            json={
                "session_id": str(sid),
                "idempotency_key": "pe1",
                "exit_price": "2900",
                "exit_quantity": "40",
                "executed_at": NOW.isoformat(),
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "60" in data["trade_state"]["remaining_quantity"]
        assert data["session_status"] == "PARTIALLY_CLOSED"


# ===================================================================
# Full Exit
# ===================================================================


class TestFullExit:
    async def test_valid_full(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_open_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/full-exit",
            json={
                "session_id": str(sid),
                "idempotency_key": "fe1",
                "exit_price": "3000",
                "exit_quantity": "100",
                "executed_at": NOW.isoformat(),
                "closing_reason": "TAKE_PROFIT",
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        remaining = data["trade_state"]["remaining_quantity"]
        assert remaining is None or "0" in str(remaining)
        assert data["session_status"] == "CLOSED_TAKE_PROFIT"


# ===================================================================
# Cancel
# ===================================================================


class TestCancel:
    async def test_valid_cancel(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_watching_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/cancel",
            json={
                "session_id": str(sid),
                "idempotency_key": "ca1",
                "cancelled_at": NOW.isoformat(),
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["session_status"] == "CANCELLED"

    async def test_open_position_cancel_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_open_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/cancel",
            json={
                "session_id": str(sid),
                "idempotency_key": "ca_bad",
                "cancelled_at": NOW.isoformat(),
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422


# ===================================================================
# Invalid lifecycle
# ===================================================================


class TestInvalidLifecycle:
    async def test_open_from_open_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_open_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/open-position",
            json={
                "session_id": str(sid),
                "idempotency_key": "op_bad",
                "entry_price": "3000",
                "quantity": "50",
                "executed_at": NOW.isoformat(),
            },
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422


# ===================================================================
# Response safety
# ===================================================================


class TestResponseSafety:
    async def test_no_password_hash(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_watching_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/actions/open-position",
            json={
                "session_id": str(sid),
                "idempotency_key": "op_safe",
                "entry_price": "2800",
                "quantity": "100",
                "executed_at": NOW.isoformat(),
            },
            cookies={"tradepilot_session": cookie},
        )
        body = resp.text
        assert "password_hash" not in body
        assert "raw_output" not in body
        assert "lease_owner" not in body
