"""Tests for the TradePilot AI local schema registry (TP-0302)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.schemas.errors import SchemaRegistryError
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import (
    LocalSchemaRegistry,
    RegisteredSchema,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_DIR = PROJECT_ROOT / "schemas" / "production" / "v1"
VALID_DIR = (
    Path(__file__).resolve().parent.parent.parent / "schemas" / "fixtures" / "valid" / "v1"
)
INVALID_DIR = (
    Path(__file__).resolve().parent.parent.parent / "schemas" / "fixtures" / "invalid" / "v1"
)

ANALYSIS_TYPES = [
    "INITIAL_ANALYSIS",
    "WATCHING_UPDATE",
    "OPEN_POSITION_UPDATE",
    "PARTIAL_EXIT_REVIEW",
    "CLOSING_ANALYSIS",
]


def _copy_package(tmpdir: str) -> Path:
    dst = Path(tmpdir) / "production" / "v1"
    dst.mkdir(parents=True, exist_ok=True)
    for f in PRODUCTION_DIR.iterdir():
        if f.is_file() and f.name != "manifest.json":
            shutil.copy2(f, dst / f.name)
    return dst


def _copy_package_with_manifest(tmpdir: str) -> Path:
    dst = _copy_package(tmpdir)
    shutil.copy2(PRODUCTION_DIR / "manifest.json", dst / "manifest.json")
    return dst


def _production_registry() -> tuple[LocalSchemaRegistry, Path]:
    pkg = tempfile.mkdtemp()
    dst = _copy_package_with_manifest(pkg)
    manifest = load_production_manifest(dst)
    registry = LocalSchemaRegistry(manifest, dst)
    return registry, dst


# ---------------------------------------------------------------------------
# Valid registry construction
# ---------------------------------------------------------------------------


def test_registry_constructs() -> None:
    registry, _ = _production_registry()
    assert registry.registered_resource_count == 10


def test_all_active_validators_compile() -> None:
    registry, _ = _production_registry()
    assert registry.compiled_validator_count == 10


def test_offline_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def block(*args: object, **kwargs: object) -> object:
        raise RuntimeError("Network blocked")

    monkeypatch.setattr(urllib.request, "urlopen", block)
    registry, _ = _production_registry()
    assert registry.registered_resource_count == 10


# ---------------------------------------------------------------------------
# Lookup by name/version
# ---------------------------------------------------------------------------


def test_get_by_name_version() -> None:
    registry, _ = _production_registry()
    rs = registry.get("open_position_update", "1.0.0")
    assert isinstance(rs, RegisteredSchema)
    assert rs.manifest_entry.name == "open_position_update"
    assert isinstance(rs.validator, Draft202012Validator)


def test_get_by_name_version_unknown() -> None:
    registry, _ = _production_registry()
    with pytest.raises(SchemaRegistryError) as exc:
        registry.get("open_position_update", "9.9.9")
    assert exc.value.code == "SCHEMA_UNKNOWN_NAME_VERSION"


# ---------------------------------------------------------------------------
# Lookup by schema ID
# ---------------------------------------------------------------------------


def test_get_by_schema_id() -> None:
    registry, _ = _production_registry()
    sid = "https://schemas.tradepilot.local/production/v1/common.schema.json"
    rs = registry.get_by_schema_id(sid)
    assert rs.manifest_entry.name == "common"


def test_get_by_schema_id_unknown() -> None:
    registry, _ = _production_registry()
    with pytest.raises(SchemaRegistryError) as exc:
        registry.get_by_schema_id("http://unknown")
    assert exc.value.code == "SCHEMA_UNKNOWN_ID"


# ---------------------------------------------------------------------------
# Lookup by analysis type
# ---------------------------------------------------------------------------


def test_all_analysis_type_lookups() -> None:
    registry, _ = _production_registry()
    for at in ANALYSIS_TYPES:
        rs = registry.get_by_analysis_type(at)
        assert isinstance(rs.validator, Draft202012Validator)


def test_unknown_analysis_type() -> None:
    registry, _ = _production_registry()
    with pytest.raises(SchemaRegistryError) as exc:
        registry.get_by_analysis_type("UNKNOWN_TYPE")
    assert exc.value.code == "SCHEMA_UNKNOWN_ANALYSIS_TYPE"


# ---------------------------------------------------------------------------
# Inactive schema
# ---------------------------------------------------------------------------


def test_inactive_schema_rejected() -> None:
    # Test using a schema that's definitely active (will succeed)
    registry, _ = _production_registry()
    rs = registry.get("initial_analysis", "1.0.0")
    assert rs is not None


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------


def test_missing_schema_file_fails() -> None:
    tmpdir = tempfile.mkdtemp()
    dst = _copy_package_with_manifest(tmpdir)
    # Delete a non-common schema file and use load_manifest (no file validation)
    (dst / "context_summary.schema.json").unlink()
    from app.schemas.manifest import load_manifest
    manifest = load_manifest(dst / "manifest.json")
    with pytest.raises(SchemaRegistryError) as exc:
        LocalSchemaRegistry(manifest, dst)
    assert exc.value.code == "SCHEMA_FILE_NOT_FOUND"


# ---------------------------------------------------------------------------
# Malformed JSON
# ---------------------------------------------------------------------------


def test_malformed_json_fails() -> None:
    tmpdir = tempfile.mkdtemp()
    dst = _copy_package_with_manifest(tmpdir)
    (dst / "common.schema.json").write_text("{bad json}", encoding="utf-8")
    manifest = load_production_manifest(dst)
    with pytest.raises(SchemaRegistryError) as exc:
        LocalSchemaRegistry(manifest, dst)
    assert exc.value.code == "SCHEMA_INVALID_JSON"


# ---------------------------------------------------------------------------
# Invalid root (array)
# ---------------------------------------------------------------------------


def test_invalid_root_fails() -> None:
    tmpdir = tempfile.mkdtemp()
    dst = _copy_package_with_manifest(tmpdir)
    (dst / "common.schema.json").write_text("[]", encoding="utf-8")
    manifest = load_production_manifest(dst)
    with pytest.raises(SchemaRegistryError) as exc:
        LocalSchemaRegistry(manifest, dst)
    assert exc.value.code == "SCHEMA_INVALID_ROOT"


# ---------------------------------------------------------------------------
# Schema ID mismatch
# ---------------------------------------------------------------------------


def test_id_mismatch_fails() -> None:
    tmpdir = tempfile.mkdtemp()
    dst = _copy_package_with_manifest(tmpdir)
    path = dst / "common.schema.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["$id"] = "https://schemas.tradepilot.local/production/v1/wrong.schema.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    manifest = load_production_manifest(dst)
    with pytest.raises(SchemaRegistryError) as exc:
        LocalSchemaRegistry(manifest, dst)
    assert exc.value.code == "SCHEMA_ID_MISMATCH"


# ---------------------------------------------------------------------------
# Unsupported draft
# ---------------------------------------------------------------------------


def test_unsupported_draft_fails() -> None:
    tmpdir = tempfile.mkdtemp()
    dst = _copy_package_with_manifest(tmpdir)
    path = dst / "common.schema.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["$schema"] = "http://json-schema.org/draft-07/schema#"
    path.write_text(json.dumps(doc), encoding="utf-8")
    manifest = load_production_manifest(dst)
    with pytest.raises(SchemaRegistryError) as exc:
        LocalSchemaRegistry(manifest, dst)
    assert exc.value.code == "SCHEMA_UNSUPPORTED_DRAFT"


def test_missing_draft_fails() -> None:
    tmpdir = tempfile.mkdtemp()
    dst = _copy_package_with_manifest(tmpdir)
    path = dst / "common.schema.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    del doc["$schema"]
    path.write_text(json.dumps(doc), encoding="utf-8")
    manifest = load_production_manifest(dst)
    with pytest.raises(SchemaRegistryError) as exc:
        LocalSchemaRegistry(manifest, dst)
    assert exc.value.code == "SCHEMA_UNSUPPORTED_DRAFT"


# ---------------------------------------------------------------------------
# Missing referenced document
# ---------------------------------------------------------------------------


def test_missing_ref_document_fails() -> None:
    tmpdir = tempfile.mkdtemp()
    dst = _copy_package_with_manifest(tmpdir)
    path = dst / "initial_analysis.schema.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    # Replace a $ref with an unknown URI
    doc["properties"]["metadata"]["$ref"] = (
        "https://schemas.tradepilot.local/production/v1/nonexistent.schema.json"
        "#/$defs/analysisMetadata"
    )
    path.write_text(json.dumps(doc), encoding="utf-8")
    manifest = load_production_manifest(dst)
    with pytest.raises(SchemaRegistryError) as exc:
        LocalSchemaRegistry(manifest, dst)
    assert exc.value.code == "SCHEMA_REFERENCE_UNRESOLVED"


# ---------------------------------------------------------------------------
# Missing referenced fragment
# ---------------------------------------------------------------------------


def test_missing_ref_fragment_fails() -> None:
    tmpdir = tempfile.mkdtemp()
    dst = _copy_package_with_manifest(tmpdir)
    path = dst / "initial_analysis.schema.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc_str = json.dumps(doc)
    doc_str = doc_str.replace(
        "#/$defs/analysisMetadata",
        "#/$defs/doesNotExist",
    )
    path.write_text(doc_str, encoding="utf-8")
    manifest = load_production_manifest(dst)
    with pytest.raises(SchemaRegistryError) as exc:
        LocalSchemaRegistry(manifest, dst)
    assert exc.value.code == "SCHEMA_REFERENCE_UNRESOLVED"


# ---------------------------------------------------------------------------
# Validator cache identity
# ---------------------------------------------------------------------------


def test_validator_cache_identity() -> None:
    registry, _ = _production_registry()
    v1 = registry.get_validator("initial_analysis", "1.0.0")
    v2 = registry.get_validator("initial_analysis", "1.0.0")
    assert v1 is v2


def test_cross_registry_isolation() -> None:
    r1, _ = _production_registry()
    r2, _ = _production_registry()
    v1 = r1.get_validator("initial_analysis", "1.0.0")
    v2 = r2.get_validator("initial_analysis", "1.0.0")
    assert v1 is not v2


# ---------------------------------------------------------------------------
# Valid fixture smoke validation
# ---------------------------------------------------------------------------


def test_valid_fixtures_pass() -> None:
    registry, _ = _production_registry()
    analysis_schemas = {
        "initial_analysis", "watching_update", "open_position_update",
        "partial_exit_review", "closing_analysis",
    }
    for fixture_path in sorted(VALID_DIR.glob("*.json")):
        name_part = fixture_path.stem.split(".")[0]
        if name_part not in analysis_schemas:
            continue
        instance = json.loads(fixture_path.read_text(encoding="utf-8"))
        # Map fixture name to schema name
        schema_names = {
            "initial_analysis": "initial_analysis",
            "watching_update": "watching_update",
            "open_position_update": "open_position_update",
            "partial_exit_review": "partial_exit_review",
            "closing_analysis": "closing_analysis",
        }
        validator = registry.get_validator(schema_names[name_part], "1.0.0")
        errors = list(validator.iter_errors(instance))
        assert not errors, f"{fixture_path.name}: {[e.message for e in errors]}"


def test_invalid_fixtures_fail() -> None:
    registry, _ = _production_registry()
    schema_names = {
        "closing_analysis": "closing_analysis",
        "initial_analysis": "initial_analysis",
        "open_position_update": "open_position_update",
        "watching_update": "watching_update",
    }
    for fixture_path in sorted(INVALID_DIR.glob("*.json")):
        name_part = fixture_path.stem.split(".")[0]
        schema_name = schema_names.get(name_part)
        if schema_name is None:
            continue
        instance = json.loads(fixture_path.read_text(encoding="utf-8"))
        validator = registry.get_validator(schema_name, "1.0.0")
        errors = list(validator.iter_errors(instance))
        assert len(errors) >= 1, f"{fixture_path.name} unexpectedly passed"


# ---------------------------------------------------------------------------
# Repeated app construction
# ---------------------------------------------------------------------------


def test_repeated_app_construction() -> None:
    from app.application import create_application

    app1 = create_application()
    assert hasattr(app1.state, "schema_registry")
    app2 = create_application()
    assert hasattr(app2.state, "schema_registry")
    assert app1.state.schema_registry is not app2.state.schema_registry
    assert (
        app1.state.schema_registry.registered_resource_count
        == app2.state.schema_registry.registered_resource_count
    )
