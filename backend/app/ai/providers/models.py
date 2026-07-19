"""Provider-independent request and response models (TP-0701)."""

from __future__ import annotations

import uuid
from copy import copy
from dataclasses import dataclass, field
from typing import Mapping

# ---------------------------------------------------------------------------
# ProviderImage
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderImage:
    """A single image to send to the provider."""

    evidence_id: uuid.UUID
    mime_type: str
    storage_reference: str
    byte_size: int
    width: int | None = None
    height: int | None = None


# ---------------------------------------------------------------------------
# ProviderUsage
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    """Token usage reported by the provider."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


# ---------------------------------------------------------------------------
# ProviderRequest
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """Normalised provider-independent request."""

    request_id: uuid.UUID
    analysis_type: str
    prompt_version: str
    user_prompt: str
    expected_schema_name: str
    expected_schema_version: str
    system_prompt: str | None = None
    images: tuple[ProviderImage, ...] = ()
    structured_output_schema: Mapping[str, object] | None = None
    timeout_seconds: int | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", copy(self.metadata))


# ---------------------------------------------------------------------------
# ProviderResponse
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """Normalised provider-independent response."""

    provider: str
    model: str
    raw_output: str
    request_id: uuid.UUID
    provider_response_id: str | None = None
    finish_reason: str | None = None
    usage: ProviderUsage | None = None
    latency_ms: int | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", copy(self.metadata))
