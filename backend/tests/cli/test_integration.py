"""Integration tests for authentication flow (TP-1704).

Creates a user via the CLI module, then exercises the full login/logout
cycle through the API and verifies protected endpoint behaviour.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.routes.trade_sessions import router as ts_router
from app.cli.create_user import create_user
from app.database.session import get_db_session

pytestmark = pytest.mark.database

_DB_URL = os.environ.get(
    "DATABASE_SYNC_URL",
    "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot_test",
)


def _build_app(override_session: AsyncSession | None = None) -> FastAPI:
    from app.api.exception_handlers import register_handlers

    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(ts_router)
    if override_session is not None:

        async def _override() -> AsyncSession:
            return override_session

        app.dependency_overrides[get_db_session] = _override
    return app


@pytest.fixture(scope="module")
def sync_engine() -> Any:
    e = create_engine(_DB_URL)
    yield e
    e.dispose()


@pytest.fixture
async def db_session(engine: Any) -> AsyncSession:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest.fixture(autouse=True)
def _cleanup(sync_engine: Any) -> None:
    with sync_engine.begin() as c:
        c.execute(text("DELETE FROM user_sessions"))
        c.execute(text("DELETE FROM users WHERE email LIKE 'integration_%@test.com'"))


class TestAuthIntegration:
    async def test_full_login_logout_cycle(
        self, engine: Any, db_session: AsyncSession, sync_engine: Any
    ) -> None:
        email = "integration_cycle@test.com"
        password = "test_pass_123"

        # Create user via CLI module (sync engine required)
        create_user(sync_engine, email, password)

        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Login
            resp = await ac.post(
                "/api/auth/login",
                json={"email": email, "password": password},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["email"] == email

            # Extract session cookie
            cookie = resp.cookies.get("tradepilot_session")
            assert cookie is not None

            # GET /api/auth/me with cookie
            me_resp = await ac.get("/api/auth/me", cookies={"tradepilot_session": cookie})
            assert me_resp.status_code == 200
            me_body = me_resp.json()
            assert me_body["email"] == email

            # List sessions
            sessions_resp = await ac.get(
                "/api/trade-sessions", cookies={"tradepilot_session": cookie}
            )
            assert sessions_resp.status_code == 200

            # Logout
            logout_resp = await ac.post("/api/auth/logout", cookies={"tradepilot_session": cookie})
            assert logout_resp.status_code == 200

            # Protected request after logout returns 401
            protected_resp = await ac.get("/api/auth/me")
            assert protected_resp.status_code in (401, 403)

    async def test_invalid_credentials_rejected(
        self, engine: Any, db_session: AsyncSession, sync_engine: Any
    ) -> None:
        email = "integration_bad@test.com"
        create_user(sync_engine, email, "correct_pw")

        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/auth/login",
                json={"email": email, "password": "wrong_pw"},
            )
            assert resp.status_code in (401, 403)
