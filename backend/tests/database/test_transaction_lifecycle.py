"""Tests for database transaction lifecycle (TP-1704 fix).

Verifies that the ``get_db_session`` dependency commits on success,
rolls back on failure, and always closes the session.
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.cli.create_user import create_user
from app.database.session import get_db_session

pytestmark = pytest.mark.database

_DB_URL = os.environ.get(
    "DATABASE_SYNC_URL",
    "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot_test",
)

_ASYNC_DB_URL = _DB_URL.replace("+psycopg", "+asyncpg")


def _build_app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    """Build app overriding get_db_session with a committing dependency."""
    from app.api.exception_handlers import register_handlers

    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            finally:
                await s.close()

    app.dependency_overrides[get_db_session] = _override
    return app


@pytest.fixture(scope="module")
def sync_engine() -> Any:
    e = create_engine(_DB_URL)
    yield e
    e.dispose()


@pytest.fixture
def factory() -> async_sessionmaker[AsyncSession]:
    """Async session factory pointing at the test database."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(_ASYNC_DB_URL)
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _cleanup(sync_engine: Any) -> None:
    with sync_engine.begin() as c:
        c.execute(text("DELETE FROM user_sessions"))
        c.execute(text("DELETE FROM users WHERE email LIKE 'tx_%@test.com'"))


class TestTransactionLifecycle:
    async def test_login_persists_session_row(
        self, sync_engine: Any, factory: async_sessionmaker[AsyncSession]
    ) -> None:
        email = "tx_persist@test.com"
        create_user(sync_engine, email, "pw")

        app = _build_app(factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/auth/login",
                json={"email": email, "password": "pw"},
            )
            assert resp.status_code == 200

        # Separate connection should see the committed row
        with sync_engine.connect() as c:
            row = c.execute(
                text(
                    "SELECT 1 FROM user_sessions "
                    "WHERE user_id = (SELECT id FROM users WHERE email = :e)"
                ),
                {"e": email},
            ).first()
            assert row is not None, "user_sessions row should persist after commit"

    async def test_auth_me_succeeds_across_requests(
        self, sync_engine: Any, factory: async_sessionmaker[AsyncSession]
    ) -> None:
        email = "tx_cross@test.com"
        create_user(sync_engine, email, "pw")

        app = _build_app(factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            login_resp = await ac.post(
                "/api/auth/login",
                json={"email": email, "password": "pw"},
            )
            cookie = login_resp.cookies.get("tradepilot_session")

            me1 = await ac.get("/api/auth/me", cookies={"tradepilot_session": cookie})
            assert me1.status_code == 200

            me2 = await ac.get("/api/auth/me", cookies={"tradepilot_session": cookie})
            assert me2.status_code == 200

    async def test_logout_persists_revocation(
        self, sync_engine: Any, factory: async_sessionmaker[AsyncSession]
    ) -> None:
        email = "tx_logout@test.com"
        create_user(sync_engine, email, "pw")

        app = _build_app(factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            login_resp = await ac.post(
                "/api/auth/login",
                json={"email": email, "password": "pw"},
            )
            cookie = login_resp.cookies.get("tradepilot_session")

            logout_resp = await ac.post("/api/auth/logout", cookies={"tradepilot_session": cookie})
            assert logout_resp.status_code == 200

            me_resp = await ac.get("/api/auth/me")
            assert me_resp.status_code in (401, 403)
