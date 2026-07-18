"""Typed manifest loading and validation for the TradePilot AI schema package."""
# mypy: ignore-errors

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping

from app.schemas.errors import ManifestLoadError, ManifestValidationError

# ---------------------------------------------------------------------------
# Stable error codes
# ---------------------------------------------------------------------------

MANIFEST_NOT_FOUND = "MANIFEST_NOT_FOUND"
MANIFEST_INVALID_JSON = "MANIFEST_INVALID_JSON"
MANIFEST_INVALID_STRUCTURE = "MANIFEST_INVALID_STRUCTURE"
MANIFEST_UNSUPPORTED_STATUS = "MANIFEST_UNSUPPORTED_STATUS"
MANIFEST_DUPLICATE_SCHEMA_NAME = "MANIFEST_DUPLICATE_SCHEMA_NAME"
MANIFEST_DUPLICATE_SCHEMA_ID = "MANIFEST_DUPLICATE_SCHEMA_ID"
MANIFEST_DUPLICATE_FILENAME = "MANIFEST_DUPLICATE_FILENAME"
MANIFEST_DUPLICATE_NAME_VERSION = "MANIFEST_DUPLICATE_NAME_VERSION"
MANIFEST_MISSING_SCHEMA_FILE = "MANIFEST_MISSING_SCHEMA_FILE"
MANIFEST_UNKNOWN_DEPENDENCY = "MANIFEST_UNKNOWN_DEPENDENCY"
MANIFEST_MISSING_ANALYSIS_MAPPING = "MANIFEST_MISSING_ANALYSIS_MAPPING"
MANIFEST_INVALID_ANALYSIS_MAPPING = "MANIFEST_INVALID_ANALYSIS_MAPPING"
MANIFEST_INVALID_SESSION_MAPPING = "MANIFEST_INVALID_SESSION_MAPPING"
MANIFEST_PATH_ESCAPE = "MANIFEST_PATH_ESCAPE"
MANIFEST_UNSUPPORTED_VERSION = "MANIFEST_UNSUPPORTED_VERSION"

# ---------------------------------------------------------------------------
# Canonical expected-sets
# ---------------------------------------------------------------------------

REQUIRED_ANALYSIS_TYPES = frozenset(
    {
        "INITIAL_ANALYSIS",
        "WATCHING_UPDATE",
        "OPEN_POSITION_UPDATE",
        "PARTIAL_EXIT_REVIEW",
        "CLOSING_ANALYSIS",
    }
)

ANALYSIS_TYPE_INTERNAL_MAP: Mapping[str, str] = {
    "INITIAL_ANALYSIS": "initial_analysis",
    "WATCHING_UPDATE": "watching_update",
    "OPEN_POSITION_UPDATE": "open_position_update",
    "PARTIAL_EXIT_REVIEW": "partial_exit_review",
    "CLOSING_ANALYSIS": "closing_analysis",
}

# ---------------------------------------------------------------------------
# Typed models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SchemaManifestEntry:
    name: str
    title: str
    version: str
    category: str
    root_schema: bool
    active: bool
    file: str
    schema_id: str
    description: str
    analysis_types: tuple[str, ...]
    dependencies: tuple[str, ...]
    used_by: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalysisTypeRegistration:
    schema_name: str
    schema_version: str
    requires_position: bool
    requires_previous_analysis: bool
    requires_canonical_trade_state: bool
    requires_user_confirmation_before_execution: bool
    required_evidence: tuple[str, ...]
    optional_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SessionStatusEntry:
    allowed_analysis_types: tuple[str, ...]
    canonical_schema: str


@dataclass(frozen=True, slots=True)
class ManifestValidationRules:
    json_schema_validation_required: bool
    domain_validation_required: bool
    validate_format_keywords: bool
    reject_unknown_properties: bool
    reject_unknown_schema_versions: bool
    reject_inactive_schemas: bool
    reject_unregistered_schema_ids: bool
    domain_validators: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ManifestNarrativeRules:
    user_facing_language: str
    technical_keys_language: str
    enum_language: str
    probabilities_are_estimates_not_guarantees: bool
    confidence_is_not_probability: bool


@dataclass(frozen=True, slots=True)
class ProviderCompatibility:
    supported_providers: tuple[str, ...]
    structured_output_required: bool
    fallback_must_preserve_schema: bool
    additional_properties_allowed: bool


