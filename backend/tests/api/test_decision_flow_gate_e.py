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
    SessionDecisionV2Reason,
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
    "note": "confirmed by user",
}


async def _seed_user(engine: AsyncEngine) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    email = f"gate-e-{user_id}@example.test"
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


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _request(
    db_session: AsyncSession,
    path: str,
    email: str | None,
    *,
    method: str = "GET",
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
        response = await client.request(method, path, json=body)
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


async def test_gate_e_availability_is_exact_read_only_and_session_scoped(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    user_id, email = await _seed_user(engine)
    statuses = [
        TradeSessionV2Status.ANALYZED,
        TradeSessionV2Status.WAITING,
        TradeSessionV2Status.OPEN_POSITION,
        TradeSessionV2Status.DRAFT,
        TradeSessionV2Status.ANALYZING,
        TradeSessionV2Status.CLOSED,
        TradeSessionV2Status.CLOSED_SKIPPED,
    ]
    session_ids = [await _seed_session(engine, user_id, status) for status in statuses]
    expected = [
        ["BUY", "WAIT", "SKIP"],
        ["BUY", "WAIT", "SKIP"],
        ["CLOSE"],
        [],
        [],
        [],
        [],
    ]
    for session_id, status, actions in zip(session_ids, statuses, expected, strict=True):
        code, payload = await _request(
            db_session,
            f"/api/v2/trade-sessions/{session_id}/available-actions",
            email,
        )
        assert code == 200
        assert payload == {
            "session_id": str(session_id),
            "session_status": status.value,
            "available_actions": actions,
        }
    assert await db_session.scalar(select(func.count()).select_from(SessionDecisionV2)) == 0
    assert await db_session.scalar(select(func.count()).select_from(PositionV2)) == 0
    statuses_after = list(
        (
            await db_session.scalars(
                select(TradeSessionV2.status).where(TradeSessionV2.user_id == user_id)
            )
        ).all()
    )
    assert sorted(status.value for status in statuses_after) == sorted(
        status.value for status in statuses
    )


async def test_gate_e_wait_is_auditable_and_preserves_related_data(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    user_id, email = await _seed_user(engine)
    session_id = await _seed_session(engine, user_id, TradeSessionV2Status.ANALYZED)
    request_id = uuid.uuid4()
    async with engine.begin() as connection:
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
        for evidence_type in EvidenceUploadV2Type:
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
    wait_path = f"/api/v2/trade-sessions/{session_id}/decisions/wait"
    code, first = await _request(db_session, wait_path, email, method="POST")
    assert code == 201 and first["decision_type"] == "WAIT"
    code, second = await _request(db_session, wait_path, email, method="POST")
    assert code == 201 and second["decision_id"] != first["decision_id"]
    assert await _count(db_session, SessionDecisionV2, session_id) == 2
    decisions = list(
        (
            await db_session.scalars(
                select(SessionDecisionV2)
                .where(SessionDecisionV2.session_id == session_id)
                .order_by(SessionDecisionV2.created_at, SessionDecisionV2.id)
            )
        ).all()
    )
    assert [decision.decision for decision in decisions] == [
        SessionDecisionV2Decision.WAIT,
        SessionDecisionV2Decision.WAIT,
    ]
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None and session.status is TradeSessionV2Status.WAITING
    assert session.closed_at is None
    assert await _count(db_session, PositionV2, session_id) == 0
    assert await _count(db_session, TradeClosureV2, session_id) == 0
    assert await _count(db_session, AnalysisRequestV2, session_id) == 1
    assert await _count(db_session, EvidenceUploadV2, session_id) == 3
    code, availability = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/available-actions",
        email,
    )
    assert code == 200 and availability["available_actions"] == ["BUY", "WAIT", "SKIP"]


async def test_gate_e_skip_requires_reason_persists_note_and_is_terminal(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    user_id, email = await _seed_user(engine)
    session_id = await _seed_session(engine, user_id, TradeSessionV2Status.WAITING)
    path = f"/api/v2/trade-sessions/{session_id}/decisions/skip"
    code, _ = await _request(db_session, path, email, method="POST", body={})
    assert code == 422
    code, _ = await _request(
        db_session, path, email, method="POST", body={"reason": "UNSUPPORTED"}
    )
    assert code == 422
    code, payload = await _request(
        db_session,
        path,
        email,
        method="POST",
        body={"reason": "RISK_TOO_HIGH", "note": "Risk is outside my limit"},
    )
    assert code == 201
    assert payload["reason"] == "RISK_TOO_HIGH"
    assert payload["note"] == "Risk is outside my limit"
    assert payload["session_status"] == "CLOSED_SKIPPED"
    assert await _count(db_session, SessionDecisionV2, session_id) == 1
    decision = await db_session.scalar(
        select(SessionDecisionV2).where(SessionDecisionV2.session_id == session_id)
    )
    assert decision is not None
    assert decision.decision is SessionDecisionV2Decision.SKIP
    assert decision.reason is SessionDecisionV2Reason.RISK_TOO_HIGH
    assert decision.note == "Risk is outside my limit"
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None and session.status is TradeSessionV2Status.CLOSED_SKIPPED
    assert session.closed_at is not None
    assert await _count(db_session, PositionV2, session_id) == 0
    assert await _count(db_session, TradeClosureV2, session_id) == 0
    assert await _count(db_session, AnalysisRequestV2, session_id) == 0
    code, availability = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/available-actions",
        email,
    )
    assert code == 200 and availability["available_actions"] == []
    code, error = await _request(db_session, path, email, method="POST", body={"reason": "OTHER"})
    assert code == 409 and error["error"]["code"] == "SKIP_NOT_ALLOWED"


async def test_gate_e_buy_preserves_facts_creates_one_position_and_rejects_repeat(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    user_id, email = await _seed_user(engine)
    session_id = await _seed_session(engine, user_id, TradeSessionV2Status.ANALYZED)
    path = f"/api/v2/trade-sessions/{session_id}/decisions/buy"
    code, payload = await _request(db_session, path, email, method="POST", body=BUY_BODY)
    assert code == 201
    assert payload["decision_type"] == "BUY"
    assert payload["position_status"] == "OPEN"
    assert payload["session_status"] == "OPEN_POSITION"
    assert payload["entry_price"] == "101.234500"
    assert payload["entry_timestamp"] == "2026-07-30T09:15:00.123456Z"
    assert payload["quantity"] == "12.500000"
    assert payload["stop_loss"] == "95.125000"
    assert payload["target_price"] == "120.750000"
    assert payload["note"] == "confirmed by user"
    assert await _count(db_session, SessionDecisionV2, session_id) == 1
    assert await _count(db_session, PositionV2, session_id) == 1
    position = await db_session.scalar(
        select(PositionV2).where(PositionV2.session_id == session_id)
    )
    assert position is not None and position.status is PositionV2Status.OPEN
    assert position.entry_price == Decimal("101.234500")
    assert position.entry_at == datetime(2026, 7, 30, 9, 15, 0, 123456, tzinfo=timezone.utc)
    assert position.quantity == Decimal("12.500000")
    assert position.stop_loss == Decimal("95.125000")
    assert position.target_price == Decimal("120.750000")
    code, error = await _request(db_session, path, email, method="POST", body=BUY_BODY)
    assert code == 409 and error["error"]["code"] == "BUY_NOT_ALLOWED"
    existing_position_session = await _seed_session(
        engine, user_id, TradeSessionV2Status.ANALYZED
    )
    async with engine.begin() as connection:
        await connection.execute(
            PositionV2.__table__.insert().values(
                id=uuid.uuid4(),
                session_id=existing_position_session,
                entry_price=Decimal("100"),
                entry_at=datetime.now(timezone.utc),
                quantity=Decimal("1"),
                stop_loss=Decimal("95"),
                target_price=Decimal("110"),
                status=PositionV2Status.OPEN,
            )
        )
    existing_code, existing_error = await _request(
        db_session,
        f"/api/v2/trade-sessions/{existing_position_session}/decisions/buy",
        email,
        method="POST",
        body=BUY_BODY,
    )
    assert existing_code == 409
    assert existing_error["error"]["code"] == "BUY_POSITION_EXISTS"
    code, availability = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/available-actions",
        email,
    )
    assert code == 200 and availability["available_actions"] == ["CLOSE"]
    assert await _count(db_session, TradeClosureV2, session_id) == 0
    assert await _count(db_session, AnalysisRequestV2, session_id) == 0


async def test_gate_e_ownership_isolation_covers_all_decision_endpoints(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    owner_id, owner_email = await _seed_user(engine)
    _, other_email = await _seed_user(engine)
    session_id = await _seed_session(engine, owner_id, TradeSessionV2Status.ANALYZED)
    base = f"/api/v2/trade-sessions/{session_id}"
    requests = [
        (f"{base}/available-actions", "GET", None),
        (f"{base}/decisions/wait", "POST", None),
        (f"{base}/decisions/skip", "POST", {"reason": "OTHER"}),
        (f"{base}/decisions/buy", "POST", BUY_BODY),
    ]
    for path, method, body in requests:
        code, payload = await _request(db_session, path, other_email, method=method, body=body)
        assert code == 404
        assert payload["error"]["code"] == "SESSION_NOT_FOUND"
    assert await _count(db_session, SessionDecisionV2, session_id) == 0
    assert await _count(db_session, PositionV2, session_id) == 0
    assert owner_email != other_email


async def _concurrent_action(
    factory: async_sessionmaker[AsyncSession],
    session_id: uuid.UUID,
    email: str,
    path: str,
    body: dict[str, object] | None,
) -> int:
    async with factory() as session:
        code, _ = await _request(
            session,
            f"/api/v2/trade-sessions/{session_id}{path}",
            email,
            method="POST",
            body=body,
        )
        return code


async def test_gate_e_concurrent_skip_and_buy_are_session_scoped(
    engine: AsyncEngine,
) -> None:
    user_id, email = await _seed_user(engine)
    skip_session = await _seed_session(engine, user_id, TradeSessionV2Status.ANALYZED)
    buy_session = await _seed_session(engine, user_id, TradeSessionV2Status.ANALYZED)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    skip_results = await asyncio.gather(
        _concurrent_action(factory, skip_session, email, "/decisions/skip", {"reason": "OTHER"}),
        _concurrent_action(factory, skip_session, email, "/decisions/skip", {"reason": "OTHER"}),
    )
    buy_results = await asyncio.gather(
        _concurrent_action(factory, buy_session, email, "/decisions/buy", BUY_BODY),
        _concurrent_action(factory, buy_session, email, "/decisions/buy", BUY_BODY),
    )
    assert sorted(skip_results) == [201, 409]
    assert sorted(buy_results) == [201, 409]
    async with factory() as session:
        assert await _count(session, SessionDecisionV2, skip_session) == 1
        assert await _count(session, TradeClosureV2, skip_session) == 0
        assert await _count(session, SessionDecisionV2, buy_session) == 1
        assert await _count(session, PositionV2, buy_session) == 1
        skip_state = await session.scalar(
            select(TradeSessionV2.status).where(TradeSessionV2.id == skip_session)
        )
        buy_state = await session.scalar(
            select(TradeSessionV2.status).where(TradeSessionV2.id == buy_session)
        )
        assert skip_state is TradeSessionV2Status.CLOSED_SKIPPED
        assert buy_state is TradeSessionV2Status.OPEN_POSITION
