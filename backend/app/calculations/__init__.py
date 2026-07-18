"""TradePilot AI deterministic financial calculations.

All monetary, price, quantity, percentage, and ratio arithmetic uses
``Decimal``.  Floats are rejected at the public API boundary.
"""

from app.calculations.decimal_utils import (
    CurrencyCode,
    quantize_money,
    quantize_percentage,
    quantize_price,
    quantize_quantity,
    safe_divide,
    to_decimal,
)
from app.calculations.errors import CalculationError, DivisionUndefinedError, InvalidDecimalError
from app.calculations.exits import (
    ExitFill,
    calculate_gross_closing_pnl,
    calculate_gross_closing_result,
    calculate_net_closing_pnl,
    calculate_net_closing_result,
    calculate_partial_realized_pnl,
    calculate_sum_realized_pnl,
    calculate_weighted_average_exit,
)
from app.calculations.market import (
    calculate_market_change,
    calculate_percentage_change,
    calculate_spread,
)
from app.calculations.models import ClosingResult
from app.calculations.position import (
    calculate_current_distance_to_stop,
    calculate_current_distance_to_target,
    calculate_remaining_quantity,
    calculate_reward_percentage,
    calculate_risk_percentage,
    calculate_risk_reward_ratio,
    calculate_setup_distance_to_stop,
    calculate_setup_distance_to_target,
    calculate_unrealized_pnl,
    calculate_unrealized_return,
)

__all__ = [
    "CalculationError",
    "ClosingResult",
    "CurrencyCode",
    "DivisionUndefinedError",
    "ExitFill",
    "InvalidDecimalError",
    "InvalidDecimalError",
    "calculate_current_distance_to_stop",
    "calculate_current_distance_to_target",
    "calculate_gross_closing_pnl",
    "calculate_gross_closing_result",
    "calculate_market_change",
    "calculate_net_closing_pnl",
    "calculate_net_closing_result",
    "calculate_partial_realized_pnl",
    "calculate_percentage_change",
    "calculate_remaining_quantity",
    "calculate_reward_percentage",
    "calculate_risk_percentage",
    "calculate_risk_reward_ratio",
    "calculate_setup_distance_to_stop",
    "calculate_setup_distance_to_target",
    "calculate_spread",
    "calculate_sum_realized_pnl",
    "calculate_unrealized_pnl",
    "calculate_unrealized_return",
    "calculate_weighted_average_exit",
    "quantize_money",
    "quantize_percentage",
    "quantize_price",
    "quantize_quantity",
    "safe_divide",
    "to_decimal",
]
