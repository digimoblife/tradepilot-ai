"""TP-0203: Schema identity, version, manifest, and mapping audit tests."""
from __future__ import annotations

import json
import os
from pathlib import Path

import jsonschema
import pytest
from referencing import Registry, Resource

PRODUCTION_DIR = (
    Path(__file__).resolve().parent.parent / "schemas" / "production" / "v1"
)
VALID_DIR = (
    Path(__file__).resolve().parent.parent / "schemas" / "fixtures" / "valid" / "v1"
)
INVALID_DIR = (
    Path(__file__).resolve().parent.parent / "schemas" / "fixtures" / "invalid" / "v1"
)

SCHEMA_FILES = sorted(PRODUCTION_DIR.glob("*.schema.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _build_registry() -> Registry:
    resources: dict[str, Resource] = {}
    for f in SCHEMA_FILES:
        schema = _load(f)
        sid = schema.get("$id", "")
        if sid:
            resources[str(sid)] = Resource.from_contents(schema)
    return Registry(retrieve=lambda uri: resources[uri])


REGISTRY = _build_registry()
MANIFEST = _load(PRODUCTION_DIR / "manifest.json")
# Map lowercased schema name for cross-schema fixture lookup
ANALYSIS_SCHEMAS = {
    "initial_analysis", "watching_update", "open_position_update",
    "partial_exit_review", "closing_analysis",
}

EXPECTED_SCHEMA_FILES = {
    "common.schema.json",
    "market_snapshot.schema.json",
    "trade_state.schema.json",
    "evidence.schema.json",
    "initial_analysis.schema.json",
    "watching_update.schema.json",
    "open_position_update.schema.json",
    "partial_exit_review.schema.json",
    "closing_analysis.schema.json",
    "context_summary.schema.json",
}

ANALYSIS_TYPE_MAP = {
    "INITIAL_ANALYSIS": "initial_analysis",
    "WATCHING_UPDATE": "watching_update",
    "OPEN_POSITION_UPDATE": "open_position_update",
    "PARTIAL_EXIT_REVIEW": "partial_exit_review",
    "CLOSING_ANALYSIS": "closing_analysis",
}

REVERSE_ANALYSIS_MAP = {v: k for k, v in ANALYSIS_TYPE_MAP.items()}


def _assert_diagnostic(cond: bool, msg: str, **ctx: object) -> None:
    if not cond:
        details = " | ".join(f"{k}={v}" for k, v in ctx.items())
        pytest.fail(f"{msg}\n  {details}")


# ---------------------------------------------------------------------------
# 1. Production file count
# ---------------------------------------------------------------------------

def test_exact_file_count() -> None:
    actual = {f.name for f in SCHEMA_FILES}
    assert actual == EXPECTED_SCHEMA_FILES, (
        f"Schema count mismatch. Missing: {EXPECTED_SCHEMA_FILES - actual}. "
        f"Extra: {actual - EXPECTED_SCHEMA_FILES}"
    )
    assert len(actual) == 10


# ---------------------------------------------------------------------------
# 2. Exact file names
# ---------------------------------------------------------------------------

def test_exact_filenames() -> None:
    for name in EXPECTED_SCHEMA_FILES:
        assert (PRODUCTION_DIR / name).exists(), f"Missing schema: {name}"


# ---------------------------------------------------------------------------
# 3. Manifest entry count
# ---------------------------------------------------------------------------

def test_manifest_entry_count() -> None:
    entries = MANIFEST["schemas"]
    assert len(entries) == 10, f"Expected 10 manifest entries, got {len(entries)}"


# ---------------------------------------------------------------------------
# 4. Unique $id
# ---------------------------------------------------------------------------

def test_unique_id() -> None:
    seen: dict[str, str] = {}
    for f in SCHEMA_FILES:
        schema = _load(f)
        sid = schema.get("$id", "")
        _assert_diagnostic(
            bool(sid), f"{f.name} missing $id", file=f.name, sid=sid
        )
        _assert_diagnostic(
            sid not in seen,
            f"Duplicate $id",
            file=f.name,
            sid=sid,
            conflict=seen.get(sid, ""),
        )
        seen[sid] = f.name


# ---------------------------------------------------------------------------
# 5. Unique schema name
# ---------------------------------------------------------------------------

def test_unique_schema_names() -> None:
    names: dict[str, str] = {}
    for f in SCHEMA_FILES:
        name = f.stem.replace(".schema", "")
        _assert_diagnostic(
            name not in names,
            "Duplicate schema name",
            file=f.name,
            name=name,
            conflict=names.get(name, ""),
        )
        names[name] = f.name


# ---------------------------------------------------------------------------
# 6. Unique filename registration
# ---------------------------------------------------------------------------

def test_unique_filename_registration() -> None:
    filenames: dict[str, int] = {}
    for entry in MANIFEST["schemas"]:
        fn = entry["file"]
        filenames[fn] = filenames.get(fn, 0) + 1
    dupes = {k for k, v in filenames.items() if v > 1}
    _assert_diagnostic(
        not dupes, "Duplicate filename in manifest", duplicates=dupes
    )


# ---------------------------------------------------------------------------
# 7. Unique (name, version) pair
# ---------------------------------------------------------------------------

def test_unique_name_version() -> None:
    pairs: dict[tuple[str, str], str] = {}
    for entry in MANIFEST["schemas"]:
        key = (entry["name"], entry["version"])
        _assert_diagnostic(
            key not in pairs,
            "Duplicate (name, version)",
            name=entry["name"],
            version=entry["version"],
            file=entry["file"],
            conflict=pairs.get(key, ""),
        )
        pairs[key] = entry["file"]


# ---------------------------------------------------------------------------
# 8. Filename equals $id basename
# ---------------------------------------------------------------------------

def test_filename_equals_id_basename() -> None:
    for f in SCHEMA_FILES:
        schema = _load(f)
        sid = schema.get("$id", "")
        expected_basename = f.name
        actual_basename = sid.split("/")[-1] if sid else ""
        _assert_diagnostic(
            actual_basename == expected_basename,
            "$id basename mismatch",
            file=f.name,
            sid=sid,
            expected_basename=expected_basename,
            actual_basename=actual_basename,
        )


# ---------------------------------------------------------------------------
# 9. Version path equals package version
# ---------------------------------------------------------------------------

def test_version_path() -> None:
    for f in SCHEMA_FILES:
        schema = _load(f)
        sid = schema.get("$id", "")
        parts = sid.split("/")
        version_path = "/".join(parts[-3:-1]) if len(parts) >= 3 else ""
        _assert_diagnostic(
            version_path == "production/v1",
            "$id version path mismatch",
            file=f.name,
            sid=sid,
            version_path=version_path,
        )


# ---------------------------------------------------------------------------
# 10. Manifest $id equals schema $id
# ---------------------------------------------------------------------------

def test_manifest_id_equals_schema_id() -> None:
    schema_ids: dict[str, str] = {}
    for f in SCHEMA_FILES:
        schema = _load(f)
        sid = schema.get("$id", "")
        schema_ids[f.name] = sid
    for entry in MANIFEST["schemas"]:
        fn = entry["file"]
        expected_sid = entry.get("schema_id", "")
        actual_sid = schema_ids.get(fn, "")
        _assert_diagnostic(
            expected_sid == actual_sid,
            "Manifest $id mismatch",
            name=entry["name"],
            file=fn,
            manifest_sid=expected_sid,
            schema_sid=actual_sid,
        )


# ---------------------------------------------------------------------------
# 11. Manifest version equals schema version
# ---------------------------------------------------------------------------

def test_manifest_version_matches_schema() -> None:
    for entry in MANIFEST["schemas"]:
        fn = entry["file"]
        f = PRODUCTION_DIR / fn
        if not f.exists():
            continue
        schema = _load(f)
        props = schema.get("properties", {})
        sv = props.get("schema_version", {})
        sv_const = sv.get("const")
        manifest_ver = entry["version"]
        if sv_const is not None:
            _assert_diagnostic(
                str(sv_const) == manifest_ver,
                "Version mismatch",
                name=entry["name"],
                file=fn,
                manifest_ver=manifest_ver,
                schema_ver=sv_const,
            )


# ---------------------------------------------------------------------------
# 12. Analysis type maps correctly
# ---------------------------------------------------------------------------

def test_analysis_type_mapping() -> None:
    at_reg = MANIFEST.get("analysis_type_registry", {})
    for atype, expected_name in ANALYSIS_TYPE_MAP.items():
        entry = at_reg.get(atype)
        _assert_diagnostic(
            entry is not None,
            "Analysis type not in registry",
            analysis_type=atype,
        )
        _assert_diagnostic(
            entry["schema"] == expected_name,
            "Analysis type schema mapping wrong",
            analysis_type=atype,
            expected=expected_name,
            actual=entry["schema"],
        )


# ---------------------------------------------------------------------------
# 13. Reverse analysis mapping complete
# ---------------------------------------------------------------------------

def test_reverse_analysis_mapping() -> None:
    at_reg = MANIFEST.get("analysis_type_registry", {})
    mapped_schemas = {e["schema"] for e in at_reg.values()}
    analysis_schema_set = {v for v in REVERSE_ANALYSIS_MAP}
    missing = analysis_schema_set - mapped_schemas
    _assert_diagnostic(
        not missing,
        "Analysis schemas not reachable from type registry",
        missing=sorted(missing),
    )


# ---------------------------------------------------------------------------
# 14. Session status mappings target valid schemas
# ---------------------------------------------------------------------------

def test_session_status_mappings() -> None:
    ss_map = MANIFEST.get("session_status_schema_mapping", {})
    registered_filenames = {entry["file"] for entry in MANIFEST["schemas"]}
    canonical_schemas = {v.get("canonical_schema") for v in ss_map.values()}
    allowed_schemas: set[str] = set()
    for v in ss_map.values():
        for at in v.get("allowed_analysis_types", []):
            mapped = ANALYSIS_TYPE_MAP.get(at)
            if mapped:
                allowed_schemas.add(f"{mapped}.schema.json")
    for ref in canonical_schemas:
        if ref:
            fn = f"{ref}.schema.json"
            _assert_diagnostic(
                fn in registered_filenames,
                "Canonical schema not registered",
                ref=ref,
                file=fn,
            )


# ---------------------------------------------------------------------------
# 15. Every dependency is registered
# ---------------------------------------------------------------------------

def _walk_refs(value: object) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "$ref" and isinstance(v, str):
                refs.append(v)
            refs.extend(_walk_refs(v))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_walk_refs(item))
    return refs


def test_every_dependency_registered() -> None:
    registered_sids = set()
    for f in SCHEMA_FILES:
        schema = _load(f)
        sid = schema.get("$id", "")
        if sid:
            registered_sids.add(sid)
    for f in SCHEMA_FILES:
        schema = _load(f)
        refs = _walk_refs(schema)
        for ref in refs:
            if ref.startswith("#"):
                continue
            uri_part = ref.split("#")[0]
            if uri_part in (
                "https://json-schema.org/draft/2020-12/schema",
            ):
                continue
            _assert_diagnostic(
                uri_part in registered_sids,
                "Unregistered dependency",
                source=f.name,
                ref=ref,
                uri=uri_part,
            )


# ---------------------------------------------------------------------------
# 16. Load all schemas offline
# ---------------------------------------------------------------------------

def test_offline_package_load() -> None:
    for f in SCHEMA_FILES:
        schema = _load(f)
        sid = schema.get("$id", "")
        if not sid:
            continue
        validator_cls = jsonschema.validators.validator_for(schema)
        validator = validator_cls(schema, registry=REGISTRY)
        errors = list(validator.iter_errors({}))
        for err in errors:
            if err.validator in ("required", "type"):
                continue
            _assert_diagnostic(
                False,
                "Offline validation error",
                file=f.name,
                error=err.message,
            )


# ---------------------------------------------------------------------------
# 17. Valid fixture version matches manifest
# ---------------------------------------------------------------------------

def test_valid_fixture_versions() -> None:
    analysis_schemas = {
        "initial_analysis", "watching_update", "open_position_update",
        "partial_exit_review", "closing_analysis",
    }
    for fixture in sorted(VALID_DIR.glob("*.json")):
        name_part = fixture.stem.split(".")[0]
        if name_part not in analysis_schemas:
            continue
        instance = _load(fixture)
        for entry in MANIFEST["schemas"]:
            if entry["name"] == name_part:
                expected_ver = entry["version"]
                meta = instance.get("metadata", {})
                schema_block = meta.get("schema", {})
                fv = schema_block.get("schema_version", "")
                _assert_diagnostic(
                    fv == expected_ver,
                    "Fixture version mismatch",
                    fixture=fixture.name,
                    expected=expected_ver,
                    actual=fv,
                )


# ---------------------------------------------------------------------------
# 18. Cross-schema fixture rejection
# ---------------------------------------------------------------------------

def _resolve_and_validate(
    instance: dict, schema: dict, registry: Registry
) -> list[str]:
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema, registry=registry)
    return [e.message for e in validator.iter_errors(instance)]


