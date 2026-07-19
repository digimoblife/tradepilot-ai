"""Validator registry mapping analysis types to applicable domain validators.

Each entry stores ``(validator_fn, payload_key)`` where *payload_key* is
the sub-object to extract from the analysis payload (``None`` means pass
the whole payload).
"""

from __future__ import annotations

from typing import Callable

from app.validation.entry_plan import validate_entry_plan
from app.validation.market_snapshot import validate_market_snapshot
from app.validation.risk_reward import validate_risk_reward
from app.validation.stop_loss import validate_stop_loss
from app.validation.target import validate_target

ValidatorFn = Callable[..., object]

# (validator_fn, payload_key | None)
_DOMAIN_REGISTRY: dict[str, list[tuple[ValidatorFn, str | None]]] = {
    "INITIAL_ANALYSIS": [
        (validate_market_snapshot, "market_snapshot"),
        (validate_entry_plan, None),
        (validate_stop_loss, None),
        (validate_target, None),
        (validate_risk_reward, None),
    ],
    "WATCHING_UPDATE": [
        (validate_market_snapshot, "market_snapshot"),
    ],
    "OPEN_POSITION_UPDATE": [
        (validate_market_snapshot, "market_snapshot"),
    ],
    "PARTIAL_EXIT_REVIEW": [
        (validate_market_snapshot, "market_snapshot"),
    ],
    "CLOSING_ANALYSIS": [],
}


def get_domain_validators(analysis_type: str) -> list[tuple[ValidatorFn, str | None]]:
    """Return the list of ``(validator_fn, payload_key)`` for *analysis_type*."""
    return _DOMAIN_REGISTRY.get(analysis_type, [])


def get_available_analysis_types() -> tuple[str, ...]:
    return tuple(_DOMAIN_REGISTRY.keys())
