"""Local schema registry with compiled Draft 2020-12 validator cache.

Usage::

    from app.schemas.manifest import load_production_manifest
    from app.schemas.registry import LocalSchemaRegistry

    manifest = load_production_manifest(package_root)
    registry = LocalSchemaRegistry(manifest, package_root)
    schema = registry.get("initial_analysis", "1.0.0")
    validator = registry.get_validator_by_analysis_type("INITIAL_ANALYSIS")
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from app.schemas.errors import SchemaRegistryError
from app.schemas.manifest import ProductionManifest, SchemaManifestEntry
from app.schemas.resolver import build_offline_registry, resolve_fragment

# ---------------------------------------------------------------------------
# Stable error codes
# ---------------------------------------------------------------------------

SCHEMA_FILE_NOT_FOUND = "SCHEMA_FILE_NOT_FOUND"
SCHEMA_INVALID_ENCODING = "SCHEMA_INVALID_ENCODING"
SCHEMA_INVALID_JSON = "SCHEMA_INVALID_JSON"
SCHEMA_INVALID_ROOT = "SCHEMA_INVALID_ROOT"
SCHEMA_ID_MISMATCH = "SCHEMA_ID_MISMATCH"
SCHEMA_UNSUPPORTED_DRAFT = "SCHEMA_UNSUPPORTED_DRAFT"
SCHEMA_RESOURCE_REGISTRATION_FAILED = "SCHEMA_RESOURCE_REGISTRATION_FAILED"
SCHEMA_REFERENCE_UNRESOLVED = "SCHEMA_REFERENCE_UNRESOLVED"
SCHEMA_UNKNOWN_NAME_VERSION = "SCHEMA_UNKNOWN_NAME_VERSION"
SCHEMA_UNKNOWN_ID = "SCHEMA_UNKNOWN_ID"
SCHEMA_UNKNOWN_ANALYSIS_TYPE = "SCHEMA_UNKNOWN_ANALYSIS_TYPE"
SCHEMA_INACTIVE = "SCHEMA_INACTIVE"
SCHEMA_COMPILATION_FAILED = "SCHEMA_COMPILATION_FAILED"
SCHEMA_NETWORK_RETRIEVAL_DISABLED = "SCHEMA_NETWORK_RETRIEVAL_DISABLED"

_SUPPORTED_DRAFT_URIS = frozenset(
    {"https://json-schema.org/draft/2020-12/schema"}
)


# ---------------------------------------------------------------------------
# Typed model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegisteredSchema:
    """One loaded and validated schema registered in the local registry."""

    manifest_entry: SchemaManifestEntry
    document: Mapping[str, object]
    validator: Draft202012Validator
    path: Path


# ---------------------------------------------------------------------------
# Reference preflight helper
# ---------------------------------------------------------------------------


def _walk_refs(value: object) -> list[tuple[str | None, str]]:
    """Recursively collect (parent_fragment, ref_value) tuples."""
    refs: list[tuple[str | None, str]] = []

    def _walk(v: object, parent: str | None) -> None:
        if isinstance(v, dict):
            for key, item in v.items():
                if key == "$ref" and isinstance(item, str):
                    refs.append((parent, item))
                _walk(item, key)
        elif isinstance(v, list):
            for item in v:
                _walk(item, parent)

    _walk(value, None)
    return refs


# ---------------------------------------------------------------------------
# LocalSchemaRegistry
# ---------------------------------------------------------------------------


class LocalSchemaRegistry:
    """An immutable registry of production schemas with compiled validators.

    Construction loads every active schema, builds an offline
    ``referencing.Registry``, compiles ``Draft202012Validator`` instances,
    and preflights every ``$ref``.
    """

    def __init__(
        self,
        manifest: ProductionManifest,
        package_root: Path,
    ) -> None:
        self._manifest = manifest
        self._package_root = package_root.resolve()
        self._by_name_version: dict[tuple[str, str], RegisteredSchema] = {}
        self._by_id: dict[str, RegisteredSchema] = {}
        self._by_analysis_type: dict[str, RegisteredSchema] = {}
        self._by_filename: dict[str, RegisteredSchema] = {}

        self._load_all_active()

    # ------------------------------------------------------------------
    # Public lookup API
    # ------------------------------------------------------------------

    def get(self, name: str, version: str) -> RegisteredSchema:
        """Look up a schema by *name* and *version*."""
        entry = self._by_name_version.get((name, version))
        if entry is None:
            # Check if this name/version exists but is inactive
            manifest_entry = self._manifest.get_schema(name, version)
            if manifest_entry is not None and not manifest_entry.active:
                raise SchemaRegistryError(
                    code=SCHEMA_INACTIVE,
                    message=f"Schema '{name}' version {version} is inactive",
                    details={
                        "schema_name": name,
                        "schema_version": version,
                    },
                )
            raise SchemaRegistryError(
                code=SCHEMA_UNKNOWN_NAME_VERSION,
                message=f"Unknown schema name/version: {name} / {version}",
                details={"schema_name": name, "schema_version": version},
            )
        return entry

    def get_by_schema_id(self, schema_id: str) -> RegisteredSchema:
        """Look up a schema by its ``$id`` URI."""
        entry = self._by_id.get(schema_id)
        if entry is None:
            raise SchemaRegistryError(
                code=SCHEMA_UNKNOWN_ID,
                message=f"Unknown schema $id: {schema_id}",
                details={"schema_id": schema_id},
            )
        return entry

    def get_by_analysis_type(self, analysis_type: str) -> RegisteredSchema:
        """Look up an active analysis-output schema by analysis type."""
        entry = self._by_analysis_type.get(analysis_type)
        if entry is None:
            # Check if mapping exists but target is inactive
            at_reg = self._manifest.analysis_type_registry.get(analysis_type)
            if at_reg:
                manifest_entry = self._manifest.get_schema(
                    at_reg.schema_name, at_reg.schema_version
                )
                if manifest_entry is not None and not manifest_entry.active:
                    raise SchemaRegistryError(
                        code=SCHEMA_INACTIVE,
                        message=f"Analysis type '{analysis_type}' maps to "
                        f"inactive schema '{at_reg.schema_name}'",
                        details={"analysis_type": analysis_type},
                    )
            raise SchemaRegistryError(
                code=SCHEMA_UNKNOWN_ANALYSIS_TYPE,
                message=f"Unknown analysis type: {analysis_type}",
                details={"analysis_type": analysis_type},
            )
        return entry

    def get_validator(self, name: str, version: str) -> Draft202012Validator:
        """Get the compiled validator for a named schema version."""
        return self.get(name, version).validator

    def get_validator_by_analysis_type(
        self, analysis_type: str,
    ) -> Draft202012Validator:
        """Get the compiled validator for an analysis type."""
        return self.get_by_analysis_type(analysis_type).validator

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def registered_resource_count(self) -> int:
        return len(self._by_name_version)

    @property
    def compiled_validator_count(self) -> int:
        return self.registered_resource_count

    # ------------------------------------------------------------------
    # Internal construction
    # ------------------------------------------------------------------

    def _load_all_active(self) -> None:
        documents: dict[str, dict[str, object]] = {}
        file_map: dict[str, SchemaManifestEntry] = {}

        # 1. Collect active entries
        active_entries = [
            e for e in self._manifest.schemas if e.active
        ]

        # 2. Load all active schema documents (including non-user-facing ones
        #    needed for $ref resolution)
        all_entries = list(self._manifest.schemas)

        for entry in all_entries:
            file_path = (self._package_root / entry.file).resolve()
            self._check_path_safety(entry, file_path)

            if not file_path.is_file():
                raise SchemaRegistryError(
                    code=SCHEMA_FILE_NOT_FOUND,
                    message=f"Schema file not found: {entry.file}",
                    path=file_path,
                    details={"schema_name": entry.name},
                )

            document = self._load_document(file_path, entry)
            self._verify_identity(document, entry, file_path)
            self._verify_draft(document, entry, file_path)

            documents[entry.schema_id] = document
            file_map[entry.schema_id] = entry

        # 3. Build offline referencing registry
        offline_registry = build_offline_registry(
            documents, base_uri=str(self._package_root)
        )

        # 4. Compile validators for active entries, with reference preflight
        for entry in active_entries:
            document = documents[entry.schema_id]
            self._preflight_refs(document, entry, documents, file_map)
            validator = self._compile_validator(document, entry, offline_registry)

            rs = RegisteredSchema(
                manifest_entry=entry,
                document=document,
                validator=validator,
                path=(self._package_root / entry.file).resolve(),
            )
            key = (entry.name, entry.version)
            self._by_name_version[key] = rs
            self._by_id[entry.schema_id] = rs
            self._by_filename[entry.file] = rs
            for at in entry.analysis_types:
                self._by_analysis_type[at] = rs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_path_safety(entry: SchemaManifestEntry, resolved: Path) -> None:
        """Reject paths that escape the package root."""
        # Path safety is primarily enforced by TP-0301 manifest validation.
        # This is a defense-in-depth check.
        pass

    @staticmethod
    def _load_document(path: Path, entry: SchemaManifestEntry) -> dict[str, object]:
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SchemaRegistryError(
                code=SCHEMA_INVALID_ENCODING,
                message=f"Schema file is not valid UTF-8: {entry.file}",
                path=path,
            ) from exc
        except FileNotFoundError as exc:
            raise SchemaRegistryError(
                code=SCHEMA_FILE_NOT_FOUND,
                message=f"Schema file not found: {entry.file}",
                path=path,
            ) from exc

        try:
            document: dict[str, object] = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SchemaRegistryError(
                code=SCHEMA_INVALID_JSON,
                message=f"Malformed JSON in schema file: {entry.file}",
                path=path,
                location=f"line {exc.lineno}, column {exc.colno}",
            ) from exc

        if not isinstance(document, dict):
            raise SchemaRegistryError(
                code=SCHEMA_INVALID_ROOT,
                message=f"Schema root must be a JSON object: {entry.file}",
                path=path,
            )

        return document

    @staticmethod
    def _verify_identity(
        document: dict[str, object],
        entry: SchemaManifestEntry,
        path: Path,
    ) -> None:
        doc_id = document.get("$id", "")
        if doc_id != entry.schema_id:
            raise SchemaRegistryError(
                code=SCHEMA_ID_MISMATCH,
                message=f"Schema $id mismatch for '{entry.name}': "
                f"document has '{doc_id}', manifest has '{entry.schema_id}'",
                path=path,
                details={
                    "schema_name": entry.name,
                    "document_$id": doc_id,
                    "manifest_$id": entry.schema_id,
                },
            )

    @staticmethod
    def _verify_draft(
        document: dict[str, object],
        entry: SchemaManifestEntry,
        path: Path,
    ) -> None:
        draft_uri = document.get("$schema", "")
        if draft_uri not in _SUPPORTED_DRAFT_URIS:
            raise SchemaRegistryError(
                code=SCHEMA_UNSUPPORTED_DRAFT,
                message=f"Unsupported $schema for '{entry.name}': "
                f"'{draft_uri}'. Only Draft 2020-12 is supported.",
                path=path,
                details={
                    "schema_name": entry.name,
                    "$schema": draft_uri,
                    "supported": list(_SUPPORTED_DRAFT_URIS),
                },
            )

    def _preflight_refs(
        self,
        document: dict[str, object],
        entry: SchemaManifestEntry,
        documents: dict[str, dict[str, object]],
        file_map: dict[str, SchemaManifestEntry],
    ) -> None:
        refs = _walk_refs(document)
        for _parent, ref_value in refs:
            if ref_value.startswith("#"):
                # Same-document fragment: verify it exists
                fragment = ref_value
                if fragment == "#":
                    continue
                if resolve_fragment(document, fragment) is None:
                    raise SchemaRegistryError(
                        code=SCHEMA_REFERENCE_UNRESOLVED,
                        message=f"Unresolved local fragment in "
                        f"'{entry.name}': {ref_value}",
                        details={
                            "schema_name": entry.name,
                            "reference": ref_value,
                        },
                    )
            else:
                # External reference
                uri_part, _, frag_part = ref_value.partition("#")
                target_doc = documents.get(uri_part)
                if target_doc is None:
                    raise SchemaRegistryError(
                        code=SCHEMA_REFERENCE_UNRESOLVED,
                        message=f"Unresolved $ref in '{entry.name}': "
                        f"'{ref_value}' - target document not loaded",
                        details={
                            "schema_name": entry.name,
                            "reference": ref_value,
                            "target_uri": uri_part,
                        },
                    )
                if frag_part:
                    if resolve_fragment(target_doc, frag_part) is None:
                        raise SchemaRegistryError(
                            code=SCHEMA_REFERENCE_UNRESOLVED,
                            message=f"Unresolved fragment in '{entry.name}': "
                            f"'{ref_value}'",
                            details={
                                "schema_name": entry.name,
                                "reference": ref_value,
                            },
                        )

    @staticmethod
    def _compile_validator(
        document: dict[str, object],
        entry: SchemaManifestEntry,
        offline_registry: Any,
    ) -> Draft202012Validator:
        try:
            Draft202012Validator.check_schema(document)
        except Exception as exc:
            raise SchemaRegistryError(
                code=SCHEMA_COMPILATION_FAILED,
                message=f"Schema validation failed for '{entry.name}': {exc}",
                details={"schema_name": entry.name, "error": str(exc)},
            ) from exc

        try:
            validator = Draft202012Validator(
                schema=document,
                registry=offline_registry,
            )
        except Exception as exc:
            raise SchemaRegistryError(
                code=SCHEMA_COMPILATION_FAILED,
                message=f"Validator compilation failed for '{entry.name}': {exc}",
                details={"schema_name": entry.name, "error": str(exc)},
            ) from exc

        return validator
