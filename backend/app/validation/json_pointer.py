"""JSON Pointer utilities following RFC 6901."""

from __future__ import annotations

ROOT_POINTER = ""


def escape_token(token: str) -> str:
    """Escape a single path token per RFC 6901 (``~`` then ``/``)."""
    return token.replace("~", "~0").replace("/", "~1")


def build_json_pointer(parts: list[str | int]) -> str:
    """Construct an RFC 6901 JSON Pointer from path segments.

    >>> build_json_pointer([])
    ''
    >>> build_json_pointer(["a"])
    '/a'
    >>> build_json_pointer(["a/b"])
    '/a~1b'
    >>> build_json_pointer(["items", 0, "price"])
    '/items/0/price'
    """
    if not parts:
        return ROOT_POINTER
    segments: list[str] = []
    for part in parts:
        if isinstance(part, int):
            segments.append(str(part))
        else:
            segments.append(escape_token(part))
    return "/" + "/".join(segments)


def append_json_pointer(pointer: str, token: str | int) -> str:
    """Append a path segment to an existing pointer."""
    if pointer == ROOT_POINTER:
        if isinstance(token, int):
            return f"/{token}"
        return f"/{escape_token(token)}"
    if isinstance(token, int):
        return f"{pointer}/{token}"
    return f"{pointer}/{escape_token(token)}"


def parse_json_pointer(pointer: str) -> list[str]:
    """Parse an RFC 6901 JSON Pointer into path tokens."""
    if not pointer or pointer == ROOT_POINTER:
        return []
    tokens: list[str] = []
    for token in pointer.lstrip("/").split("/"):
        tokens.append(token.replace("~1", "/").replace("~0", "~"))
    return tokens
