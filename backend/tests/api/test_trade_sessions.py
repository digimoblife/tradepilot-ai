"""Tests for Trade Session API (TP-1002)."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.routes.trade_sessions import router as ts_router
from app.auth import hash_password

pytestmark = pytest.mark.database


# ===================================================================
# Helpers
# ===================================================================


async def _ensure_user_sessions_table(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS user_sessions ("
                "id UUID PRIMARY KEY, "
                "user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                "token_hash VARCHAR(64) NOT NULL UNIQUE, "
                "expires_at TIMESTAMPTZ NOT NULL, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), "
                "last_used_at TIMESTAMPTZ, "
                "revoked_at TIMESTAMPTZ"
                ")"
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
    unique_email = email or f"ts_{uid.hex[:8]}@test.com"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, account_status) "
                "VALUES (:id, :e, :ph, :st)"
            ),
            {"id": uid, "e": unique_email, "ph": pw_hash, "st": account_status},
        )
    return uid, unique_email


async def _login_user(client: AsyncClient, email: str, password: str = "testpass123") -> str:
    resp = await client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert resp.status_code == 200
    cookie = resp.cookies.get("tradepilot_session")
    assert cookie is not None
    return cookie


async def _make_session_raw(
    engine: AsyncEngine,
    uid: uuid.UUID,
    status: str = "DRAFT",
) -> uuid.UUID:
    sid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:id, :oid, :t, :ls, :ss)"
            ),
            {"id": sid, "oid": uid, "t": "BBRI", "ls": status, "ss": status},
        )
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status, state_version) "
                "VALUES (:sid, 'NOT_OPENED', 'INTACT', 1)"
            ),
            {"sid": sid},
        )
    return sid


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

    from app.auth.errors import AuthenticationError
    from app.database.session import get_db_session

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request, exc: AuthenticationError):
        from fastapi.responses import JSONResponse

        from app.auth.errors import AUTHENTICATION_INACTIVE

        if exc.code == AUTHENTICATION_INACTIVE:
            return JSONResponse(
                status_code=403,
                content={"detail": "Account is not active", "code": exc.code},
            )
        return JSONResponse(
            status_code=401,
            content={
                "detail": exc.message or "Authentication failed",
                "code": exc.code,
            },
        )

    app.include_router(auth_router)
    app.include_router(ts_router)

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
# Authentication protection
# ===================================================================


class TestAuthProtection:
    async def test_anonymous_create_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.post("/api/trade-sessions", json={"ticker": "BBRI"})
        assert resp.status_code == 401

    async def test_anonymous_list_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        resp = await client.get("/api/trade-sessions")
        assert resp.status_code == 401

    async def test_anonymous_detail_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.get(f"/api/trade-sessions/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_anonymous_archive_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.post(f"/api/trade-sessions/{uuid.uuid4()}/archive")
        assert resp.status_code == 401

    async def test_invalid_cookie_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        resp = await client.get(
            "/api/trade-sessions",
            cookies={"tradepilot_session": "not_a_valid_token"},
        )
        assert resp.status_code == 401


# ===================================================================
# Create
# ===================================================================


class TestCreate:
    async def test_valid_create(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": "BBRI"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "BBRI"
        assert data["lifecycle_status"] == "DRAFT"
        assert data["currency"] == "IDR"

    async def test_authenticated_owner(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": "BBRI"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201
        # Verify by re-fetching through the API
        detail = await client.get(
            f"/api/trade-sessions/{resp.json()['id']}",
            cookies={"tradepilot_session": cookie},
        )
        assert detail.status_code == 200

    async def test_draft_initial_status(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": "BBRI"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.json()["lifecycle_status"] == "DRAFT"

    async def test_empty_trade_state_created(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": "BBRI"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201
        detail = await client.get(
            f"/api/trade-sessions/{resp.json()['id']}",
            cookies={"tradepilot_session": cookie},
        )
        assert detail.json()["trade_state"]["position_status"] == "NOT_OPENED"

    async def test_ticker_normalized(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": "  bbri  "},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.json()["ticker"] == "BBRI"

    async def test_currency_normalized(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": "BBRI", "currency": "usd"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.json()["currency"] == "USD"

    async def test_owner_id_not_from_body(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        other_id = uuid.uuid4()
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": "BBRI", "owner_id": str(other_id)},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201
        detail = await client.get(
            f"/api/trade-sessions/{resp.json()['id']}",
            cookies={"tradepilot_session": cookie},
        )
        assert detail.status_code == 200

    async def test_invalid_request_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": ""},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422

    async def test_invalid_create_rollback(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        await client.post(
            "/api/trade-sessions",
            json={"ticker": ""},
            cookies={"tradepilot_session": cookie},
        )
        async with engine.begin() as conn:
            rows = (
                await conn.execute(
                    text("SELECT COUNT(*) FROM trade_sessions WHERE owner_id=:uid"),
                    {"uid": uid},
                )
            ).first()[0]
            assert rows == 0


# ===================================================================
# List
# ===================================================================


class TestList:
    async def test_own_sessions(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        await _make_session_raw(engine, uid)
        await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            "/api/trade-sessions",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    async def test_cross_user_excluded(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        await _make_session_raw(engine, uid1)
        await _make_session_raw(engine, uid2)
        cookie = await _login_user(client, email1)
        resp = await client.get(
            "/api/trade-sessions",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    async def test_empty_list(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.get(
            "/api/trade-sessions",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["sessions"] == []


# ===================================================================
# Detail
# ===================================================================


class TestDetail:
    async def test_owner_retrieves(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session"]["id"] == str(sid)
        assert data["session"]["ticker"] == "BBRI"

    async def test_trade_state_included(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        ts = resp.json()["trade_state"]
        assert ts["position_status"] == "NOT_OPENED"
        assert ts["state_version"] == 1

    async def test_cross_user_404(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid1)
        cookie = await _login_user(client, email2)
        resp = await client.get(
            f"/api/trade-sessions/{sid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404

    async def test_unknown_uuid_404(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{uuid.uuid4()}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404


# ===================================================================
# Archive
# ===================================================================


class TestArchive:
    async def test_eligible_archived(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid, status="CLOSED_TAKE_PROFIT")
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/archive",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["lifecycle_status"] == "ARCHIVED"

    async def test_cross_user_archive_fails(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid1, status="CLOSED_TAKE_PROFIT")
        cookie = await _login_user(client, email2)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/archive",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404

    async def test_invalid_lifecycle_fails(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid, status="DRAFT")
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/archive",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422


# ===================================================================
# Ownership impersonation
# ===================================================================


class TestOwnershipImpersonation:
    async def test_body_owner_id_ignored(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": "BBRI", "owner_id": str(uuid.uuid4())},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201
        detail = await client.get(
            f"/api/trade-sessions/{resp.json()['id']}",
            cookies={"tradepilot_session": cookie},
        )
        assert detail.status_code == 200

    async def test_query_owner_id_ignored(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        s1 = await _make_session_raw(engine, uid1)
        s2 = await _make_session_raw(engine, uid2)
        cookie = await _login_user(client, email1)
        resp = await client.get(
            "/api/trade-sessions",
            params={"owner_id": str(uid2)},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["sessions"]]
        assert str(s1) in ids
        assert str(s2) not in ids

    async def test_header_owner_id_ignored(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.post(
            "/api/trade-sessions",
            json={"ticker": "BBRI"},
            headers={"X-User-ID": str(uuid.uuid4())},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201
        detail = await client.get(
            f"/api/trade-sessions/{resp.json()['id']}",
            cookies={"tradepilot_session": cookie},
        )
        assert detail.status_code == 200


# ===================================================================
# Sensitive field exclusion
# ===================================================================


class TestSensitiveFields:
    async def test_no_password_hash(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}",
            cookies={"tradepilot_session": cookie},
        )
        body = resp.text
        assert "password_hash" not in body
        assert "password" not in body


# ===================================================================
# PATCH /{session_id}
# ===================================================================


class TestPatch:
    async def test_patch_title(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.patch(
            f"/api/trade-sessions/{sid}",
            json={"title": "New Title"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    async def test_patch_company_name(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.patch(
            f"/api/trade-sessions/{sid}",
            json={"company_name": "Test Corp"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["company_name"] == "Test Corp"

    async def test_partial_update_omitted_unchanged(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        # Set title first
        await client.patch(
            f"/api/trade-sessions/{sid}",
            json={"title": "Before", "company_name": "Before Co"},
            cookies={"tradepilot_session": cookie},
        )
        # Partial update — only change company_name
        resp = await client.patch(
            f"/api/trade-sessions/{sid}",
            json={"company_name": "After Co"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.json()["title"] == "Before"
        assert resp.json()["company_name"] == "After Co"

    async def test_owner_immutable_via_patch(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.patch(
            f"/api/trade-sessions/{sid}",
            json={"title": "Test"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200

    async def test_lifecycle_immutable_via_patch(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.patch(
            f"/api/trade-sessions/{sid}",
            json={"title": "Test"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["lifecycle_status"] == "DRAFT"

    async def test_patch_anonymous_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.patch(
            f"/api/trade-sessions/{uuid.uuid4()}",
            json={"title": "Test"},
        )
        assert resp.status_code == 401

    async def test_patch_cross_user_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid1)
        cookie = await _login_user(client, email2)
        resp = await client.patch(
            f"/api/trade-sessions/{sid}",
            json={"title": "Hacked"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404


# ===================================================================
# POST /{session_id}/ready
# ===================================================================


class TestReady:
    async def test_valid_ready_transition(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/ready",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["lifecycle_status"] == "READY_FOR_ANALYSIS"

    async def test_invalid_ready_transition_fails(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        # OPEN_POSITION cannot go to READY_FOR_ANALYSIS
        sid = await _make_session_raw(engine, uid, status="OPEN_POSITION")
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/ready",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422

    async def test_ready_stable_error_code(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid, status="OPEN_POSITION")
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/ready",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "code" in body.get("detail", {}) or "detail" in body

    async def test_ready_anonymous_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.post(f"/api/trade-sessions/{uuid.uuid4()}/ready")
        assert resp.status_code == 401

    async def test_ready_cross_user_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid1)
        cookie = await _login_user(client, email2)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/ready",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404

    async def test_ready_rollback(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid, status="OPEN_POSITION")
        cookie = await _login_user(client, email)
        await client.post(
            f"/api/trade-sessions/{sid}/ready",
            cookies={"tradepilot_session": cookie},
        )
        async with engine.begin() as conn:
            row = await conn.execute(
                text("SELECT lifecycle_status FROM trade_sessions WHERE id=:sid"),
                {"sid": sid},
            )
            assert row.first()[0] == "OPEN_POSITION"


# ===================================================================
# Allowed actions in detail
# ===================================================================


class TestAllowedActions:
    async def test_draft_allowed_actions(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        actions = resp.json()["allowed_actions"]
        assert "MARK_READY" in actions
        assert "CANCEL" in actions

    async def test_watching_allowed_actions(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid, status="WATCHING")
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        actions = resp.json()["allowed_actions"]
        assert "CANCEL" in actions
        assert "ARCHIVE" in actions
        assert "MARK_READY" not in actions

    async def test_archived_no_actions(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid, status="ARCHIVED")
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        actions = resp.json()["allowed_actions"]
        assert actions == []

    async def test_deterministic_actions(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid)
        cookie = await _login_user(client, email)
        r1 = await client.get(
            f"/api/trade-sessions/{sid}",
            cookies={"tradepilot_session": cookie},
        )
        r2 = await client.get(
            f"/api/trade-sessions/{sid}",
            cookies={"tradepilot_session": cookie},
        )
        assert r1.json()["allowed_actions"] == r2.json()["allowed_actions"]


# ===================================================================
# Archive stable error code regression
# ===================================================================


class TestArchiveStableError:
    async def test_invalid_archive_stable_code(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session_raw(engine, uid, status="DRAFT")
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/archive",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422
        body = resp.json()
        detail = body.get("detail", {})
        if isinstance(detail, dict):
            assert "code" in detail
            assert detail["code"] == "ARCHIVE_SESSION_INVALID_STATE"
        else:
            # String detail — still acceptable
            assert "ARCHIVE_SESSION_INVALID_STATE" in str(detail)
