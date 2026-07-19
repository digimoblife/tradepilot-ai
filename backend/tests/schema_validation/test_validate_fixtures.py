"""Tests for Fixture Validation CLI (TP-0403)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.schema_validation.validate_fixtures import (
    _CATALOG,
    KNOWN_CATEGORIES,
    KNOWN_SCENARIOS,
    FixtureValidationSummary,
    validate_fixtures,
)

HERE = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS = HERE / "scripts"


# ===================================================================


class TestValidateAll:
    def test_all_fixtures_pass(self) -> None:
        summary = validate_fixtures()
        assert summary.checked > 0
        assert summary.failed == 0, (
            f"{summary.failed} fixture(s) failed: "
            f"{[r.name for r in summary.results if not r.passed]}"
        )

    def test_all_checked(self) -> None:
        summary = validate_fixtures()
        assert summary.checked == len(_CATALOG)


class TestSchemaFilter:
    def test_market_snapshot(self) -> None:
        summary = validate_fixtures(schema="market_snapshot")
        assert summary.checked >= 1
        assert summary.failed == 0

    def test_trade_state(self) -> None:
        summary = validate_fixtures(schema="trade_state")
        assert summary.checked >= 4
        assert summary.failed == 0

    def test_unknown(self) -> None:
        summary = validate_fixtures(schema="unknown_schema")
        assert summary.checked == 0


class TestCategoryFilter:
    def test_schemas(self) -> None:
        summary = validate_fixtures(category="schemas")
        assert summary.checked >= 6
        assert summary.failed == 0

    def test_domain(self) -> None:
        summary = validate_fixtures(category="domain")
        assert summary.checked >= 6
        assert summary.failed == 0

    def test_manifests(self) -> None:
        summary = validate_fixtures(category="manifests")
        assert summary.checked == 1
        assert summary.failed == 0

    def test_unknown(self) -> None:
        summary = validate_fixtures(category="unknown")
        assert summary.checked == 0

    def test_known_categories(self) -> None:
        assert "manifests" in KNOWN_CATEGORIES
        assert "schemas" in KNOWN_CATEGORIES
        assert "domain" in KNOWN_CATEGORIES


class TestScenarioFilter:
    def test_entry_mismatch(self) -> None:
        summary = validate_fixtures(scenario="entry_mismatch")
        assert summary.checked == 1
        assert summary.failed == 0

    def test_valid_market_snapshot(self) -> None:
        summary = validate_fixtures(scenario="valid_market_snapshot")
        assert summary.checked == 1
        assert summary.failed == 0

    def test_unknown(self) -> None:
        summary = validate_fixtures(scenario="nonexistent")
        assert summary.checked == 0

    def test_known_scenarios(self) -> None:
        required = {
            "valid_manifest",
            "valid_market_snapshot",
            "valid_trade_state_watching",
            "valid_trade_state_open",
            "valid_trade_state_partial",
            "valid_trade_state_closed",
            "valid_open_position_update",
            "entry_mismatch",
            "quantity_mismatch",
            "active_stop_mismatch",
            "active_target_mismatch",
            "valid_partial_exit",
            "valid_closing_result",
        }
        for s in required:
            assert s in KNOWN_SCENARIOS, f"Missing scenario: {s}"


class TestCombinedFilters:
    def test_category_and_scenario(self) -> None:
        summary = validate_fixtures(category="domain", scenario="entry_mismatch")
        assert summary.checked == 1
        assert summary.failed == 0

    def test_category_and_schema(self) -> None:
        summary = validate_fixtures(category="schemas", schema="market_snapshot")
        assert summary.checked >= 1
        assert summary.failed == 0

    def test_no_match(self) -> None:
        summary = validate_fixtures(category="schemas", scenario="entry_mismatch")
        assert summary.checked == 0


class TestExpectedInvalid:
    def test_all_invalid_fixtures_pass_as_expected(self) -> None:
        """Invalid fixtures must fail with the expected code and path."""
        for entry in _CATALOG:
            if entry.expected_invalid:
                result = entry.validate()
                assert result.passed, (
                    f"{entry.scenario}: expected invalid to pass (fail as expected), "
                    f"got: {result.message}"
                )


class TestReturnType:
    def test_summary_has_correct_attrs(self) -> None:
        summary = validate_fixtures()
        assert isinstance(summary, FixtureValidationSummary)
        assert summary.checked > 0
        assert summary.passed >= 0
        assert summary.failed >= 0
        assert isinstance(summary.results, tuple)


class TestCliScript:
    def test_root_script_exists(self) -> None:
        assert (SCRIPTS / "validate_fixtures.py").exists()

    def test_root_script_exit_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_fixtures.py")],
            capture_output=True,
            text=True,
            cwd=HERE,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    def test_root_script_exit_nonzero_unknown_scenario(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_fixtures.py"), "--scenario", "nonexistent"],
            capture_output=True,
            text=True,
            cwd=HERE,
        )
        assert result.returncode != 0

    def test_root_script_exit_nonzero_unknown_category(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_fixtures.py"), "--category", "unknown"],
            capture_output=True,
            text=True,
            cwd=HERE,
        )
        assert result.returncode != 0
