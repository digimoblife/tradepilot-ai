from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

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
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.session_decision import (
    SessionDecisionV2,
    SessionDecisionV2Decision,
)
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database

BUY_BODY = {
    "entry_price": "101.234500",
    "entry_timestamp": "2026-07-30T09:15:00.123456Z",
    "quantity": "12.500000",
    "stop_loss": "95.125000",
    "target_price": "120.750000",
}


async def _seed(
    engine: AsyncEngine,
    status: TradeSessionV2Status,
    *,
    owner: tuple[uuid.UUID, str] | None = None,
    with_position: bool = False,
    with_buy: bool = False,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    if owner is None:
        user_id, email = uuid.uuid4(), f"p64-{uuid.uuid4()}@example.test"
        create_user = True
    else:
        user_id, email = owner
        create_user = False
    session_id = uuid.uuid4()
    async with engine.begin() as connection:
        if create_user:
            await connection.execute(
                User.__table__.insert().values(
                    id=user_id,
                    email=email,
                    password_hash=hash_password("testpass123"),
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
        if with_buy:
            await connection.execute(
                SessionDecisionV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    decision=SessionDecisionV2Decision.BUY,
                )
            )
        if with_position:
            await connection.execute(
                PositionV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    entry_price=Decimal("100"),
                    entry_at=datetime.now(timezone.utc),
                    quantity=Decimal("1"),
                    stop_loss=Decimal("95"),
                    target_price=Decimal("110"),
                    status=PositionV2Status.OPEN,
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


async def _post_buy(
    db_session: AsyncSession,
    session_id: uuid.UUID,
    email: str | None,
    body: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if email is not None:
            login = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "testpass123"},
            )
            assert login.status_code == 200
        response = await client.post(
            f"/api/v2/trade-sessions/{session_id}/decisions/buy",
            json=BUY_BODY if body is None else body,
        )
    return response.status_code, response.json()


async def _count(
    db_session: AsyncSession,
    model: type[object],
    session_id: uuid.UUID,
) -> int:
    return int(
        await db_session.scalar(
            select(func.count()).select_from(model).where(model.session_id == session_id)  # type: ignore[attr-defined]
        )
    )


@pytest.mark.parametrize("status", [TradeSessionV2Status.ANALYZED, TradeSessionV2Status.WAITING])
async def test_owner_can_buy_and_preserves_confirmed_facts(
    engine: AsyncEngine, db_session: AsyncSession, status: TradeSessionV2Status
) -> None:
    _, session_id, email = await _seed(engine, status)
    code, payload = await _post_buy(
        db_session, session_id, email, {**BUY_BODY, "note": "confirmed"}
    )
    assert code == 201
    assert payload["session_id"] == str(session_id)
    assert payload["decision_type"] == "BUY"
    assert payload["position_status"] == "OPEN"
    assert payload["session_status"] == "OPEN_POSITION"
    assert payload["entry_price"] == "101.234500"
    assert payload["entry_timestamp"] == "2026-07-30T09:15:00.123456Z"
    assert payload["quantity"] == "12.500000"
    assert payload["stop_loss"] == "95.125000"
    assert payload["target_price"] == "120.750000"
    assert payload["note"] == "confirmed"
    assert await _count(db_session, SessionDecisionV2, session_id) == 1
    assert await _count(db_session, PositionV2, session_id) == 1
    decision = await db_session.scalar(
        select(SessionDecisionV2).where(SessionDecisionV2.session_id == session_id)
    )
    position = await db_session.scalar(
        select(PositionV2).where(PositionV2.session_id == session_id)
    )
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert decision is not None and decision.decision is SessionDecisionV2Decision.BUY
    assert decision.note == "confirmed"
    assert position is not None and position.status is PositionV2Status.OPEN
    assert position.entry_price == Decimal("101.234500")
    assert position.entry_at == datetime(2026, 7, 30, 9, 15, 0, 123456, tzinfo=timezone.utc)
    assert position.quantity == Decimal("12.500000")
    assert position.stop_loss == Decimal("95.125000")
    assert position.target_price == Decimal("120.750000")
    assert session is not None
    assert session.status is TradeSessionV2Status.OPEN_POSITION
    assert session.closed_at is None


async def test_omitted_note_is_accepted_and_p61_availability_returns_close(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    code, payload = await _post_buy(db_session, session_id, email)
    assert code == 201
    assert payload["note"] is None
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
        response = await client.get(f"/api/v2/trade-sessions/{session_id}/available-actions")
    assert response.status_code == 200
    assert response.json()["available_actions"] == ["CLOSE"]


@pytest.mark.parametrize(
    "field",
    ["entry_price", "entry_timestamp", "quantity", "stop_loss", "target_price"],
)
async def test_missing_required_buy_field_is_rejected(
    engine: AsyncEngine, db_session: AsyncSession, field: str
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    body = {key: value for key, value in BUY_BODY.items() if key != field}
    code, payload = await _post_buy(db_session, session_id, email, body)
    assert code == 422
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert await _count(db_session, SessionDecisionV2, session_id) == 0
    assert await _count(db_session, PositionV2, session_id) == 0


async def test_extra_buy_field_and_non_positive_fact_are_rejected(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    for body in ({**BUY_BODY, "provider": "gemini"}, {**BUY_BODY, "quantity": "0"}):
        code, payload = await _post_buy(db_session, session_id, email, body)
        assert code == 422
        assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert await _count(db_session, SessionDecisionV2, session_id) == 0
    assert await _count(db_session, PositionV2, session_id) == 0


@pytest.mark.parametrize(
    "status",
    [
        TradeSessionV2Status.DRAFT,
        TradeSessionV2Status.ANALYZING,
        TradeSessionV2Status.OPEN_POSITION,
        TradeSessionV2Status.CLOSED,
        TradeSessionV2Status.CLOSED_SKIPPED,
    ],
)
async def test_buy_rejects_inactive_status_without_partial_persistence(
    engine: AsyncEngine, db_session: AsyncSession, status: TradeSessionV2Status
) -> None:
    _, session_id, email = await _seed(engine, status)
    code, payload = await _post_buy(db_session, session_id, email)
    assert code == 409
    assert payload["error"]["code"] == "BUY_NOT_ALLOWED"
    assert await _count(db_session, SessionDecisionV2, session_id) == 0
    assert await _count(db_session, PositionV2, session_id) == 0


@pytest.mark.parametrize(
    "seed_kw, expected_code",
    [("with_position", "BUY_POSITION_EXISTS"), ("with_buy", "BUY_ALREADY_EXISTS")],
)
async def test_existing_position_or_buy_rejects_duplicate(
    engine: AsyncEngine,
    db_session: AsyncSession,
    seed_kw: str,
    expected_code: str,
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.ANALYZED, **{seed_kw: True})
    code, payload = await _post_buy(db_session, session_id, email)
    assert code == 409
    assert payload["error"]["code"] == expected_code


async def test_buy_preserves_prior_wait_evidence_and_analysis(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.WAITING)
    request_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            SessionDecisionV2.__table__.insert().values(
                id=uuid.uuid4(),
                session_id=session_id,
                decision=SessionDecisionV2Decision.WAIT,
            )
        )
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                id=request_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                status=AnalysisRequestV2Status.COMPLETED,
                provider="gemini",
                model="configured-model",
                prompt_version="v1",
                input_snapshot={"preserved": True},
                processed_response={"summary": "preserved"},
            )
        )
        for evidence_type in (
            EvidenceUploadV2Type.ORDERBOOK,
            EvidenceUploadV2Type.CHART_3_MONTH,
            EvidenceUploadV2Type.CHART_6_MONTH,
            EvidenceUploadV2Type.FOREIGN_FLOW_1W,
        ):
            await connection.execute(
                EvidenceUploadV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    analysis_request_id=request_id,
                    evidence_type=evidence_type,
                    file_path=f"local/{uuid.uuid4()}.png",
                    original_filename=f"{evidence_type.value}.png",
                    mime_type="image/png",
                    size_bytes=10,
                )
            )
    code, _ = await _post_buy(db_session, session_id, email)
    assert code == 201
    assert await _count(db_session, SessionDecisionV2, session_id) == 2
    assert await _count(db_session, EvidenceUploadV2, session_id) == 4
    analysis = await db_session.scalar(
        select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
    )
    assert analysis is not None and analysis.processed_response == {"summary": "preserved"}
    assert await _count(db_session, TradeClosureV2, session_id) == 0


async def test_buy_enforces_ownership_missing_session_and_authentication(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, owner_email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    _, other_session_id, other_email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    cross_code, _ = await _post_buy(db_session, session_id, other_email)
    missing_code, _ = await _post_buy(db_session, uuid.uuid4(), owner_email)
    unauthenticated_code, _ = await _post_buy(db_session, other_session_id, None)
    assert cross_code == 404
    assert missing_code == 404
    assert unauthenticated_code == 401


async def test_concurrent_buy_calls_create_one_decision_and_position(
    engine: AsyncEngine,
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def call() -> int:
        async with factory() as session:
            code, _ = await _post_buy(session, session_id, email)
            return code

    results = await asyncio.gather(call(), call())
    assert sorted(results) == [201, 409]
    async with factory() as session:
        assert await _count(session, SessionDecisionV2, session_id) == 1
        assert await _count(session, PositionV2, session_id) == 1
