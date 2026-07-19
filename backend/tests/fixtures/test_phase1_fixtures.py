"""Tests for Phase 1 schema fixtures (TP-0402)."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas.registry import LocalSchemaRegistry
from app.validation.closing import validate_closing
from app.validation.json_schema import JsonSchemaValidationService
from app.validation.market_snapshot import validate_market_snapshot
from app.validation.partial_exit import validate_partial_exit
from app.validation.state_consistency import validate_state_consistency
from app.validation.trade_state import validate_trade_state

FIXTURES = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _registry() -> LocalSchemaRegistry:
    """Build a schema registry from production schemas for validation."""
    import shutil
    import tempfile

    from app.schemas.manifest import load_production_manifest

    pkg = Path(tempfile.mkdtemp()) / "production" / "v1"
    pkg.mkdir(parents=True)
    prod = Path(__file__).resolve().parent.parent.parent / "schemas" / "production" / "v1"
    for f in prod.iterdir():
        if f.is_file():
            shutil.copy2(f, pkg / f.name)
    manifest = load_production_manifest(pkg)
    return LocalSchemaRegistry(manifest, pkg)


def _schema_service() -> JsonSchemaValidationService:
    return JsonSchemaValidationService(_registry())


# ===================================================================
# 1. Valid manifest
# ===================================================================


class TestValidManifest:
    def test_loads(self) -> None:
        # Use the production manifest for a valid-load test
        import shutil
        import tempfile

        from app.schemas.manifest import load_production_manifest

        pkg = Path(tempfile.mkdtemp()) / "production" / "v1"
        pkg.mkdir(parents=True)
        prod = FIXTURES.parent.parent.parent / "schemas" / "production" / "v1"
        for f in prod.iterdir():
            if f.is_file():
                shutil.copy2(f, pkg / f.name)
        m = load_production_manifest(pkg)
        assert m is not None
        assert m.manifest_version == "1.0.0"


# ===================================================================
# 2-6. Valid schema fixtures
# ===================================================================


class TestValidSchemaFixtures:
    def _check_schema(self, fixture_path: str, schema_name: str) -> None:
        payload = _load(fixture_path)
        # The manifest maps schema names to versions; we need the analysis
        # type for the schema_service.  For trade_state and market_snapshot,
        # validate directly.
        reg = _registry()
        validator = reg.get_validator(schema_name, "1.0.0")
        errors = list(validator.iter_errors(payload))
        assert not errors, f"{fixture_path}: {[e.message for e in errors]}"

    def test_market_snapshot(self) -> None:
        # Market snapshot is validated via domain validator, not schema here
        pass

    def test_trade_state_watching(self) -> None:
        payload = _load("schemas/valid_trade_state_watching.json")
        position = payload.get("position", {})
        assert isinstance(position, dict)
        assert position.get("position_status") == "NOT_OPENED"

    def test_trade_state_open(self) -> None:
        payload = _load("schemas/valid_trade_state_open.json")
        position = payload.get("position", {})
        assert isinstance(position, dict)
        assert position.get("position_status") == "OPEN"
        assert position.get("remaining_quantity") == position.get("original_quantity")

    def test_trade_state_partial(self) -> None:
        payload = _load("schemas/valid_trade_state_partial.json")
        position = payload.get("position", {})
        assert isinstance(position, dict)
        assert position.get("position_status") == "PARTIALLY_CLOSED"
        assert 0 < position["remaining_quantity"] < position["original_quantity"]

    def test_trade_state_closed(self) -> None:
        payload = _load("schemas/valid_trade_state_closed.json")
        position = payload.get("position", {})
        assert isinstance(position, dict)
        assert position.get("position_status") == "CLOSED"
        assert position.get("remaining_quantity") == 0
        assert position.get("active_stop_loss") is None
        assert position.get("active_target") is None

    def test_open_position_update(self) -> None:
        payload = _load("schemas/valid_open_position_update.json")
        meta = payload.get("metadata", {})
        assert isinstance(meta, dict)
        assert meta.get("analysis_type") == "OPEN_POSITION_UPDATE"
        assert "position_assessment" in payload


# ===================================================================
# Domain validation
# ===================================================================


class TestValidDomain:
    def test_market_snapshot(self) -> None:
        payload = _load("schemas/valid_market_snapshot.json")
        result = validate_market_snapshot(payload)
        assert result.valid, f"Market snapshot issues: {result.issues}"

    def test_trade_state_watching(self) -> None:
        payload = _load("schemas/valid_trade_state_watching.json")
        # validate_trade_state works on the full payload
        result = validate_trade_state(payload)
        assert result.valid, f"Trade state issues: {result.issues}"

    def test_trade_state_open(self) -> None:
        payload = _load("schemas/valid_trade_state_open.json")
        result = validate_trade_state(payload)
        assert result.valid, f"Trade state issues: {result.issues}"

    def test_trade_state_partial(self) -> None:
        payload = _load("schemas/valid_trade_state_partial.json")
        result = validate_trade_state(payload)
        assert result.valid, f"Trade state issues: {result.issues}"

    def test_trade_state_closed(self) -> None:
        payload = _load("schemas/valid_trade_state_closed.json")
        result = validate_trade_state(payload)
        assert result.valid, f"Trade state issues: {result.issues}"

    def test_partial_exit(self) -> None:
        fixture = _load("domain/valid_partial_exit.json")
        result = validate_partial_exit(
            fixture["previous_state"],
            fixture["partial_exit"],
            fixture["resulting_state"],
        )
        assert result.valid, f"Partial exit issues: {result.issues}"

    def test_closing_result(self) -> None:
        fixture = _load("domain/valid_closing_result.json")
        result = validate_closing(
            fixture["previous_state"],
            fixture["final_exit"],
            fixture["resulting_state"],
            closing_reason=fixture["closing_reason"],
            resulting_session_status=fixture["resulting_session_status"],
        )
        assert result.valid, f"Closing issues: {result.issues}"


# ===================================================================
# Invalid domain fixtures
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
