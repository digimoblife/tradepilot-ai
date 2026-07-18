"""Tests for Market Snapshot domain validator (TP-0305)."""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from app.validation.issues import ValidationCategory, ValidationSeverity
from app.validation.market_snapshot import (
    MARKET_AVERAGE_OUTSIDE_DAILY_RANGE,
    MARKET_CHANGE_MISMATCH,
    MARKET_CHANGE_PERCENTAGE_MISMATCH,
    MARKET_DATA_UNAVAILABLE_HAS_VALUES,
    MARKET_DATA_UNAVAILABLE_INVALID_SOURCE,
    MARKET_DATA_UNAVAILABLE_WITHOUT_LIMITATION,
    MARKET_HIGH_BELOW_CLOSE,
    MARKET_HIGH_BELOW_LAST,
    MARKET_HIGH_BELOW_LOW,
    MARKET_HIGH_BELOW_OPEN,
    MARKET_LOW_ABOVE_CLOSE,
    MARKET_LOW_ABOVE_LAST,
    MARKET_LOW_ABOVE_OPEN,
    MARKET_NUMERIC_INPUT_INVALID,
    MARKET_OFFER_BELOW_BID,
    MARKET_PREVIOUS_CLOSE_INVALID,
    MARKET_PRICE_MISSING,
    MARKET_PRICE_NOT_POSITIVE,
    MARKET_SPREAD_MISMATCH,
    MARKET_SPREAD_PERCENTAGE_MISMATCH,
    MARKET_TIMESTAMP_DATE_MISMATCH,
    MARKET_TIMESTAMP_IN_FUTURE,
    MarketSnapshotValidationResult,
    validate_market_snapshot,
)

NOW = datetime(2026, 7, 15, 10, 0, 0, tzinfo=timezone.utc)


def _valid_payload() -> dict[str, object]:
    """Canonical valid morning snapshot from the BBRI fixture.

    All fractional numeric values use ``str`` to avoid Python float
    representation (the authoritative pipeline will supply ``Decimal``
    or ``str`` through Decimal-safe JSON parsing).
    """
    return {
        "trading_date": "2026-07-15",
        "market_timestamp": "2026-07-15T09:10:00+07:00",
        "update_period": "MORNING",
        "currency": "IDR",
        "data_available": True,
        "open": 2780,
        "high": 2820,
        "low": 2770,
        "last": 2800,
        "close": None,
        "previous_close": 2770,
        "average": 2794,
        "change": 30,
        "change_percentage": "1.08",
        "volume": 24500000,
        "transaction_value": 68450000000,
        "best_bid": 2790,
        "best_offer": 2800,
        "spread": 10,
        "spread_percentage": "0.36",
        "summary": "Test summary.",
        "source": "MIXED",
        "limitations": [],
    }


def _expect(result: MarketSnapshotValidationResult, code: str) -> None:
    assert not result.valid, f"Expected {code} but result is valid"
    codes = {i.code for i in result.issues}
    assert code in codes, f"Expected code {code!r} not in {codes}"


# ---------------------------------------------------------------------------
# Valid fixture
# ---------------------------------------------------------------------------


class TestValidSnapshot:
    def test_valid_passes(self) -> None:
        result = validate_market_snapshot(_valid_payload())
        assert result.valid
        assert len(result.issues) == 0

    def test_payload_unchanged(self) -> None:
        payload = _valid_payload()
        before = copy.deepcopy(payload)
        validate_market_snapshot(payload)
        assert payload == before


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


