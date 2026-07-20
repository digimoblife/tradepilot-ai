"""Context Rebuild Coordinator (TP-0904).

Integrates TP-0903 ``ensure_fresh()`` into existing material workflows
so that Context Summary is rebuilt after every material longitudinal event.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.context import ContextFreshnessEnsureResult, ContextFreshnessService


class ContextRebuildReason(StrEnum):
    ANALYSIS_ACCEPTED = "ANALYSIS_ACCEPTED"
    POSITION_OPENED = "POSITION_OPENED"
    STOP_LOSS_CHANGED = "STOP_LOSS_CHANGED"
    TARGET_CHANGED = "TARGET_CHANGED"
    PARTIAL_EXIT = "PARTIAL_EXIT"
    FULL_EXIT = "FULL_EXIT"
    EVIDENCE_REPLACED = "EVIDENCE_REPLACED"


@dataclass(frozen=True, slots=True)
class ContextRebuildResult:
    session_id: uuid.UUID
    reason: ContextRebuildReason
    context_summary_id: uuid.UUID
    context_version: int
    source_cutoff: datetime
    rebuilt: bool


class ContextRebuildError(Exception):
    code: str = "CONTEXT_REBUILD_TRIGGER_FAILED"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class ContextRebuildService:
    """Thin coordinator around TP-0903 for material workflow integration."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._freshness = ContextFreshnessService(session)

    async def rebuild_after_material_event(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        reason: ContextRebuildReason,
        source_id: uuid.UUID | None = None,
    ) -> ContextRebuildResult:
        """Ensure a fresh Context Summary exists after a material event.

        Calls TP-0903's ``ensure_fresh()`` which detects stale or missing
        summaries and rebuilds through TP-0902 when needed.

        Raises
        ------
        ContextRebuildError
            If the rebuild itself fails.  The underlying TP-0903 error code
            is preserved in the message.
        """
        try:
            result: ContextFreshnessEnsureResult = await self._freshness.ensure_fresh(
                session_id=session_id,
                owner_id=owner_id,
            )
        except Exception as exc:
            raise ContextRebuildError(
                code=getattr(exc, "code", CONTEXT_REBUILD_TRIGGER_FAILED),
                message=f"Context rebuild failed after {reason.value}: {exc}",
            ) from exc

        return ContextRebuildResult(
            session_id=session_id,
            reason=reason,
            context_summary_id=result.context_summary_id,
            context_version=result.context_version,
            source_cutoff=result.source_cutoff,
            rebuilt=result.rebuilt,
        )


CONTEXT_REBUILD_TRIGGER_FAILED = "CONTEXT_REBUILD_TRIGGER_FAILED"
