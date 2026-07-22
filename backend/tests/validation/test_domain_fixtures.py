"""Comprehensive domain fixture validation (TP-1502).

Loads every invalid domain fixture and asserts its expected error code
and JSON Pointer path through the correct production validator.

Fixtures are stored in backend/tests/fixtures/domain/ as JSON files with:
  - scenario: human-readable name
  - expected_code: the blocking error code
  - expected_path: JSON Pointer path of the offending field
  - payload: the payload to validate
  - canonical_state (optional): canonical trade state for state_consistency
  - previous_state / partial_exit / resulting_state (for partial_exit)
  - previous_state / final_exit / closing_reason / resulting_session_status (for closing)
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from app.validation.closing import validate_closing
from app.validation.entry_plan import validate_entry_plan
from app.validation.market_snapshot import validate_market_snapshot
from app.validation.partial_exit import validate_partial_exit
from app.validation.risk_reward import validate_risk_reward
from app.validation.state_consistency import validate_state_consistency
from app.validation.stop_loss import validate_stop_loss
from app.validation.target import validate_target
from app.validation.trade_state import validate_trade_state

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "domain"

VALIDATOR_MAP = {
    "STATE_": ("state_consistency", validate_state_consistency),
    "MARKET_": ("market_snapshot", validate_market_snapshot),
    "ENTRY_": ("entry_plan", validate_entry_plan),
    "STOP_": ("stop_loss", validate_stop_loss),
    "TARGET_": ("target", validate_target),
    "RISK_": ("risk_reward", validate_risk_reward),
    "PARTIAL_EXIT_": ("partial_exit", validate_partial_exit),
    "CLOSING_": ("closing", validate_closing),
    "CONTEXT_": ("context_summary", None),
    "TRADE_STATE_": ("trade_state", validate_trade_state),
    "MAXIMUM_RISK_": ("risk_reward", validate_risk_reward),
    "REWARD_": ("risk_reward", validate_risk_reward),
}


def _detect_validator(expected_code: str):
    """Return (validator_name, validator_fn) for an expected code."""
    for prefix, (name, fn) in VALIDATOR_MAP.items():
        if expected_code.startswith(prefix):
            return name, fn
    return "unknown", None


def _get_issues(result) -> tuple:
    """Normalize validator return to a tuple of issues."""
    if hasattr(result, "valid"):
        return result.issues if hasattr(result, "issues") else ()
    if isinstance(result, tuple):
        return result
    return ()


def _load(name: str) -> dict:
    return json.loads(
        (FIXTURE_DIR / name).read_text(encoding="utf-8"),
        parse_float=Decimal,
    )


def _get_fixtures():
    """Yield (name, data) for each domain fixture."""
    for f in sorted(FIXTURE_DIR.glob("*.json")):
        if f.name.startswith("valid_"):
            continue
        yield f.name, json.loads(f.read_text(encoding="utf-8"), parse_float=Decimal)


class TestDomainFixtures:
    """Automated test for every invalid domain fixture."""

    def test_all_invalid_fixtures(self) -> None:
        """Load every domain fixture and assert its expected error."""
        errors = []
        tested = 0
        for fname, fixture in _get_fixtures():
            tested += 1
            expected_code = fixture["expected_code"]
            expected_path = fixture["expected_path"]
            payload = fixture["payload"]

            validator_name, validator_fn = _detect_validator(expected_code)
            assert validator_fn is not None, f"{fname}: no validator for code {expected_code}"

            try:
                if expected_code.startswith("STATE_"):
                    canonical = fixture.get("canonical_state", {})
                    result = validator_fn(payload, canonical)
                elif expected_code.startswith("PARTIAL_EXIT_"):
                    result = validator_fn(
                        fixture["previous_state"],
                        fixture["partial_exit"],
                        fixture["resulting_state"],
                    )
                elif expected_code.startswith("CLOSING_"):
                    result = validator_fn(
                        fixture["previous_state"],
                        fixture["final_exit"],
                        fixture["resulting_state"],
                        closing_reason=fixture.get("closing_reason", ""),
                        resulting_session_status=fixture.get("resulting_session_status", ""),
                    )
                elif expected_code.startswith("MARKET_"):
                    result = validator_fn(payload)
                elif expected_code.startswith("ENTRY_"):
                    result = validator_fn(payload)
                elif expected_code.startswith("STOP_"):
                    result = validator_fn(payload)
                elif expected_code.startswith("TARGET_"):
                    result = validator_fn(payload)
                elif (
                    expected_code.startswith("RISK_")
                    or expected_code.startswith("MAXIMUM_RISK_")
                    or expected_code.startswith("REWARD_")
                ):
                    result = validator_fn(payload)
                elif expected_code.startswith("TRADE_STATE_"):
                    result = validator_fn(payload)
                else:
                    errors.append(f"{fname}: unknown validator for {expected_code}")
                    continue

                issues = _get_issues(result)

                # Assert: must fail (non-empty issues)
                if not issues:
                    errors.append(f"{fname}: expected failure for {expected_code} but passed")
                    continue

                # Assert: code must be present
                codes = {i.code for i in issues}
                if expected_code not in codes:
                    errors.append(f"{fname}: expected code {expected_code} not in {codes}")
                    continue

                # Assert: path must be present
                paths = {i.path for i in issues}
                if expected_path not in paths:
                    errors.append(f"{fname}: expected path {expected_path} not in {paths}")
                    continue

            except Exception as e:
                errors.append(f"{fname}: validator raised {type(e).__name__}: {e}")

        assert not errors, f"{len(errors)} fixture failure(s):\n" + "\n".join(errors)
        assert tested >= 4, f"Only {tested} fixtures loaded (expected 4+)"
