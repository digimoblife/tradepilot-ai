"""Tests for Canonical State Consistency Validator (TP-0308)."""

from __future__ import annotations

import copy

from app.validation.state_consistency import (
    STATE_ACTIVE_STOP_MISMATCH,
    STATE_ACTIVE_TARGET_MISMATCH,
    STATE_ENTRY_PRICE_MISMATCH,
    STATE_NUMERIC_INPUT_INVALID,
    STATE_ORIGINAL_QUANTITY_MISMATCH,
    STATE_POSITION_STATUS_MISMATCH,
    STATE_REMAINING_QUANTITY_MISMATCH,
    STATE_SESSION_ID_MISMATCH,
    STATE_TICKER_MISMATCH,
    StateConsistencyValidationResult,
    validate_state_consistency,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CANONICAL = {
    "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "ticker": "BBRI",
    "position": {
        "entry_price": 2800,
        "original_quantity": 100,
        "remaining_quantity": 100,
        "active_stop_loss": 2840,
        "active_target": 2920,
        "position_status": "OPEN",
    },
}

AI_PAYLOAD = {
    "metadata": {
        "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "ticker": "BBRI",
        "original_quantity": 100,
    },
    "position_assessment": {
        "entry_price": 2800,
        "remaining_quantity": 100,
        "active_stop_loss": 2840,
        "active_target": 2920,
    },
    "position_status": "OPEN",
}


def _expect(result: StateConsistencyValidationResult, code: str) -> None:
    assert not result.valid, f"Expected {code} but result is valid"
    codes = {i.code for i in result.issues}
    assert code in codes, f"Expected code {code!r} not in {codes}"


# ===================================================================
# Session ID and ticker
# ===================================================================


class TestIdentity:
    def test_matching_session_id(self) -> None:
        r = validate_state_consistency(AI_PAYLOAD, CANONICAL)
        assert r.valid

    def test_altered_session_id(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["metadata"]["session_id"] = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        _expect(validate_state_consistency(p, CANONICAL), STATE_SESSION_ID_MISMATCH)

    def test_matching_ticker(self) -> None:
        assert validate_state_consistency(AI_PAYLOAD, CANONICAL).valid

    def test_altered_ticker(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["metadata"]["ticker"] = "SOFI"
        _expect(validate_state_consistency(p, CANONICAL), STATE_TICKER_MISMATCH)


# ===================================================================
# Entry price
# ===================================================================


class TestEntryPrice:
    def test_matching(self) -> None:
        assert validate_state_consistency(AI_PAYLOAD, CANONICAL).valid

    def test_altered(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["position_assessment"]["entry_price"] = 999
        _expect(validate_state_consistency(p, CANONICAL), STATE_ENTRY_PRICE_MISMATCH)

    def test_float_rejected(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["position_assessment"]["entry_price"] = 2800.5
        _expect(validate_state_consistency(p, CANONICAL), STATE_NUMERIC_INPUT_INVALID)


# ===================================================================
# Original quantity
# ===================================================================


class TestOriginalQuantity:
    def test_matching(self) -> None:
        assert validate_state_consistency(AI_PAYLOAD, CANONICAL).valid

    def test_altered(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["metadata"]["original_quantity"] = 999
        _expect(validate_state_consistency(p, CANONICAL), STATE_ORIGINAL_QUANTITY_MISMATCH)


# ===================================================================
# Remaining quantity
# ===================================================================


class TestRemainingQuantity:
    def test_matching(self) -> None:
        assert validate_state_consistency(AI_PAYLOAD, CANONICAL).valid

    def test_altered(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["position_assessment"]["remaining_quantity"] = 999
        _expect(validate_state_consistency(p, CANONICAL), STATE_REMAINING_QUANTITY_MISMATCH)


# ===================================================================
# Active stop
# ===================================================================


class TestActiveStop:
    def test_matching(self) -> None:
        assert validate_state_consistency(AI_PAYLOAD, CANONICAL).valid

    def test_altered_rejected(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["position_assessment"]["active_stop_loss"] = 999
        _expect(validate_state_consistency(p, CANONICAL), STATE_ACTIVE_STOP_MISMATCH)

    def test_canonical_null_ai_invents(self) -> None:
        """AI must not invent an active stop when canonical has none."""
        c = copy.deepcopy(CANONICAL)
        c["position"]["active_stop_loss"] = None
        r = validate_state_consistency(AI_PAYLOAD, c)
        _expect(r, STATE_ACTIVE_STOP_MISMATCH)

    def test_proposed_stop_may_differ(self) -> None:
        """The proposed_stop_loss field (e.g. from stop_loss_assessment) may differ."""
        p = dict(AI_PAYLOAD)
        p["stop_loss_assessment"] = {"proposed_stop_loss": 999}
        r = validate_state_consistency(p, CANONICAL)
        assert r.valid, f"Proposed stop difference should not fail: {r.issues}"

    def test_canonical_null_ai_null_valid(self) -> None:
        """Both null is valid."""
        c = copy.deepcopy(CANONICAL)
        c["position"]["active_stop_loss"] = None
        p = copy.deepcopy(AI_PAYLOAD)
        p["position_assessment"]["active_stop_loss"] = None
        assert validate_state_consistency(p, c).valid


# ===================================================================
# Active target
# ===================================================================


class TestActiveTarget:
    def test_matching(self) -> None:
        assert validate_state_consistency(AI_PAYLOAD, CANONICAL).valid

    def test_altered_rejected(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["position_assessment"]["active_target"] = 999
        _expect(validate_state_consistency(p, CANONICAL), STATE_ACTIVE_TARGET_MISMATCH)

    def test_canonical_null_ai_invents(self) -> None:
        c = copy.deepcopy(CANONICAL)
        c["position"]["active_target"] = None
        _expect(validate_state_consistency(AI_PAYLOAD, c), STATE_ACTIVE_TARGET_MISMATCH)

    def test_proposed_target_may_differ(self) -> None:
        p = dict(AI_PAYLOAD)
        p["target_assessment"] = {"proposed_target": 999}
        r = validate_state_consistency(p, CANONICAL)
        assert r.valid, f"Proposed target difference should not fail: {r.issues}"


# ===================================================================
# Position status
# ===================================================================


class TestPositionStatus:
    def test_matching(self) -> None:
        assert validate_state_consistency(AI_PAYLOAD, CANONICAL).valid

    def test_altered(self) -> None:
        p = dict(AI_PAYLOAD)
        p["position_status"] = "CLOSED"
        _expect(validate_state_consistency(p, CANONICAL), STATE_POSITION_STATUS_MISMATCH)


# ===================================================================
# Immutability
# ===================================================================


class TestImmutability:
    def test_ai_payload_unchanged(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["position_assessment"]["entry_price"] = 999
        before = copy.deepcopy(p)
        validate_state_consistency(p, CANONICAL)
        assert p == before

    def test_canonical_state_unchanged(self) -> None:
        c = copy.deepcopy(CANONICAL)
        before = copy.deepcopy(c)
        p = copy.deepcopy(AI_PAYLOAD)
        p["position_assessment"]["entry_price"] = 999
        validate_state_consistency(p, c)
        assert c == before


# ===================================================================
# Multi-error determinism
# ===================================================================


class TestMultiError:
    def test_multiple_mismatches(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["metadata"]["session_id"] = "x"
        p["metadata"]["ticker"] = "x"
        p["position_assessment"]["entry_price"] = 999
        r = validate_state_consistency(p, CANONICAL)
        assert not r.valid
        assert len(r.issues) >= 3

    def test_deterministic_ordering(self) -> None:
        p = copy.deepcopy(AI_PAYLOAD)
        p["metadata"]["session_id"] = "x"
        p["position_assessment"]["entry_price"] = 999
        r1 = validate_state_consistency(p, CANONICAL)
        r2 = validate_state_consistency(p, CANONICAL)
        assert r1.issues == r2.issues
