from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from referencing import Registry, Resource  # type: ignore[import]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_DIR = PROJECT_ROOT / "schemas" / "production" / "v1"
FIXTURES_DIR = PROJECT_ROOT / "schemas" / "fixtures"
VALID_DIR = FIXTURES_DIR / "valid" / "v1"
INVALID_DIR = FIXTURES_DIR / "invalid" / "v1"

SCHEMA_FILE_PATTERN = "*.schema.json"
SCHEMA_FILES = sorted(PRODUCTION_DIR.glob(SCHEMA_FILE_PATTERN))
def _load_json(path: Path) -> dict[str, object]:
    with open(path) as f:
        return json.load(f)


def _build_registry() -> Registry:
    resources: dict[str, Resource] = {}
    for file in SCHEMA_FILES:
        schema = _load_json(file)
        sid = str(schema.get("$id", ""))
        if sid:
            resources[sid] = Resource.from_contents(schema)
    def retriever(uri: str) -> Resource:
        if uri in resources:
            return resources[uri]
        raise jsonschema.RefResolutionError(f"Unresolvable $ref: {uri}")
    return Registry(retrieve=retriever)  # type: ignore[call-arg]


REGISTRY = _build_registry()

schema_ids: dict[str, dict[str, object]] = {}
for file in SCHEMA_FILES:
    schema = _load_json(file)
    sid = str(schema.get("$id", ""))
    schema_ids[sid] = schema


@pytest.fixture(scope="module")
def registry() -> Registry:
    return REGISTRY


@pytest.fixture(scope="module")
def schema_map() -> dict[str, dict[str, object]]:
    return dict(schema_ids)


def _get_schema_for_fixture(fixture_path: Path) -> str | None:
    name_part = fixture_path.stem.split(".")[0]
    for schema_file in SCHEMA_FILES:
        if schema_file.stem.startswith(name_part):
            return str(schema_file)
    return None


def _resolve_and_validate(
    instance: dict[str, object], schema: dict[str, object], registry: Registry
) -> list[str]:
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema, registry=registry)
    errors = list(validator.iter_errors(instance))
    return [e.message for e in errors]


# ---------------------------------------------------------------------------
# 1. Every schema file is valid JSON
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("schema_file", SCHEMA_FILES, ids=lambda p: p.name)
def test_schema_is_valid_json(schema_file: Path) -> None:
    _load_json(schema_file)


# ---------------------------------------------------------------------------
# 2. Every schema is valid under Draft 2020-12
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("schema_file", SCHEMA_FILES, ids=lambda p: p.name)
def test_schema_is_valid_draft2020(schema_file: Path) -> None:
    schema = _load_json(schema_file)
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)


# ---------------------------------------------------------------------------
# 3. All $ref references resolve
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("schema_file", SCHEMA_FILES, ids=lambda p: p.name)
def test_schema_refs_resolve(schema_file: Path, registry: Registry) -> None:
    schema = _load_json(schema_file)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema, registry=registry)
    validator.iter_errors({})


# ---------------------------------------------------------------------------
# 4. Valid fixtures pass schema validation
# ---------------------------------------------------------------------------

def _valid_fixtures() -> list[tuple[str, str, Path]]:
    results: list[tuple[str, str, Path]] = []
    for fixture in sorted(VALID_DIR.glob("*.json")):
        schema_file = _get_schema_for_fixture(fixture)
        if schema_file:
            results.append((fixture.stem, fixture.name, fixture))
    return results


@pytest.mark.parametrize(
    ("_test_id", "fixture_name", "fixture_path"),
    _valid_fixtures(),
)
def test_valid_fixture_passes(
    _test_id: str,
    fixture_name: str,
    fixture_path: Path,
    registry: Registry,
) -> None:
    instance = _load_json(fixture_path)
    schema_file = _get_schema_for_fixture(fixture_path)
    assert schema_file is not None, f"No matching schema for {fixture_name}"
    schema = _load_json(Path(schema_file))
    errors = _resolve_and_validate(instance, schema, registry)
    assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# 5. Invalid fixtures fail schema validation
# ---------------------------------------------------------------------------

def _invalid_fixtures() -> list[tuple[str, str, Path]]:
    results: list[tuple[str, str, Path]] = []
    for fixture in sorted(INVALID_DIR.glob("*.json")):
        schema_file = _get_schema_for_fixture(fixture)
        if schema_file:
            results.append((fixture.stem, fixture.name, fixture))
    return results


@pytest.mark.parametrize(
    ("_test_id", "fixture_name", "fixture_path"),
    _invalid_fixtures(),
)
def test_invalid_fixture_fails(
    _test_id: str,
    fixture_name: str,
    fixture_path: Path,
    registry: Registry,
) -> None:
    instance = _load_json(fixture_path)
    schema_file = _get_schema_for_fixture(fixture_path)
    assert schema_file is not None, f"No matching schema for {fixture_name}"
    schema = _load_json(Path(schema_file))
    errors = _resolve_and_validate(instance, schema, registry)
    assert len(errors) >= 1, f"Expected {fixture_name} to be invalid but it passed"


