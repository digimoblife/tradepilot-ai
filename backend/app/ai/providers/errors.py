"""Stable contract-level errors for the AI provider layer."""

from __future__ import annotations


class AIProviderError(Exception):
    """Base for all AI provider-layer errors."""

    code: str = "AI_PROVIDER_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class ProviderCapabilityUnsupportedError(AIProviderError):
    """Raised when a request exceeds the provider's declared capabilities."""

    code: str = "PROVIDER_CAPABILITY_UNSUPPORTED"


class ProviderRequestInvalidError(AIProviderError):
    """Raised when a request is structurally invalid."""

    code: str = "PROVIDER_REQUEST_INVALID"
