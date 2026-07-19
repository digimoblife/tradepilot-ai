"""Job queue result models (TP-0801)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class JobLease:
    """Lease metadata for a claimed job."""

    job_id: uuid.UUID
    worker_id: str
    claimed_at: datetime
    expires_at: datetime
    attempt_number: int


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    """Result of a successful claim."""

    job_id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: str
    attempt_number: int
    lease: JobLease