# ---------------------------------------------------------------------------
# 6. Manifest entries match actual files
# ---------------------------------------------------------------------------

def test_manifest_matches_files() -> None:
    manifest_path = PRODUCTION_DIR / "manifest.json"
    assert manifest_path.exists()
    manifest = _load_json(manifest_path)
    manifest_files: set[str] = set()
    for entry in manifest["schemas"]:
        fname = entry["file"]
        manifest_files.add(fname)
    actual_files = {p.name for p in SCHEMA_FILES}
    assert manifest_files == actual_files, (
        f"Mismatch: manifest has {manifest_files - actual_files}, "
        f"files missing from manifest: {actual_files - manifest_files}"
    )


# ---------------------------------------------------------------------------
# 7. $id values are unique
# ---------------------------------------------------------------------------

def test_schema_ids_are_unique() -> None:
    ids = []
    for file in SCHEMA_FILES:
        schema = _load_json(file)
        sid = schema.get("$id")
        if sid:
            ids.append(sid)
    duplicates = {id_ for id_ in ids if ids.count(id_) > 1}
    assert not duplicates, f"Duplicate $id values: {duplicates}"


# ---------------------------------------------------------------------------
# 8. All schemas have additionalProperties: false at root
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("schema_file", SCHEMA_FILES, ids=lambda p: p.name)
def test_schema_root_has_additional_properties_false(schema_file: Path) -> None:
    schema = _load_json(schema_file)
    assert schema.get("additionalProperties") is False, (
        f"{schema_file.name} is missing additionalProperties: false at root"
    )


# ---------------------------------------------------------------------------
# 9. schema_version pattern is enforced
# ---------------------------------------------------------------------------

PATTERN_SEMVER = "^[0-9]+\\.[0-9]+\\.[0-9]+$"


def _check_semver_pattern(schema: dict[str, object], path: str, registry: Registry) -> None:
    parts = path.split(".")
    val: dict = schema
    for part in parts:
        if isinstance(val, dict) and part in val:
            val = val[part]
        else:
            return
    if not isinstance(val, dict):
        return
    pattern = val.get("pattern")
    if pattern is not None:
        assert pattern == PATTERN_SEMVER, f"Wrong pattern at {path}: {pattern}"


@pytest.mark.parametrize("schema_file", SCHEMA_FILES, ids=lambda p: p.name)
def test_schema_version_pattern(schema_file: Path, registry: Registry) -> None:
    schema = _load_json(schema_file)
    sv_prop = (
        schema.get("$defs", {})
        .get("schemaMetadata", {})
        .get("properties", {})
        .get("schema_version", {})
    )
    if sv_prop.get("pattern"):
        assert sv_prop["pattern"] == PATTERN_SEMVER, (
            f"{schema_file.name}: common schema_version pattern mismatch"
        )
    meta_schema = (
        schema.get("properties", {})
        .get("metadata", {})
        .get("properties", {})
        .get("schema", {})
        .get("properties", {})
        .get("schema_version", {})
    )
    if meta_schema and isinstance(meta_schema, dict) and meta_schema.get("pattern"):
        assert meta_schema["pattern"] == PATTERN_SEMVER, (
            f"{schema_file.name}: metadata.schema.schema_version pattern mismatch"
        )
    if "properties" in schema:
        for key in ("schema_version", "prompt_version", "context_version"):
            if key in schema["properties"]:
                prop = schema["properties"][key]
                if isinstance(prop, dict) and prop.get("pattern"):
                    assert prop["pattern"] == PATTERN_SEMVER, (
                        f"{schema_file.name}: root {key} pattern mismatch"
                    )


# ---------------------------------------------------------------------------
# 10. Fixture metadata correctness
# ---------------------------------------------------------------------------

def test_valid_fixtures_have_correct_metadata() -> None:
    analysis_schemas = {
        "initial_analysis", "watching_update", "open_position_update",
        "partial_exit_review", "closing_analysis",
    }
    for fixture in sorted(VALID_DIR.glob("*.json")):
        instance = _load_json(fixture)
        schema_name = fixture.stem.split(".")[0]
        if schema_name not in analysis_schemas:
            continue
        meta = instance["metadata"]
        assert meta.get("provider") == "GEMINI", f"{fixture.name}: provider not GEMINI"
        assert meta.get("model") == "gemini-2.0-flash", f"{fixture.name}: model mismatch"
        assert meta.get("language") == "id", f"{fixture.name}: language not id"
        assert meta.get("prompt_version") == "1.0.0", f"{fixture.name}: prompt_version wrong"
        schema_block = meta.get("schema", {})
        if schema_block:
            assert schema_block.get("schema_name") == schema_name, (
                f"{fixture.name}: schema_name mismatch"
            )
            assert schema_block.get("schema_version") == "1.0.0", (
                f"{fixture.name}: schema_version not 1.0.0"
            )
