"""Tests for TP-0307 entry, stop, target, and risk validators."""

from __future__ import annotations

import copy

from app.validation.entry_plan import (
    ENTRY_ABOVE_MAXIMUM_ACCEPTABLE,
    ENTRY_ZONE_LOW_ABOVE_HIGH,
    ENTRY_ZONE_STRUCTURE_INVALID,
    EXACT_ENTRY_STRUCTURE_INVALID,
    MAXIMUM_ACCEPTABLE_ENTRY_INVALID,
    NON_ENTRY_PLAN_HAS_ENTRY_PRICE,
    validate_entry_plan,
)
from app.validation.entry_plan import (
    NUMERIC_INPUT_INVALID as ENTRY_NUM_INVALID,
)
from app.validation.risk_reward import (
    NUMERIC_INPUT_INVALID as RR_NUM_INVALID,
)
from app.validation.risk_reward import (
    RISK_EXCEEDS_MAXIMUM,
    RISK_PERCENTAGE_MISMATCH,
    RISK_REWARD_MISMATCH,
    validate_risk_reward,
)
from app.validation.stop_loss import (
    NUMERIC_INPUT_INVALID as STOP_NUM_INVALID,
)
from app.validation.stop_loss import (
    STOP_NOT_BELOW_ENTRY,
    validate_stop_loss,
)
from app.validation.target import (
    NUMERIC_INPUT_INVALID as TARGET_NUM_INVALID,
)
from app.validation.target import (
    TARGET_NOT_ABOVE_ENTRY,
    validate_target,
)


def _bbri_exact_entry() -> dict[str, object]:
    """BBRI-like exact-entry analysis."""
    return {
        "entry_plan": {
            "entry_recommended": True,
            "entry_type": "EXACT_PRICE",
            "entry_price": 2800,
            "entry_zone_low": None,
            "entry_zone_high": None,
            "maximum_acceptable_entry": 2820,
        },
        "stop_loss_plan": {
            "stop_loss_recommended": True,
            "stop_loss_price": 2700,
        },
        "target_plan": {
            "target_recommended": True,
            "target_price": 2920,
        },
    }


def _bbri_zone_entry() -> dict[str, object]:
    return {
        "entry_plan": {
            "entry_recommended": True,
            "entry_type": "PRICE_ZONE",
            "entry_price": None,
            "entry_zone_low": 2780,
            "entry_zone_high": 2820,
            "maximum_acceptable_entry": 2850,
        },
        "stop_loss_plan": {
            "stop_loss_recommended": True,
            "stop_loss_price": 2700,
        },
        "target_plan": {
            "target_recommended": True,
            "target_price": 2920,
        },
    }


def _expect(issues: tuple, code: str) -> None:
    assert issues, f"Expected {code} but no issues returned"
    codes = {i.code for i in issues}
    assert code in codes, f"Expected code {code!r} not in {codes}"


# ===================================================================
# Entry plan
# ===================================================================