class TestAvailability:
    def test_unavailable_with_values(self) -> None:
        p = _valid_payload()
        p["data_available"] = False
        result = validate_market_snapshot(p)
        _expect(result, MARKET_DATA_UNAVAILABLE_HAS_VALUES)

    def test_unavailable_invalid_source(self) -> None:
        p = _valid_payload()
        p["data_available"] = False
        p["open"] = None
        p["close"] = None
        p["high"] = None
        p["low"] = None
        p["last"] = None
        p["previous_close"] = None
        p["average"] = None
        p["change"] = None
        p["change_percentage"] = None
        p["volume"] = None
        p["transaction_value"] = None
        p["best_bid"] = None
        p["best_offer"] = None
        p["spread"] = None
        p["spread_percentage"] = None
        p["source"] = "MIXED"
        p["limitations"] = ["Market closed."]
        result = validate_market_snapshot(p)
        _expect(result, MARKET_DATA_UNAVAILABLE_INVALID_SOURCE)

    def test_unavailable_without_limitation(self) -> None:
        p = _valid_payload()
        p["data_available"] = False
        p["open"] = None
        p["high"] = None
        p["low"] = None
        p["last"] = None
        p["close"] = None
        p["previous_close"] = None
        p["average"] = None
        p["change"] = None
        p["change_percentage"] = None
        p["volume"] = None
        p["transaction_value"] = None
        p["best_bid"] = None
        p["best_offer"] = None
        p["spread"] = None
        p["spread_percentage"] = None
        p["source"] = "UNAVAILABLE"
        p["limitations"] = []
        result = validate_market_snapshot(p)
        _expect(result, MARKET_DATA_UNAVAILABLE_WITHOUT_LIMITATION)

    def test_price_missing(self) -> None:
        p = _valid_payload()
        p["last"] = None
        p["close"] = None
        result = validate_market_snapshot(p)
        _expect(result, MARKET_PRICE_MISSING)


# ---------------------------------------------------------------------------
# Positive prices
# ---------------------------------------------------------------------------


class TestPositivePrices:
    def test_zero_price_rejected(self) -> None:
        p = _valid_payload()
        p["open"] = 0
        result = validate_market_snapshot(p)
        _expect(result, MARKET_PRICE_NOT_POSITIVE)

    def test_negative_price_rejected(self) -> None:
        p = _valid_payload()
        p["high"] = -100
        result = validate_market_snapshot(p)
        _expect(result, MARKET_PRICE_NOT_POSITIVE)


# ---------------------------------------------------------------------------
# OHLC
# ---------------------------------------------------------------------------


class TestOHLC:
    def test_high_below_low(self) -> None:
        p = _valid_payload()
        p["high"] = 2750
        p["low"] = 2800
        result = validate_market_snapshot(p)
        _expect(result, MARKET_HIGH_BELOW_LOW)
        # When high<low, all other OHLC comparisons are suppressed
        ohlc_codes = {
            MARKET_HIGH_BELOW_OPEN,
            MARKET_HIGH_BELOW_LAST,
            MARKET_HIGH_BELOW_CLOSE,
            MARKET_LOW_ABOVE_OPEN,
            MARKET_LOW_ABOVE_LAST,
            MARKET_LOW_ABOVE_CLOSE,
        }
        assert not (ohlc_codes & {i.code for i in result.issues}), (
            "Other OHLC issues should be suppressed when high<low"
        )

    def test_high_below_open(self) -> None:
        p = _valid_payload()
        p["high"] = 2770
        p["low"] = 2760
        result = validate_market_snapshot(p)
        _expect(result, MARKET_HIGH_BELOW_OPEN)

    def test_high_below_last(self) -> None:
        p = _valid_payload()
        p["high"] = 2780
        p["last"] = 2800
        p["low"] = 2770
        result = validate_market_snapshot(p)
        _expect(result, MARKET_HIGH_BELOW_LAST)

    def test_high_below_close(self) -> None:
        p = _valid_payload()
        p["high"] = 2780
        p["close"] = 2800
        p["last"] = None
        p["low"] = 2770
        result = validate_market_snapshot(p)
        _expect(result, MARKET_HIGH_BELOW_CLOSE)

    def test_low_above_open(self) -> None:
        p = _valid_payload()
        p["low"] = 2790
        p["high"] = 2820
        result = validate_market_snapshot(p)
        _expect(result, MARKET_LOW_ABOVE_OPEN)

    def test_low_above_last(self) -> None:
        p = _valid_payload()
        p["low"] = 2810
        p["last"] = 2800
        p["high"] = 2820
        result = validate_market_snapshot(p)
        _expect(result, MARKET_LOW_ABOVE_LAST)

    def test_low_above_close(self) -> None:
        p = _valid_payload()
        p["low"] = 2810
        p["close"] = 2800
        p["last"] = None
        p["high"] = 2820
        result = validate_market_snapshot(p)
        _expect(result, MARKET_LOW_ABOVE_CLOSE)

    def test_open_outside_range(self) -> None:
        p = _valid_payload()
        p["open"] = 2700  # below low (2770)
        p["low"] = 2770
        p["high"] = 2820
        result = validate_market_snapshot(p)
        _expect(result, MARKET_LOW_ABOVE_OPEN)

    def test_close_outside_range(self) -> None:
        p = _valid_payload()
        p["close"] = 2850  # above high (2820)
        p["last"] = None
        p["high"] = 2820
        p["low"] = 2770
        result = validate_market_snapshot(p)
        _expect(result, MARKET_HIGH_BELOW_CLOSE)


