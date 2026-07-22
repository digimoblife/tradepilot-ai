"""Tests for Context Summary and Timeline API (TP-1006)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.routes.context import router as context_router
from app.api.routes.timeline import router as timeline_router
from app.auth import hash_password

pytestmark = pytest.mark.database


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
    unique_email = email or f"ct_{uid.hex[:8]}@test.com"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, account_status) "
                "VALUES (:id, :e, :ph, 'ACTIVE')"
            ),
            {"id": uid, "e": unique_email, "ph": pw_hash},
        )
    return uid, unique_email


async def _make_session(engine: AsyncEngine, uid: uuid.UUID) -> uuid.UUID:
    sid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions (id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:id, :oid, 'BBRI', 'WATCHING', 'WATCHING')"
            ),
            {"id": sid, "oid": uid},
        )
    return sid


async def _make_context_summary(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    *,
    version: int = 1,
    stale: bool = False,
) -> uuid.UUID:
    cid = uuid.uuid4()
    payload = '{"executive_summary": "test", "context_version": "1.0.0"}'
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO context_summaries (id, session_id, context_version, payload, is_stale) "
                "VALUES (:cid, :sid, :v, :pl, :stale)"
            ),
            {"cid": cid, "sid": session_id, "v": version, "pl": payload, "stale": stale},
        )
    return cid


async def _make_session_event(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    event_type: str,
    occurred_at: datetime,
    summary: str | None = None,
) -> uuid.UUID:
    eid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO session_events (id, session_id, event_type, occurred_at, compact_summary) "
                "VALUES (:eid, :sid, :et, :oa, :summary)"
            ),
            {
                "eid": eid,
                "sid": session_id,
                "et": event_type,
                "oa": occurred_at,
                "summary": summary,
            },
        )
    return eid


async def _make_trade_action(
    engine: AsyncEngine,
    session_id: uuid.UUID,
) -> uuid.UUID:
    aid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_actions (id, session_id, action_type, confirmed_at, idempotency_key, "
                "price, quantity) "
                "VALUES (:aid, :sid, 'POSITION_OPENED', :now, :ik, 2500, 100)"
            ),
            {"aid": aid, "sid": session_id, "now": now, "ik": f"ct_{uuid.uuid4().hex}"},
        )
    return aid


async def _make_accepted_analysis(engine: AsyncEngine, session_id: uuid.UUID) -> uuid.UUID:
    aid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO analyses (id, session_id, analysis_type, acceptance_status, "
                "prompt_name, prompt_version, schema_name, schema_version, payload, accepted_at, created_at) "
                "VALUES (:aid, :sid, 'WATCHING_UPDATE', 'ACCEPTED', "
                "'test', '1.0.0', 'test', '1.0.0', "
                "'{}'::jsonb, :now, :now)"
            ),
            {"aid": aid, "sid": session_id, "now": now},
        )
    return aid


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
    app.include_router(context_router)
    app.include_router(timeline_router)

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
    async def test_anonymous_context_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.get(f"/api/trade-sessions/{uuid.uuid4()}/context")
        assert resp.status_code == 401

    async def test_anonymous_timeline_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.get(f"/api/trade-sessions/{uuid.uuid4()}/timeline")
        assert resp.status_code == 401

    async def test_cross_user_context_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid1)
        await _make_context_summary(engine, sid)
        cookie = await _login_user(client, email2)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/context",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404

    async def test_cross_user_timeline_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid1)
        cookie = await _login_user(client, email2)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/timeline",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404


# ===================================================================
# Context summary
# ===================================================================


class TestContext:
    async def test_latest_context_retrieved(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cid = await _make_context_summary(engine, sid, version=1)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/context",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(cid)
        assert data["context_version"] == 1
        assert data["is_stale"] is False

    async def test_latest_version_only(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        await _make_context_summary(engine, sid, version=1)
        cid2 = await _make_context_summary(engine, sid, version=2)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/context",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.json()["id"] == str(cid2)
        assert resp.json()["context_version"] == 2

    async def test_payload_unchanged(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        await _make_context_summary(engine, sid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/context",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.json()["payload"]["executive_summary"] == "test"

    async def test_missing_context_404(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/context",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404

    async def test_stale_flag_retained(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        await _make_context_summary(engine, sid, version=1, stale=True)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/context",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.json()["is_stale"] is True


# ===================================================================
# Timeline
# ===================================================================


class TestTimeline:
    async def test_chronological_order(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        t1 = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)
        e1 = await _make_session_event(engine, sid, "SESSION_CREATED", t1)
        e2 = await _make_session_event(engine, sid, "EVIDENCE_UPLOADED", t2)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/timeline",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["events"][0]["id"] == str(e1)
        assert data["events"][1]["id"] == str(e2)

    async def test_empty_timeline(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/timeline",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_related_action_included(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        action_id = await _make_trade_action(engine, sid)
        now = datetime.now(timezone.utc)
        eid = uuid.uuid4()
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO session_events (id, session_id, event_type, occurred_at, related_action_id) "
                    "VALUES (:eid, :sid, 'POSITION_OPENED', :now, :aid)"
                ),
                {"eid": eid, "sid": sid, "now": now, "aid": action_id},
            )
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/timeline",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        ev = resp.json()["events"][0]
        assert ev["related_action"] is not None
        assert ev["related_action"]["action_type"] == "POSITION_OPENED"

    async def test_related_analysis_included(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        analysis_id = await _make_accepted_analysis(engine, sid)
        now = datetime.now(timezone.utc)
        eid = uuid.uuid4()
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO session_events (id, session_id, event_type, occurred_at, related_analysis_id) "
                    "VALUES (:eid, :sid, 'ANALYSIS_ACCEPTED', :now, :aid)"
                ),
                {"eid": eid, "sid": sid, "now": now, "aid": analysis_id},
            )
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/timeline",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        ev = resp.json()["events"][0]
        assert ev["related_analysis"] is not None
        assert ev["related_analysis"]["analysis_type"] == "WATCHING_UPDATE"
