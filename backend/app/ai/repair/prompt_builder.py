"""Repair prompt builder (TP-0706).

Constructs a deterministic repair prompt from validation errors,
canonical facts, and schema identity.
"""

from __future__ import annotations

import json
from typing import Mapping, Sequence

from app.validation import ValidationIssue


class RepairPromptBuilder:
    """Builds a repair prompt instructing the provider to fix its output."""

    def build(
        self,
        *,
        original_raw_output: str,
        validation_errors: Sequence[ValidationIssue],
        canonical_facts: Mapping[str, object],
        expected_schema_name: str,
        expected_schema_version: str,
    ) -> str:
        errors_json = _serialize_issues(validation_errors)
        facts_json = json.dumps(dict(canonical_facts), indent=2, ensure_ascii=False)

        return (
            "You previously responded to a TradePilot AI analysis request. "
            "Your response failed validation. Please correct it.\n\n"
            "--- ORIGINAL OUTPUT ---\n"
            f"{original_raw_output}\n"
            "--- END ORIGINAL OUTPUT ---\n\n"
            "--- VALIDATION ERRORS ---\n"
            f"{errors_json}\n"
            "--- END VALIDATION ERRORS ---\n\n"
            "--- CANONICAL FACTS (DO NOT CHANGE) ---\n"
            f"{facts_json}\n"
            "--- END CANONICAL FACTS ---\n\n"
            "RULES:\n"
            "1. The canonical facts listed above are authoritative. "
            "Do not change any canonical value.\n"
            "2. Correct the specific issues listed in VALIDATION ERRORS.\n"
            "3. AI proposals and estimates may be corrected where they "
            "conflict with canonical facts or validation rules.\n"
            "4. Return exactly one valid JSON object matching the "
            f"'{expected_schema_name}' schema (version {expected_schema_version}).\n"
            "5. Do not include Markdown fences or code blocks.\n"
            "6. Do not include any commentary or explanation.\n"
            "7. Do not return a JSON array. Return exactly one JSON object.\n"
            "8. Do not fabricate values that are unavailable."  # noqa: E501
        )


def _serialize_issues(issues: Sequence[ValidationIssue]) -> str:
    """Serialize validation issues to a deterministic JSON array string."""
    items: list[dict[str, str]] = []
    for issue in issues:
        items.append(
            {
                "code": issue.code,
                "path": issue.path,
                "message": issue.message,
                "category": issue.category.value,
            }
        )
    return json.dumps(items, indent=2, ensure_ascii=False)
