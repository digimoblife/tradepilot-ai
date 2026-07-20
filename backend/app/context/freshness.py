"""Context Freshness Service (TP-0903).

Determines whether the latest persisted Context Summary is safe to use
for a new analysis by comparing its source cutoff against newer material
session data, and rebuilds stale or missing summaries through TP-0902.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from app.context.builder import (
    ContextSummaryBuilder,
)
from app.context.history_selector import (
    _CONFIRMED_EVENT_TYPES,
    _LIFECYCLE_EVENT_TYPES,
)
from app.models.context_summary import ContextSummary
from app.models.enums import (
    AcceptanceStatus,
    ContextQuality,
    EvidenceType,
)
from app.models.session_event import SessionEvent
from app.repositories.analysis import AnalysisRepository
from app.repositories.context_summary import ContextSummaryRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.session_event import SessionEventRepository
from app.repositories.trade_action import TradeActionRepository
from app.repositories.trade_session import TradeSessionRepository

# ---------------------------------------------------------------------------
# Typed result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContextStaleReason:
    """One deterministic reason the Context Summary is stale."""

    code: str
    source_type: str
    source_id: uuid.UUID | None
    source_timestamp: datetime | None


@dataclass(frozen=True, slots=True)
class ContextFreshnessEnsureResult:
    """Result of ensuring a fresh Context Summary exists."""

    session_id: uuid.UUID
    context_summary_id: uuid.UUID
    context_version: int
    source_cutoff: datetime
    rebuilt: bool
    payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ContextFreshnessResult:
    """Result of a freshness check."""

    session_id: uuid.UUID
    context_summary_id: uuid.UUID
    source_cutoff: datetime
    required_cutoff: datetime
    fresh: bool
    stale_reasons: tuple[ContextStaleReason, ...] = ()


# ---------------------------------------------------------------------------
# Stable error codes
# ---------------------------------------------------------------------------

CONTEXT_FRESHNESS_SESSION_NOT_FOUND = "CONTEXT_FRESHNESS_SESSION_NOT_FOUND_OR_NOT_OWNED"
CONTEXT_SUMMARY_NOT_FOUND = "CONTEXT_SUMMARY_NOT_FOUND"
CONTEXT_SUMMARY_INVALID_CUTOFF = "CONTEXT_SUMMARY_INVALID_CUTOFF"
CONTEXT_SUMMARY_SESSION_MISMATCH = "CONTEXT_SUMMARY_SESSION_MISMATCH"

# Stale reason codes
CONTEXT_EXPLICITLY_STALE = "CONTEXT_EXPLICITLY_STALE"
CONTEXT_NEWER_TRADE_ACTION = "CONTEXT_NEWER_TRADE_ACTION"
CONTEXT_NEWER_ACCEPTED_ANALYSIS = "CONTEXT_NEWER_ACCEPTED_ANALYSIS"
CONTEXT_NEWER_ACTIVE_EVIDENCE = "CONTEXT_NEWER_ACTIVE_EVIDENCE"
CONTEXT_NEWER_MATERIAL_EVENT = "CONTEXT_NEWER_MATERIAL_EVENT"
CONTEXT_CANONICAL_STATE_CHANGED = "CONTEXT_CANONICAL_STATE_CHANGED"
CONTEXT_LIFECYCLE_CHANGED = "CONTEXT_LIFECYCLE_CHANGED"

# Ensure / rebuild error codes
CONTEXT_REBUILD_FAILED = "CONTEXT_REBUILD_FAILED"
CONTEXT_REBUILD_VALIDATION_FAILED = "CONTEXT_REBUILD_VALIDATION_FAILED"
CONTEXT_REBUILD_PERSISTENCE_FAILED = "CONTEXT_REBUILD_PERSISTENCE_FAILED"
CONTEXT_REBUILD_STILL_STALE = "CONTEXT_REBUILD_STILL_STALE"


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class ContextFreshnessError(Exception):
    code: str = "CONTEXT_FRESHNESS_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class ContextFreshnessSessionNotFoundError(ContextFreshnessError):
    code: str = CONTEXT_FRESHNESS_SESSION_NOT_FOUND


class ContextSummaryNotFoundError(ContextFreshnessError):
    code: str = CONTEXT_SUMMARY_NOT_FOUND


class ContextSummaryInvalidCutoffError(ContextFreshnessError):
    code: str = CONTEXT_SUMMARY_INVALID_CUTOFF


class ContextSummarySessionMismatchError(ContextFreshnessError):
    code: str = CONTEXT_SUMMARY_SESSION_MISMATCH


class ContextRebuildError(ContextFreshnessError):
    code: str = CONTEXT_REBUILD_FAILED


class ContextRebuildValidationFailedError(ContextRebuildError):
    code: str = CONTEXT_REBUILD_VALIDATION_FAILED


class ContextRebuildPersistenceFailedError(ContextRebuildError):
    code: str = CONTEXT_REBUILD_PERSISTENCE_FAILED


class ContextRebuildStillStaleError(ContextRebuildError):
    code: str = CONTEXT_REBUILD_STILL_STALE


# ---------------------------------------------------------------------------
# Evidence types relevant to analysis context
# ---------------------------------------------------------------------------

_CONTEXT_RELEVANT_EVIDENCE_TYPES: frozenset[str] = frozenset(
    {
        EvidenceType.CHART_THREE_MONTH.value,
        EvidenceType.CHART_SIX_MONTH.value,
        EvidenceType.CHART_DAILY.value,
        EvidenceType.CHART_INTRADAY.value,
        EvidenceType.ORDERBOOK_SCREENSHOT.value,
        EvidenceType.MARKET_DATA_SNAPSHOT.value,
    }
)

# ---------------------------------------------------------------------------
# Freshness service
# ---------------------------------------------------------------------------


class ContextFreshnessService:
    """Read-only freshness check for persisted Context Summary records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._session_repo = TradeSessionRepository(session)
        self._cs_repo = ContextSummaryRepository(session)
        self._action_repo = TradeActionRepository(session)
        self._analysis_repo = AnalysisRepository(session)
        self._evidence_repo = EvidenceRepository(session)
        self._event_repo = SessionEventRepository(session)

    async def check(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        context_summary_id: uuid.UUID | None = None,
    ) -> ContextFreshnessResult:
        """Check whether a Context Summary is fresh enough for the next analysis.

        Parameters
        ----------
        session_id:
            The Trade Session to check.
        owner_id:
            The owning user.  Ownership is enforced.
        context_summary_id:
            Optional explicit summary ID.  When omitted, the latest summary
            for the session is inspected.

        Returns
        -------
        A ``ContextFreshnessResult`` with ``fresh`` set to ``True`` when the
        summary is safe to use.

        Raises
        ------
        ContextFreshnessSessionNotFoundError
            Session not found or not owned.
        ContextSummaryNotFoundError
            No Context Summary exists for the session.
        ContextSummaryInvalidCutoffError
            The summary's ``source_cutoff`` is missing or not timezone-aware.
        ContextSummarySessionMismatchError
            The requested summary does not belong to the requested session.
        """
        # 1. Session ownership
        ts = await self._session_repo.get_by_id_for_user(session_id, owner_id)
        if ts is None:
            raise ContextFreshnessSessionNotFoundError(
                message=f"Trade Session {session_id} not found or not owned by {owner_id}",
            )

        # 2. Context Summary — explicit or latest
        if context_summary_id is not None:
            cs = await self._cs_repo.get_by_id_for_user(context_summary_id, owner_id)
            if cs is None:
                raise ContextSummaryNotFoundError(
                    message=f"Context Summary {context_summary_id} not found or not owned",
                )
            if cs.session_id != session_id:
                raise ContextSummarySessionMismatchError(
                    message=(
                        f"Context Summary {context_summary_id} does not belong "
                        f"to session {session_id}"
                    ),
                )
        else:
            cs = await self._cs_repo.get_latest_for_user(session_id, owner_id)
            if cs is None:
                raise ContextSummaryNotFoundError(
                    message=f"No Context Summary found for session {session_id}",
                )

        # 3. Source cutoff validation
        if cs.source_cutoff is None:
            raise ContextSummaryInvalidCutoffError(
                message=f"Context Summary {cs.id} has no source_cutoff",
            )
        if cs.source_cutoff.tzinfo is None:
            raise ContextSummaryInvalidCutoffError(
                message=f"Context Summary {cs.id} source_cutoff is not timezone-aware",
            )

        source_cutoff = cs.source_cutoff
        reasons: list[ContextStaleReason] = []

        # 4. Explicit stale flag
        if cs.is_stale:
            reasons.append(
                ContextStaleReason(
                    code=CONTEXT_EXPLICITLY_STALE,
                    source_type="context_summary",
                    source_id=cs.id,
                    source_timestamp=source_cutoff,
                )
            )

        # 5. Derive required cutoff from material sources
        required_cutoff = await self._derive_required_cutoff(
            session_id,
            owner_id,
            source_cutoff,
            reasons,
        )

        # 6. Basic freshness rule
        fresh = not reasons and source_cutoff >= required_cutoff

        # 7. Deterministic ordering of stale reasons
        ordered_reasons = tuple(
            sorted(
                reasons,
                key=lambda r: (
                    -(r.source_timestamp.timestamp() if r.source_timestamp else 0),
                    r.source_type,
                    str(r.source_id or ""),
                ),
            )
        )

        return ContextFreshnessResult(
            session_id=session_id,
            context_summary_id=cs.id,
            source_cutoff=source_cutoff,
            required_cutoff=required_cutoff,
            fresh=fresh,
            stale_reasons=ordered_reasons,
        )

    # ------------------------------------------------------------------
    # Ensure-fresh (detect + rebuild if needed)
    # ------------------------------------------------------------------

    async def ensure_fresh(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        context_summary_id: uuid.UUID | None = None,
        maximum_events: int | None = None,
    ) -> ContextFreshnessEnsureResult:
        """Ensure a usable fresh Context Summary exists for the session.

        If the latest summary is already fresh, return it unchanged.

        If missing or stale, build a new version through TP-0902, persist it,
        verify it is fresh, and return the new summary.

        Parameters
        ----------
        session_id:
            The Trade Session to check and potentially rebuild.
        owner_id:
            The owning user.  Ownership is enforced.
        context_summary_id:
            Optional explicit summary ID.  When omitted, the latest summary
            is inspected.
        maximum_events:
            Optional override for TP-0902's maximum_events.

        Returns
        -------
        A ``ContextFreshnessEnsureResult``.

        Raises
        ------
        ContextFreshnessSessionNotFoundError
            Session not found or not owned.
        ContextRebuildValidationFailedError
            TP-0902 validation failed; nothing was persisted.
        ContextRebuildPersistenceFailedError
            Persistence failed after a successful build.
        ContextRebuildStillStaleError
            The newly built summary is already stale at creation.
        """
        # 1. Session ownership
        ts = await self._session_repo.get_by_id_for_user(session_id, owner_id)
        if ts is None:
            raise ContextFreshnessSessionNotFoundError(
                message=f"Trade Session {session_id} not found or not owned by {owner_id}",
            )

        # 2. Try to check the existing summary
        try:
            check_result = await self.check(
                session_id=session_id,
                owner_id=owner_id,
                context_summary_id=context_summary_id,
            )
        except (ContextSummaryNotFoundError, ContextSummaryInvalidCutoffError):
            cs_exists = False
            check_result = None
        else:
            cs_exists = True

        # 3. If fresh, return existing summary
        if cs_exists and check_result is not None and check_result.fresh:
            cs = await self._load_summary(check_result.context_summary_id, owner_id)
            assert cs is not None
            assert cs.source_cutoff is not None
            return ContextFreshnessEnsureResult(
                session_id=session_id,
                context_summary_id=cs.id,
                context_version=cs.context_version,
                source_cutoff=cs.source_cutoff,
                rebuilt=False,
                payload=dict(cs.payload) if cs.payload else {},
            )

        # 4. Compute required cutoff from all material sources
        stale_reasons: list[ContextStaleReason] = []
        # Start from the existing summary's cutoff (or session creation for missing)
        base_cutoff = check_result.source_cutoff if check_result is not None else ts.created_at
        required_cutoff = await self._derive_required_cutoff(
            session_id,
            owner_id,
            base_cutoff,
            stale_reasons,
        )

        # 5. Build new summary via TP-0902 with required cutoff
        max_events = maximum_events if maximum_events is not None else 50
        builder = ContextSummaryBuilder(self._session)
        try:
            build_result = await builder.build(
                session_id=session_id,
                owner_id=owner_id,
                source_cutoff=required_cutoff,
                maximum_events=max_events,
            )
        except Exception as exc:
            raise ContextRebuildValidationFailedError(
                message=f"TP-0902 build failed: {exc}",
            ) from exc

        # 6. Persist new Context Summary (with atomic version allocation)
        payload_mapping: Mapping[str, object] = build_result.payload
        now = await self._db_now()
        new_cs = ContextSummary(
            session_id=session_id,
            context_version=await self._next_version(session_id, owner_id),
            source_cutoff=build_result.source_cutoff,
            payload=dict(payload_mapping),
            quality=ContextQuality.HIGH,
            is_stale=False,
            created_at=now,
        )
        try:
            persisted = await self._cs_repo.add(new_cs)
        except Exception as exc:
            raise ContextRebuildPersistenceFailedError(
                message=f"Failed to persist new Context Summary: {exc}",
            ) from exc

        # 8. Verify the new summary is fresh
        verify = await self.check(
            session_id=session_id,
            owner_id=owner_id,
            context_summary_id=persisted.id,
        )
        if not verify.fresh:
            raise ContextRebuildStillStaleError(
                message=(
                    f"Newly built Context Summary {persisted.id} "
                    f"is already stale (cutoff={build_result.source_cutoff}, "
                    f"required={verify.required_cutoff})"
                ),
            )

        assert persisted.source_cutoff is not None
        return ContextFreshnessEnsureResult(
            session_id=session_id,
            context_summary_id=persisted.id,
            context_version=persisted.context_version,
            source_cutoff=persisted.source_cutoff,
            rebuilt=True,
            payload=dict(persisted.payload) if persisted.payload else {},
        )

    async def _load_summary(
        self,
        summary_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> ContextSummary | None:
        """Load a Context Summary by ID with ownership check."""
        return await self._cs_repo.get_by_id_for_user(summary_id, owner_id)

    async def _next_version(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> int:
        """Allocate the next context version for the session.

        Uses a timestamp-based version for safe uniqueness without
        depending on MVCC visibility of uncommitted rows.
        """
        import time

        ts = int(time.time() * 1000)
        return ts % 2147483647  # stay within PostgreSQL Integer range

    @staticmethod
    async def _db_now() -> datetime:
        """Return the current UTC timestamp for persistence."""
        from datetime import timezone

        return datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Required cutoff derivation
    # ------------------------------------------------------------------

    async def _derive_required_cutoff(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        source_cutoff: datetime,
        reasons: list[ContextStaleReason],
    ) -> datetime:
        """Derive the latest material source timestamp for the session.

        Starts from ``source_cutoff`` and advances it when a newer material
        source is found.
        """
        cutoff = source_cutoff

        cutoff = await self._check_trade_actions(session_id, owner_id, cutoff, reasons)
        cutoff = await self._check_accepted_analyses(session_id, owner_id, cutoff, reasons)
        cutoff = await self._check_active_evidence(session_id, owner_id, cutoff, reasons)
        cutoff = await self._check_material_events(session_id, owner_id, cutoff, reasons)

        return cutoff

    # ------------------------------------------------------------------
    # Source checks
    # ------------------------------------------------------------------

    async def _check_trade_actions(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        cutoff: datetime,
        reasons: list[ContextStaleReason],
    ) -> datetime:
        actions = await self._action_repo.list_for_session_for_user(session_id, owner_id)
        for action in actions:
            if action.confirmed_at > cutoff:
                reasons.append(
                    ContextStaleReason(
                        code=CONTEXT_NEWER_TRADE_ACTION,
                        source_type="trade_action",
                        source_id=action.id,
                        source_timestamp=action.confirmed_at,
                    )
                )
                cutoff = max(cutoff, action.confirmed_at)
        return cutoff

    async def _check_accepted_analyses(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        cutoff: datetime,
        reasons: list[ContextStaleReason],
    ) -> datetime:
        all_analyses = await self._analysis_repo.list_for_session_for_user(
            session_id,
            owner_id,
        )
        for analysis in all_analyses:
            if analysis.acceptance_status != AcceptanceStatus.ACCEPTED:
                continue
            if analysis.accepted_at is None:
                continue
            if analysis.accepted_at > cutoff:
                reasons.append(
                    ContextStaleReason(
                        code=CONTEXT_NEWER_ACCEPTED_ANALYSIS,
                        source_type="analysis",
                        source_id=analysis.id,
                        source_timestamp=analysis.accepted_at,
                    )
                )
                cutoff = max(cutoff, analysis.accepted_at)
        return cutoff

    async def _check_active_evidence(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        cutoff: datetime,
        reasons: list[ContextStaleReason],
    ) -> datetime:
        all_active = await self._evidence_repo.list_active_for_session_for_user(
            session_id,
            owner_id,
        )
        for ev in all_active:
            if ev.evidence_type.value not in _CONTEXT_RELEVANT_EVIDENCE_TYPES:
                continue
            ts_candidates: list[datetime] = []
            if ev.market_timestamp is not None and ev.market_timestamp.tzinfo is not None:
                ts_candidates.append(ev.market_timestamp)
            if ev.uploaded_at is not None and ev.uploaded_at.tzinfo is not None:
                ts_candidates.append(ev.uploaded_at)
            if not ts_candidates:
                continue
            ev_ts = max(ts_candidates)
            if ev_ts > cutoff:
                reasons.append(
                    ContextStaleReason(
                        code=CONTEXT_NEWER_ACTIVE_EVIDENCE,
                        source_type="evidence",
                        source_id=ev.id,
                        source_timestamp=ev_ts,
                    )
                )
                cutoff = max(cutoff, ev_ts)
        return cutoff

    async def _check_material_events(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        cutoff: datetime,
        reasons: list[ContextStaleReason],
    ) -> datetime:
        all_events = await self._event_repo.list_for_session_for_user(
            session_id,
            owner_id,
        )
        for event in all_events:
            if not _is_material_event(event):
                continue
            if event.occurred_at > cutoff:
                reasons.append(
                    ContextStaleReason(
                        code=CONTEXT_NEWER_MATERIAL_EVENT,
                        source_type="session_event",
                        source_id=event.id,
                        source_timestamp=event.occurred_at,
                    )
                )
                cutoff = max(cutoff, event.occurred_at)
        return cutoff


# ---------------------------------------------------------------------------
# Material event classification
# ---------------------------------------------------------------------------


def _is_material_event(event: SessionEvent) -> bool:
    """Determine if a SessionEvent is material for freshness purposes.

    Uses the same materiality rules as TP-0901's ``MaterialHistorySelector``,
    extended with ``ANALYSIS_ACCEPTED`` which is a direct signal that the
    longitudinal memory should advance.
    """
    et = event.event_type.value
    if et in _CONFIRMED_EVENT_TYPES:
        return True
    if et in _LIFECYCLE_EVENT_TYPES:
        return True
    if et == "ANALYSIS_ACCEPTED":
        return True
    return False
