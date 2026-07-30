from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Protocol


class AnalysisRequestQueueError(Exception):
    """Base error for the rebuild analysis-request queue boundary."""


class AnalysisRequestQueueSubmissionError(AnalysisRequestQueueError):
    """Raised when the injected transport rejects one enqueue attempt."""


class AnalysisRequestQueueTransport(Protocol):
    """Small transport contract required by the rebuild queue boundary."""

    async def publish(self, payload: bytes) -> None:
        """Publish one already-serialized rebuild queue payload."""


@dataclass(frozen=True, slots=True)
class EnqueuedAnalysisRequest:
    """Result of one successful rebuild queue submission."""

    analysis_request_id: uuid.UUID


class AnalysisRequestQueue:
    """Publish exactly one rebuild analysis-request identifier per call."""

    def __init__(self, transport: AnalysisRequestQueueTransport) -> None:
        self._transport = transport

    async def enqueue(self, *, analysis_request_id: uuid.UUID) -> EnqueuedAnalysisRequest:
        payload = _serialize_payload(analysis_request_id)
        try:
            await self._transport.publish(payload)
        except Exception as exc:
            raise AnalysisRequestQueueSubmissionError(
                "Rebuild analysis request could not be queued"
            ) from exc
        return EnqueuedAnalysisRequest(analysis_request_id=analysis_request_id)


def _serialize_payload(analysis_request_id: uuid.UUID) -> bytes:
    return json.dumps(
        {"analysis_request_id": str(analysis_request_id)},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
