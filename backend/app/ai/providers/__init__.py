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
from app.ai.providers.selection import (
    AnalysisProviderConfig,
    AnalysisProviderConfigurationError,
    build_analysis_provider_config,
    parse_provider_order,
    validate_analysis_provider_startup,
)

__all__ = [
    "AIProvider",
    "AIProviderError",
    "AnalysisProviderConfig",
    "AnalysisProviderConfigurationError",
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
    "ProviderResponse",
    "ProviderRouteAttempt",
    "ProviderRouter",
    "ProviderRouterError",
    "ProviderRoutingFailedError",
    "ProviderRoutingResult",
    "ProviderUnknownError",
    "ProviderUsage",
    "build_analysis_provider_config",
    "ensure_request_supported",
    "parse_provider_order",
    "validate_analysis_provider_startup",
]
