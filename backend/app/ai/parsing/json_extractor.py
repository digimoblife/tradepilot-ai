"""JSON object extractor (TP-0705).

Finds exactly one root-level JSON object inside raw provider output,
handling Markdown fences and leading/trailing commentary.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class ExtractionError(Exception):
    """Base for all extraction errors."""

    code: str = "JSON_EXTRACTION_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class ExtractionEmptyError(ExtractionError):
    code: str = "JSON_EXTRACTION_EMPTY"


class ExtractionObjectNotFoundError(ExtractionError):
    code: str = "JSON_OBJECT_NOT_FOUND"


class ExtractionMultipleObjectsError(ExtractionError):
    code: str = "JSON_MULTIPLE_OBJECTS"


class ExtractionRootNotObjectError(ExtractionError):
    code: str = "JSON_ROOT_NOT_OBJECT"


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


def extract_json_object(raw_output: str) -> str:
    """Extract exactly one root-level JSON object from *raw_output*.

    Handles Markdown fences, leading/trailing commentary, braces inside
    strings, and escaped quotes/backslashes.
    """
    if not raw_output or not raw_output.strip():
        raise ExtractionEmptyError(message="Raw output is empty")

    text = raw_output.strip()

    # Remove Markdown fences
    text = _remove_fences(text)

    if not text:
        raise ExtractionObjectNotFoundError(
            message="No content found after removing Markdown fences",
        )

    # Find all top-level brace-enclosed regions
    candidates = _find_top_level_objects(text)

    if len(candidates) == 0:
        raise ExtractionObjectNotFoundError(
            message="No JSON object found in output",
        )

    if len(candidates) > 1:
        raise ExtractionMultipleObjectsError(
            message=f"Found {len(candidates)} JSON objects, expected exactly one",
        )

    return text[candidates[0][0] : candidates[0][1]]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _remove_fences(text: str) -> str:
    """Strip one pair of Markdown code fences if present."""
    lines = text.splitlines()

    # Check for opening fence
    first_non_empty = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            first_non_empty = i
            break

    if first_non_empty is None:
        return text

    first_line = lines[first_non_empty].strip()
    if first_line.startswith("```"):
        # Find closing fence
        fence_prefix = "```"
        for j in range(first_non_empty + 1, len(lines)):
            if lines[j].strip() == fence_prefix:
                # Found closing fence
                content_lines = lines[first_non_empty + 1 : j]
                # Collect content until closing fence
                result = "\n".join(content_lines).strip()
                # Check for content after closing fence
                after_lines = lines[j + 1 :]
                after_text = "\n".join(after_lines).strip()
                if after_text:
                    result = result + "\n" + after_text
                return result

    return text


def _find_top_level_objects(text: str) -> list[tuple[int, int]]:
    """Find all top-level JSON objects (``{...}``) in *text*.

    Returns list of ``(start, end)`` exclusive-end positions.
    Handles strings, escaped quotes, and escaped backslashes.
    """
    candidates: list[tuple[int, int]] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "{":
            end = _match_brace(text, i)
            if end is not None:
                # Check if this is a root-level object (not inside another object)
                is_root = True
                for start, end_pos in candidates:
                    if i > start and i < end_pos:
                        is_root = False
                        break
                if is_root:
                    # Also check depth: count unclosed braces before this position
                    depth = 0
                    for j in range(i):
                        c = text[j]
                        if c == "{":
                            depth += 1
                        elif c == "}":
                            depth -= 1
                    # If depth > 0, we're inside another object already found
                    if depth == 0:
                        candidates.append((i, end + 1))
                i = end + 1
                continue
        i += 1
    return candidates


def _match_brace(text: str, start: int) -> int | None:
    """Return the index of the ``}`` matching ``{`` at *start*.

    Handles string literals, escaped quotes, and escaped backslashes.
    Returns ``None`` if unmatched.
    """
    depth = 0
    i = start
    in_string = False
    escape = False

    while i < len(text):
        ch = text[i]

        if escape:
            escape = False
            i += 1
            continue

        if ch == "\\" and in_string:
            escape = True
            i += 1
            continue

        if ch == '"':
            in_string = not in_string
            i += 1
            continue

        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i

        i += 1

    return None
