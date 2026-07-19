"""Fixture validation CLI core logic and catalog.

Canonical catalog of TP-0402 fixtures with their validation functions.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Callable, cast

from app.schemas.registry import LocalSchemaRegistry
from app.validation.closing import validate_closing
from app.validation.market_snapshot import validate_market_snapshot
from app.validation.partial_exit import validate_partial_exit
from app.validation.state_consistency import validate_state_consistency
from app.validation.trade_state import validate_trade_state

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = _HERE / "tests" / "fixtures"
PROD_SCHEMAS_DIR = _HERE.parent / "schemas" / "production" / "v1"


def _registry() -> LocalSchemaRegistry:
    from app.schemas.manifest import load_production_manifest

    pkg = Path(tempfile.mkdtemp()) / "production" / "v1"
    pkg.mkdir(parents=True)
    for f in PROD_SCHEMAS_DIR.iterdir():
        if f.is_file():
            shutil.copy2(f, pkg / f.name)
    return LocalSchemaRegistry(load_production_manifest(pkg), pkg)


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FixtureResult:
    name: str
    passed: bool
    message: str = ""
    expected_code: str | None = None
    expected_path: str | None = None


@dataclass(frozen=True, slots=True)
class FixtureCatalogEntry:
    """One entry in the fixture catalog."""

    scenario: str
    category: str
    schema_name: str | None
    path: str  # relative to FIXTURES_DIR
    validate: Callable[[], FixtureResult]
    expected_code: str | None = None
    expected_path: str | None = None
    expected_invalid: bool = False


# ---------------------------------------------------------------------------
# Fixture catalog
# ---------------------------------------------------------------------------

_CATALOG: list[FixtureCatalogEntry] = []


def _load(fixture_path: str) -> dict[str, object]:
    result = json.loads(
        (FIXTURES_DIR / fixture_path).read_text(encoding="utf-8"),
        parse_float=Decimal,
    )
    return result  # type: ignore[no-any-return]


def _check_schema(fixture_path: str, schema_name: str) -> list[str]:
    """Validate against production JSON Schema. Returns list of error messages."""
    payload = _load(fixture_path)
    reg = _registry()
    validator = reg.get_validator(schema_name, "1.0.0")
    return [e.message for e in validator.iter_errors(payload)]


# ---------------------------------------------------------------------------
# Validator helpers
# ---------------------------------------------------------------------------


def _validate_manifest() -> FixtureResult:
    """Load the fixture manifest."""
    from app.schemas.manifest import load_production_manifest

    pkg = Path(tempfile.mkdtemp()) / "production" / "v1"
    pkg.mkdir(parents=True)
    for f in PROD_SCHEMAS_DIR.iterdir():
        if f.is_file():
            shutil.copy2(f, pkg / f.name)
    shutil.copy2(FIXTURES_DIR / "manifests" / "valid_manifest.json", pkg / "manifest.json")
    try:
        m = load_production_manifest(pkg)
        if m is None or m.manifest_version != "1.0.0":
            return FixtureResult(
                name="valid_manifest", passed=False, message="Manifest did not load"
            )
        return FixtureResult(name="valid_manifest", passed=True)
    except Exception as exc:
        return FixtureResult(name="valid_manifest", passed=False, message=str(exc))


def _validate_schema(fixture_path: str, schema_name: str, scenario: str) -> FixtureResult:
    errs = _check_schema(fixture_path, schema_name)
    if errs:
        return FixtureResult(
            name=scenario, passed=False, message=f"Schema errors: {'; '.join(errs[:3])}"
        )
    # Also run domain validation
    return FixtureResult(name=scenario, passed=True)


def _make_schema_validator(
    fixture_path: str, schema_name: str, scenario: str
) -> Callable[[], FixtureResult]:
    def fn() -> FixtureResult:
        return _validate_schema(fixture_path, schema_name, scenario)

    return fn


def _validate_trade_state_fixture(fixture_path: str, scenario: str) -> FixtureResult:
    errs = _check_schema(fixture_path, "trade_state")
    if errs:
        return FixtureResult(
            name=scenario, passed=False, message=f"Schema errors: {'; '.join(errs[:3])}"
        )
    payload = _load(fixture_path)
    result = validate_trade_state(payload)
    if not result.valid:
        return FixtureResult(
            name=scenario,
            passed=False,
            message=f"Domain issues: {[i.message for i in result.issues]}",
        )
    return FixtureResult(name=scenario, passed=True)


def _make_trade_state_validator(fixture_path: str, scenario: str) -> Callable[[], FixtureResult]:
    def fn() -> FixtureResult:
        return _validate_trade_state_fixture(fixture_path, scenario)

    return fn


def _validate_market_snapshot_fixture(fixture_path: str, scenario: str) -> FixtureResult:
    errs = _check_schema(fixture_path, "market_snapshot")
    if errs:
        return FixtureResult(
            name=scenario, passed=False, message=f"Schema errors: {'; '.join(errs[:3])}"
        )
    payload = _load(fixture_path)
    result = validate_market_snapshot(payload)
    if not result.valid:
        return FixtureResult(
            name=scenario,
            passed=False,
            message=f"Domain issues: {[i.message for i in result.issues]}",
        )
    return FixtureResult(name=scenario, passed=True)


def _make_market_snapshot_validator(
    fixture_path: str, scenario: str
) -> Callable[[], FixtureResult]:
    def fn() -> FixtureResult:
        return _validate_market_snapshot_fixture(fixture_path, scenario)

    return fn


def _validate_opu(fixture_path: str, scenario: str) -> FixtureResult:
    from app.validation.service import UnifiedValidationService

    errs = _check_schema(fixture_path, "open_position_update")
    if errs:
        return FixtureResult(
            name=scenario, passed=False, message=f"Schema errors: {'; '.join(errs[:3])}"
        )
    payload = _load(fixture_path)
    canonical = _load("schemas/valid_trade_state_open.json")
    svc = UnifiedValidationService(schema_package_root=str(PROD_SCHEMAS_DIR))
    result = svc.validate(
        payload=payload,
        expected_analysis_type="OPEN_POSITION_UPDATE",
        trade_state=canonical,
    )
    if not result.valid or result.errors:
        msgs = [i.message for i in result.issues]
        return FixtureResult(
            name=scenario, passed=False, message=f"Unified issues: {'; '.join(msgs[:5])}"
        )
    return FixtureResult(name=scenario, passed=True)


def _make_opu_validator(fixture_path: str, scenario: str) -> Callable[[], FixtureResult]:
    def fn() -> FixtureResult:
        return _validate_opu(fixture_path, scenario)

    return fn


def _validate_invalid_domain(
    fixture_path: str, scenario: str, code: str, path: str
) -> FixtureResult:
    fixture = _load(fixture_path)
    payload = fixture["payload"]
    canonical = fixture["canonical_state"]
    result = validate_state_consistency(payload, canonical)  # type: ignore[arg-type]
    if result.valid:
        return FixtureResult(
            name=scenario,
            passed=False,
            message="Expected failure but result is valid",
            expected_code=code,
            expected_path=path,
        )
    codes = {i.code for i in result.issues}
    if code not in codes:
        return FixtureResult(
            name=scenario,
            passed=False,
            message=f"Expected code {code} not in {codes}",
            expected_code=code,
            expected_path=path,
        )
    paths = {i.path for i in result.issues}
    if path not in paths:
        return FixtureResult(
            name=scenario,
            passed=False,
            message=f"Expected path {path} not in {paths}",
            expected_code=code,
            expected_path=path,
        )
    return FixtureResult(name=scenario, passed=True, expected_code=code, expected_path=path)


def _make_invalid_domain_validator(
    fixture_path: str, scenario: str, code: str, path: str
) -> Callable[[], FixtureResult]:
    def fn() -> FixtureResult:
        return _validate_invalid_domain(fixture_path, scenario, code, path)

    return fn


def _validate_partial_exit_fixture(fixture_path: str, scenario: str) -> FixtureResult:
    f = _load(fixture_path)
    result = validate_partial_exit(
        f["previous_state"],  # type: ignore[arg-type]
        f["partial_exit"],  # type: ignore[arg-type]
        f["resulting_state"],  # type: ignore[arg-type]
    )
    if not result.valid:
        return FixtureResult(
            name=scenario,
            passed=False,
            message=f"Partial exit issues: {[i.message for i in result.issues]}",
        )
    return FixtureResult(name=scenario, passed=True)


def _make_partial_exit_validator(fixture_path: str, scenario: str) -> Callable[[], FixtureResult]:
    def fn() -> FixtureResult:
        return _validate_partial_exit_fixture(fixture_path, scenario)

    return fn


def _validate_closing_fixture(fixture_path: str, scenario: str) -> FixtureResult:
    f = _load(fixture_path)
    result = validate_closing(
        f["previous_state"],  # type: ignore[arg-type]
        f["final_exit"],  # type: ignore[arg-type]
        f["resulting_state"],  # type: ignore[arg-type]
        closing_reason=cast("str | None", f.get("closing_reason")),
        resulting_session_status=cast("str | None", f.get("resulting_session_status")),
    )
    if not result.valid:
        return FixtureResult(
            name=scenario,
            passed=False,
            message=f"Closing issues: {[i.message for i in result.issues]}",
        )
    return FixtureResult(name=scenario, passed=True)


def _make_closing_validator(fixture_path: str, scenario: str) -> Callable[[], FixtureResult]:
    def fn() -> FixtureResult:
        return _validate_closing_fixture(fixture_path, scenario)

    return fn


# ---------------------------------------------------------------------------
# Register fixtures
# ---------------------------------------------------------------------------

_CATALOG = [
    # Manifest
    FixtureCatalogEntry(
        scenario="valid_manifest",
        category="manifests",
        schema_name=None,
        path="manifests/valid_manifest.json",
        validate=_validate_manifest,
    ),
    # Schema fixtures
    FixtureCatalogEntry(
        scenario="valid_market_snapshot",
        category="schemas",
        schema_name="market_snapshot",
        path="schemas/valid_market_snapshot.json",
        validate=_make_market_snapshot_validator(
            "schemas/valid_market_snapshot.json", "valid_market_snapshot"
        ),
    ),
    FixtureCatalogEntry(
        scenario="valid_trade_state_watching",
        category="schemas",
        schema_name="trade_state",
        path="schemas/valid_trade_state_watching.json",
        validate=_make_trade_state_validator(
            "schemas/valid_trade_state_watching.json", "valid_trade_state_watching"
        ),
    ),
    FixtureCatalogEntry(
        scenario="valid_trade_state_open",
        category="schemas",
        schema_name="trade_state",
        path="schemas/valid_trade_state_open.json",
        validate=_make_trade_state_validator(
            "schemas/valid_trade_state_open.json", "valid_trade_state_open"
        ),
    ),
    FixtureCatalogEntry(
        scenario="valid_trade_state_partial",
        category="schemas",
        schema_name="trade_state",
        path="schemas/valid_trade_state_partial.json",
        validate=_make_trade_state_validator(
            "schemas/valid_trade_state_partial.json", "valid_trade_state_partial"
        ),
    ),
    FixtureCatalogEntry(
        scenario="valid_trade_state_closed",
        category="schemas",
        schema_name="trade_state",
        path="schemas/valid_trade_state_closed.json",
        validate=_make_trade_state_validator(
            "schemas/valid_trade_state_closed.json", "valid_trade_state_closed"
        ),
    ),
    FixtureCatalogEntry(
        scenario="valid_open_position_update",
        category="schemas",
        schema_name="open_position_update",
        path="schemas/valid_open_position_update.json",
        validate=_make_opu_validator(
            "schemas/valid_open_position_update.json", "valid_open_position_update"
        ),
    ),
    # Domain fixtures (invalid expected-failure)
    FixtureCatalogEntry(
        scenario="entry_mismatch",
        category="domain",
        schema_name="open_position_update",
        path="domain/entry_mismatch.json",
        validate=_make_invalid_domain_validator(
            "domain/entry_mismatch.json",
            "entry_mismatch",
            "STATE_ENTRY_PRICE_MISMATCH",
            "/position_assessment/entry_price",
        ),
        expected_code="STATE_ENTRY_PRICE_MISMATCH",
        expected_path="/position_assessment/entry_price",
        expected_invalid=True,
    ),
    FixtureCatalogEntry(
        scenario="quantity_mismatch",
        category="domain",
        schema_name="open_position_update",
        path="domain/quantity_mismatch.json",
        validate=_make_invalid_domain_validator(
            "domain/quantity_mismatch.json",
            "quantity_mismatch",
            "STATE_ORIGINAL_QUANTITY_MISMATCH",
            "/original_quantity",
        ),
        expected_code="STATE_ORIGINAL_QUANTITY_MISMATCH",
        expected_path="/original_quantity",
        expected_invalid=True,
    ),
    FixtureCatalogEntry(
        scenario="active_stop_mismatch",
        category="domain",
        schema_name="open_position_update",
        path="domain/active_stop_mismatch.json",
        validate=_make_invalid_domain_validator(
            "domain/active_stop_mismatch.json",
            "active_stop_mismatch",
            "STATE_ACTIVE_STOP_MISMATCH",
            "/position_assessment/active_stop_loss",
        ),
        expected_code="STATE_ACTIVE_STOP_MISMATCH",
        expected_path="/position_assessment/active_stop_loss",
        expected_invalid=True,
    ),
    FixtureCatalogEntry(
        scenario="active_target_mismatch",
        category="domain",
        schema_name="open_position_update",
        path="domain/active_target_mismatch.json",
        validate=_make_invalid_domain_validator(
            "domain/active_target_mismatch.json",
            "active_target_mismatch",
            "STATE_ACTIVE_TARGET_MISMATCH",
            "/position_assessment/active_target",
        ),
        expected_code="STATE_ACTIVE_TARGET_MISMATCH",
        expected_path="/position_assessment/active_target",
        expected_invalid=True,
    ),
    # Domain fixtures (valid)
    FixtureCatalogEntry(
        scenario="valid_partial_exit",
        category="domain",
        schema_name=None,
        path="domain/valid_partial_exit.json",
        validate=_make_partial_exit_validator(
            "domain/valid_partial_exit.json", "valid_partial_exit"
        ),
    ),
    FixtureCatalogEntry(
        scenario="valid_closing_result",
        category="domain",
        schema_name=None,
        path="domain/valid_closing_result.json",
        validate=_make_closing_validator(
            "domain/valid_closing_result.json", "valid_closing_result"
        ),
    ),
]

KNOWN_CATEGORIES = {"manifests", "schemas", "domain"}
KNOWN_SCENARIOS = {e.scenario for e in _CATALOG}


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def _matches(
    entry: FixtureCatalogEntry,
    schema: str | None,
    category: str | None,
    scenario: str | None,
) -> bool:
    if schema is not None and entry.schema_name != schema:
        return False
    if category is not None and entry.category != category:
        return False
    if scenario is not None and entry.scenario != scenario:
        return False
    return True


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FixtureValidationSummary:
    checked: int = 0
    passed: int = 0
    failed: int = 0
    results: tuple[FixtureResult, ...] = field(default_factory=tuple)


def validate_fixtures(
    *,
    schema: str | None = None,
    category: str | None = None,
    scenario: str | None = None,
) -> FixtureValidationSummary:
    """Validate TP-0402 fixtures matching the given filters.

    Returns a ``FixtureValidationSummary``.  Does not call ``sys.exit``.
    """
    selected = [e for e in _CATALOG if _matches(e, schema, category, scenario)]

    results: list[FixtureResult] = []
    for entry in selected:
        try:
            result = entry.validate()
        except Exception as exc:
            result = FixtureResult(name=entry.scenario, passed=False, message=str(exc))
        results.append(result)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    return FixtureValidationSummary(
        checked=len(results),
        passed=passed,
        failed=failed,
        results=tuple(results),
    )
