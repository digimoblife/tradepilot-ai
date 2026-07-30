from __future__ import annotations

import json
import uuid

import pytest

from app.trade_workspace.queue.analysis_request_queue import (
    AnalysisRequestQueue,
    AnalysisRequestQueueSubmissionError,
)


class FakeTransport:
    def __init__(self) -> None:
        self.payloads: list[bytes] = []

    async def publish(self, payload: bytes) -> None:
        self.payloads.append(payload)


class FailingTransport:
    def __init__(self) -> None:
        self.calls = 0

    async def publish(self, payload: bytes) -> None:
        self.calls += 1
        raise RuntimeError("transport secret=should-not-leak")


@pytest.mark.asyncio
async def test_enqueue_publishes_one_request_identifier_only() -> None:
    transport = FakeTransport()
    request_id = uuid.uuid4()

    result = await AnalysisRequestQueue(transport).enqueue(analysis_request_id=request_id)

    assert result.analysis_request_id == request_id
    assert len(transport.payloads) == 1
    assert json.loads(transport.payloads[0]) == {"analysis_request_id": str(request_id)}


@pytest.mark.asyncio
async def test_enqueue_failure_is_sanitized_and_not_retried() -> None:
    transport = FailingTransport()

    with pytest.raises(AnalysisRequestQueueSubmissionError) as exc_info:
        await AnalysisRequestQueue(transport).enqueue(analysis_request_id=uuid.uuid4())

    assert transport.calls == 1
    assert str(exc_info.value) == "Rebuild analysis request could not be queued"
    assert "should-not-leak" not in str(exc_info.value)
