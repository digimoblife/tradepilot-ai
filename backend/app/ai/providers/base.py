"""Provider-independent AI adapter interface (TP-0701)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.providers.capabilities import ProviderCapabilities
from app.ai.providers.models import ProviderRequest, ProviderResponse


class AIProvider(ABC):
    """Abstract base for all AI provider adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. ``"gemini"``)."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model name (e.g. ``"gemini-3.5-flash"``)."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declared capabilities for this provider/model combination."""

    @abstractmethod
    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        """Send a request and return a normalised response.

        Parameters
        ----------
        request:
            Provider-independent request containing prompts, images,
            and structured-output schema.

        Returns
        -------
        ProviderResponse
            Normalised response with raw output retained exactly.

        Raises
        ------
        ProviderCapabilityUnsupportedError
            If the request exceeds declared capabilities.
        """
