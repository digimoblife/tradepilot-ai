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
from app.ai.providers.router import (
    ProviderOrderEmptyError,
    ProviderRouteAttempt,
    ProviderRouter,
    ProviderRouterError,
    ProviderRoutingFailedError,
    ProviderRoutingResult,
    ProviderUnknownError,
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
    "ProviderOrderEmptyError",
    "ProviderRequest",
    "ProviderRequestInvalidError",
    "ProviderRouteAttempt",
    "ProviderRouter",
    "ProviderRouterError",
    "ProviderRoutingFailedError",
    "ProviderRoutingResult",
    "ProviderUnknownError",
    "ProviderUsage",
    "ensure_request_supported",
]
