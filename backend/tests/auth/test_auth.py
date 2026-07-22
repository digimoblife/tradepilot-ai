"""Tests for TP-1001 Authentication Foundation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.auth import (
    hash_password,
    verify_password,
)
from app.auth.sessions import SessionStore, hash_token

pytestmark = pytest.mark.database


# ===================================================================
# Helpers
# ===================================================================


async def _ensure_user_sessions_table(engine: AsyncEngine) -> None:
    """Create user_sessions matching migration 4a2b6c8d0e1f."""
    """Create the user_sessions table if it does not exist."""
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
    password: str = "secure_password123",
    account_status: str = "ACTIVE",
) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    pw_hash = hash_password(password)
    unique_email = email or f"auth_{uid.hex[:8]}@test.com"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, account_status) "
                "VALUES (:id, :e, :ph, :st)"
            ),
            {"id": uid, "e": unique_email, "ph": pw_hash, "st": account_status},
        )
    return uid, unique_email


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    """Provide a DB session for dependency override."""
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest.fixture
def app(engine: AsyncEngine, db_session: AsyncSession) -> FastAPI:
    app = FastAPI()

    from app.auth.errors import (
        AUTHENTICATION_INACTIVE,
        AuthenticationError,
    )

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request, exc: AuthenticationError):
        from fastapi.responses import JSONResponse

        if exc.code == AUTHENTICATION_INACTIVE:
            return JSONResponse(
                status_code=403,
                content={"detail": "Account is not active", "code": exc.code},
            )
        return JSONResponse(
            status_code=401,
            content={"detail": exc.message or "Authentication failed", "code": exc.code},
        )

    app.include_router(auth_router)

    from app.database.session import get_db_session

    async def _override() -> AsyncSession:
        return db_session

    app.dependency_overrides[get_db_session] = _override
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ===================================================================
# Password hashing
# ===================================================================


class TestPasswords:
    def test_hash_differs_from_plaintext(self) -> None:
        pw = "my_secret_password"
        h = hash_password(pw)
        assert h != pw
        assert "$2b$" in h  # bcrypt format marker

    def test_correct_password_verifies(self) -> None:
        pw = "my_secret_password"
        h = hash_password(pw)
        assert verify_password(pw, h) is True

    def test_wrong_password_fails(self) -> None:
        h = hash_password("correct_password")
        assert verify_password("wrong_password", h) is False

    def test_malformed_hash_fails_safely(self) -> None:
        assert verify_password("any", "") is False
        assert verify_password("any", "not_a_hash") is False

    def test_empty_password_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            hash_password("")


# ===================================================================
# Session operations
# ===================================================================


class TestSessions:
    async def test_create_session(
        self, engine: AsyncEngine, factory: async_sessionmaker[AsyncSession]
    ) -> None:
        uid, _ = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        async with factory() as s:
            raw, session = SessionStore.create(uid, 3600)
            s.add(session)
            await s.flush()
            assert session.user_id == uid
            assert session.token_hash == hash_token(raw)
            assert session.revoked_at is None
            assert session.expires_at > datetime.now(timezone.utc)

    async def test_session_validity(
        self, engine: AsyncEngine, factory: async_sessionmaker[AsyncSession]
    ) -> None:
        uid, _ = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        async with factory() as s:
            raw, session = SessionStore.create(uid, 3600)
            s.add(session)
            await s.flush()
            assert SessionStore.is_valid(session) is True

    async def test_expired_session_invalid(
        self, engine: AsyncEngine, factory: async_sessionmaker[AsyncSession]
    ) -> None:
        uid, _ = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        async with factory() as s:
            _, session = SessionStore.create(uid, -1)  # already expired
            s.add(session)
            await s.flush()
            assert SessionStore.is_valid(session) is False

    async def test_revoked_session_invalid(
        self, engine: AsyncEngine, factory: async_sessionmaker[AsyncSession]
    ) -> None:
        uid, _ = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        async with factory() as s:
            _, session = SessionStore.create(uid, 3600)
            s.add(session)
            await s.flush()
            SessionStore.revoke(session)
            assert SessionStore.is_valid(session) is False

    async def test_token_is_opaque(
        self, engine: AsyncEngine, factory: async_sessionmaker[AsyncSession]
    ) -> None:
        uid, _ = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        async with factory() as s:
            raw, session = SessionStore.create(uid, 3600)
            s.add(session)
            await s.flush()
            # Raw token should not contain user ID or email
            assert str(uid) not in raw
            # Only hash is stored, not raw token
            assert session.token_hash != raw


# ===================================================================
# Login flow
# ===================================================================


class TestLogin:
    async def test_active_user_login(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "secure_password123",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(uid)
        assert data["email"] == email
        assert "tradepilot_session" in resp.cookies

    async def test_wrong_password_fails(self, engine: AsyncEngine, client: AsyncClient) -> None:
        _, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "wrong_password",
            },
        )
        assert resp.status_code == 401

    async def test_unknown_email_fails_same_as_wrong_password(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        await _ensure_user_sessions_table(engine)
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "any_password",
            },
        )
        assert resp.status_code == 401

    async def test_inactive_user_fails(self, engine: AsyncEngine, client: AsyncClient) -> None:
        _, email = await _make_user(engine, account_status="DISABLED")
        await _ensure_user_sessions_table(engine)
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "secure_password123",
            },
        )
        assert resp.status_code == 403


# ===================================================================
# Logout
# ===================================================================


class TestLogout:
    async def test_logout_revokes_session(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        login_resp = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "secure_password123",
            },
        )
        assert login_resp.status_code == 200
        cookie = login_resp.cookies.get("tradepilot_session")
        assert cookie is not None

        logout_resp = await client.post(
            "/api/auth/logout",
            cookies={
                "tradepilot_session": cookie,
            },
        )
        assert logout_resp.status_code == 200

        me_resp = await client.get(
            "/api/auth/me",
            cookies={
                "tradepilot_session": cookie,
            },
        )
        assert me_resp.status_code == 401


# ===================================================================
# Protected endpoint (me)
# ===================================================================


class TestMe:
    async def test_anonymous_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        await _ensure_user_sessions_table(engine)
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_invalid_cookie_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        await _ensure_user_sessions_table(engine)
        resp = await client.get(
            "/api/auth/me",
            cookies={
                "tradepilot_session": "not_a_valid_token",
            },
        )
        assert resp.status_code == 401

    async def test_valid_session_returns_identity(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        login_resp = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "secure_password123",
            },
        )
        cookie = login_resp.cookies.get("tradepilot_session")

        me_resp = await client.get(
            "/api/auth/me",
            cookies={
                "tradepilot_session": cookie,
            },
        )
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["id"] == str(uid)
        assert data["email"] == email

    async def test_no_password_hash_in_response(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        _, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        login_resp = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "secure_password123",
            },
        )
        assert login_resp.status_code == 200
        body = login_resp.json()
        assert "password_hash" not in body
        assert "password" not in body

    async def test_owner_id_not_from_body(self, engine: AsyncEngine, client: AsyncClient) -> None:
        """Client cannot supply another user's ID to impersonate."""
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)

        login_resp = await client.post(
            "/api/auth/login",
            json={
                "email": email1,
                "password": "secure_password123",
            },
        )
        cookie = login_resp.cookies.get("tradepilot_session")

        me_resp = await client.get(
            "/api/auth/me",
            cookies={
                "tradepilot_session": cookie,
            },
        )
        assert me_resp.json()["id"] == str(uid1)
        assert me_resp.json()["id"] != str(uid2)


# ===================================================================
# Cookie configuration
# ===================================================================


class TestCookieConfig:
    async def test_cookie_is_httponly(self, engine: AsyncEngine, client: AsyncClient) -> None:
        _, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "secure_password123",
            },
        )
        cookie_header = resp.headers.get("set-cookie", "")
        assert "HttpOnly" in cookie_header
        assert "SameSite=Lax" in cookie_header or "samesite=lax" in cookie_header.lower()