@dataclass(frozen=True, slots=True)
class ProductionManifest:
    manifest_name: str
    manifest_version: str
    schema_standard: str
    environment: str
    status: str
    base_uri: str
    default_language: str
    technical_language: str
    description: str
    schemas: tuple[SchemaManifestEntry, ...]
    analysis_type_registry: Mapping[str, AnalysisTypeRegistration]
    session_status_schema_mapping: Mapping[str, SessionStatusEntry]
    validation: ManifestValidationRules | None
    narrative_rules: ManifestNarrativeRules | None
    provider_compatibility: ProviderCompatibility | None

    # internally-built lookup indexes
    _by_name: Mapping[str, SchemaManifestEntry] = field(repr=False)
    _by_schema_id: Mapping[str, SchemaManifestEntry] = field(repr=False)
    _by_filename: Mapping[str, SchemaManifestEntry] = field(repr=False)
    _by_analysis_type: Mapping[str, SchemaManifestEntry] = field(repr=False)

    def get_schema(self, name: str, version: str) -> SchemaManifestEntry | None:
        for entry in self.schemas:
            if entry.name == name and entry.version == version:
                return entry
        return None

    def get_by_schema_id(self, schema_id: str) -> SchemaManifestEntry | None:
        return self._by_schema_id.get(schema_id)

    def get_by_analysis_type(self, analysis_type: str) -> SchemaManifestEntry | None:
        return self._by_analysis_type.get(analysis_type)

    def active_schemas(self) -> tuple[SchemaManifestEntry, ...]:
        return tuple(e for e in self.schemas if e.active)


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

ACCEPTED_STATUSES = frozenset({"ACTIVE", "INACTIVE", "DRAFT", "DEPRECATED"})

PRODUCTION_REQUIRED_STATUS = "ACTIVE"


def _raise(
    code: str,
    message: str,
    path: Path | None = None,
    location: str | None = None,
    details: Mapping[str, object] | None = None,
) -> ManifestValidationError:
    raise ManifestValidationError(
        code=code,
        message=message,
        path=path,
        location=location,
        details=details,
    )


def _check_path_escape(filename: str, package_root: Path) -> None:
    resolved = (package_root / filename).resolve()
    if not str(resolved).startswith(str(package_root.resolve())):
        raise ManifestValidationError(
            code=MANIFEST_PATH_ESCAPE,
            message=f"Schema file escapes package root: {filename}",
            path=package_root / filename,
        )


def _build_indexes(
    entries: tuple[SchemaManifestEntry, ...],
) -> dict[str, Any]:
    by_name: dict[str, SchemaManifestEntry] = {}
    by_id: dict[str, SchemaManifestEntry] = {}
    by_file: dict[str, SchemaManifestEntry] = {}
    by_at: dict[str, SchemaManifestEntry] = {}
    for entry in entries:
        by_name[entry.name] = entry
        by_id[entry.schema_id] = entry
        by_file[entry.file] = entry
        for at in entry.analysis_types:
            by_at[at] = entry
    return {
        "_by_name": by_name,
        "_by_schema_id": by_id,
        "_by_filename": by_file,
        "_by_analysis_type": by_at,
    }


def load_manifest(path: Path) -> ProductionManifest:
    """Load and validate a schema manifest from *path*."""
    if not path.exists():
        raise ManifestLoadError(
            code=MANIFEST_NOT_FOUND,
            message=f"Manifest file not found: {path}",
            path=path,
        )
    try:
        raw: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestLoadError(
            code=MANIFEST_INVALID_JSON,
            message=f"Invalid JSON in manifest: {exc.msg}",
            path=path,
            location=f"line {exc.lineno}, column {exc.colno}",
        ) from exc

    if not isinstance(raw, dict):
        raise ManifestValidationError(
            code=MANIFEST_INVALID_STRUCTURE,
            message="Manifest root must be a JSON object",
            path=path,
        )
    return _parse_manifest(raw, path)


def load_production_manifest(package_root: Path) -> ProductionManifest:
    """Load the production manifest from *package_root*/manifest.json."""
    manifest_path = package_root / "manifest.json"
    manifest = load_manifest(manifest_path)
    validate_manifest_files(manifest, package_root)
    return manifest


def validate_manifest_files(
    manifest: ProductionManifest,
    package_root: Path,
) -> None:
    """Validate that every registered schema file exists and is safe."""
    for entry in manifest.schemas:
        fn = entry.file
        _check_path_escape(fn, package_root)
        schema_path = (package_root / fn).resolve()
        if not schema_path.is_file():
            raise ManifestValidationError(
                code=MANIFEST_MISSING_SCHEMA_FILE,
                message=f"Registered schema file not found: {fn}",
                path=schema_path,
            )


