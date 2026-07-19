"""Provider-independent AI adapter interfaces and contracts."""

from app.ai.providers.base import AIProvider
from app.ai.providers.capabilities import (
    ProviderCapabilities,
    ensure_request_supported,
)
from app.ai.providers.deepseek import (
    DeepSeekAuthenticationError,
    DeepSeekConfigurationError,
    DeepSeekError,
    DeepSeekInvalidResponseError,
    DeepSeekProvider,
    DeepSeekRateLimitedError,
    DeepSeekRefusedError,
    DeepSeekRequestFailedError,
    DeepSeekTimeoutError,
)
from app.ai.providers.errors import (
    AIProviderError,
    ProviderCapabilityUnsupportedError,
    ProviderRequestInvalidError,
)
from app.ai.providers.gemini import (
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiError,
    GeminiInvalidResponseError,
    GeminiProvider,
    GeminiRateLimitedError,
    GeminiRefusedError,
    GeminiRequestFailedError,
    GeminiTimeoutError,
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
    "DeepSeekAuthenticationError",
    "DeepSeekConfigurationError",
    "DeepSeekError",
    "DeepSeekInvalidResponseError",
    "DeepSeekProvider",
    "DeepSeekRateLimitedError",
    "DeepSeekRefusedError",
    "DeepSeekRequestFailedError",
    "DeepSeekTimeoutError",
    "GeminiAuthenticationError",
    "GeminiConfigurationError",
    "GeminiError",
    "GeminiInvalidResponseError",
    "GeminiProvider",
    "GeminiRateLimitedError",
    "GeminiRefusedError",
    "GeminiRequestFailedError",
    "GeminiTimeoutError",
    "ProviderCapabilities",
    "ProviderCapabilityUnsupportedError",
    "ProviderImage",
    "ProviderRequest",
    "ProviderRequestInvalidError",
    "ProviderResponse",
    "ProviderUsage",
    "ensure_request_supported",
]