class TestExactEntry:
    def test_valid(self) -> None:
        assert validate_entry_plan(_bbri_exact_entry()) == ()

    def test_non_positive_entry(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_price"] = 0
        _expect(validate_entry_plan(p), EXACT_ENTRY_STRUCTURE_INVALID)

    def test_negative_entry(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_price"] = -100
        _expect(validate_entry_plan(p), EXACT_ENTRY_STRUCTURE_INVALID)

    def test_entry_at_max_acceptable(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_price"] = 2820
        assert validate_entry_plan(p) == ()

    def test_entry_above_max_acceptable(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_price"] = 3000
        _expect(validate_entry_plan(p), ENTRY_ABOVE_MAXIMUM_ACCEPTABLE)

    def test_float_rejected(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_price"] = 2800.5
        _expect(validate_entry_plan(p), ENTRY_NUM_INVALID)

    def test_payload_unchanged(self) -> None:
        p = _bbri_exact_entry()
        before = copy.deepcopy(p)
        validate_entry_plan(p)
        assert p == before


class TestEntryZone:
    def test_valid_zone(self) -> None:
        assert validate_entry_plan(_bbri_zone_entry()) == ()

    def test_equal_bounds(self) -> None:
        p = _bbri_zone_entry()
        p["entry_plan"]["entry_zone_low"] = 2800
        p["entry_plan"]["entry_zone_high"] = 2800
        assert validate_entry_plan(p) == ()

    def test_low_above_high(self) -> None:
        p = _bbri_zone_entry()
        p["entry_plan"]["entry_zone_low"] = 2850
        p["entry_plan"]["entry_zone_high"] = 2800
        _expect(validate_entry_plan(p), ENTRY_ZONE_LOW_ABOVE_HIGH)

    def test_non_positive_low(self) -> None:
        p = _bbri_zone_entry()
        p["entry_plan"]["entry_zone_low"] = 0
        _expect(validate_entry_plan(p), ENTRY_ZONE_STRUCTURE_INVALID)

    def test_zone_high_exceeds_max_acceptable(self) -> None:
        p = _bbri_zone_entry()
        p["entry_plan"]["entry_zone_high"] = 2900
        _expect(validate_entry_plan(p), ENTRY_ABOVE_MAXIMUM_ACCEPTABLE)


class TestNonEntryPlan:
    def test_waith_has_no_entry_price(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_recommended"] = False
        p["entry_plan"]["entry_type"] = "WAIT"
        p["entry_plan"]["entry_price"] = None
        assert validate_entry_plan(p) == ()

    def test_waith_with_entry_price(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_recommended"] = False
        p["entry_plan"]["entry_type"] = "WAIT"
        p["entry_plan"]["entry_price"] = 2800
        _expect(validate_entry_plan(p), NON_ENTRY_PLAN_HAS_ENTRY_PRICE)


class TestMaxAcceptableEntry:
    def test_non_positive_max(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["maximum_acceptable_entry"] = 0
        _expect(validate_entry_plan(p), MAXIMUM_ACCEPTABLE_ENTRY_INVALID)


# ===================================================================
# Stop loss
# ===================================================================


class TestStopLoss:
    def test_stop_below_exact_entry(self) -> None:
        assert validate_stop_loss(_bbri_exact_entry()) == ()

    def test_stop_equal_to_entry(self) -> None:
        p = _bbri_exact_entry()
        p["stop_loss_plan"]["stop_loss_price"] = 2800
        _expect(validate_stop_loss(p), STOP_NOT_BELOW_ENTRY)

    def test_stop_above_entry(self) -> None:
        p = _bbri_exact_entry()
        p["stop_loss_plan"]["stop_loss_price"] = 2900
        _expect(validate_stop_loss(p), STOP_NOT_BELOW_ENTRY)

    def test_stop_below_zone_low(self) -> None:
        """For zone entry, stop is referenced against zone low."""
        assert validate_stop_loss(_bbri_zone_entry()) == ()

    def test_stop_above_zone_low(self) -> None:
        p = _bbri_zone_entry()
        p["stop_loss_plan"]["stop_loss_price"] = 2800  # above zone low (2780)
        _expect(validate_stop_loss(p), STOP_NOT_BELOW_ENTRY)

    def test_float_rejected(self) -> None:
        p = _bbri_exact_entry()
        p["stop_loss_plan"]["stop_loss_price"] = 2700.5
        _expect(validate_stop_loss(p), STOP_NUM_INVALID)


# ===================================================================
# Target
# ===================================================================


class TestTarget:
    def test_target_above_exact_entry(self) -> None:
        assert validate_target(_bbri_exact_entry()) == ()

    def test_target_equal_to_entry(self) -> None:
        p = _bbri_exact_entry()
        p["target_plan"]["target_price"] = 2800
        _expect(validate_target(p), TARGET_NOT_ABOVE_ENTRY)

    def test_target_below_entry(self) -> None:
        p = _bbri_exact_entry()
        p["target_plan"]["target_price"] = 2700
        _expect(validate_target(p), TARGET_NOT_ABOVE_ENTRY)

    def test_target_above_zone_high(self) -> None:
        """For zone entry, target is referenced against zone high."""
        p = _bbri_zone_entry()
        p["target_plan"]["target_price"] = 2900  # above zone high (2820)
        assert validate_target(p) == ()

    def test_target_below_zone_high(self) -> None:
        p = _bbri_zone_entry()
        p["target_plan"]["target_price"] = 2800  # below zone high (2820)
        _expect(validate_target(p), TARGET_NOT_ABOVE_ENTRY)

    def test_float_rejected(self) -> None:
        p = _bbri_exact_entry()
        p["target_plan"]["target_price"] = 2920.5
        _expect(validate_target(p), TARGET_NUM_INVALID)


# ===================================================================
# Risk, reward, risk-reward
# ===================================================================


class TestRiskBoundary:
    def test_risk_below_5pct(self) -> None:
        """Entry 2800, stop 2660 → risk = (2800-2660)/2800*100 = 5.0%."""
        p = _bbri_exact_entry()
        p["stop_loss_plan"]["stop_loss_price"] = 2660
        assert validate_risk_reward(p) == ()

    def test_risk_exactly_5pct(self) -> None:
        """Entry 2800, stop 2660 → risk = 5.0%.  Uses quantize: 140/2800*100 = 5.0."""
        p = _bbri_exact_entry()
        p["stop_loss_plan"]["stop_loss_price"] = 2660
        assert validate_risk_reward(p) == ()

    def test_risk_just_above_5pct(self) -> None:
        """Entry 2800, stop 2659 → risk = (2800-2659)/2800*100 = 5.0357... → 5.04%."""
        p = _bbri_exact_entry()
        p["stop_loss_plan"]["stop_loss_price"] = 2659
        issues = validate_risk_reward(p)
        _expect(issues, RISK_EXCEEDS_MAXIMUM)

    def test_risk_reported_mismatch(self) -> None:
        """When stop_loss_plan has initial_risk_percentage, it is checked."""
        p = _bbri_exact_entry()
        p["stop_loss_plan"]["initial_risk_percentage"] = "1.00"
        issues = validate_risk_reward(p)
        _expect(issues, RISK_PERCENTAGE_MISMATCH)


class TestReward:
    def test_reward_correct(self) -> None:
        """target_plan does not store reward_percentage by default → no consistency check."""
        assert validate_risk_reward(_bbri_exact_entry()) == ()


class TestRiskRewardMismatch:
    def test_reported_rr_correct(self) -> None:
        """Entry 2800, stop 2700, target 2920 → RR = (2920-2800)/(2800-2700) = 1.20."""
        p = _bbri_exact_entry()
        p["target_plan"]["risk_reward_ratio"] = "1.20"
        assert validate_risk_reward(p) == ()

    def test_reported_rr_incorrect(self) -> None:
        p = _bbri_exact_entry()
        p["target_plan"]["risk_reward_ratio"] = "9.99"
        _expect(validate_risk_reward(p), RISK_REWARD_MISMATCH)


class TestRiskRewardFloat:
    def test_float_rejected(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_price"] = 2800.5
        _expect(validate_risk_reward(p), RR_NUM_INVALID)


# ===================================================================
# Multi-error determinism
# ===================================================================


class TestMultiError:
    def test_multiple_entry_errors(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_price"] = 0
        p["entry_plan"]["maximum_acceptable_entry"] = 0
        issues = validate_entry_plan(p)
        assert len(issues) >= 2

    def test_deterministic_ordering(self) -> None:
        p = _bbri_exact_entry()
        p["entry_plan"]["entry_price"] = 0
        p["entry_plan"]["maximum_acceptable_entry"] = 0
        assert validate_entry_plan(p) == validate_entry_plan(p)
