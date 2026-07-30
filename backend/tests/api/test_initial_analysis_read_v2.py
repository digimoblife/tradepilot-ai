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
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database

_CREATED_AT = datetime(2026, 7, 30, 10, 0, tzinfo=timezone.utc)


async def _seed(
    engine: AsyncEngine,
    *,
    request_rows: tuple[dict[str, object], ...] = (),
    session_status: TradeSessionV2Status = TradeSessionV2Status.ANALYZING,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    user_id, session_id = uuid.uuid4(), uuid.uuid4()
    email = f"p55a-{user_id}@example.test"
    async with engine.begin() as connection:
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
                note="Catatan awal",
                status=session_status,
            )
        )
        for row in request_rows:
            await connection.execute(
                AnalysisRequestV2.__table__.insert().values(
                    id=row["id"],
                    session_id=session_id,
                    analysis_type=row.get("analysis_type", AnalysisRequestV2Type.INITIAL_ANALYSIS),
                    observation_period=(
                        "MORNING"
                        if row.get("analysis_type") is AnalysisRequestV2Type.WAIT_UPDATE
                        else None
                    ),
                    current_price=(
                        Decimal("100")
                        if row.get("analysis_type") is AnalysisRequestV2Type.WAIT_UPDATE
                        else None
                    ),
                    observation_at=(
                        _CREATED_AT
                        if row.get("analysis_type") is AnalysisRequestV2Type.WAIT_UPDATE
                        else None
                    ),
                    status=row["status"],
                    provider="gemini",
                    model="gemini-3.1-flash-lite",
                    prompt_version="v1",
                    input_snapshot={"internal": "not exposed"},
                    raw_response=row.get("raw_response"),
                    processed_response=row.get("processed_response"),
                    error_code=row.get("error_code"),
                    error_message=row.get("error_message"),
                    created_at=row.get("created_at", _CREATED_AT),
                    started_at=row.get("started_at"),
                    completed_at=row.get("completed_at"),
                )
            )
    return user_id, session_id, email


def _request_row(
    request_id: uuid.UUID,
    status: AnalysisRequestV2Status,
    **values: object,
) -> dict[str, object]:
    return {"id": request_id, "status": status, **values}


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
        response = await client.get(f"/api/v2/trade-sessions/{session_id}/initial-analysis")
    return response.status_code, response.json()


@pytest.mark.parametrize(
    ("request_status", "session_status", "processed", "error_code", "error_message"),
    [
        (AnalysisRequestV2Status.PENDING, TradeSessionV2Status.ANALYZING, None, None, None),
        (AnalysisRequestV2Status.PROCESSING, TradeSessionV2Status.ANALYZING, None, None, None),
        (
            AnalysisRequestV2Status.COMPLETED,
            TradeSessionV2Status.ANALYZED,
            {"summary": "Ringkasan tersimpan"},
            None,
            None,
        ),
        (
            AnalysisRequestV2Status.FAILED,
            TradeSessionV2Status.DRAFT,
            None,
            "RESPONSE_VALIDATION_FAILED",
            "Analisis tidak dapat diproses",
        ),
    ],
)
async def test_owner_reads_status_specific_safe_initial_analysis_state(
    engine: AsyncEngine,
    db_session: AsyncSession,
    request_status: AnalysisRequestV2Status,
    session_status: TradeSessionV2Status,
    processed: dict[str, object] | None,
    error_code: str | None,
    error_message: str | None,
) -> None:
    request_id = uuid.uuid4()
    _, session_id, email = await _seed(
        engine,
        session_status=session_status,
        request_rows=(
            _request_row(
                request_id,
                request_status,
                processed_response=processed,
                raw_response={"secret": "hidden"},
                error_code=error_code,
                error_message=error_message,
                started_at=(
                    _CREATED_AT
                    if request_status is not AnalysisRequestV2Status.PENDING
                    else None
                ),
                completed_at=(
                    _CREATED_AT
                    if request_status
                    in {AnalysisRequestV2Status.COMPLETED, AnalysisRequestV2Status.FAILED}
                    else None
                ),
            ),
        ),
    )

    status_code, payload = await _get(db_session, session_id, email)

    assert status_code == 200
    assert payload["analysis_request_id"] == str(request_id)
    assert payload["session_id"] == str(session_id)
    assert payload["analysis_type"] == "INITIAL_ANALYSIS"
    assert payload["request_status"] == request_status.value
    assert payload["session_status"] == session_status.value
    assert payload["processed_response"] == processed
    assert payload["error_code"] == error_code
    assert payload["error_message"] == error_message
    assert "raw_response" not in payload
    assert "input_snapshot" not in payload
    assert "provider" not in payload
    assert "model" not in payload


async def test_latest_initial_request_is_deterministic_and_other_types_are_ignored(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    older_id = uuid.UUID("00000000-0000-4000-8000-000000000001")
    latest_id = uuid.UUID("00000000-0000-4000-8000-000000000002")
    _, session_id, email = await _seed(
        engine,
        request_rows=(
            _request_row(
                older_id,
                AnalysisRequestV2Status.FAILED,
                created_at=_CREATED_AT,
                error_code="OLD",
                error_message="old",
            ),
            _request_row(
                latest_id,
                AnalysisRequestV2Status.COMPLETED,
                created_at=_CREATED_AT,
                processed_response={"summary": "Terbaru"},
            ),
            _request_row(
                uuid.uuid4(),
                AnalysisRequestV2Status.PROCESSING,
                analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                created_at=datetime(2026, 7, 30, 11, 0, tzinfo=timezone.utc),
            ),
        ),
        session_status=TradeSessionV2Status.ANALYZED,
    )

    status_code, payload = await _get(db_session, session_id, email)

    assert status_code == 200
    assert payload["analysis_request_id"] == str(latest_id)
    assert payload["processed_response"] == {"summary": "Terbaru"}


@pytest.mark.parametrize("case", ["missing_session", "cross_user", "no_request"])
async def test_safe_not_found_cases(
    engine: AsyncEngine, db_session: AsyncSession, case: str
) -> None:
    if case == "missing_session":
        _, _, email = await _seed(engine)
        session_id = uuid.uuid4()
    elif case == "cross_user":
        _, session_id, _ = await _seed(
            engine,
            request_rows=(
                _request_row(uuid.uuid4(), AnalysisRequestV2Status.COMPLETED),
            ),
        )
        _, _, email = await _seed(engine)
    else:
        _, session_id, email = await _seed(engine)

    status_code, payload = await _get(db_session, session_id, email)
    assert status_code == 404
    assert payload["error"]["code"] == "SESSION_NOT_FOUND"


async def test_unauthenticated_request_is_rejected(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _ = await _seed(engine)
    status_code, payload = await _get(db_session, session_id, None)
    assert status_code in {401, 403}
    assert "analysis_request_id" not in payload


async def test_read_does_not_modify_request_or_create_rows(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    request_id = uuid.uuid4()
    _, session_id, email = await _seed(
        engine,
        request_rows=(_request_row(request_id, AnalysisRequestV2Status.PENDING),),
    )
    before = await db_session.scalar(
        select(AnalysisRequestV2.created_at).where(AnalysisRequestV2.id == request_id)
    )
    status_code, _ = await _get(db_session, session_id, email)
    after = await db_session.scalar(
        select(AnalysisRequestV2.created_at).where(AnalysisRequestV2.id == request_id)
    )
    assert status_code == 200
    assert before == after