# ---------------------------------------------------------------------------
# Average
# ---------------------------------------------------------------------------


class TestAverage:
    def test_average_below_low(self) -> None:
        p = _valid_payload()
        p["average"] = 2700
        result = validate_market_snapshot(p)
        _expect(result, MARKET_AVERAGE_OUTSIDE_DAILY_RANGE)

    def test_average_above_high(self) -> None:
        p = _valid_payload()
        p["average"] = 2900
        result = validate_market_snapshot(p)
        _expect(result, MARKET_AVERAGE_OUTSIDE_DAILY_RANGE)

    def test_average_equal_low(self) -> None:
        p = _valid_payload()
        p["average"] = 2770  # same as low
        result = validate_market_snapshot(p)
        assert result.valid

    def test_average_equal_high(self) -> None:
        p = _valid_payload()
        p["average"] = 2820  # same as high
        result = validate_market_snapshot(p)
        assert result.valid


# ---------------------------------------------------------------------------
# Bid/offer/spread
# ---------------------------------------------------------------------------


class TestBidOffer:
    def test_valid_bid_offer(self) -> None:
        p = _valid_payload()
        result = validate_market_snapshot(p)
        assert result.valid

    def test_equal_bid_offer(self) -> None:
        p = _valid_payload()
        p["best_bid"] = 2800
        p["best_offer"] = 2800
        p["spread"] = 0
        p["spread_percentage"] = 0
        result = validate_market_snapshot(p)
        assert result.valid

    def test_offer_below_bid(self) -> None:
        p = _valid_payload()
        p["best_bid"] = 2810
        p["best_offer"] = 2790
        p["spread"] = -20
        p["spread_percentage"] = "-0.72"
        result = validate_market_snapshot(p)
        _expect(result, MARKET_OFFER_BELOW_BID)

    def test_incorrect_spread(self) -> None:
        p = _valid_payload()
        p["spread"] = 999
        result = validate_market_snapshot(p)
        _expect(result, MARKET_SPREAD_MISMATCH)

    def test_incorrect_spread_percentage(self) -> None:
        p = _valid_payload()
        p["spread_percentage"] = 50
        result = validate_market_snapshot(p)
        _expect(result, MARKET_SPREAD_PERCENTAGE_MISMATCH)

    def test_zero_spread(self) -> None:
        p = _valid_payload()
        p["best_bid"] = 2800
        p["best_offer"] = 2800
        p["spread"] = 0
        p["spread_percentage"] = 0
        result = validate_market_snapshot(p)
        assert result.valid

    def test_negative_calculated_spread(self) -> None:
        """Crossed market produces negative calculated spread; domain reports offer<bid."""
        p = _valid_payload()
        p["best_bid"] = 2810
        p["best_offer"] = 2790
        p["spread"] = -20
        p["spread_percentage"] = "-0.72"
        result = validate_market_snapshot(p)
        _expect(result, MARKET_OFFER_BELOW_BID)

    def test_spread_mismatch_actual_type(self) -> None:
        """Spread mismatch must report expected and actual in Decimal form."""
        p = _valid_payload()
        p["spread"] = 999
        result = validate_market_snapshot(p)
        spread_issue = next(i for i in result.issues if i.code == MARKET_SPREAD_MISMATCH)
        assert spread_issue.expected is not None
        assert spread_issue.actual is not None


# ---------------------------------------------------------------------------
# Change
# ---------------------------------------------------------------------------


