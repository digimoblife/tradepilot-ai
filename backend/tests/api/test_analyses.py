"""Tests for Analysis API (TP-1004)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.routes.analyses import analysis_router
from app.api.routes.analyses import session_router as analysis_session_router
from app.api.routes.analysis_jobs import router as analysis_jobs_router
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
                "id UUID PRIMARY KEY, "
                "user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                "token_hash VARCHAR(64) NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), last_used_at TIMESTAMPTZ, "
                "revoked_at TIMESTAMPTZ)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_sessions_token_hash "
                "ON user_sessions(token_hash)"
            )
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id)")
        )


async def _make_user(
    engine: AsyncEngine,
    email: str | None = None,
    password: str = "testpass123",
    account_status: str = "ACTIVE",
) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    pw_hash = hash_password(password)
    unique_email = email or f"an_{uid.hex[:8]}@test.com"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, account_status) "
                "VALUES (:id, :e, :ph, :st)"
            ),
            {"id": uid, "e": unique_email, "ph": pw_hash, "st": account_status},
        )
    return uid, unique_email


async def _make_ready_session(engine: AsyncEngine, uid: uuid.UUID) -> uuid.UUID:
    sid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:id, :oid, 'BBRI', 'READY_FOR_ANALYSIS', 'READY_FOR_ANALYSIS')"
            ),
            {"id": sid, "oid": uid},
        )
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status, state_version) "
                "VALUES (:sid, 'NOT_OPENED', 'INTACT', 1)"
            ),
            {"sid": sid},
        )
        # Add required evidence for INITIAL_ANALYSIS
        for etype in ("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"):
            await conn.execute(
                text(
                    "INSERT INTO evidence "
                    "(id, session_id, owner_id, evidence_type, evidence_status, "
                    "storage_object_key, mime_type, file_size_bytes) "
                    "VALUES (:eid, :sid, :oid, :et, 'AVAILABLE', :key, 'image/png', 100)"
                ),
                {
                    "eid": uuid.uuid4(),
                    "sid": sid,
                    "oid": uid,
                    "et": etype,
                    "key": f"test/{etype.lower()}.png",
                },
            )
    return sid


async def _make_accepted_analysis(
    engine: AsyncEngine,
    session_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
    aid = uuid.uuid4()
    jid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                "attempt_count, max_attempts, requested_at, available_at) "
                "VALUES (:jid, :sid, 'WATCHING_UPDATE', 'COMPLETED', 1, 3, :now, :now)"
            ),
            {"jid": jid, "sid": session_id, "now": now},
        )
        await conn.execute(
            text(
                "INSERT INTO analyses (id, session_id, analysis_job_id, analysis_type, "
                "acceptance_status, prompt_name, prompt_version, schema_name, schema_version, "
                "payload, accepted_at, created_at) "
                "VALUES (:aid, :sid, :jid, 'WATCHING_UPDATE', 'ACCEPTED', "
                "'test', '1.0.0', 'test', '1.0.0', "
                '\'{"executive_summary": "test summary"}\'::jsonb, :now, :now)'
            ),
            {"aid": aid, "sid": session_id, "jid": jid, "now": now},
        )
    return aid, jid


async def _login_user(client: AsyncClient, email: str, password: str = "testpass123") -> str:
    resp = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    cookie = resp.cookies.get("tradepilot_session")
    assert cookie is not None
    return cookie


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
    app.include_router(analysis_session_router)
    app.include_router(analysis_router)
    app.include_router(analysis_jobs_router)

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
    async def test_anonymous_create_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.post(
            f"/api/trade-sessions/{uuid.uuid4()}/analyses",
            json={"analysis_type": "INITIAL_ANALYSIS"},
        )
        assert resp.status_code == 401

    async def test_anonymous_list_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        resp = await client.get(f"/api/trade-sessions/{uuid.uuid4()}/analyses")
        assert resp.status_code == 401

    async def test_anonymous_detail_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.get(f"/api/analyses/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_anonymous_job_status_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.get(f"/api/analysis-jobs/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_anonymous_retry_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.post(f"/api/analysis-jobs/{uuid.uuid4()}/retry")
        assert resp.status_code == 401


# ===================================================================
# Job creation
# ===================================================================


class TestCreate:
    async def test_valid_create_returns_immediately(
        self, engine: AsyncEngine, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/analyses",
            json={"analysis_type": "INITIAL_ANALYSIS"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "QUEUED"
        assert data["analysis_type"] == "INITIAL_ANALYSIS"
        await db_session.commit()

        async with engine.begin() as conn:
            context_count = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM context_summaries "
                        "WHERE session_id = :sid AND is_stale = false"
                    ),
                    {"sid": sid},
                )
            ).scalar_one()
        assert context_count >= 1

    async def test_request_rebuilds_stale_context_before_queueing(
        self, engine: AsyncEngine, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        old_cutoff = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO context_summaries "
                    "(session_id, context_version, source_cutoff, payload, is_stale) "
                    "VALUES (:sid, 1, :cutoff, '{}', true)"
                ),
                {"sid": sid, "cutoff": old_cutoff},
            )

        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/analyses",
            json={"analysis_type": "INITIAL_ANALYSIS"},
            cookies={"tradepilot_session": cookie},
        )

        assert resp.status_code == 202
        await db_session.commit()
        async with engine.begin() as conn:
            fresh_count = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM context_summaries "
                        "WHERE session_id = :sid AND is_stale = false "
                        "AND source_cutoff > :cutoff"
                    ),
                    {"sid": sid, "cutoff": old_cutoff},
                )
            ).scalar_one()
        assert fresh_count >= 1

    async def test_duplicate_active_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        cookie = await _login_user(client, email)
        resp1 = await client.post(
            f"/api/trade-sessions/{sid}/analyses",
            json={"analysis_type": "INITIAL_ANALYSIS"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp1.status_code == 202
        resp2 = await client.post(
            f"/api/trade-sessions/{sid}/analyses",
            json={"analysis_type": "INITIAL_ANALYSIS"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp2.status_code == 409

    async def test_cross_user_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid1)
        cookie = await _login_user(client, email2)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/analyses",
            json={"analysis_type": "INITIAL_ANALYSIS"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404


# ===================================================================
# Analysis listing
# ===================================================================


class TestList:
    async def test_accepted_analysis_returned(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        await _make_accepted_analysis(engine, sid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/analyses",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_empty_list(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/analyses",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_rejected_analysis_excluded(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        now = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO analyses (id, session_id, analysis_type, acceptance_status, "
                    "prompt_name, prompt_version, schema_name, schema_version, created_at) "
                    "VALUES (:aid, :sid, 'WATCHING_UPDATE', 'REJECTED', "
                    "'test', '1.0.0', 'test', '1.0.0', :now)"
                ),
                {"aid": uuid.uuid4(), "sid": sid, "now": now},
            )
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/analyses",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.json()["total"] == 0


# ===================================================================
# Analysis detail
# ===================================================================


class TestDetail:
    async def test_accepted_payload_returned(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        aid, _ = await _make_accepted_analysis(engine, sid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/analyses/{aid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["payload"]["executive_summary"] == "test summary"
        assert data["acceptance_status"] == "ACCEPTED"

    async def test_cross_user_404(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid1)
        aid, _ = await _make_accepted_analysis(engine, sid)
        cookie = await _login_user(client, email2)
        resp = await client.get(
            f"/api/analyses/{aid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404


# ===================================================================
# Job status
# ===================================================================


class TestJobStatus:
    async def test_job_status_retrieved(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        aid, jid = await _make_accepted_analysis(engine, sid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/analysis-jobs/{jid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert data["analysis_id"] == str(aid)

    async def test_cross_user_404(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid1)
        _, jid = await _make_accepted_analysis(engine, sid)
        cookie = await _login_user(client, email2)
        resp = await client.get(
            f"/api/analysis-jobs/{jid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404

    async def test_status_terminalizes_expired_exhausted_processing(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        jid = uuid.uuid4()
        past = datetime.now(timezone.utc).replace(microsecond=0)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, lease_owner, lease_expires_at, "
                    "requested_at, available_at) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'PROCESSING', "
                    "3, 3, 'old-worker', :past, :past, :past)"
                ),
                {"jid": jid, "sid": sid, "past": past},
            )

        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/analysis-jobs/{jid}",
            cookies={"tradepilot_session": cookie},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "FAILED"
        assert data["last_error_code"] == "JOB_ATTEMPTS_EXHAUSTED"


# ===================================================================
# Retry
# ===================================================================


class TestRetry:
    async def test_failed_job_retried(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        jid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, requested_at, available_at) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'FAILED', 1, 3, :now, :now)"
                ),
                {"jid": jid, "sid": sid, "now": now},
            )
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/analysis-jobs/{jid}/retry",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "QUEUED"
        assert data["attempt_count"] == 0

    async def test_exhausted_failed_job_retried(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        jid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, requested_at, available_at, completed_at, "
                    "last_error_code) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'FAILED', "
                    "3, 3, :now, :now, :now, 'JOB_ATTEMPTS_EXHAUSTED')"
                ),
                {"jid": jid, "sid": sid, "now": now},
            )

        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/analysis-jobs/{jid}/retry",
            cookies={"tradepilot_session": cookie},
        )

        assert resp.status_code == 202
        data = resp.json()
        assert data["job_id"] == str(jid)
        assert data["status"] == "QUEUED"
        assert data["attempt_count"] == 0

    async def test_completed_retry_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        _, jid = await _make_accepted_analysis(engine, sid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/analysis-jobs/{jid}/retry",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422

    async def test_cross_user_404(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid1)
        jid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, requested_at, available_at) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'FAILED', 1, 3, :now, :now)"
                ),
                {"jid": jid, "sid": sid, "now": now},
            )
        cookie = await _login_user(client, email2)
        resp = await client.post(
            f"/api/analysis-jobs/{jid}/retry",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404

    async def test_retry_is_idempotent_after_requeue(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        jid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, requested_at, available_at) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'FAILED', 3, 3, :now, :now)"
                ),
                {"jid": jid, "sid": sid, "now": now},
            )

        cookie = await _login_user(client, email)
        first = await client.post(
            f"/api/analysis-jobs/{jid}/retry",
            cookies={"tradepilot_session": cookie},
        )
        second = await client.post(
            f"/api/analysis-jobs/{jid}/retry",
            cookies={"tradepilot_session": cookie},
        )

        assert first.status_code == 202
        assert second.status_code == 202
        assert second.json()["job_id"] == str(jid)
        assert second.json()["status"] == "QUEUED"

        async with engine.begin() as conn:
            count = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM analysis_jobs "
                        "WHERE session_id = :sid AND analysis_type = 'INITIAL_ANALYSIS'"
                    ),
                    {"sid": sid},
                )
            ).scalar_one()

        assert count == 1

    async def test_retry_prevents_duplicate_active_jobs(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        failed_jid = uuid.uuid4()
        active_jid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, requested_at, available_at) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'FAILED', 3, 3, :now, :now)"
                ),
                {"jid": failed_jid, "sid": sid, "now": now},
            )
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, requested_at, available_at) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'QUEUED', 0, 3, :now, :now)"
                ),
                {"jid": active_jid, "sid": sid, "now": now},
            )

        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/analysis-jobs/{failed_jid}/retry",
            cookies={"tradepilot_session": cookie},
        )

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "ANALYSIS_JOB_ALREADY_ACTIVE"

    async def test_retry_terminalizes_expired_exhausted_processing_first(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_ready_session(engine, uid)
        jid = uuid.uuid4()
        past = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, lease_owner, lease_expires_at, "
                    "requested_at, available_at) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'PROCESSING', "
                    "3, 3, 'old-worker', :past, :past, :past)"
                ),
                {"jid": jid, "sid": sid, "past": past},
            )

        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/analysis-jobs/{jid}/retry",
            cookies={"tradepilot_session": cookie},
        )

        assert resp.status_code == 202
        assert resp.json()["status"] == "QUEUED"
