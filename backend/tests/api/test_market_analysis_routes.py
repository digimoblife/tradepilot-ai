"""HTTP-level tests for the live /api/sessions/{id}/analyze and /workspace routes.

These endpoints back ModernSessionWorkspace (the frontend surface actually
reachable at /sessions/[sessionId]) and drive MarketAnalysisEngine, which now
calls Gemini. Every test here mocks the two external I/O boundaries —
MarketDataCollector.acquire_snapshot (ZAPI) and MarketAnalysisEngine.analyze
(Gemini) — and exercises real database rows, so route wiring (session lookup,
position/closure/decision assembly, caching, error handling) is verified
without any live network call.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.auth import hash_password
from app.database.session import get_db_session
from app.main import app
from app.models.user import User
from app.services.market_analysis_engine import MarketAnalysisEngineError
from app.services.market_data.zapi_client import ZapiClientError
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from tests.services.test_prompt_context_integration import _create_sample_snapshot

pytestmark = pytest.mark.database

_ANALYSIS_RESULT = {
    "symbol": "BBCA",
    "session_id": "placeholder",
    "action": "WAIT",
    "signal_quality": "SPECULATIVE",
    "confidence_score": 45,
    "trading_style": "Swing Trade",
    "is_in_trade": False,
    "key_levels": {"current_price": 6325.0, "atr14": 150.0},
    "reasoning": {"thesis": "Gemini thesis text"},
    "market_evidence": {},
    "analyzed_at": "2026-09-13T00:00:00+00:00",
}


async def _seed_session(
    engine: AsyncEngine,
    *,
    status: TradeSessionV2Status = TradeSessionV2Status.ANALYZED,
    with_position: bool = False,
    position_status: PositionV2Status = PositionV2Status.OPEN,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    email = f"market-analysis-{uuid.uuid4()}@example.test"
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
                ticker="BBCA",
                company_name="Bank Central Asia Tbk",
                status=status,
            )
        )
        if with_position:
            await connection.execute(
                PositionV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    entry_price=Decimal("6200.000000"),
                    entry_at=datetime(2026, 9, 8, 2, tzinfo=timezone.utc),
                    quantity=Decimal("10.000000"),
                    stop_loss=Decimal("6000.000000"),
                    target_price=Decimal("6500.000000"),
                    status=position_status,
                )
            )
    return user_id, session_id, email


def _client(db_session: AsyncSession) -> AsyncClient:
    async def _override() -> AsyncSession:
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_analyze_pre_trade_calls_engine_with_no_position(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _ = await _seed_session(engine, status=TradeSessionV2Status.ANALYZED)
    snapshot = _create_sample_snapshot()

    with (
        patch(
            "app.api.routes.market_evidence.MarketDataCollector.acquire_snapshot",
            new_callable=AsyncMock,
        ) as mock_acquire,
        patch(
            "app.api.routes.market_evidence.MarketAnalysisEngine.analyze",
            new_callable=AsyncMock,
        ) as mock_analyze,
    ):
        mock_acquire.return_value = (snapshot, object())
        mock_analyze.return_value = {**_ANALYSIS_RESULT, "session_id": str(session_id)}

        async with _client(db_session) as client:
            response = await client.post(f"/api/sessions/{session_id}/analyze")

        assert response.status_code == 200
        assert response.json()["action"] == "WAIT"
        assert mock_analyze.await_args.kwargs["position"] is None


@pytest.mark.asyncio
async def test_analyze_in_trade_passes_open_position_to_engine(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _ = await _seed_session(
        engine, status=TradeSessionV2Status.OPEN_POSITION, with_position=True
    )
    snapshot = _create_sample_snapshot()

    with (
        patch(
            "app.api.routes.market_evidence.MarketDataCollector.acquire_snapshot",
            new_callable=AsyncMock,
        ) as mock_acquire,
        patch(
            "app.api.routes.market_evidence.MarketAnalysisEngine.analyze",
            new_callable=AsyncMock,
        ) as mock_analyze,
    ):
        mock_acquire.return_value = (snapshot, object())
        mock_analyze.return_value = {
            **_ANALYSIS_RESULT,
            "session_id": str(session_id),
            "action": "HOLD",
            "is_in_trade": True,
        }

        async with _client(db_session) as client:
            response = await client.post(f"/api/sessions/{session_id}/analyze")

        assert response.status_code == 200
        assert response.json()["action"] == "HOLD"
        position_arg = mock_analyze.await_args.kwargs["position"]
        assert position_arg is not None
        assert position_arg["status"] == "OPEN"
        assert float(position_arg["entry_price"]) == 6200.0


@pytest.mark.asyncio
async def test_analyze_returns_404_for_missing_session(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    async with _client(db_session) as client:
        response = await client.post(f"/api/sessions/{uuid.uuid4()}/analyze")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyze_returns_502_when_zapi_acquisition_fails(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _ = await _seed_session(engine)

    with patch(
        "app.api.routes.market_evidence.MarketDataCollector.acquire_snapshot",
        new_callable=AsyncMock,
    ) as mock_acquire:
        mock_acquire.side_effect = ZapiClientError("ZAPI unavailable")

        async with _client(db_session) as client:
            response = await client.post(f"/api/sessions/{session_id}/analyze")

        assert response.status_code == 502


@pytest.mark.asyncio
async def test_analyze_returns_502_when_gemini_analysis_fails(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _ = await _seed_session(engine)
    snapshot = _create_sample_snapshot()

    with (
        patch(
            "app.api.routes.market_evidence.MarketDataCollector.acquire_snapshot",
            new_callable=AsyncMock,
        ) as mock_acquire,
        patch(
            "app.api.routes.market_evidence.MarketAnalysisEngine.analyze",
            new_callable=AsyncMock,
        ) as mock_analyze,
    ):
        mock_acquire.return_value = (snapshot, object())
        mock_analyze.side_effect = MarketAnalysisEngineError("Gemini API key is not configured.")

        async with _client(db_session) as client:
            response = await client.post(f"/api/sessions/{session_id}/analyze")

        assert response.status_code == 502


@pytest.mark.asyncio
async def test_workspace_reuses_cached_analysis_without_refresh(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _ = await _seed_session(engine, status=TradeSessionV2Status.ANALYZED)
    snapshot = _create_sample_snapshot()

    with (
        patch(
            "app.api.routes.market_evidence.MarketDataCollector.acquire_snapshot",
            new_callable=AsyncMock,
        ) as mock_acquire,
        patch(
            "app.api.routes.market_evidence.MarketAnalysisEngine.analyze",
            new_callable=AsyncMock,
        ) as mock_analyze,
    ):
        mock_acquire.return_value = (snapshot, object())
        mock_analyze.return_value = {**_ANALYSIS_RESULT, "session_id": str(session_id)}

        async with _client(db_session) as client:
            first = await client.get(f"/api/sessions/{session_id}/workspace")
            second = await client.get(f"/api/sessions/{session_id}/workspace")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["analysis"]["action"] == "WAIT"
        assert second.json()["analysis"]["action"] == "WAIT"
        assert first.json()["session"]["ticker"] == "BBCA"
        # Second GET must reuse the cached analysis rather than calling Gemini again.
        assert mock_analyze.await_count == 1


@pytest.mark.asyncio
async def test_workspace_refresh_true_forces_new_analysis(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _ = await _seed_session(engine, status=TradeSessionV2Status.ANALYZED)
    snapshot = _create_sample_snapshot()

    with (
        patch(
            "app.api.routes.market_evidence.MarketDataCollector.acquire_snapshot",
            new_callable=AsyncMock,
        ) as mock_acquire,
        patch(
            "app.api.routes.market_evidence.MarketAnalysisEngine.analyze",
            new_callable=AsyncMock,
        ) as mock_analyze,
    ):
        mock_acquire.return_value = (snapshot, object())
        mock_analyze.return_value = {**_ANALYSIS_RESULT, "session_id": str(session_id)}

        async with _client(db_session) as client:
            await client.get(f"/api/sessions/{session_id}/workspace")
            await client.get(f"/api/sessions/{session_id}/workspace?refresh=true")

        assert mock_analyze.await_count == 2


@pytest.mark.asyncio
async def test_workspace_returns_404_for_missing_session(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    async with _client(db_session) as client:
        response = await client.get(f"/api/sessions/{uuid.uuid4()}/workspace")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_workspace_includes_open_position_details(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _ = await _seed_session(
        engine, status=TradeSessionV2Status.OPEN_POSITION, with_position=True
    )
    snapshot = _create_sample_snapshot()

    with (
        patch(
            "app.api.routes.market_evidence.MarketDataCollector.acquire_snapshot",
            new_callable=AsyncMock,
        ) as mock_acquire,
        patch(
            "app.api.routes.market_evidence.MarketAnalysisEngine.analyze",
            new_callable=AsyncMock,
        ) as mock_analyze,
    ):
        mock_acquire.return_value = (snapshot, object())
        mock_analyze.return_value = {
            **_ANALYSIS_RESULT,
            "session_id": str(session_id),
            "is_in_trade": True,
        }

        async with _client(db_session) as client:
            response = await client.get(f"/api/sessions/{session_id}/workspace")

        assert response.status_code == 200
        payload = response.json()
        assert payload["position"] is not None
        assert payload["position"]["status"] == "OPEN"
        assert payload["closure"] is None
        assert payload["decision"] is None
