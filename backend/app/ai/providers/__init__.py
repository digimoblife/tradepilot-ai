"""Provider-independent AI adapter interfaces and contracts."""

from app.ai.providers.base import AIProvider
from app.ai.providers.capabilities import (
    ProviderCapabilities,
    ensure_request_supported,
)
from app.ai.providers.errors import (
    AIProviderError,
    ProviderCapabilityUnsupportedError,
    ProviderRequestInvalidError,
)
from app.ai.providers.models import (
    ProviderImage,
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)

__all__ = [
    "AIProvider",
    "AIProviderError",
    "ProviderCapabilities",
    "ProviderCapabilityUnsupportedError",
    "ProviderImage",
    "ProviderRequest",
    "ProviderRequestInvalidError",
    "ProviderResponse",
    "ProviderUsage",
    "ensure_request_supported",
]