# ---------------------------------------------------------------------------
# Internal parsing
# ---------------------------------------------------------------------------

_REQUIRED_ROOT_FIELDS = frozenset(
    {
        "manifest_name",
        "manifest_version",
        "schema_standard",
        "status",
        "base_uri",
        "schemas",
        "analysis_type_registry",
        "session_status_schema_mapping",
    }
)

_UNKNOWN_ROOT_FIELDS_ALLOWED = {  # fields that may appear but are not required
    "environment",
    "generated_at",
    "description",
    "default_language",
    "technical_language",
    "validation",
    "narrative_rules",
    "provider_compatibility",
    "canonical_state_rules",
    "context_rules",
    "narrative_rules",
    "storage_rules",
    "migration_rules",
    "experimental_schemas",
    "session_status_schema_mapping",
}


def _parse_manifest(raw: dict[str, object], path: Path) -> ProductionManifest:
    # Root required fields
    for req_field in _REQUIRED_ROOT_FIELDS:
        if req_field not in raw:
            _raise(
                code=MANIFEST_INVALID_STRUCTURE,
                message=f"Missing required root field: {req_field}",
                path=path,
            )

    status = str(raw.get("status", ""))
    if status not in ACCEPTED_STATUSES:
        raise ManifestValidationError(
            code=MANIFEST_UNSUPPORTED_STATUS,
            message=f"Unsupported manifest status: {status}",
            path=path,
        )

    # Parse schemas
    schemas_raw_obj = raw.get("schemas", [])
    if not isinstance(schemas_raw_obj, list):
        _raise(
            code=MANIFEST_INVALID_STRUCTURE,
            message="'schemas' must be an array",
            path=path,
        )
    schemas_raw: list[object] = schemas_raw_obj

    entries: list[SchemaManifestEntry] = []
    seen_names: dict[str, str] = {}
    seen_ids: dict[str, str] = {}
    seen_files: dict[str, str] = {}
    seen_name_version: dict[tuple[str, str], str] = {}

    for idx, entry_raw in enumerate(schemas_raw):
        if not isinstance(entry_raw, dict):
            _raise(
                code=MANIFEST_INVALID_STRUCTURE,
                location=f"schemas[{idx}]",
                message="Each schema entry must be a JSON object",
                path=path,
            )
        entry = _parse_schema_entry(entry_raw, f"schemas[{idx}]", path)

        # Duplicate checks
        if entry.name in seen_names:
            raise ManifestValidationError(
                code=MANIFEST_DUPLICATE_SCHEMA_NAME,
                message=f"Duplicate schema name: {entry.name}",
                details={
                    "name": entry.name,
                    "first_file": seen_names[entry.name],
                    "second_file": entry.file,
                },
                path=path,
            )
        seen_names[entry.name] = entry.file

        if entry.schema_id in seen_ids:
            raise ManifestValidationError(
                code=MANIFEST_DUPLICATE_SCHEMA_ID,
                message=f"Duplicate schema $id: {entry.schema_id}",
                details={
                    "schema_id": entry.schema_id,
                    "first_file": seen_ids[entry.schema_id],
                    "second_file": entry.file,
                },
                path=path,
            )
        seen_ids[entry.schema_id] = entry.file

        if entry.file in seen_files:
            raise ManifestValidationError(
                code=MANIFEST_DUPLICATE_FILENAME,
                message=f"Duplicate filename: {entry.file}",
                details={
                    "file": entry.file,
                    "first_name": seen_files[entry.file],
                    "second_name": entry.name,
                },
                path=path,
            )
        seen_files[entry.file] = entry.name

        nv_key = (entry.name, entry.version)
        if nv_key in seen_name_version:
            raise ManifestValidationError(
                code=MANIFEST_DUPLICATE_NAME_VERSION,
                message=f"Duplicate (name, version): {nv_key}",
                details={
                    "name": entry.name,
                    "version": entry.version,
                    "first_file": seen_name_version[nv_key],
                    "second_file": entry.file,
                },
                path=path,
            )
        seen_name_version[nv_key] = entry.file

        entries.append(entry)

    # Parse registries
    at_registry = _parse_analysis_type_registry(
        raw.get("analysis_type_registry", {}), path
    )
    ss_mapping = _parse_session_status_mapping(
        raw.get("session_status_schema_mapping", {}), path
    )

    # Validate required analysis mappings
    for atype in REQUIRED_ANALYSIS_TYPES:
        if atype not in at_registry:
            raise ManifestValidationError(
                code=MANIFEST_MISSING_ANALYSIS_MAPPING,
                message=f"Missing required analysis type: {atype}",
                details={"analysis_type": atype},
                path=path,
            )
        reg = at_registry[atype]
        expected_name = ANALYSIS_TYPE_INTERNAL_MAP.get(atype)
        if expected_name and reg.schema_name != expected_name:
            raise ManifestValidationError(
                code=MANIFEST_INVALID_ANALYSIS_MAPPING,
                message=f"Analysis type {atype} maps to wrong schema: {reg.schema_name}",
                details={
                    "analysis_type": atype,
                    "expected": expected_name,
                    "actual": reg.schema_name,
                },
                path=path,
            )

    # Validate session status mappings
    name_to_entry = {e.name: e for e in entries}
    for status_key, sse in ss_mapping.items():
        canonical = sse.canonical_schema
        if canonical not in name_to_entry:
            raise ManifestValidationError(
                code=MANIFEST_INVALID_SESSION_MAPPING,
                message=f"Session status {status_key} references unknown schema: {canonical}",
                details={"status": status_key, "schema": canonical},
                path=path,
            )
        for at in sse.allowed_analysis_types:
            if at not in at_registry:
                raise ManifestValidationError(
                    code=MANIFEST_INVALID_SESSION_MAPPING,
                    message=f"Session status {status_key} references unknown analysis type: {at}",
                    details={"status": status_key, "analysis_type": at},
                    path=path,
                )

    # Parse ancillary sections
    validation_rules = _parse_validation_rules(raw.get("validation"))
    narrative_rules = _parse_narrative_rules(raw.get("narrative_rules"))
    provider_comp = _parse_provider_compatibility(
        raw.get("provider_compatibility")
    )

    entries_tuple = tuple(entries)
    indexes = _build_indexes(entries_tuple)

    return ProductionManifest(
        manifest_name=str(raw.get("manifest_name", "")),
        manifest_version=str(raw.get("manifest_version", "")),
        schema_standard=str(raw.get("schema_standard", "")),
        environment=str(raw.get("environment", "")),
        status=status,
        base_uri=str(raw.get("base_uri", "")),
        default_language=str(raw.get("default_language", "id")),
        technical_language=str(raw.get("technical_language", "en")),
        description=str(raw.get("description", "")),
        schemas=entries_tuple,
        analysis_type_registry=at_registry,
        session_status_schema_mapping=ss_mapping,
        validation=validation_rules,
        narrative_rules=narrative_rules,
        provider_compatibility=provider_comp,
        **indexes,  # type: ignore[arg-type]
    )


