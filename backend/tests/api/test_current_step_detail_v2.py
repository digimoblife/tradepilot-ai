from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.trade_workspace.api.routes.trade_sessions import router as trade_sessions_router
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database


def _valid_initial_result() -> dict[str, object]:
    return {
        "summary": "Ringkasan tersedia",
        "orderbook_analysis": "Valid",
        "three_month_chart_analysis": "Valid",
        "six_month_chart_analysis": "Valid",
        "support": {"value": "valid"},
        "resistance": {"value": "valid"},
        "entry_area": {"value": "valid"},
        "stop_recommendation": {"value": "valid"},
        "target_recommendation": {"value": "valid"},
        "probabilities": {"value": "valid"},
        "risks": ["Valid"],
        "trading_plan": "Valid",
        "conclusion": "Valid",
    }


def _app(db_session: AsyncSession) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(trade_sessions_router)

    async def override_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = override_db
    return app


async def test_detail_adds_owner_scoped_current_step_without_removing_fields(
    engine: AsyncEngine,
) -> None:
    owner_id, other_id, session_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    owner_email = f"current-step-owner-{owner_id}@example.test"
    other_email = f"current-step-other-{other_id}@example.test"
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        db.add_all(
            [
                User(
                    id=owner_id,
                    email=owner_email,
                    password_hash=hash_password("testpass123"),
                ),
                User(
                    id=other_id,
                    email=other_email,
                    password_hash=hash_password("testpass123"),
                ),
                TradeSessionV2(
                    id=session_id,
                    user_id=owner_id,
                    ticker="BBRI",
                    company_name="Bank BRI",
                    status=TradeSessionV2Status.DRAFT,
                ),
            ]
        )
        await db.commit()

        app = _app(db)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            unauthenticated = await client.get(
                f"/api/v2/trade-sessions/{session_id}/detail"
            )
            assert unauthenticated.status_code == 401

            other_login = await client.post(
                "/api/auth/login",
                json={"email": other_email, "password": "testpass123"},
            )
            assert other_login.status_code == 200
            cross_owner = await client.get(
                f"/api/v2/trade-sessions/{session_id}/detail"
            )
            assert cross_owner.status_code == 404

            await client.post("/api/auth/logout")
            owner_login = await client.post(
                "/api/auth/login",
                json={"email": owner_email, "password": "testpass123"},
            )
            assert owner_login.status_code == 200
            response = await client.get(
                f"/api/v2/trade-sessions/{session_id}/detail"
            )

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {
            "session",
            "initial_evidence",
            "initial_analysis",
            "decisions",
            "wait_updates",
            "position",
            "position_updates",
            "closure",
            "current_step",
            "latest_analysis",
            "recent_activity",
        }
        assert payload["current_step"] == {
            "code": "INITIAL_EVIDENCE",
            "mode": "ACTIONABLE",
            "workflow_actions": ["SUBMIT_INITIAL_EVIDENCE"],
            "active_request": None,
            "failed_request": None,
            "read_only": False,
        }
        assert payload["latest_analysis"] is None
        assert len(payload["recent_activity"]) == 1
        assert payload["recent_activity"][0]["type"] == "SESSION_CREATED"


async def test_detail_exposes_typed_safe_latest_analysis_without_raw_result(
    engine: AsyncEngine,
) -> None:
    owner_id, session_id = uuid.uuid4(), uuid.uuid4()
    email = f"summary-owner-{owner_id}@example.test"
    completed_at = datetime(2026, 8, 5, tzinfo=timezone.utc)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        db.add_all(
            [
                User(id=owner_id, email=email, password_hash=hash_password("testpass123")),
                TradeSessionV2(
                    id=session_id,
                    user_id=owner_id,
                    ticker="BBRI",
                    company_name="Bank BRI",
                    status=TradeSessionV2Status.DRAFT,
                ),
            ]
        )
        await db.flush()
        db.add(
            AnalysisRequestV2(
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                status=AnalysisRequestV2Status.COMPLETED,
                provider="gemini",
                model="test-model",
                prompt_version="v1",
                input_snapshot={},
                processed_response=_valid_initial_result(),
                completed_at=completed_at,
            )
        )
        await db.commit()
        app = _app(db)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            login = await client.post(
                "/api/auth/login", json={"email": email, "password": "testpass123"}
            )
            assert login.status_code == 200
            response = await client.get(f"/api/v2/trade-sessions/{session_id}/detail")

    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_analysis"] == {
        "analysis_type": "INITIAL_ANALYSIS",
        "completed_at": "2026-08-05T00:00:00Z",
        "has_result": True,
    }
    assert all("processed_response" not in item for item in payload["recent_activity"])
