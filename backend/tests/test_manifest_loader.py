"""Tests for the TradePilot AI manifest loader (TP-0301)."""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from app.schemas.errors import ManifestLoadError, ManifestValidationError
from app.schemas.manifest import (
    PRODUCTION_REQUIRED_STATUS,
    REQUIRED_ANALYSIS_TYPES,
    ProductionManifest,
    load_manifest,
    load_production_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_DIR = PROJECT_ROOT / "schemas" / "production" / "v1"
PRODUCTION_MANIFEST = PRODUCTION_DIR / "manifest.json"


def _read_production_manifest() -> dict:
    return json.loads(PRODUCTION_MANIFEST.read_text(encoding="utf-8"))


def _copy_production_package(tmpdir: str) -> Path:
    dst = Path(tmpdir) / "production" / "v1"
    dst.mkdir(parents=True, exist_ok=True)
    for f in PRODUCTION_DIR.iterdir():
        if f.is_file():
            shutil.copy2(f, dst / f.name)
    return dst


# ---------------------------------------------------------------------------
# Valid manifest
# ---------------------------------------------------------------------------


def test_valid_production_manifest_loads() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    assert isinstance(manifest, ProductionManifest)
    assert manifest.status == PRODUCTION_REQUIRED_STATUS


def test_typed_manifest() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    assert hasattr(manifest, "schemas")
    assert hasattr(manifest, "analysis_type_registry")
    assert hasattr(manifest, "session_status_schema_mapping")


def test_exact_schema_count() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    assert len(manifest.schemas) == 10


def test_active_schema_count() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    active = manifest.active_schemas()
    assert len(active) == 10


def test_required_analysis_mappings_work() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    for atype in REQUIRED_ANALYSIS_TYPES:
        entry = manifest.get_by_analysis_type(atype)
        assert entry is not None, f"Missing analysis type mapping: {atype}"
        assert entry.active is True
        assert entry.category == "AI_ANALYSIS"


def test_session_mappings_parse() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    assert len(manifest.session_status_schema_mapping) >= 5


def test_narrative_rules_parse() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    assert manifest.narrative_rules is not None
    assert manifest.narrative_rules.user_facing_language == "id"


def test_deterministic_ordering() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    names = [e.name for e in manifest.schemas]
    # Manifest order is deterministic — verify no duplicates
    assert len(names) == len(set(names))
    # Expected canonical order from manifest.json
    expected = [
        "common", "market_snapshot", "trade_state", "evidence",
        "initial_analysis", "watching_update", "open_position_update",
        "partial_exit_review", "closing_analysis", "context_summary",
    ]
    assert names == expected


def test_lookup_by_name_version() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    entry = manifest.get_schema("initial_analysis", "1.0.0")
    assert entry is not None
    assert entry.file == "initial_analysis.schema.json"


def test_lookup_by_schema_id() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    entry = manifest.get_by_schema_id(
        "https://schemas.tradepilot.local/production/v1/common.schema.json"
    )
    assert entry is not None
    assert entry.name == "common"


def test_lookup_by_analysis_type() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    entry = manifest.get_by_analysis_type("CLOSING_ANALYSIS")
    assert entry is not None
    assert entry.name == "closing_analysis"


def test_unknown_identity_returns_none() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    assert manifest.get_schema("nonexistent", "1.0") is None
    assert manifest.get_by_schema_id("http://unknown") is None
    assert manifest.get_by_analysis_type("UNKNOWN_TYPE") is None


def test_immutable_collections() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    entries = manifest.active_schemas()
    with pytest.raises(dataclasses.FrozenInstanceError):
        entries[0].name = "changed"  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Missing manifest
# ---------------------------------------------------------------------------


def test_missing_manifest() -> None:
    with pytest.raises(ManifestLoadError) as excinfo:
        load_manifest(Path("/nonexistent/manifest.json"))
    assert excinfo.value.code == "MANIFEST_NOT_FOUND"
    assert excinfo.value.path is not None


# ---------------------------------------------------------------------------
# Invalid JSON
# ---------------------------------------------------------------------------


def test_invalid_json() -> None:
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text("{invalid json}", encoding="utf-8")
    with pytest.raises(ManifestLoadError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_INVALID_JSON"
    assert "line" in str(excinfo.value.location or "")
    os.unlink(tmp)


# ---------------------------------------------------------------------------
# Root structure
# ---------------------------------------------------------------------------


def test_root_array() -> None:
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text("[]", encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_INVALID_STRUCTURE"
    os.unlink(tmp)


def test_missing_required_root_field() -> None:
    data = _read_production_manifest()
    del data["manifest_name"]
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_INVALID_STRUCTURE"
    os.unlink(tmp)


def test_unsupported_manifest_status() -> None:
    data = _read_production_manifest()
    data["status"] = "OBSOLETE"
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_UNSUPPORTED_STATUS"
    os.unlink(tmp)


# ---------------------------------------------------------------------------
# Duplicate checks
# ---------------------------------------------------------------------------


def _inject_duplicate_entry_field(
    field: str, value_a: object, value_b: object
) -> dict:
    data = _read_production_manifest()
    schemas = list(data["schemas"])
    entry0 = dict(schemas[0])
    entry0[field] = value_a
    entry1 = dict(schemas[1])
    entry1[field] = value_b
    schemas[0] = entry0
    schemas[1] = entry1
    data["schemas"] = schemas
    return data


def test_duplicate_name() -> None:
    data = _inject_duplicate_entry_field("name", "dup-name", "dup-name")
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_DUPLICATE_SCHEMA_NAME"
    os.unlink(tmp)


def test_duplicate_id() -> None:
    data = _inject_duplicate_entry_field(
        "schema_id",
        "https://schemas.tradepilot.local/production/v1/dup.schema.json",
        "https://schemas.tradepilot.local/production/v1/dup.schema.json",
    )
    data["schemas"][1]["name"] = "other-name"
    data["schemas"][1]["file"] = "other.schema.json"
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_DUPLICATE_SCHEMA_ID"
    os.unlink(tmp)


def test_duplicate_filename() -> None:
    data = _inject_duplicate_entry_field(
        "file", "same.schema.json", "same.schema.json"
    )
    data["schemas"][1]["name"] = "other-name"
    data["schemas"][1]["schema_id"] = (
        "https://schemas.tradepilot.local/production/v1/other.schema.json"
    )
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_DUPLICATE_FILENAME"
    os.unlink(tmp)


def test_duplicate_name_version() -> None:
    data = _read_production_manifest()
    schemas = list(data["schemas"])
    entry0 = dict(schemas[0])
    entry0["name"] = "dup-name"
    entry0["version"] = "1.0.0"
    entry1 = dict(schemas[1])
    entry1["name"] = "dup-name"
    entry1["version"] = "1.0.0"
    schemas[0] = entry0
    schemas[1] = entry1
    data["schemas"] = schemas
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code in (
        "MANIFEST_DUPLICATE_NAME_VERSION", "MANIFEST_DUPLICATE_SCHEMA_NAME",
    )
    os.unlink(tmp)


# ---------------------------------------------------------------------------
# Filename safety
# ---------------------------------------------------------------------------


def test_absolute_posix_path() -> None:
    data = _read_production_manifest()
    data["schemas"] = list(data["schemas"])
    entry = dict(data["schemas"][0])
    entry["file"] = "/etc/passwd"
    data["schemas"][0] = entry
    tmpdir = tempfile.mkdtemp()
    pkg = _copy_production_package(tmpdir)
    (pkg / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_production_manifest(pkg)
    assert excinfo.value.code == "MANIFEST_PATH_ESCAPE"
    shutil.rmtree(tmpdir)


def test_traversal_path() -> None:
    data = _read_production_manifest()
    data["schemas"] = list(data["schemas"])
    entry = dict(data["schemas"][0])
    entry["file"] = "../../../etc/passwd"
    data["schemas"][0] = entry
    tmpdir = tempfile.mkdtemp()
    pkg = _copy_production_package(tmpdir)
    (pkg / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_production_manifest(pkg)
    assert excinfo.value.code == "MANIFEST_PATH_ESCAPE"
    shutil.rmtree(tmpdir)


def test_missing_schema_file() -> None:
    tmpdir = tempfile.mkdtemp()
    pkg = _copy_production_package(tmpdir)
    manifest_entry = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    manifest_entry["schemas"] = list(manifest_entry["schemas"])
    entry = dict(manifest_entry["schemas"][0])
    entry["file"] = "nonexistent.schema.json"
    manifest_entry["schemas"][0] = entry
    (pkg / "manifest.json").write_text(json.dumps(manifest_entry), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_production_manifest(pkg)
    assert excinfo.value.code == "MANIFEST_MISSING_SCHEMA_FILE"
    shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Dependency validation
# ---------------------------------------------------------------------------


def test_valid_dependencies_resolve() -> None:
    manifest = load_production_manifest(PRODUCTION_DIR)
    for entry in manifest.schemas:
        for dep in entry.dependencies:
            if dep == "common":
                assert manifest.get_schema(
                    "common", "1.0.0"
                ), f"Missing dependency: {dep}"


# ---------------------------------------------------------------------------
# Analysis mapping tests
# ---------------------------------------------------------------------------


def test_missing_required_analysis_type_fails() -> None:
    data = _read_production_manifest()
    at_reg = dict(data.get("analysis_type_registry", {}))
    del at_reg["CLOSING_ANALYSIS"]
    data["analysis_type_registry"] = at_reg
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_MISSING_ANALYSIS_MAPPING"
    os.unlink(tmp)


def test_wrong_analysis_schema_mapping() -> None:
    data = _read_production_manifest()
    at_reg = dict(data.get("analysis_type_registry", {}))
    at_reg["INITIAL_ANALYSIS"] = dict(at_reg["INITIAL_ANALYSIS"])
    at_reg["INITIAL_ANALYSIS"]["schema"] = "closing_analysis"
    data["analysis_type_registry"] = at_reg
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_INVALID_ANALYSIS_MAPPING"
    os.unlink(tmp)


# ---------------------------------------------------------------------------
# Session mapping tests
# ---------------------------------------------------------------------------


def test_session_mapping_unknown_schema_fails() -> None:
    data = _read_production_manifest()
    ss_map = dict(data.get("session_status_schema_mapping", {}))
    ss_map["TEST_STATUS"] = {"allowed_analysis_types": [], "canonical_schema": "unknown"}
    data["session_status_schema_mapping"] = ss_map
    tmp = tempfile.mktemp(suffix=".json")
    Path(tmp).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestValidationError) as excinfo:
        load_manifest(Path(tmp))
    assert excinfo.value.code == "MANIFEST_INVALID_SESSION_MAPPING"
    os.unlink(tmp)


# ---------------------------------------------------------------------------
# No registry / compilation
# ---------------------------------------------------------------------------


def test_no_registry_compilation() -> None:
    import app.schemas.manifest as m

    source = Path(m.__file__).read_text(encoding="utf-8")
    assert "Draft202012Validator" not in source
    assert "referencing.Registry" not in source


def test_no_network_refs(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def block(*args: object, **kwargs: object) -> object:
        raise RuntimeError("Network access blocked")

    monkeypatch.setattr(urllib.request, "urlopen", block)
    manifest = load_production_manifest(PRODUCTION_DIR)
    assert manifest.status == "ACTIVE"