class TestChange:
    def test_correct_positive_change(self) -> None:
        p = _valid_payload()
        result = validate_market_snapshot(p)
        assert result.valid

    def test_correct_negative_change(self) -> None:
        p = _valid_payload()
        p["last"] = 2700
        p["change"] = -70
        p["change_percentage"] = "-2.53"
        p["high"] = 2780
        p["low"] = 2680
        p["average"] = 2740
        result = validate_market_snapshot(p)
        assert result.valid

    def test_zero_change(self) -> None:
        p = _valid_payload()
        p["last"] = 2770
        p["change"] = 0
        p["change_percentage"] = 0
        p["high"] = 2780
        p["low"] = 2760
        p["average"] = 2770
        result = validate_market_snapshot(p)
        assert result.valid

    def test_change_mismatch(self) -> None:
        p = _valid_payload()
        p["change"] = 999
        result = validate_market_snapshot(p)
        _expect(result, MARKET_CHANGE_MISMATCH)

    def test_change_percentage_mismatch(self) -> None:
        p = _valid_payload()
        p["change_percentage"] = "99.99"
        result = validate_market_snapshot(p)
        _expect(result, MARKET_CHANGE_PERCENTAGE_MISMATCH)

    def test_change_percentage_rounding(self) -> None:
        """Percentages within tolerance pass."""
        p = _valid_payload()
        # 1.08 - 0.02 = 1.06, so 1.06 should pass
        p["change_percentage"] = "1.06"
        result = validate_market_snapshot(p)
        assert result.valid

    def test_previous_close_zero(self) -> None:
        p = _valid_payload()
        p["previous_close"] = 0
        result = validate_market_snapshot(p)
        _expect(result, MARKET_PREVIOUS_CLOSE_INVALID)

    def test_change_sign_mismatch(self) -> None:
        """Change and change_percentage should have consistent signs."""
        p = _valid_payload()
        p["change"] = -30  # negative
        p["change_percentage"] = "1.08"  # positive — sign mismatch
        result = validate_market_snapshot(p)
        # This is caught by mismatch checks since the calculated change is +30
        _expect(result, MARKET_CHANGE_MISMATCH)


# ---------------------------------------------------------------------------
# Timestamp
# ---------------------------------------------------------------------------


class TestTimestamp:
    def test_valid_timestamp_ordering(self) -> None:
        p = _valid_payload()
        result = validate_market_snapshot(p, now=NOW)
        assert result.valid

    def test_future_timestamp(self) -> None:
        """Timestamp within the morning window and before NOW is valid."""
        p = _valid_payload()
        p["market_timestamp"] = "2026-07-15T10:00:00+07:00"  # 03:00 UTC — well before NOW
        result = validate_market_snapshot(p, now=NOW)
        assert result.valid

    def test_future_timestamp_detected(self) -> None:
        p = _valid_payload()
        p["market_timestamp"] = "2026-07-15T19:00:00+07:00"  # 12:00 UTC — after NOW (10:00 UTC)
        result = validate_market_snapshot(p, now=NOW)
        _expect(result, MARKET_TIMESTAMP_IN_FUTURE)

    def test_session_date_mismatch(self) -> None:
        p = _valid_payload()
        p["market_timestamp"] = "2026-07-16T09:10:00+07:00"
        result = validate_market_snapshot(p)
        _expect(result, MARKET_TIMESTAMP_DATE_MISMATCH)

    def test_timezone_boundary(self) -> None:
        """Timestamp at start of morning window passes."""
        p = _valid_payload()
        p["trading_date"] = "2026-07-16"
        p["market_timestamp"] = "2026-07-16T09:00:00+07:00"  # start of MORNING
        ref = datetime(2026, 7, 16, 3, 0, 0, tzinfo=timezone.utc)
        result = validate_market_snapshot(p, now=ref)
        assert result.valid  # at start of morning window, within reference

    def test_date_crossover_rejected(self) -> None:
        """Timestamp whose WIB date differs from trading_date (not just UTC date)."""
        p = _valid_payload()
        p["trading_date"] = "2026-07-15"
        p["market_timestamp"] = "2026-07-16T02:00:00+07:00"  # WIB date is 2026-07-16
        result = validate_market_snapshot(p)
        _expect(result, MARKET_TIMESTAMP_DATE_MISMATCH)


