"""Deterministic prompt registry (TP-0702).

Resolves prompt definitions by analysis type and version,
validates schema references, and renders user-prompt templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from app.ai.prompts.catalog import load_catalog
from app.ai.prompts.models import PromptDefinition, RenderedPrompt

# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class PromptRegistryError(Exception):
    """Base for prompt registry errors."""

    code: str = "PROMPT_REGISTRY_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class PromptNotFoundError(PromptRegistryError):
    code: str = "PROMPT_NOT_FOUND"


class PromptVersionNotFoundError(PromptRegistryError):
    code: str = "PROMPT_VERSION_NOT_FOUND"


class PromptDuplicateRegistrationError(PromptRegistryError):
    code: str = "PROMPT_DUPLICATE_REGISTRATION"


class PromptTemplateVariableMissingError(PromptRegistryError):
    code: str = "PROMPT_TEMPLATE_VARIABLE_MISSING"


class PromptSchemaReferenceInvalidError(PromptRegistryError):
    code: str = "PROMPT_SCHEMA_REFERENCE_INVALID"


# ---------------------------------------------------------------------------
# Default version constant
# ---------------------------------------------------------------------------

_DEFAULT_PROMPT_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class PromptRegistry:
    """Deterministic versioned prompt registry.

    Loads prompt definitions from version-controlled files at
    initialisation and provides analysis-type and version lookups
    together with template rendering.
    """

    def __init__(self, prompts_root: Path) -> None:
        self._definitions: dict[str, dict[str, PromptDefinition]] = {}
        self._load(prompts_root)

    # ------------------------------------------------------------------
    # Public lookup
    # ------------------------------------------------------------------

    def get(
        self,
        *,
        analysis_type: str,
        prompt_version: str | None = None,
    ) -> PromptDefinition:
        version = prompt_version or _DEFAULT_PROMPT_VERSION
        by_type = self._definitions.get(analysis_type)
        if by_type is None:
            raise PromptNotFoundError(
                message=f"No prompts registered for analysis type {analysis_type!r}",
            )
        definition = by_type.get(version)
        if definition is None:
            raise PromptVersionNotFoundError(
                message=(f"No prompt version {version!r} for analysis type {analysis_type!r}"),
            )
        return definition

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(
        self,
        *,
        analysis_type: str,
        prompt_version: str | None = None,
        variables: Mapping[str, str],
    ) -> RenderedPrompt:
        definition = self.get(
            analysis_type=analysis_type,
            prompt_version=prompt_version,
        )

        try:
            user_prompt = definition.user_prompt_template.format(**variables)
        except KeyError as exc:
            raise PromptTemplateVariableMissingError(
                message=f"Missing required template variable: {exc}",
            ) from exc

        return RenderedPrompt(
            analysis_type=definition.analysis_type,
            prompt_version=definition.prompt_version,
            system_prompt=definition.system_prompt,
            user_prompt=user_prompt,
            expected_schema_name=definition.expected_schema_name,
            expected_schema_version=definition.expected_schema_version,
        )

    # ------------------------------------------------------------------
    # Internal loading
    # ------------------------------------------------------------------

    def _load(self, prompts_root: Path) -> None:
        catalog = load_catalog(prompts_root)

        for entry in catalog:
            by_type = self._definitions.setdefault(entry.analysis_type, {})
            if entry.prompt_version in by_type:
                raise PromptDuplicateRegistrationError(
                    message=(
                        f"Duplicate prompt registration: "
                        f"{entry.analysis_type} {entry.prompt_version}"
                    ),
                )
            by_type[entry.prompt_version] = entry.definition
