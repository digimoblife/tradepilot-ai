from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _seed_user(engine: AsyncEngine, label: str) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    email = f"ux14-{label}-{user_id}@example.test"
    async with engine.begin() as connection:
        await connection.execute(
            User.__table__.insert().values(
                id=user_id,
                email=email,
                password_hash=hash_password("testpass123"),
            )
        )
    return user_id, email


async def _seed_session(
    engine: AsyncEngine,
    user_id: uuid.UUID,
    status: TradeSessionV2Status,
    *,
    archived_at: datetime | None = None,
) -> uuid.UUID:
    session_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            TradeSessionV2.__table__.insert().values(
                id=session_id,
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                status=status,
                closed_at=(datetime.now(timezone.utc) if status in {
                    TradeSessionV2Status.CLOSED,
                    TradeSessionV2Status.CLOSED_SKIPPED,
                } else None),
                archived_at=archived_at,
            )
        )
    return session_id


def _app(db_session: AsyncSession) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)

    async def override_db() -> AsyncSession:
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = override_db
    return app


async def _request(
    db_session: AsyncSession,
    path: str,
    email: str | None,
    *,
    method: str = "GET",
) -> tuple[int, dict[str, object]]:
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if email is not None:
            login = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "testpass123"},
            )
            assert login.status_code == 200
        response = await client.request(method, path)
    return response.status_code, response.json()


async def _cleanup(engine: AsyncEngine, user_ids: list[uuid.UUID]) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            delete(TradeSessionV2).where(TradeSessionV2.user_id.in_(user_ids))
        )
        await connection.execute(delete(User).where(User.id.in_(user_ids)))


async def test_v2_archive_restore_contract_and_list_boundaries(
    engine: AsyncEngine,
    db_session: AsyncSession,
) -> None:
    owner_id, owner_email = await _seed_user(engine, "owner")
    other_id, other_email = await _seed_user(engine, "other")
    session_ids: list[uuid.UUID] = []
    try:
        closed_id = await _seed_session(engine, owner_id, TradeSessionV2Status.CLOSED)
        skipped_id = await _seed_session(engine, owner_id, TradeSessionV2Status.CLOSED_SKIPPED)
        archived_id = await _seed_session(
            engine,
            owner_id,
            TradeSessionV2Status.CLOSED,
            archived_at=datetime.now(timezone.utc),
        )
        other_session_id = await _seed_session(engine, other_id, TradeSessionV2Status.CLOSED)
        session_ids.extend([closed_id, skipped_id, archived_id, other_session_id])

        code, payload = await _request(db_session, "/api/v2/trade-sessions", owner_email)
        assert code == 200
        assert {item["id"] for item in payload["sessions"]} == {str(closed_id), str(skipped_id)}
        assert all(item["archived_at"] is None for item in payload["sessions"])

        code, payload = await _request(
            db_session, "/api/v2/trade-sessions/archived", owner_email
        )
        assert code == 200
        assert [item["id"] for item in payload["sessions"]] == [str(archived_id)]
        assert payload["sessions"][0]["archived_at"] is not None

        code, payload = await _request(
            db_session, f"/api/v2/trade-sessions/{closed_id}/archive", owner_email, method="POST"
        )
        assert code == 200
        assert payload["id"] == str(closed_id)
        assert payload["status"] == TradeSessionV2Status.CLOSED.value
        assert payload["archived_at"] is not None

        code, payload = await _request(
            db_session, f"/api/v2/trade-sessions/{closed_id}/archive", owner_email, method="POST"
        )
        assert code == 409
        assert payload["error"]["code"] == "SESSION_ALREADY_ARCHIVED"

        code, payload = await _request(
            db_session, f"/api/v2/trade-sessions/{closed_id}/restore", owner_email, method="POST"
        )
        assert code == 200
        assert payload == {
            "id": str(closed_id),
            "status": TradeSessionV2Status.CLOSED.value,
            "archived_at": None,
        }

        code, payload = await _request(
            db_session, f"/api/v2/trade-sessions/{closed_id}", owner_email
        )
        assert code == 200
        assert payload["archived_at"] is None
        assert payload["status"] == TradeSessionV2Status.CLOSED.value

        code, payload = await _request(
            db_session, f"/api/v2/trade-sessions/{archived_id}", owner_email
        )
        assert code == 200
        assert payload["archived_at"] is not None
        assert payload["status"] == TradeSessionV2Status.CLOSED.value

        code, payload = await _request(
            db_session,
            f"/api/v2/trade-sessions/{other_session_id}/archive",
            owner_email,
            method="POST",
        )
        assert code == 404
        assert payload["error"]["code"] == "SESSION_NOT_FOUND"

        code, payload = await _request(
            db_session,
            f"/api/v2/trade-sessions/{archived_id}",
            other_email,
        )
        assert code == 404
        assert payload["error"]["code"] == "SESSION_NOT_FOUND"

        for status_value in (
            TradeSessionV2Status.DRAFT,
            TradeSessionV2Status.ANALYZING,
            TradeSessionV2Status.ANALYZED,
            TradeSessionV2Status.WAITING,
            TradeSessionV2Status.OPEN_POSITION,
        ):
            session_id = await _seed_session(engine, owner_id, status_value)
            session_ids.append(session_id)
            code, payload = await _request(
                db_session,
                f"/api/v2/trade-sessions/{session_id}/archive",
                owner_email,
                method="POST",
            )
            assert code == 409
            assert payload["error"]["code"] == "ARCHIVE_NOT_ALLOWED"

        code, payload = await _request(
            db_session, f"/api/v2/trade-sessions/{skipped_id}/archive", owner_email, method="POST"
        )
        assert code == 200
        assert payload["status"] == TradeSessionV2Status.CLOSED_SKIPPED.value
        assert payload["archived_at"] is not None

        code, payload = await _request(
            db_session, "/api/v2/trade-sessions/archived", other_email
        )
        assert code == 200
        assert payload["sessions"] == []

        code, payload = await _request(
            db_session, "/api/v2/trade-sessions/archived", None
        )
        assert code == 401
        assert payload["error"]["code"] == "AUTHENTICATION_REQUIRED"
    finally:
        await _cleanup(engine, [owner_id, other_id])