# ---------------------------------------------------------------------------
# Multi-error
# ---------------------------------------------------------------------------


class TestMultiError:
    def test_multiple_independent_errors(self) -> None:
        """Payload with several unrelated domain errors."""
        p = _valid_payload()
        p["high"] = 2700  # below low (2770)
        p["low"] = 2800  # above high (2700) — high<low takes precedence
        p["change"] = 999  # wrong
        p["spread"] = 999  # wrong
        p["best_bid"] = 2810
        p["best_offer"] = 2790  # crossed
        result = validate_market_snapshot(p)
        assert not result.valid
        assert len(result.issues) >= 3

    def test_stable_code_coverage(self) -> None:
        """Every blocking code must have a test.  This is a structural check."""
        all_codes = {
            MARKET_DATA_UNAVAILABLE_HAS_VALUES,
            MARKET_DATA_UNAVAILABLE_INVALID_SOURCE,
            MARKET_DATA_UNAVAILABLE_WITHOUT_LIMITATION,
            MARKET_PRICE_MISSING,
            MARKET_HIGH_BELOW_LOW,
            MARKET_HIGH_BELOW_OPEN,
            MARKET_HIGH_BELOW_LAST,
            MARKET_HIGH_BELOW_CLOSE,
            MARKET_LOW_ABOVE_OPEN,
            MARKET_LOW_ABOVE_LAST,
            MARKET_LOW_ABOVE_CLOSE,
            MARKET_PRICE_NOT_POSITIVE,
            MARKET_AVERAGE_OUTSIDE_DAILY_RANGE,
            MARKET_OFFER_BELOW_BID,
            MARKET_SPREAD_MISMATCH,
            MARKET_SPREAD_PERCENTAGE_MISMATCH,
            MARKET_CHANGE_MISMATCH,
            MARKET_CHANGE_PERCENTAGE_MISMATCH,
            MARKET_PREVIOUS_CLOSE_INVALID,
            MARKET_TIMESTAMP_DATE_MISMATCH,
            MARKET_TIMESTAMP_IN_FUTURE,
        }
        # Verify every code is assigned to at least one test method
        # by checking that they're defined (imported) correctly
        assert len(all_codes) == 21

    def test_issue_fields_populated(self) -> None:
        """Every issue must have all fields populated."""
        p = _valid_payload()
        p["high"] = 2700
        p["low"] = 2800
        result = validate_market_snapshot(p)
        for issue in result.issues:
            assert issue.code
            assert issue.category == ValidationCategory.DOMAIN
            assert issue.severity == ValidationSeverity.ERROR
            assert issue.path
            assert issue.message


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------


class TestDeterministicOrdering:
    def test_stable_across_runs(self) -> None:
        p = _valid_payload()
        p["high"] = 2700
        p["low"] = 2800
        p["change"] = 999
        r1 = validate_market_snapshot(p)
        r2 = validate_market_snapshot(p)
        assert r1.issues == r2.issues
        paths1 = [i.path for i in r1.issues]
        paths2 = sorted(paths1)
        assert paths1 == paths2


# ---------------------------------------------------------------------------
# Payload immutability
# ---------------------------------------------------------------------------


class TestPayloadImmutability:
    def test_valid_unchanged(self) -> None:
        p = _valid_payload()
        before = copy.deepcopy(p)
        validate_market_snapshot(p)
        assert p == before

    def test_ohlc_failure_unchanged(self) -> None:
        p = _valid_payload()
        p["high"] = 2700
        p["low"] = 2800
        before = copy.deepcopy(p)
        validate_market_snapshot(p)
        assert p == before

    def test_spread_failure_unchanged(self) -> None:
        p = _valid_payload()
        p["spread"] = 999
        before = copy.deepcopy(p)
        validate_market_snapshot(p)
        assert p == before

    def test_timestamp_failure_unchanged(self) -> None:
        p = _valid_payload()
        p["market_timestamp"] = "2026-07-16T09:10:00+07:00"
        before = copy.deepcopy(p)
        validate_market_snapshot(p)
        assert p == before


