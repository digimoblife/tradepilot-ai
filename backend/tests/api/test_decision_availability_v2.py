from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.position import PositionV2
from app.trade_workspace.models.session_decision import SessionDecisionV2
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database


async def _seed(
    engine: AsyncEngine,
    status: TradeSessionV2Status,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    user_id, session_id = uuid.uuid4(), uuid.uuid4()
    email = f"p61-{user_id}@example.test"
    async with engine.begin() as connection:
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
    return user_id, session_id, email


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


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _get(
    db_session: AsyncSession,
    session_id: uuid.UUID,
    email: str | None,
) -> tuple[int, dict[str, object]]:
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if email is not None:
            login = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "testpass123"},
            )
            assert login.status_code == 200
        response = await client.get(f"/api/v2/trade-sessions/{session_id}/available-actions")
    return response.status_code, response.json()


@pytest.mark.parametrize(
    ("session_status", "expected_actions"),
    [
        (TradeSessionV2Status.ANALYZED, ["BUY", "WAIT", "SKIP"]),
        (TradeSessionV2Status.WAITING, ["BUY", "WAIT", "SKIP"]),
        (TradeSessionV2Status.OPEN_POSITION, ["CLOSE"]),
        (TradeSessionV2Status.DRAFT, []),
        (TradeSessionV2Status.ANALYZING, []),
        (TradeSessionV2Status.CLOSED, []),
        (TradeSessionV2Status.CLOSED_SKIPPED, []),
    ],
)
async def test_available_actions_follow_persisted_status(
    engine: AsyncEngine,
    db_session: AsyncSession,
    session_status: TradeSessionV2Status,
    expected_actions: list[str],
) -> None:
    _, session_id, email = await _seed(engine, session_status)
    code, payload = await _get(db_session, session_id, email)
    assert code == 200
    assert payload == {
        "session_id": str(session_id),
        "session_status": session_status.value,
        "available_actions": expected_actions,
    }


async def test_available_actions_is_read_only_and_has_no_unsupported_actions(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    code, payload = await _get(db_session, session_id, email)
    assert code == 200
    assert set(payload["available_actions"]) <= {"BUY", "WAIT", "SKIP", "CLOSE"}
    assert await db_session.scalar(
        select(func.count()).select_from(SessionDecisionV2)
    ) == 0
    assert await db_session.scalar(select(func.count()).select_from(PositionV2)) == 0
    assert await db_session.scalar(select(func.count()).select_from(TradeClosureV2)) == 0
    status = await db_session.scalar(
        select(TradeSessionV2.status).where(TradeSessionV2.id == session_id)
    )
    assert status is TradeSessionV2Status.ANALYZED


async def test_available_actions_enforces_ownership_and_authentication(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, owner_email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    _, other_session_id, other_email = await _seed(engine, TradeSessionV2Status.WAITING)
    cross_user_code, _ = await _get(db_session, session_id, other_email)
    missing_code, _ = await _get(db_session, uuid.uuid4(), owner_email)
    unauthenticated_code, _ = await _get(db_session, other_session_id, None)
    assert cross_user_code == 404
    assert missing_code == 404
    assert unauthenticated_code == 401


async def test_available_actions_isolated_between_sessions(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    owner_id, analyzed_id, email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    _, draft_id, _ = await _seed(engine, TradeSessionV2Status.DRAFT)
    async with engine.begin() as connection:
        await connection.execute(
            update(TradeSessionV2)
            .where(TradeSessionV2.id == draft_id)
            .values(user_id=owner_id)
        )
    analyzed_code, analyzed = await _get(db_session, analyzed_id, email)
    draft_code, draft = await _get(db_session, draft_id, email)
    assert analyzed_code == draft_code == 200
    assert analyzed["available_actions"] == ["BUY", "WAIT", "SKIP"]
    assert draft["available_actions"] == []
