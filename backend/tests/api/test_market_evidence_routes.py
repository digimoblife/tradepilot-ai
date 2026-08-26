"""API route tests for Market Evidence endpoints (Fase 5).

Verifies /preview, /acquire, and /delta REST endpoints with mock sessions and providers.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.schemas.evidence_snapshot import (
    EvidenceSnapshotSchema,
    PriceDelta,
)
from app.database.session import get_db_session
from app.main import app
from app.services.evidence_validator import ValidationResult
from tests.services.test_prompt_context_integration import _create_sample_snapshot


@pytest.mark.asyncio
async def test_preview_market_evidence_success() -> None:
    session_id = uuid.uuid4()
    mock_snapshot = _create_sample_snapshot()
    mock_val_result = ValidationResult(
        is_valid=True,
        completeness_status="COMPLETE",
        critical_errors=[],
        warnings=[],
    )

    mock_db = AsyncMock()
    mock_session_obj = MagicMock()
    mock_session_obj.id = session_id
    mock_session_obj.ticker = "BBCA"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_session_obj
    mock_db.execute.return_value = mock_result

    with (
        patch("app.api.routes.market_evidence.MarketDataCollector.acquire_snapshot", new_callable=AsyncMock) as mock_acquire,
    ):
        mock_acquire.return_value = (mock_snapshot, mock_val_result)
        app.dependency_overrides[get_db_session] = lambda: mock_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/sessions/{session_id}/market-evidence/preview")

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot"]["symbol"] == "BBCA"
        assert data["validation"]["is_valid"] is True
        assert data["validation"]["completeness_status"] == "COMPLETE"


@pytest.mark.asyncio
async def test_compute_evidence_delta_endpoint() -> None:
    session_id = uuid.uuid4()
    base_snapshot = _create_sample_snapshot()
    current_snapshot = _create_sample_snapshot()
    current_snapshot.snapshot_id = "SNP-20260826-BBCA-002"
    current_snapshot.quote.last_price = 6400.0

    payload = {
        "base_snapshot": base_snapshot.model_dump(mode="json"),
        "current_snapshot": current_snapshot.model_dump(mode="json"),
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/sessions/{session_id}/market-evidence/delta",
            json=payload,
        )

    assert response.status_code == 200
    data = response.json()
    assert "delta" in data
    assert data["delta"]["price_delta"]["previous_price"] == 6325.0
    assert data["delta"]["price_delta"]["current_price"] == 6400.0
    assert data["delta"]["price_delta"]["diff"] == 75.0