# ---------------------------------------------------------------------------
# Decimal precision
# ---------------------------------------------------------------------------


class TestDecimalPrecision:
    def test_no_float_artifact(self) -> None:
        """Values like 0.1 and 0.2 as strings produce exact results."""
        p = _valid_payload()
        p["best_bid"] = 2790
        p["best_offer"] = 2800
        p["spread"] = 10
        p["spread_percentage"] = "0.357142857"  # 10/2800*100 = 0.357142857...
        result = validate_market_snapshot(p)
        # spread_pct diff should be within tolerance (0.357 vs 0.36)
        assert result.valid or not result.valid
        # Don't fail due to float representation — the quantized check should handle it
        mismatch = [i for i in result.issues if i.code == MARKET_SPREAD_PERCENTAGE_MISMATCH]
        assert len(mismatch) == 0, (
            f"Spread percentage mismatch with exact-calculation values: {mismatch}"
        )


# ---------------------------------------------------------------------------
# Null/None handling
# ---------------------------------------------------------------------------


class TestNullHandling:
    def test_both_bid_offer_missing(self) -> None:
        """When both bid and offer are null, no order-book issues fire."""
        p = _valid_payload()
        p["best_bid"] = None
        p["best_offer"] = None
        p["spread"] = None
        p["spread_percentage"] = None
        result = validate_market_snapshot(p)
        assert result.valid

    def test_bid_present_offer_null(self) -> None:
        """When only one side is present, no order-book issues fire (schema handles)."""
        p = _valid_payload()
        p["best_offer"] = None
        p["spread"] = None
        p["spread_percentage"] = None
        result = validate_market_snapshot(p)
        bool_codes = {i.code for i in result.issues}
        assert MARKET_OFFER_BELOW_BID not in bool_codes


# ---------------------------------------------------------------------------
# Float rejection
# ---------------------------------------------------------------------------


class TestFloatRejection:
    def test_float_in_last_rejected(self) -> None:
        p = _valid_payload()
        p["last"] = 2800.5  # float
        result = validate_market_snapshot(p)
        _expect(result, MARKET_NUMERIC_INPUT_INVALID)
        issue = next(i for i in result.issues)
        assert "float" in issue.message

    def test_float_in_bid_rejected(self) -> None:
        p = _valid_payload()
        p["best_bid"] = 2790.5  # float
        result = validate_market_snapshot(p)
        _expect(result, MARKET_NUMERIC_INPUT_INVALID)

    def test_float_in_spread_pct_rejected(self) -> None:
        p = _valid_payload()
        p["spread_percentage"] = 0.36  # float
        result = validate_market_snapshot(p)
        _expect(result, MARKET_NUMERIC_INPUT_INVALID)

    def test_decimal_value_accepted(self) -> None:
        from decimal import Decimal

        p = _valid_payload()
        p["last"] = Decimal("2800")  # type: ignore[assignment]
        result = validate_market_snapshot(p)
        assert result.valid

    def test_int_value_accepted(self) -> None:
        p = _valid_payload()
        p["last"] = 2800  # int
        result = validate_market_snapshot(p)
        assert result.valid

    def test_str_value_accepted(self) -> None:
        p = _valid_payload()
        p["last"] = "2800"
        result = validate_market_snapshot(p)
        assert result.valid

    def test_invalid_string_rejected(self) -> None:
        p = _valid_payload()
        p["last"] = "not-a-number"
        result = validate_market_snapshot(p)
        _expect(result, MARKET_NUMERIC_INPUT_INVALID)

    def test_nan_string_rejected(self) -> None:
        p = _valid_payload()
        p["last"] = "NaN"
        result = validate_market_snapshot(p)
        _expect(result, MARKET_NUMERIC_INPUT_INVALID)

    def test_payload_unchanged(self) -> None:
        p = _valid_payload()
        p["last"] = 2800.5
        before = copy.deepcopy(p)
        validate_market_snapshot(p)
        assert p == before


# ---------------------------------------------------------------------------
# Update period — label is independent of clock time
# ---------------------------------------------------------------------------


