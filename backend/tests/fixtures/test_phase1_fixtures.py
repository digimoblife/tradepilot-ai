"""Tests for Phase 1 schema fixtures (TP-0402)."""

from __future__ import annotations

import json
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from app.schemas.registry import LocalSchemaRegistry
from app.validation.closing import validate_closing
from app.validation.market_snapshot import validate_market_snapshot
from app.validation.partial_exit import validate_partial_exit
from app.validation.state_consistency import validate_state_consistency
from app.validation.trade_state import validate_trade_state

FIXTURES = Path(__file__).resolve().parent
PROD_SCHEMAS = FIXTURES.parent.parent.parent / "schemas" / "production" / "v1"


def _load(name: str) -> dict[str, object]:
    return json.loads(
        (FIXTURES / name).read_text(encoding="utf-8"),
        parse_float=Decimal,
    )


def _registry() -> LocalSchemaRegistry:
    from app.schemas.manifest import load_production_manifest

    pkg = Path(tempfile.mkdtemp()) / "production" / "v1"
    pkg.mkdir(parents=True)
    for f in PROD_SCHEMAS.iterdir():
        if f.is_file():
            shutil.copy2(f, pkg / f.name)
    return LocalSchemaRegistry(load_production_manifest(pkg), pkg)


def _check_schema(fixture_name: str, schema_name: str) -> None:
    """Assert *fixture_name* passes its production JSON Schema."""
    payload = _load(f"schemas/{fixture_name}")
    reg = _registry()
    validator = reg.get_validator(schema_name, "1.0.0")
    errors = list(validator.iter_errors(payload))
    assert not errors, (
        f"{fixture_name}: {len(errors)} schema error(s): {[e.message for e in errors]}"
    )


# ===================================================================
# 1. Valid manifest fixture
# ===================================================================


class TestValidManifest:
    def test_loads(self) -> None:
        pkg = Path(tempfile.mkdtemp()) / "production" / "v1"
        pkg.mkdir(parents=True)
        for f in PROD_SCHEMAS.iterdir():
            if f.is_file():
                shutil.copy2(f, pkg / f.name)
        shutil.copy2(FIXTURES / "manifests" / "valid_manifest.json", pkg / "manifest.json")
        from app.schemas.manifest import load_production_manifest

        m = load_production_manifest(pkg)
        assert m is not None
        assert m.manifest_version == "1.0.0"


# ===================================================================
# 2. Market Snapshot — schema + domain
# ===================================================================


class TestMarketSnapshot:
    def test_production_schema(self) -> None:
        _check_schema("valid_market_snapshot.json", "market_snapshot")

    def test_domain_valid(self) -> None:
        assert validate_market_snapshot(_load("schemas/valid_market_snapshot.json")).valid


# ===================================================================
# 3-6. Trade State — production schema + domain
# ===================================================================


class TestTradeState:
    def test_watching(self) -> None:
        _check_schema("valid_trade_state_watching.json", "trade_state")
        p = _load("schemas/valid_trade_state_watching.json")
        assert p["position"]["position_status"] == "NOT_OPENED"
        assert validate_trade_state(p).valid

    def test_open(self) -> None:
        _check_schema("valid_trade_state_open.json", "trade_state")
        p = _load("schemas/valid_trade_state_open.json")
        assert p["position"]["position_status"] == "OPEN"
        assert p["position"]["remaining_quantity"] == p["position"]["original_quantity"]
        assert validate_trade_state(p).valid

    def test_partial(self) -> None:
        _check_schema("valid_trade_state_partial.json", "trade_state")
        p = _load("schemas/valid_trade_state_partial.json")
        assert p["position"]["position_status"] == "PARTIALLY_CLOSED"
        assert 0 < p["position"]["remaining_quantity"] < p["position"]["original_quantity"]
        assert validate_trade_state(p).valid

    def test_closed(self) -> None:
        _check_schema("valid_trade_state_closed.json", "trade_state")
        p = _load("schemas/valid_trade_state_closed.json")
        assert p["position"]["position_status"] == "CLOSED"
        assert p["position"]["remaining_quantity"] == 0
        assert p["position"]["active_stop_loss"] is None
        assert p["position"]["active_target"] is None
        assert validate_trade_state(p).valid


# ===================================================================
# 7. Open Position Update — Unified Validation (must pass fully)
# ===================================================================


class TestOpenPositionUpdate:
    def test_unified_validation(self) -> None:
        from app.validation.service import UnifiedValidationService

        payload = _load("schemas/valid_open_position_update.json")
        canonical = _load("schemas/valid_trade_state_open.json")
        svc = UnifiedValidationService(schema_package_root=str(PROD_SCHEMAS))
        result = svc.validate(
            payload=payload,
            expected_analysis_type="OPEN_POSITION_UPDATE",
            trade_state=canonical,
        )
        assert result.valid, f"Unified validation issues: {[i.message for i in result.issues]}"
        assert result.errors == (), f"Unified validation errors: {result.errors}"


# ===================================================================
# 8. Invalid domain fixtures (state-consistency failures)
# ===================================================================


class TestInvalidDomain:
    def _check(self, fixture_name: str) -> None:
        fixture = _load(f"domain/{fixture_name}.json")
        payload = fixture["payload"]
        canonical = fixture["canonical_state"]
        expected_code = fixture["expected_code"]
        expected_path = fixture["expected_path"]

        result = validate_state_consistency(payload, canonical)
        assert not result.valid, f"Expected {expected_code} but result is valid"
        codes = {i.code for i in result.issues}
        assert expected_code in codes, f"Expected {expected_code} in {codes}"
        paths = {i.path for i in result.issues}
        assert expected_path in paths, f"Expected {expected_path} in {paths}"

    def test_entry_mismatch(self) -> None:
        self._check("entry_mismatch")

    def test_quantity_mismatch(self) -> None:
        self._check("quantity_mismatch")

    def test_active_stop_mismatch(self) -> None:
        self._check("active_stop_mismatch")

    def test_active_target_mismatch(self) -> None:
        self._check("active_target_mismatch")


# ===================================================================
# 9-10. Partial exit and closing result
# ===================================================================


class TestPartialExit:
    def test_valid(self) -> None:
        f = _load("domain/valid_partial_exit.json")
        result = validate_partial_exit(
            f["previous_state"],
            f["partial_exit"],
            f["resulting_state"],
        )
        assert result.valid, f"Partial exit issues: {result.issues}"


class TestClosingResult:
    def test_valid(self) -> None:
        f = _load("domain/valid_closing_result.json")
        result = validate_closing(
            f["previous_state"],
            f["final_exit"],
            f["resulting_state"],
            closing_reason=f["closing_reason"],
            resulting_session_status=f["resulting_session_status"],
        )
        assert result.valid, f"Closing issues: {result.issues}"
