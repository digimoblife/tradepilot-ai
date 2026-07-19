"""Prompt definition and rendered-prompt models (TP-0702)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptDefinition:
    """Immutable prompt definition loaded from version-controlled files."""

    analysis_type: str
    prompt_version: str
    system_prompt: str
    user_prompt_template: str
    expected_schema_name: str
    expected_schema_version: str
    requires_images: bool = False
    required_evidence_types: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    """Result of rendering a prompt definition with concrete variables."""

    analysis_type: str
    prompt_version: str
    system_prompt: str
    user_prompt: str
    expected_schema_name: str
    expected_schema_version: str
