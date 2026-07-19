"""TradePilot AI validation package."""

from app.validation.closing import (
    ClosingValidationResult,
    validate_closing,
)
from app.validation.context_summary import (
    ContextSummaryValidationResult,
    validate_context_summary,
)
from app.validation.entry_plan import validate_entry_plan
from app.validation.issues import (
    JsonSchemaValidationResult,
    ValidationCategory,
    ValidationIssue,
    ValidationSeverity,
)
from app.validation.json_schema import JsonSchemaValidationService
from app.validation.market_snapshot import (
    MarketSnapshotValidationResult,
    validate_market_snapshot,
)
from app.validation.partial_exit import (
    PartialExitValidationResult,
    validate_partial_exit,
)
from app.validation.risk_reward import validate_risk_reward
from app.validation.service import UnifiedValidationResult, UnifiedValidationService
from app.validation.state_consistency import (
    StateConsistencyValidationResult,
    validate_state_consistency,
)
from app.validation.stop_loss import validate_stop_loss
from app.validation.target import validate_target
from app.validation.trade_state import (
    ConfirmedActionSnapshot,
    TradeStateValidationResult,
    validate_trade_state,
)

__all__ = [
    "ClosingValidationResult",
    "ConfirmedActionSnapshot",
    "ContextSummaryValidationResult",
    "UnifiedValidationResult",
    "UnifiedValidationService",
    "JsonSchemaValidationResult",
    "JsonSchemaValidationService",
    "MarketSnapshotValidationResult",
    "PartialExitValidationResult",
    "StateConsistencyValidationResult",
    "TradeStateValidationResult",
    "ValidationCategory",
    "ValidationIssue",
    "ValidationSeverity",
    "validate_closing",
    "validate_context_summary",
    "validate_entry_plan",
    "validate_market_snapshot",
    "validate_partial_exit",
    "validate_risk_reward",
    "validate_state_consistency",
    "validate_stop_loss",
    "validate_target",
    "validate_trade_state",
]
