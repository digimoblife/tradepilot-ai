"""Offline `$ref` resolver for the TradePilot AI production schema package."""

from __future__ import annotations

from typing import Mapping

from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from app.schemas.errors import SchemaRegistryError


def build_offline_registry(
    documents: Mapping[str, dict[str, object]],
    *,
    base_uri: str | None = None,
) -> Registry:
    """Build an offline ``referencing.Registry`` from pre-loaded schema documents.

    Parameters
    ----------
    documents:
        A mapping from schema ``$id`` to parsed JSON document.
    base_uri:
        Optional base URI for error diagnostics.

    Returns
    -------
    A ``referencing.Registry`` with all documents registered as Draft 2020-12
    resources.  The retrieval callback will refuse to fetch unknown URIs.
    """
    resources: dict[str, Resource] = {}
    for sid, document in documents.items():
        resources[sid] = Resource(contents=document, specification=DRAFT202012)

    def _retrieve(uri: str) -> Resource:
        resource = resources.get(uri)
        if resource is not None:
            return resource
        raise SchemaRegistryError(
            code="SCHEMA_REFERENCE_UNRESOLVED",
            message=f"Cannot resolve $ref URI: {uri}",
            details={"reference_uri": uri, "base_uri": base_uri},
        )

    return Registry(retrieve=_retrieve)


def check_fragment(resource: Resource, fragment: str) -> bool:
    """Return ``True`` if *fragment* (a JSON Pointer) exists in *resource*."""
    try:
        resource.contents[fragment]
        return True
    except (LookupError, TypeError, KeyError, IndexError):
        return False


def resolve_fragment(schema: object, fragment: str) -> object | None:
    """Resolve *fragment* (JSON Pointer) against a schema document.

    Returns the pointed-to value, or ``None`` if the fragment cannot be
    resolved.
    """
    if not fragment or fragment == "#":
        return schema
    pointer = fragment.lstrip("#/")
    if not pointer:
        return schema
    parts = _parse_json_pointer(pointer)
    current: object = schema
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)  # type: ignore[arg-type]
        elif isinstance(current, list):
            try:
                idx = int(part)
                current = current[idx]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def _parse_json_pointer(pointer: str) -> list[str]:
    """Parse a JSON Pointer string into a list of path segments.

    Handles ``~0`` (tilde) and ``~1`` (forward slash) escaping per RFC 6901.
    """
    parts: list[str] = []
    for token in pointer.split("/"):
        if token == pointer and not pointer.startswith("/"):
            # Single-segment pointer without leading /
            parts.append(_unescape(token))
        else:
            if token:
                parts.append(_unescape(token))
    return parts


def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")
