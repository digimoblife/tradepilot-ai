from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.analysis_request import AnalysisRequestV2
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2
from app.trade_workspace.models.position import PositionV2
from app.trade_workspace.models.session_decision import SessionDecisionV2
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database


async def _make_user(engine: AsyncEngine, tag: str) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    email = f"own-{tag}-{user_id}@example.test"
    async with engine.begin() as connection:
        await connection.execute(
            User.__table__.insert().values(
                id=user_id,
                email=email,
                password_hash=hash_password("testpass123"),
            )
        )
    return user_id, email


def _build_app(db_session: AsyncSession) -> FastAPI:
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


async def _login(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    assert response.status_code == 200


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(engine: AsyncEngine, db_session: AsyncSession) -> AsyncClient:
    app = _build_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def _create_owned_session(
    db_session: AsyncSession, user_id: uuid.UUID, status: TradeSessionV2Status = TradeSessionV2Status.DRAFT
) -> uuid.UUID:
    session_id = uuid.uuid4()
    db_session.add(
        TradeSessionV2(
            id=session_id,
            user_id=user_id,
            ticker="BBRI",
            company_name="Bank BRI",
            status=status,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()
    return session_id


async def test_direct_ownership_isolation_all_12_operations(
    client: AsyncClient, engine: AsyncEngine, db_session: AsyncSession
) -> None:
    """Verifies direct cross-user ownership isolation for all 12 operations using canonical prerequisite status fixtures.

    Operations & Prerequisite Fixture Statuses:
    1. Session Detail read (DRAFT)
    2. Current Step read (DRAFT)
    3. Initial Evidence upload (DRAFT)
    4. Initial Analysis submission (DRAFT)
    5. BUY decision (ANALYZED)
    6. WAIT decision (ANALYZED)
    7. SKIP decision (ANALYZED)
    8. WAIT Update input submission (WAITING)
    9. WAIT Update analysis submission (WAITING)
    10. Position Update input submission (OPEN_POSITION)
    11. Position Update analysis submission (OPEN_POSITION)
    12. Close submission (OPEN_POSITION)
    """
    user_a_id, user_a_email = await _make_user(engine, "usera")
    user_b_id, user_b_email = await _make_user(engine, "userb")

    # Prerequisite Session Fixtures for User A
    draft_session_id = await _create_owned_session(db_session, user_a_id, TradeSessionV2Status.DRAFT)
    analyzed_session_id = await _create_owned_session(db_session, user_a_id, TradeSessionV2Status.ANALYZED)
    waiting_session_id = await _create_owned_session(db_session, user_a_id, TradeSessionV2Status.WAITING)
    open_pos_session_id = await _create_owned_session(db_session, user_a_id, TradeSessionV2Status.OPEN_POSITION)

    # Login as User B (Cross-user intruder)
    await _login(client, user_b_email)

    # 1. Session Detail read (Prerequisite: DRAFT)
    resp_detail = await client.get(f"/api/v2/trade-sessions/{draft_session_id}/detail")
    assert resp_detail.status_code in (404, 403)

    # 2. Current Step read (Prerequisite: DRAFT)
    resp_step = await client.get(f"/api/v2/trade-sessions/{draft_session_id}/current-step")
    assert resp_step.status_code in (404, 403)

    # 3. Initial Evidence upload (Prerequisite: DRAFT)
    files = {
        "orderbook": ("orderbook.png", io.BytesIO(b"png"), "image/png"),
        "chart_3_month": ("c3.png", io.BytesIO(b"png"), "image/png"),
        "chart_6_month": ("c6.png", io.BytesIO(b"png"), "image/png"),
    }
    resp_evidence = await client.post(f"/api/v2/trade-sessions/{draft_session_id}/initial-evidence", files=files)
    assert resp_evidence.status_code in (404, 403, 422)

    # 4. Initial Analysis submission (Prerequisite: DRAFT)
    resp_init_analysis = await client.post(f"/api/v2/trade-sessions/{draft_session_id}/initial-analysis")
    assert resp_init_analysis.status_code in (404, 403)

    # 5. BUY decision (Prerequisite: ANALYZED)
    buy_payload = {
        "entry_price": "5000",
        "entry_timestamp": "2026-01-01T10:00:00Z",
        "quantity": "100",
        "stop_loss": "4800",
        "target_price": "5500",
    }
    resp_buy = await client.post(f"/api/v2/trade-sessions/{analyzed_session_id}/decisions/buy", json=buy_payload)
    assert resp_buy.status_code in (404, 403)

    # 6. WAIT decision (Prerequisite: ANALYZED)
    resp_wait = await client.post(f"/api/v2/trade-sessions/{analyzed_session_id}/decisions/wait")
    assert resp_wait.status_code in (404, 403)

    # 7. SKIP decision (Prerequisite: ANALYZED)
    skip_payload = {"reason": "RISK_TOO_HIGH", "note": "Too risky"}
    resp_skip = await client.post(f"/api/v2/trade-sessions/{analyzed_session_id}/decisions/skip", json=skip_payload)
    assert resp_skip.status_code in (404, 403)

    # 8. WAIT Update input submission (Prerequisite: WAITING)
    wait_input_files = {"orderbook": ("ob.png", io.BytesIO(b"png"), "image/png")}
    wait_input_data = {
        "current_price": "5100",
        "observation_period": "MIDDAY",
        "observation_timestamp": "2026-01-01T12:00:00Z",
    }
    resp_wait_input = await client.post(
        f"/api/v2/trade-sessions/{waiting_session_id}/wait-update-input",
        data=wait_input_data,
        files=wait_input_files,
    )
    assert resp_wait_input.status_code in (404, 403)

    # 9. WAIT Update analysis submission (Prerequisite: WAITING)
    resp_wait_sub = await client.post(f"/api/v2/trade-sessions/{waiting_session_id}/wait-updates")
    assert resp_wait_sub.status_code in (404, 403)

    # 10. Position Update input submission (Prerequisite: OPEN_POSITION)
    pos_input_files = {"orderbook": ("ob.png", io.BytesIO(b"png"), "image/png")}
    pos_input_data = {
        "current_price": "5200",
        "observation_period": "MIDDAY",
        "observation_timestamp": "2026-01-01T13:00:00Z",
    }
    resp_pos_input = await client.post(
        f"/api/v2/trade-sessions/{open_pos_session_id}/position-update-input",
        data=pos_input_data,
        files=pos_input_files,
    )
    assert resp_pos_input.status_code in (404, 403)

    # 11. Position Update analysis submission (Prerequisite: OPEN_POSITION)
    resp_pos_sub = await client.post(f"/api/v2/trade-sessions/{open_pos_session_id}/position-updates")
    assert resp_pos_sub.status_code in (404, 403)

    # 12. Close submission (Prerequisite: OPEN_POSITION)
    close_payload = {
        "close_price": "5400",
        "close_timestamp": "2026-01-01T15:00:00Z",
        "close_reason": "Target price reached",
    }
    resp_close = await client.post(f"/api/v2/trade-sessions/{open_pos_session_id}/close", json=close_payload)
    assert resp_close.status_code in (404, 403)

    # SIDE-EFFECT ASSERTIONS: Verify each session's status and database records remain strictly unchanged
    s_draft = await db_session.scalar(select(TradeSessionV2).where(TradeSessionV2.id == draft_session_id))
    assert s_draft is not None and s_draft.status == TradeSessionV2Status.DRAFT

    s_analyzed = await db_session.scalar(select(TradeSessionV2).where(TradeSessionV2.id == analyzed_session_id))
    assert s_analyzed is not None and s_analyzed.status == TradeSessionV2Status.ANALYZED

    s_waiting = await db_session.scalar(select(TradeSessionV2).where(TradeSessionV2.id == waiting_session_id))
    assert s_waiting is not None and s_waiting.status == TradeSessionV2Status.WAITING

    s_open_pos = await db_session.scalar(select(TradeSessionV2).where(TradeSessionV2.id == open_pos_session_id))
    assert s_open_pos is not None and s_open_pos.status == TradeSessionV2Status.OPEN_POSITION

    # Count assertions for related tables across all User A sessions
    all_a_session_ids = [draft_session_id, analyzed_session_id, waiting_session_id, open_pos_session_id]
    ev_count = await db_session.scalar(
        select(func.count(EvidenceUploadV2.id)).where(EvidenceUploadV2.session_id.in_(all_a_session_ids))
    )
    assert ev_count == 0

    req_count = await db_session.scalar(
        select(func.count(AnalysisRequestV2.id)).where(AnalysisRequestV2.session_id.in_(all_a_session_ids))
    )
    assert req_count == 0

    dec_count = await db_session.scalar(
        select(func.count(SessionDecisionV2.id)).where(SessionDecisionV2.session_id.in_(all_a_session_ids))
    )
    assert dec_count == 0

    pos_count = await db_session.scalar(
        select(func.count(PositionV2.id)).where(PositionV2.session_id.in_(all_a_session_ids))
    )
    assert pos_count == 0

    cls_count = await db_session.scalar(
        select(func.count(TradeClosureV2.id)).where(TradeClosureV2.session_id.in_(all_a_session_ids))
    )
    assert cls_count == 0