CROSS_REJECTION_TESTS = [
    ("initial_analysis", "closing_analysis"),
    ("watching_update", "open_position_update"),
    ("partial_exit_review", "closing_analysis"),
]


def test_cross_schema_fixture_rejection() -> None:
    for fixture_name, wrong_schema in CROSS_REJECTION_TESTS:
        fixture_path = VALID_DIR / f"{fixture_name}.valid.json"
        wrong_path = PRODUCTION_DIR / f"{wrong_schema}.schema.json"
        _assert_diagnostic(
            fixture_path.exists(),
            "Fixture not found",
            fixture=fixture_path.name,
        )
        _assert_diagnostic(
            wrong_path.exists(),
            "Schema not found",
            schema=wrong_path.name,
        )
        instance = _load(fixture_path)
        wrong_schema_data = _load(wrong_path)
        errors = _resolve_and_validate(instance, wrong_schema_data, REGISTRY)
        _assert_diagnostic(
            len(errors) >= 1,
            "Fixture validated against wrong schema",
            fixture=fixture_name,
            wrong_schema=wrong_schema,
        )


# ---------------------------------------------------------------------------
# 19. Invalid version fixtures
# ---------------------------------------------------------------------------

INVALID_VERSION_FIXTURES = [
    ("open_position_update.invalid.missing_required", "version"),
]


def test_invalid_version_fixtures() -> None:
    for fix_name, _ in INVALID_VERSION_FIXTURES:
        fixture_path = INVALID_DIR / f"{fix_name}.json"
        _assert_diagnostic(
            fixture_path.exists(),
            "Invalid fixture not found",
            fixture=fixture_path.name,
        )
        # Determine target schema from fixture name
        name_part = fix_name.split(".")[0]
        schema_path = PRODUCTION_DIR / f"{name_part}.schema.json"
        _assert_diagnostic(
            schema_path.exists(),
            "Schema not found for in valid fixture",
            fixture=fix_name,
            schema=schema_path.name,
        )
        instance = _load(fixture_path)
        schema_data = _load(schema_path)
        errors = _resolve_and_validate(instance, schema_data, REGISTRY)
        _assert_diagnostic(
            len(errors) >= 1,
            "Invalid fixture unexpectedly passed",
            fixture=fix_name,
        )