def _parse_schema_entry(
    raw: dict[str, object], location: str, path: Path
) -> SchemaManifestEntry:
    r: dict[str, object] = raw
    name = str(r.get("name", ""))
    if not name:
        _raise(
            code=MANIFEST_INVALID_STRUCTURE,
            location=location,
            message="Schema entry missing 'name'",
            path=path,
        )
    file_val = str(r.get("file", ""))
    if not file_val:
        _raise(
            code=MANIFEST_INVALID_STRUCTURE,
            location=location,
            message="Schema entry missing 'file'",
            path=path,
        )
    sid = str(r.get("schema_id", ""))
    if not sid or not sid.startswith("http"):
        _raise(
            code=MANIFEST_INVALID_STRUCTURE,
            location=location,
            message=f"Schema entry missing or invalid 'schema_id': {sid}",
            path=path,
        )
    at_list: list[str] = []
    for v in (r.get("analysis_types") or []):
        if isinstance(v, str):
            at_list.append(v)
    dep_list: list[str] = []
    for v in (r.get("dependencies") or []):
        if isinstance(v, str):
            dep_list.append(v)
    used_by_list: list[str] = []
    for v in (r.get("used_by") or []):
        if isinstance(v, str):
            used_by_list.append(v)

    return SchemaManifestEntry(
        name=name,
        title=str(raw.get("title", "")),
        version=str(raw.get("version", "")),
        category=str(raw.get("category", "")),
        root_schema=bool(raw.get("root_schema", False)),
        active=bool(raw.get("active", True)),
        file=file_val,
        schema_id=sid,
        description=str(raw.get("description", "")),
        analysis_types=tuple(at_list),
        dependencies=tuple(dep_list),
        used_by=tuple(used_by_list),
    )