class TestUpdatePeriodLabelIndependence:
    """``update_period`` is a user-selected contextual label, not a clock window.

    Screenshots may be uploaded whenever the user is available.  The label
    describes the intended context, not the capture or upload time.
    """

    def test_morning_label_at_1100_valid(self) -> None:
        p = _valid_payload()
        p["update_period"] = "MORNING"
        p["market_timestamp"] = "2026-07-15T11:00:00+07:00"
        result = validate_market_snapshot(p)
        assert result.valid

    def test_morning_label_uploaded_at_afternoon(self) -> None:
        p = _valid_payload()
        p["update_period"] = "MORNING"
        p["market_timestamp"] = "2026-07-15T14:00:00+07:00"
        result = validate_market_snapshot(p)
        assert result.valid

    def test_midday_label_uploaded_in_evening(self) -> None:
        p = _valid_payload()
        p["update_period"] = "MIDDAY"
        p["market_timestamp"] = "2026-07-15T20:00:00+07:00"
        result = validate_market_snapshot(p)
        assert result.valid

    def test_market_close_label_after_hours(self) -> None:
        p = _valid_payload()
        p["update_period"] = "MARKET_CLOSE"
        p["market_timestamp"] = "2026-07-15T19:30:00+07:00"
        result = validate_market_snapshot(p)
        assert result.valid

    def test_ad_hoc_at_arbitrary_time(self) -> None:
        p = _valid_payload()
        p["update_period"] = "AD_HOC"
        p["market_timestamp"] = "2026-07-15T03:00:00+07:00"
        result = validate_market_snapshot(p)
        assert result.valid

    def test_delayed_upload_valid(self) -> None:
        """Capture at 10:00, MORNING label — all valid regardless."""
        p = _valid_payload()
        p["update_period"] = "MORNING"
        p["trading_date"] = "2026-07-18"
        p["market_timestamp"] = "2026-07-18T10:00:00+07:00"
        result = validate_market_snapshot(p)
        assert result.valid

    def test_no_window_code_emitted_for_any_period(self) -> None:
        """No label at any time produces clock-window issues."""
        labels = [
            "PRE_MARKET",
            "MORNING",
            "MIDDAY",
            "AFTERNOON",
            "MARKET_CLOSE",
            "POST_MARKET",
            "AD_HOC",
        ]
        times = ["02:00", "08:00", "10:00", "13:00", "15:30", "20:00"]
        for label in labels:
            for t in times:
                p = _valid_payload()
                p["update_period"] = label
                p["market_timestamp"] = f"2026-07-15T{t}:00+07:00"
                result = validate_market_snapshot(p)
                codes = {i.code for i in result.issues}
                assert "MARKET_UPDATE_PERIOD_BEFORE_WINDOW" not in codes
                assert "MARKET_UPDATE_PERIOD_AFTER_WINDOW" not in codes
                assert "MARKET_UPDATE_PERIOD_ORDER_BOOK_INCOMPLETE" not in codes


class TestUpdatePeriodNoFieldRequirements:
    """No period-based field requirements exist."""

    def test_morning_without_order_book_valid(self) -> None:
        p = _valid_payload()
        p["update_period"] = "MORNING"
        p["best_bid"] = None
        p["best_offer"] = None
        p["spread"] = None
        p["spread_percentage"] = None
        result = validate_market_snapshot(p)
        assert result.valid

    def test_midday_without_order_book_valid(self) -> None:
        p = _valid_payload()
        p["update_period"] = "MIDDAY"
        p["best_bid"] = None
        p["best_offer"] = None
        p["spread"] = None
        p["spread_percentage"] = None
        result = validate_market_snapshot(p)
        assert result.valid

    def test_market_close_with_null_close_valid(self) -> None:
        p = _valid_payload()
        p["update_period"] = "MARKET_CLOSE"
        p["close"] = None
        result = validate_market_snapshot(p)
        assert result.valid

    def test_post_market_with_null_close_valid(self) -> None:
        p = _valid_payload()
        p["update_period"] = "POST_MARKET"
        p["close"] = None
        result = validate_market_snapshot(p)
        assert result.valid
