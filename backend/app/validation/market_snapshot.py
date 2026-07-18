"""Domain validation for TradePilot AI Market Snapshot payloads.

Runs after JSON Schema validation (TP-0303) and assumes required field
shapes are structurally valid.  Domain rules cover OHLC relationships,
bid/offer/spread consistency, change reconciliation, and timestamp ordering.

``update_period`` is a contextual label selected by the user.  It is not
derived from, or validated against, upload time, capture time, or market
clock windows.  Screenshots may be uploaded whenever the user is available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Mapping

from app.calculations.decimal_utils import (
    quantize_percentage,
    to_decimal,
)
from app.calculations.errors import InvalidDecimalError
from app.calculations.market import (
    calculate_market_change,
    calculate_percentage_change,
    calculate_spread,
)
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

# ---------------------------------------------------------------------------
# Domain issue category
# ---------------------------------------------------------------------------

DOMAIN_CATEGORY = ValidationCategory("DOMAIN")

# ---------------------------------------------------------------------------
# Stable error codes
# ---------------------------------------------------------------------------

# Availability
MARKET_DATA_UNAVAILABLE_HAS_VALUES = "MARKET_DATA_UNAVAILABLE_HAS_VALUES"
MARKET_DATA_UNAVAILABLE_INVALID_SOURCE = "MARKET_DATA_UNAVAILABLE_INVALID_SOURCE"
MARKET_DATA_UNAVAILABLE_WITHOUT_LIMITATION = "MARKET_DATA_UNAVAILABLE_WITHOUT_LIMITATION"
MARKET_PRICE_MISSING = "MARKET_PRICE_MISSING"

# OHLC
MARKET_HIGH_BELOW_LOW = "MARKET_HIGH_BELOW_LOW"
MARKET_HIGH_BELOW_OPEN = "MARKET_HIGH_BELOW_OPEN"
MARKET_HIGH_BELOW_LAST = "MARKET_HIGH_BELOW_LAST"
MARKET_HIGH_BELOW_CLOSE = "MARKET_HIGH_BELOW_CLOSE"
MARKET_LOW_ABOVE_OPEN = "MARKET_LOW_ABOVE_OPEN"
MARKET_LOW_ABOVE_LAST = "MARKET_LOW_ABOVE_LAST"
MARKET_LOW_ABOVE_CLOSE = "MARKET_LOW_ABOVE_CLOSE"

# Positive
MARKET_PRICE_NOT_POSITIVE = "MARKET_PRICE_NOT_POSITIVE"

# Average
MARKET_AVERAGE_OUTSIDE_DAILY_RANGE = "MARKET_AVERAGE_OUTSIDE_DAILY_RANGE"

# Bid/offer/spread
MARKET_OFFER_BELOW_BID = "MARKET_OFFER_BELOW_BID"
MARKET_SPREAD_MISMATCH = "MARKET_SPREAD_MISMATCH"
MARKET_SPREAD_PERCENTAGE_MISMATCH = "MARKET_SPREAD_PERCENTAGE_MISMATCH"

# Change
MARKET_CHANGE_MISMATCH = "MARKET_CHANGE_MISMATCH"
MARKET_CHANGE_PERCENTAGE_MISMATCH = "MARKET_CHANGE_PERCENTAGE_MISMATCH"
MARKET_PREVIOUS_CLOSE_INVALID = "MARKET_PREVIOUS_CLOSE_INVALID"

# Timestamp
MARKET_TIMESTAMP_DATE_MISMATCH = "MARKET_TIMESTAMP_DATE_MISMATCH"
MARKET_TIMESTAMP_IN_FUTURE = "MARKET_TIMESTAMP_IN_FUTURE"

# Numeric input
MARKET_NUMERIC_INPUT_INVALID = "MARKET_NUMERIC_INPUT_INVALID"

# ---------------------------------------------------------------------------
# Tolerance
# ---------------------------------------------------------------------------

PERCENT_TOLERANCE = Decimal("0.02")

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarketSnapshotValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NUMERIC_FIELDS = frozenset(
    {
        "open",
        "high",
        "low",
        "last",
        "close",
        "previous_close",
        "average",
        "best_bid",
        "best_offer",
    }
)

_NUMERIC_SIGNED = frozenset({"change"})
_NUMERIC_PERCENT = frozenset({"change_percentage", "spread_percentage"})
_NUMERIC_NONNEG = frozenset({"volume", "transaction_value", "spread"})


def _extract_decimal(
    payload: Mapping[str, object], numeric_field: str
) -> tuple[Decimal | None, list[ValidationIssue]]:
    """Convert a payload field to Decimal using authoritative ``to_decimal()``.

    Returns ``(value_or_None, issues)``.  If the value is not a supported
    type (e.g. ``float``), an issue is returned and the value is ``None``.
    """
    raw = payload.get(numeric_field)
    if raw is None:
        return None, []
    try:
        d = to_decimal(raw)  # type: ignore[arg-type]
        return d, []
    except InvalidDecimalError:
        return None, [
            _make_issue(
                MARKET_NUMERIC_INPUT_INVALID,
                f"/{numeric_field}",
                f"Invalid numeric input for {numeric_field}: "
                f"type={type(raw).__name__}, value={raw!r}",
                expected="Decimal, int, or str",
                actual=f"{type(raw).__name__}: {raw!r}",
            )
        ]


def _is_non_null_price(value: object) -> bool:
    """Check if a field is a non-null number."""
    return value is not None


def _make_issue(
    code: str,
    path: str,
    message: str,
    expected: str | None = None,
    actual: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        category=DOMAIN_CATEGORY,
        severity=ValidationSeverity.ERROR,
        path=path,
        message=message,
        expected=expected,
        actual=actual,
    )


def _sort_key(issue: ValidationIssue) -> tuple[str, str, str, str]:
    return (issue.path, issue.code, issue.category.value, issue.message)


# ---------------------------------------------------------------------------
# Numeric input scan
# ---------------------------------------------------------------------------


def _validate_numeric_inputs(payload: Mapping[str, object]) -> list[ValidationIssue]:
    """Validate all numeric fields through authoritative ``to_decimal()``."""
    issues: list[ValidationIssue] = []
    all_numeric = _NUMERIC_FIELDS | _NUMERIC_SIGNED | _NUMERIC_PERCENT | _NUMERIC_NONNEG
    for numeric_field in all_numeric:
        _, field_issues = _extract_decimal(payload, numeric_field)
        issues.extend(field_issues)
    return issues


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


def _validate_availability(payload: Mapping[str, object]) -> list[ValidationIssue]:
    """Validate data_available flag consistency."""
    issues: list[ValidationIssue] = []
    data_available = payload.get("data_available")

    if data_available is False:
        price_fields = _NUMERIC_FIELDS | _NUMERIC_SIGNED | _NUMERIC_PERCENT | _NUMERIC_NONNEG
        has_values = any(payload.get(f) is not None for f in price_fields)
        if has_values:
            issues.append(
                _make_issue(
                    MARKET_DATA_UNAVAILABLE_HAS_VALUES,
                    "/data_available",
                    "Market data is unavailable but numeric fields contain values",
                    expected=None,
                    actual="non-null values present",
                )
            )

        source = payload.get("source")
        if source is not None and source != "UNAVAILABLE":
            issues.append(
                _make_issue(
                    MARKET_DATA_UNAVAILABLE_INVALID_SOURCE,
                    "/source",
                    f"Source must be UNAVAILABLE when data_available=false, got {source!r}",
                    expected="UNAVAILABLE",
                    actual=str(source),
                )
            )

        limitations = payload.get("limitations")
        if not limitations or (isinstance(limitations, list) and len(limitations) == 0):
            issues.append(
                _make_issue(
                    MARKET_DATA_UNAVAILABLE_WITHOUT_LIMITATION,
                    "/limitations",
                    "Limitations must contain at least one item when data_available=false",
                    expected="minItems: 1",
                    actual=str(limitations),
                )
            )

    if data_available is True:
        has_last = _is_non_null_price(payload.get("last"))
        has_close = _is_non_null_price(payload.get("close"))
        if not has_last and not has_close:
            issues.append(
                _make_issue(
                    MARKET_PRICE_MISSING,
                    "/data_available",
                    "At least one of last or close must be non-null when data_available=true",
                    expected="non-null last or close",
                    actual="both null",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Positive prices
# ---------------------------------------------------------------------------


def _validate_positive_prices(payload: Mapping[str, object]) -> list[ValidationIssue]:
    """All available prices must be positive."""
    issues: list[ValidationIssue] = []
    for numeric_field in _NUMERIC_FIELDS:
        d, _ = _extract_decimal(payload, numeric_field)
        if d is not None and d <= Decimal("0"):
            issues.append(
                _make_issue(
                    MARKET_PRICE_NOT_POSITIVE,
                    f"/{numeric_field}",
                    f"{numeric_field} must be positive, got {d}",
                    expected="> 0",
                    actual=str(d),
                )
            )
    return issues


# ---------------------------------------------------------------------------
# OHLC
# ---------------------------------------------------------------------------


def _d(payload: Mapping[str, object], numeric_field: str) -> Decimal | None:
    """Helper: extract a Decimal from payload, returning None on failure."""
    d, _ = _extract_decimal(payload, numeric_field)
    return d


def _validate_ohlc(payload: Mapping[str, object]) -> list[ValidationIssue]:
    """Validate OHLC field relationships."""
    issues: list[ValidationIssue] = []

    high = _d(payload, "high")
    low = _d(payload, "low")
    open_ = _d(payload, "open")
    last = _d(payload, "last")
    close = _d(payload, "close")

    if high is not None and low is not None:
        if high < low:
            issues.append(
                _make_issue(
                    MARKET_HIGH_BELOW_LOW,
                    "/high",
                    f"High ({high}) is below low ({low})",
                    expected=f">= {low}",
                    actual=str(high),
                )
            )
            return issues

    if high is not None and open_ is not None and high < open_:
        issues.append(
            _make_issue(
                MARKET_HIGH_BELOW_OPEN,
                "/high",
                f"High ({high}) is below open ({open_})",
                expected=f">= {open_}",
                actual=str(high),
            )
        )

    if high is not None and last is not None and high < last:
        issues.append(
            _make_issue(
                MARKET_HIGH_BELOW_LAST,
                "/high",
                f"High ({high}) is below last ({last})",
                expected=f">= {last}",
                actual=str(high),
            )
        )

    if high is not None and close is not None and high < close:
        issues.append(
            _make_issue(
                MARKET_HIGH_BELOW_CLOSE,
                "/high",
                f"High ({high}) is below close ({close})",
                expected=f">= {close}",
                actual=str(high),
            )
        )

    if low is not None and open_ is not None and low > open_:
        issues.append(
            _make_issue(
                MARKET_LOW_ABOVE_OPEN,
                "/low",
                f"Low ({low}) is above open ({open_})",
                expected=f"<= {open_}",
                actual=str(low),
            )
        )

    if low is not None and last is not None and low > last:
        issues.append(
            _make_issue(
                MARKET_LOW_ABOVE_LAST,
                "/low",
                f"Low ({low}) is above last ({last})",
                expected=f"<= {last}",
                actual=str(low),
            )
        )

    if low is not None and close is not None and low > close:
        issues.append(
            _make_issue(
                MARKET_LOW_ABOVE_CLOSE,
                "/low",
                f"Low ({low}) is above close ({close})",
                expected=f"<= {close}",
                actual=str(low),
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Average
# ---------------------------------------------------------------------------


def _validate_average(payload: Mapping[str, object]) -> list[ValidationIssue]:
    """Validate average price is within daily range."""
    issues: list[ValidationIssue] = []

    avg = _d(payload, "average")
    high = _d(payload, "high")
    low = _d(payload, "low")

    if avg is not None and high is not None and low is not None:
        if avg < low or avg > high:
            issues.append(
                _make_issue(
                    MARKET_AVERAGE_OUTSIDE_DAILY_RANGE,
                    "/average",
                    f"Average ({avg}) is outside daily range [{low}, {high}]",
                    expected=f"between {low} and {high}",
                    actual=str(avg),
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Bid/offer/spread
# ---------------------------------------------------------------------------


def _validate_bid_offer(payload: Mapping[str, object]) -> list[ValidationIssue]:
    """Validate bid/offer relationship and spread."""
    issues: list[ValidationIssue] = []

    bid = _d(payload, "best_bid")
    offer = _d(payload, "best_offer")

    if bid is not None and offer is not None:
        if offer < bid:
            issues.append(
                _make_issue(
                    MARKET_OFFER_BELOW_BID,
                    "/best_offer",
                    f"Best offer ({offer}) is below best bid ({bid})",
                    expected=f">= {bid}",
                    actual=str(offer),
                )
            )

        calculated_spread = calculate_spread(bid, offer)
        reported_spread = _d(payload, "spread")
        if reported_spread is not None:
            spread_diff = abs(calculated_spread - reported_spread)
            if spread_diff > Decimal("0.000001"):
                issues.append(
                    _make_issue(
                        MARKET_SPREAD_MISMATCH,
                        "/spread",
                        f"Reported spread ({reported_spread}) != calculated ({calculated_spread})",
                        expected=str(calculated_spread),
                        actual=str(reported_spread),
                    )
                )

        reported_spread_pct = _d(payload, "spread_percentage")
        if reported_spread_pct is not None and offer != Decimal("0"):
            calculated_spread_pct = (calculated_spread / offer) * Decimal("100")
            calculated_spread_pct = quantize_percentage(calculated_spread_pct)
            pct_diff = abs(calculated_spread_pct - reported_spread_pct)
            if pct_diff > PERCENT_TOLERANCE:
                issues.append(
                    _make_issue(
                        MARKET_SPREAD_PERCENTAGE_MISMATCH,
                        "/spread_percentage",
                        f"Reported spread percentage ({reported_spread_pct}) != "
                        f"calculated ({calculated_spread_pct})",
                        expected=str(calculated_spread_pct),
                        actual=str(reported_spread_pct),
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# Change
# ---------------------------------------------------------------------------


def _validate_change(payload: Mapping[str, object]) -> list[ValidationIssue]:
    """Validate market change and change percentage.

    Reference price: ``close`` when available, otherwise ``last``.
    Independent of the ``update_period`` label.
    """
    issues: list[ValidationIssue] = []

    prev_close = _d(payload, "previous_close")
    if prev_close is None:
        return issues

    if prev_close <= Decimal("0"):
        issues.append(
            _make_issue(
                MARKET_PREVIOUS_CLOSE_INVALID,
                "/previous_close",
                f"Previous close must be positive, got {prev_close}",
                expected="> 0",
                actual=str(prev_close),
            )
        )
        return issues

    close = _d(payload, "close")
    last = _d(payload, "last")
    ref_price = close if close is not None else last
    if ref_price is None:
        return issues

    expected_change = calculate_market_change(ref_price, prev_close)
    reported_change = _d(payload, "change")
    if reported_change is not None:
        change_diff = abs(expected_change - reported_change)
        if change_diff > Decimal("0.000001"):
            issues.append(
                _make_issue(
                    MARKET_CHANGE_MISMATCH,
                    "/change",
                    f"Reported change ({reported_change}) != calculated ({expected_change})",
                    expected=str(expected_change),
                    actual=str(reported_change),
                )
            )

    expected_change_pct = calculate_percentage_change(ref_price, prev_close)
    reported_change_pct = _d(payload, "change_percentage")
    if expected_change_pct is not None and reported_change_pct is not None:
        pct_diff = abs(expected_change_pct - reported_change_pct)
        if pct_diff > PERCENT_TOLERANCE:
            issues.append(
                _make_issue(
                    MARKET_CHANGE_PERCENTAGE_MISMATCH,
                    "/change_percentage",
                    f"Reported change percentage ({reported_change_pct}) != "
                    f"calculated ({expected_change_pct})",
                    expected=str(expected_change_pct),
                    actual=str(reported_change_pct),
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Timestamp
# ---------------------------------------------------------------------------


def _validate_timestamp(
    payload: Mapping[str, object],
    now: datetime | None = None,
) -> list[ValidationIssue]:
    """Validate market timestamp consistency."""
    issues: list[ValidationIssue] = []

    market_ts_str = payload.get("market_timestamp")
    trading_date_str = payload.get("trading_date")

    if market_ts_str is not None and isinstance(market_ts_str, str):
        try:
            market_dt = datetime.fromisoformat(market_ts_str)
        except (ValueError, TypeError):
            return issues

        if now is not None and market_dt > now:
            issues.append(
                _make_issue(
                    MARKET_TIMESTAMP_IN_FUTURE,
                    "/market_timestamp",
                    f"Market timestamp ({market_ts_str}) is in the future",
                    expected=f"<= {now.isoformat()}",
                    actual=market_ts_str,
                )
            )

        if trading_date_str is not None and isinstance(trading_date_str, str):
            try:
                trading_date = date.fromisoformat(trading_date_str)
                market_date = market_dt.date()
                if market_date != trading_date:
                    issues.append(
                        _make_issue(
                            MARKET_TIMESTAMP_DATE_MISMATCH,
                            "/market_timestamp",
                            f"Market timestamp date ({market_date}) "
                            f"!= trading_date ({trading_date_str})",
                            expected=trading_date_str,
                            actual=str(market_date),
                        )
                    )
            except (ValueError, TypeError):
                pass

    return issues


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------


def validate_market_snapshot(
    payload: Mapping[str, object],
    now: datetime | None = None,
) -> MarketSnapshotValidationResult:
    """Validate a Market Snapshot payload against all domain rules.

    Parameters
    ----------
    payload:
        The Market Snapshot dictionary (already schema-validated).
    now:
        Optional reference time for future-timestamp checks.
        Should be timezone-aware.  If ``None``, future checks are skipped.

    Returns
    -------
    MarketSnapshotValidationResult
    """
    issues: list[ValidationIssue] = []

    # Numeric input validation must run first to reject floats before
    # downstream checks use them.
    issues.extend(_validate_numeric_inputs(payload))
    if issues:
        return MarketSnapshotValidationResult(valid=False, issues=tuple(issues))

    issues.extend(_validate_availability(payload))
    issues.extend(_validate_positive_prices(payload))
    issues.extend(_validate_ohlc(payload))
    issues.extend(_validate_average(payload))
    issues.extend(_validate_bid_offer(payload))
    issues.extend(_validate_change(payload))
    issues.extend(_validate_timestamp(payload, now))

    issues.sort(key=_sort_key)

    return MarketSnapshotValidationResult(
        valid=len(issues) == 0,
        issues=tuple(issues),
    )
