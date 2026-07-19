"""TradePilot AI test fixture factories.

Deterministic, reusable factories for all production schemas.
"""

from tests.factories.analysis_factory import make_analysis
from tests.factories.context_factory import make_context_summary
from tests.factories.deep_merge import deep_merge
from tests.factories.evidence_factory import make_evidence
from tests.factories.market_snapshot_factory import make_market_snapshot
from tests.factories.trade_state_factory import (
    make_closed_trade_state,
    make_not_opened_trade_state,
    make_open_trade_state,
    make_partial_trade_state,
)

__all__ = [
    "deep_merge",
    "make_analysis",
    "make_closed_trade_state",
    "make_context_summary",
    "make_evidence",
    "make_market_snapshot",
    "make_not_opened_trade_state",
    "make_open_trade_state",
    "make_partial_trade_state",
]
