from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database

OBSERVATION = datetime(2026, 7, 30, 2, 15, tzinfo=timezone.utc)


async def _seed_user_and_session(
    engine: AsyncEngine,
    *,
    status: TradeSessionV2Status = TradeSessionV2Status.OPEN_POSITION,
    position_status: PositionV2Status | None = PositionV2Status.OPEN,
    owner: tuple[uuid.UUID, str] | None = None,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID | None, str]:
    if owner is None:
        user_id, email = uuid.uuid4(), f"p85a-{uuid.uuid4()}@example.test"
        create_user = True
    else:
        user_id, email = owner
        create_user = False
    session_id = uuid.uuid4()
    position_id = uuid.uuid4() if position_status is not None else None
    async with engine.begin() as connection:
        if create_user:
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
        if position_id is not None:
            await connection.execute(
                PositionV2.__table__.insert().values(
                    id=position_id,
                    session_id=session_id,
                    entry_price=Decimal("1200.000000"),
                    entry_at=datetime(2026, 7, 29, 2, tzinfo=timezone.utc),
                    quantity=Decimal("10.000000"),
                    stop_loss=Decimal("1100.000000"),
                    target_price=Decimal("1400.000000"),
                    note="Open position note",
                    status=position_status,
                )
            )
    return user_id, session_id, position_id, email


async def _add_analysis_request(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    *,
    analysis_type: AnalysisRequestV2Type = AnalysisRequestV2Type.POSITION_UPDATE,
    status: AnalysisRequestV2Status = AnalysisRequestV2Status.COMPLETED,
    created_at: datetime | None = None,
    current_price: Decimal | None = Decimal("1250.000000"),
    observation_period: AnalysisRequestV2ObservationPeriod | None = AnalysisRequestV2ObservationPeriod.MIDDAY,
    processed_response: dict[str, object] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> uuid.UUID:
    request_id = uuid.uuid4()
    values: dict[str, object] = {
        "id": request_id,
        "session_id": session_id,
        "analysis_type": analysis_type,
        "observation_period": observation_period,
        "current_price": current_price,
        "observation_at": OBSERVATION,
        "status": status,
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "prompt_version": "v2",
        "input_snapshot": {"ticker": "BBRI"},
        "processed_response": processed_response,
        "error_code": error_code,
        "error_message": error_message,
    }
    if created_at is not None:
        values["created_at"] = created_at
    async with engine.begin() as connection:
        await connection.execute(AnalysisRequestV2.__table__.insert().values(**values))
    return request_id


def _build_app(engine: AsyncEngine) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_db() -> AsyncSession:
        async with session_maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db_session] = _override_db
    return app


async def _login(client: AsyncClient, email: str) -> None:
    res = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_position_update_read_contract(engine: AsyncEngine) -> None:
    user_id, session_id, position_id, email = await _seed_user_and_session(engine)

    t1 = datetime(2026, 7, 30, 9, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 7, 30, 13, 0, tzinfo=timezone.utc)

    # 1. Initial Analysis (should be excluded)
    await _add_analysis_request(
        engine,
        session_id,
        analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
        status=AnalysisRequestV2Status.COMPLETED,
        created_at=t1,
        current_price=None,
        observation_period=None,
    )

    # 2. WAIT Update (should be excluded)
    await _add_analysis_request(
        engine,
        session_id,
        analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
        status=AnalysisRequestV2Status.COMPLETED,
        created_at=t1,
        current_price=Decimal("1180.000000"),
        observation_period=AnalysisRequestV2ObservationPeriod.MORNING,
    )

    # 3. Position Update 1 (Completed)
    req1_id = await _add_analysis_request(
        engine,
        session_id,
        analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
        status=AnalysisRequestV2Status.COMPLETED,
        created_at=t1,
        current_price=Decimal("1250.000000"),
        observation_period=AnalysisRequestV2ObservationPeriod.MORNING,
        processed_response={"update_summary": "Kondisi stabil."},
    )

    # 4. Position Update 2 (Failed)
    req2_id = await _add_analysis_request(
        engine,
        session_id,
        analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
        status=AnalysisRequestV2Status.FAILED,
        created_at=t2,
        current_price=Decimal("1270.000000"),
        observation_period=AnalysisRequestV2ObservationPeriod.MIDDAY,
        error_code="GEMINI_API_ERROR",
        error_message="Timeout.",
    )

    app = _build_app(engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)

        res = await client.get(f"/api/v2/trade-sessions/{session_id}/position-updates")
        assert res.status_code == 200
        payload = res.json()

        # Check top-level structure
        assert "position" in payload
        assert "updates" in payload

        # Check Position facts match stored PositionV2 facts exactly (Test cases 1, 2, 3, 15)
        pos = payload["position"]
        assert pos is not None
        assert pos["id"] == str(position_id)
        assert pos["session_id"] == str(session_id)
        assert pos["status"] == "OPEN"
        assert Decimal(str(pos["entry_price"])) == Decimal("1200.000000")
        assert Decimal(str(pos["quantity"])) == Decimal("10.000000")
        assert Decimal(str(pos["stop_loss"])) == Decimal("1100.000000")
        assert Decimal(str(pos["target_price"])) == Decimal("1400.000000")

        # Check Updates filtering and chronological order (Test cases 4, 5, 6, 7, 8, 9, 10, 13, 14)
        updates = payload["updates"]
        assert len(updates) == 2
        assert updates[0]["analysis_request_id"] == str(req1_id)
        assert updates[0]["analysis_type"] == "POSITION_UPDATE"
        assert updates[0]["request_status"] == "COMPLETED"
        assert updates[0]["processed_response"] == {"update_summary": "Kondisi stabil."}

        assert updates[1]["analysis_request_id"] == str(req2_id)
        assert updates[1]["analysis_type"] == "POSITION_UPDATE"
        assert updates[1]["request_status"] == "FAILED"
        assert updates[1]["error_code"] == "GEMINI_API_ERROR"
        assert updates[1]["error_message"] == "Timeout."

        # Check non-owner access (Test case 11)
        other_user_id, _, _, other_email = await _seed_user_and_session(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other_client:
        await _login(other_client, other_email)
        res_forbidden = await other_client.get(f"/api/v2/trade-sessions/{session_id}/position-updates")
        assert res_forbidden.status_code == 404

        # Check non-existent session (Test case 12)
        res_missing = await other_client.get(f"/api/v2/trade-sessions/{uuid.uuid4()}/position-updates")
        assert res_missing.status_code == 404
