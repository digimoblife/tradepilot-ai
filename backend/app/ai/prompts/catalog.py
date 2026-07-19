"""Prompt file catalog loader (TP-0702).

Reads prompt definition files from a version-controlled directory
and returns ``CatalogEntry`` objects for the registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ai.prompts.models import PromptDefinition

# ---------------------------------------------------------------------------
# Catalog entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    analysis_type: str
    prompt_version: str
    definition: PromptDefinition


# ---------------------------------------------------------------------------
# Schema-name / analysis-type mapping (derived from production manifest)
# ---------------------------------------------------------------------------

_ANALYSIS_TYPE_SCHEMA: dict[str, tuple[str, str]] = {
    "INITIAL_ANALYSIS": ("initial_analysis", "1.0.0"),
    "OPEN_POSITION_UPDATE": ("open_position_update", "1.0.0"),
}

# Required evidence metadata for each analysis type
_REQUIRED_EVIDENCE: dict[str, tuple[str, ...]] = {
    "INITIAL_ANALYSIS": (
        "ORDERBOOK_SCREENSHOT",
        "CHART_THREE_MONTH",
        "CHART_SIX_MONTH",
    ),
    "OPEN_POSITION_UPDATE": (),
}

# Whether the analysis type requires image evidence
_REQUIRES_IMAGES: dict[str, bool] = {
    "INITIAL_ANALYSIS": True,
    "OPEN_POSITION_UPDATE": True,
}

# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_catalog(prompts_root: Path) -> list[CatalogEntry]:
    """Scan *prompts_root* for prompt files and return catalog entries.

    File naming convention::

        prompts/production/v1/
            {analysis_type_lower}.system.md
            {analysis_type_lower}.user.md
    """
    entries: list[CatalogEntry] = []
    for analysis_type, (schema_name, schema_version) in _ANALYSIS_TYPE_SCHEMA.items():
        key = _analysis_type_to_file_key(analysis_type)

        system_path = prompts_root / f"{key}.system.md"
        user_path = prompts_root / f"{key}.user.md"

        if not system_path.is_file():
            raise FileNotFoundError(
                f"Prompt file not found: {system_path}",
            )
        if not user_path.is_file():
            raise FileNotFoundError(
                f"Prompt file not found: {user_path}",
            )

        system_prompt = system_path.read_text(encoding="utf-8")
        user_template = user_path.read_text(encoding="utf-8")

        definition = PromptDefinition(
            analysis_type=analysis_type,
            prompt_version="1.0.0",
            system_prompt=system_prompt,
            user_prompt_template=user_template,
            expected_schema_name=schema_name,
            expected_schema_version=schema_version,
            requires_images=_REQUIRES_IMAGES.get(analysis_type, False),
            required_evidence_types=_REQUIRED_EVIDENCE.get(analysis_type, ()),
        )

        entries.append(
            CatalogEntry(
                analysis_type=analysis_type,
                prompt_version="1.0.0",
                definition=definition,
            ),
        )
    return entries


def _analysis_type_to_file_key(analysis_type: str) -> str:
    return analysis_type.lower()
