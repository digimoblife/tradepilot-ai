"""Transition registry for Trade Session lifecycle."""

from __future__ import annotations

from app.models.enums import TradeSessionStatus

# ---------------------------------------------------------------------------
# Canonical transition map (from SESSION_LIFECYCLE.md section 7)
# ---------------------------------------------------------------------------

_TRANSITION_MAP: dict[TradeSessionStatus, set[TradeSessionStatus]] = {
    TradeSessionStatus.DRAFT: {
        TradeSessionStatus.READY_FOR_ANALYSIS,
        TradeSessionStatus.CANCELLED,
        TradeSessionStatus.ARCHIVED,
    },
    TradeSessionStatus.READY_FOR_ANALYSIS: {
        TradeSessionStatus.DRAFT,
        TradeSessionStatus.ANALYZING,
        TradeSessionStatus.CANCELLED,
        TradeSessionStatus.ARCHIVED,
    },
    TradeSessionStatus.ANALYZING: {
        # to stable_status or ANALYZING itself via re-analysis
        TradeSessionStatus.WATCHING,
        # Follow-up succeeds, fails, or is cancelled → previous stable status
        # We handle ANALYZING->stable separately via the service
    },
    TradeSessionStatus.WATCHING: {
        TradeSessionStatus.ANALYZING,
        TradeSessionStatus.OPEN_POSITION,
        TradeSessionStatus.CANCELLED,
        TradeSessionStatus.ARCHIVED,
    },
    TradeSessionStatus.OPEN_POSITION: {
        TradeSessionStatus.ANALYZING,
        TradeSessionStatus.PARTIALLY_CLOSED,
        TradeSessionStatus.CLOSED_TAKE_PROFIT,
        TradeSessionStatus.CLOSED_STOP_LOSS,
        TradeSessionStatus.CLOSED_MANUAL,
    },
    TradeSessionStatus.PARTIALLY_CLOSED: {
        TradeSessionStatus.ANALYZING,
        TradeSessionStatus.PARTIALLY_CLOSED,  # another partial exit
        TradeSessionStatus.CLOSED_TAKE_PROFIT,
        TradeSessionStatus.CLOSED_STOP_LOSS,
        TradeSessionStatus.CLOSED_MANUAL,
    },
    # Terminal closed states: only ARCHIVED
    TradeSessionStatus.CLOSED_TAKE_PROFIT: {
        TradeSessionStatus.ARCHIVED,
    },
    TradeSessionStatus.CLOSED_STOP_LOSS: {
        TradeSessionStatus.ARCHIVED,
    },
    TradeSessionStatus.CLOSED_MANUAL: {
        TradeSessionStatus.ARCHIVED,
    },
    TradeSessionStatus.CANCELLED: {
        TradeSessionStatus.ARCHIVED,
    },
    TradeSessionStatus.ARCHIVED: {
        # Can restore to pre_archive_status
        # Pre-archive status restoration handled by the service
    },
}

# ---------------------------------------------------------------------------
# Terminal statuses
# ---------------------------------------------------------------------------

TERMINAL_STATUSES: frozenset[TradeSessionStatus] = frozenset(
    {
        TradeSessionStatus.CLOSED_TAKE_PROFIT,
        TradeSessionStatus.CLOSED_STOP_LOSS,
        TradeSessionStatus.CLOSED_MANUAL,
        TradeSessionStatus.CANCELLED,
    }
)

# ---------------------------------------------------------------------------
# Transient statuses (not stable business states)
# ---------------------------------------------------------------------------

TRANSIENT_STATUSES: frozenset[TradeSessionStatus] = frozenset(
    {
        TradeSessionStatus.ANALYZING,
        TradeSessionStatus.ARCHIVED,
    }
)


# ---------------------------------------------------------------------------
# Pure function
# ---------------------------------------------------------------------------


def is_transition_allowed(
    current_status: TradeSessionStatus,
    target_status: TradeSessionStatus,
) -> bool:
    """Return ``True`` when *target_status* is reachable from *current_status*.

    Special cases:
    - ``ANALYZING`` can transition to **any** stable status (the analysis
      result determines the next state).
    - ``ARCHIVED`` can only be restored to ``pre_archive_status`` (handled
      by the service).
    """
    if current_status == TradeSessionStatus.ANALYZING:
        # ANALYZING can transition to any non-transient status
        return (
            target_status not in TRANSIENT_STATUSES
            or target_status == TradeSessionStatus.ANALYZING
        )

    allowed = _TRANSITION_MAP.get(current_status, set())
    return target_status in allowed


def get_allowed_transitions(
    current_status: TradeSessionStatus,
) -> set[TradeSessionStatus]:
    """Return the set of allowed target statuses from *current_status*."""
    if current_status == TradeSessionStatus.ANALYZING:
        return set(TradeSessionStatus) - TRANSIENT_STATUSES | {TradeSessionStatus.ANALYZING}
    if current_status == TradeSessionStatus.ARCHIVED:
        return set()  # pre_archive_status handled by the service
    return _TRANSITION_MAP.get(current_status, set()).copy()