def _parse_analysis_type_registry(
    raw: object, path: Path
) -> dict[str, AnalysisTypeRegistration]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, AnalysisTypeRegistration] = {}
    raw_dict: dict[str, object] = raw
    for atype, entry_raw in raw_dict.items():
        if not isinstance(entry_raw, dict):
            continue
        entry_dict: dict[str, object] = entry_raw
        req_ev: list[str] = []
        for v in entry_dict.get("required_evidence", []):
            if isinstance(v, str):
                req_ev.append(v)
        opt_ev: list[str] = []
        for v in entry_dict.get("optional_evidence", []):
            if isinstance(v, str):
                opt_ev.append(v)
        result[atype] = AnalysisTypeRegistration(
            schema_name=str(entry_dict.get("schema", "")),
            schema_version=str(entry_dict.get("schema_version", "")),
            requires_position=bool(entry_dict.get("requires_position", False)),
            requires_previous_analysis=bool(
                entry_dict.get("requires_previous_analysis", False)
            ),
            requires_canonical_trade_state=bool(
                entry_dict.get("requires_canonical_trade_state", False)
            ),
            requires_user_confirmation_before_execution=bool(
                entry_dict.get("requires_user_confirmation_before_execution", False)
            ),
            required_evidence=tuple(req_ev),
            optional_evidence=tuple(opt_ev),
        )
    return result


def _parse_session_status_mapping(
    raw: object, path: Path
) -> dict[str, SessionStatusEntry]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, SessionStatusEntry] = {}
    raw_dict: dict[str, object] = raw
    for status_key, entry_raw in raw_dict.items():
        if not isinstance(entry_raw, dict):
            continue
        entry_dict: dict[str, object] = entry_raw
        at_list: list[str] = []
        for v in entry_dict.get("allowed_analysis_types", []):
            if isinstance(v, str):
                at_list.append(v)
        result[status_key] = SessionStatusEntry(
            allowed_analysis_types=tuple(at_list),
            canonical_schema=str(entry_dict.get("canonical_schema", "")),
        )
    return result


def _parse_validation_rules(raw: object) -> ManifestValidationRules | None:
    if not isinstance(raw, dict):
        return None
    d: dict[str, object] = raw
    dv: list[str] = []
    for v in d.get("domain_validators", []):
        if isinstance(v, str):
            dv.append(v)
    return ManifestValidationRules(
        json_schema_validation_required=bool(d.get("json_schema_validation_required", True)),
        domain_validation_required=bool(d.get("domain_validation_required", True)),
        validate_format_keywords=bool(d.get("validate_format_keywords", True)),
        reject_unknown_properties=bool(d.get("reject_unknown_properties", True)),
        reject_unknown_schema_versions=bool(d.get("reject_unknown_schema_versions", True)),
        reject_inactive_schemas=bool(d.get("reject_inactive_schemas", True)),
        reject_unregistered_schema_ids=bool(d.get("reject_unregistered_schema_ids", True)),
        domain_validators=tuple(dv),
    )


def _parse_narrative_rules(raw: object) -> ManifestNarrativeRules | None:
    if not isinstance(raw, dict):
        return None
    d: dict[str, object] = raw
    return ManifestNarrativeRules(
        user_facing_language=str(d.get("user_facing_language", "id")),
        technical_keys_language=str(d.get("technical_keys_language", "en")),
        enum_language=str(d.get("enum_language", "en")),
        probabilities_are_estimates_not_guarantees=bool(d.get("probabilities_are_estimates_not_guarantees", True)),
        confidence_is_not_probability=bool(d.get("confidence_is_not_probability", True)),
    )


def _parse_provider_compatibility(raw: object) -> ProviderCompatibility | None:
    if not isinstance(raw, dict):
        return None
    d: dict[str, object] = raw
    providers: list[str] = []
    for v in d.get("supported_providers", []):
        if isinstance(v, str):
            providers.append(v)
    return ProviderCompatibility(
        supported_providers=tuple(providers),
        structured_output_required=bool(d.get("structured_output_required", True)),
        fallback_must_preserve_schema=bool(d.get("fallback_must_preserve_schema", True)),
        additional_properties_allowed=bool(d.get("additional_properties_allowed", False)),
    )
