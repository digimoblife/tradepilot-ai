"""Tests for fixture factories (TP-0401)."""

from __future__ import annotations

import copy

from app.validation.market_snapshot import validate_market_snapshot
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

# ===================================================================
# Determinism
# ===================================================================


class TestDeterminism:
    def test_market_snapshot(self) -> None:
        assert make_market_snapshot() == make_market_snapshot()

    def test_not_opened(self) -> None:
        assert make_not_opened_trade_state() == make_not_opened_trade_state()

    def test_open(self) -> None:
        assert make_open_trade_state() == make_open_trade_state()

    def test_partial(self) -> None:
        assert make_partial_trade_state() == make_partial_trade_state()

    def test_closed(self) -> None:
        assert make_closed_trade_state() == make_closed_trade_state()

    def test_evidence(self) -> None:
        assert make_evidence() == make_evidence()

    def test_analysis(self) -> None:
        assert make_analysis("INITIAL_ANALYSIS") == make_analysis("INITIAL_ANALYSIS")

    def test_context(self) -> None:
        assert make_context_summary() == make_context_summary()


# ===================================================================
# Fixed IDs
# ===================================================================


class TestFixedIds:
    def test_session_id(self) -> None:
        assert make_open_trade_state()["session_id"] == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_evidence_id(self) -> None:
        ev = make_evidence()
        assert ev["evidence_id"] == "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        assert ev["session_id"] == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_analysis_id(self) -> None:
        a = make_analysis("INITIAL_ANALYSIS")
        meta = a.get("metadata", {})
        if isinstance(meta, dict):
            assert meta.get("analysis_id") == "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

    def test_context_id(self) -> None:
        c = make_context_summary()
        assert c["context_id"] == "66666666-6666-4666-8666-666666666666"


# ===================================================================
# Valid defaults
# ===================================================================


class TestValidDefaults:
    def test_market_snapshot_valid(self) -> None:
        ms = make_market_snapshot()
        result = validate_market_snapshot(ms)
        assert result.valid, f"Market snapshot issues: {result.issues}"

    def test_not_opened_valid(self) -> None:
        ts = make_not_opened_trade_state()
        # validate_top-level structure as trade state position
        position = ts.get("position")
        assert position is not None
        assert isinstance(position, dict)
        assert position.get("position_status") == "NOT_OPENED"

    def test_open_valid(self) -> None:
        ts = make_open_trade_state()
        position = ts.get("position")
        assert isinstance(position, dict)
        assert position.get("position_status") == "OPEN"
        assert position.get("remaining_quantity") == position.get("original_quantity")

    def test_partial_valid(self) -> None:
        ts = make_partial_trade_state()
        position = ts.get("position")
        assert isinstance(position, dict)
        assert position.get("position_status") == "PARTIALLY_CLOSED"
        assert 0 < position["remaining_quantity"] < position["original_quantity"]

    def test_closed_valid(self) -> None:
        ts = make_closed_trade_state()
        position = ts.get("position")
        assert isinstance(position, dict)
        assert position.get("position_status") == "CLOSED"
        assert position.get("remaining_quantity") == 0
        assert position.get("active_stop_loss") is None
        assert position.get("active_target") is None


# ===================================================================
# Automatic calculations
# ===================================================================


class TestCalculations:
    def test_market_change(self) -> None:
        ms = make_market_snapshot()
        assert ms["change"] == 50  # 2830 - 2780

    def test_market_spread(self) -> None:
        ms = make_market_snapshot()
        assert ms["spread"] == 10  # 2830 - 2820

    def test_closing_weighted_exit(self) -> None:
        ts = make_closed_trade_state()
        pos = ts["position"]
        assert pos["average_exit_price"] == 2910  # (50*2920 + 50*2900) / 100


# ===================================================================
# Deep merge
# ===================================================================


class TestDeepMerge:
    def test_nested_scalar(self) -> None:
        ms = make_market_snapshot(overrides={"open": 3000})
        assert ms["open"] == 3000
        assert ms["high"] == 2850  # unchanged

    def test_nullable_override(self) -> None:
        ms = make_market_snapshot(overrides={"close": 2900})
        assert ms["close"] == 2900

    def test_list_replacement(self) -> None:
        ms = make_market_snapshot(overrides={"limitations": ["Only delayed data."]})
        assert ms["limitations"] == ["Only delayed data."]

    def test_multi_level_override(self) -> None:
        ts = make_open_trade_state(overrides={"position": {"remaining_quantity": 50}})
        assert ts["position"]["remaining_quantity"] == 50
        assert ts["position"]["entry_price"] == 2800  # unchanged

    def test_base_immutable(self) -> None:
        base = make_open_trade_state()
        before = copy.deepcopy(base)
        make_open_trade_state(overrides={"position": {"remaining_quantity": 50}})
        assert base == before

    def test_override_immutable(self) -> None:
        ov = {"position": {"remaining_quantity": 50}}
        before = copy.deepcopy(ov)
        make_open_trade_state(overrides=ov)
        assert ov == before


# ===================================================================
# Isolation
# ===================================================================


class TestIsolation:
    def test_separate_calls_independent(self) -> None:
        a = make_market_snapshot()
        b = make_market_snapshot()
        a["open"] = 9999
        assert b["open"] == 2800

    def test_nested_isolation(self) -> None:
        a = make_open_trade_state()
        b = make_open_trade_state()
        a["position"]["remaining_quantity"] = 999
        assert b["position"]["remaining_quantity"] == 100


# ===================================================================
# Deep merge utility
# ===================================================================


class TestDeepMergeUtility:
    def test_nested_merge(self) -> None:
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        merged = deep_merge(base, {"b": {"c": 99}})
        assert merged["b"]["c"] == 99
        assert merged["b"]["d"] == 3
        assert base["b"]["c"] == 2  # unchanged

    def test_list_replaces(self) -> None:
        base = {"items": [1, 2, 3]}
        merged = deep_merge(base, {"items": [4]})
        assert merged["items"] == [4]

    def test_new_key(self) -> None:
        base = {"a": 1}
        merged = deep_merge(base, {"b": 2})
        assert merged["b"] == 2

    def test_null_value(self) -> None:
        base = {"x": 5}
        merged = deep_merge(base, {"x": None})
        assert merged["x"] is None
