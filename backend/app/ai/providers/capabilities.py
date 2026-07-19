"""Provider capability model and contract validation (TP-0701)."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.providers.errors import ProviderCapabilityUnsupportedError
from app.ai.providers.models import ProviderRequest


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Immutable declaration of a provider's capabilities."""

    supports_images: bool = False
    supports_structured_output: bool = False
    supports_system_prompt: bool = False
    supports_json_schema: bool = False
    supports_multi_image: bool = False
    maximum_images: int = 1


def ensure_request_supported(
    request: ProviderRequest,
    capabilities: ProviderCapabilities,
) -> None:
    """Raise ``ProviderCapabilityUnsupportedError`` if *request* exceeds
    the given *capabilities*."""
    if request.images and not capabilities.supports_images:
        raise ProviderCapabilityUnsupportedError(
            message=f"Provider does not support images ({len(request.images)} image(s) requested)",
        )

    if request.images and capabilities.supports_multi_image is False:
        if len(request.images) > 1:
            raise ProviderCapabilityUnsupportedError(
                message=f"Provider does not support multiple images "
                f"({len(request.images)} requested, max 1)",
            )

    if (
        capabilities.maximum_images is not None
        and len(request.images) > capabilities.maximum_images
    ):
        raise ProviderCapabilityUnsupportedError(
            message=f"Provider supports at most {capabilities.maximum_images} images "
            f"({len(request.images)} requested)",
        )

    if request.structured_output_schema and not capabilities.supports_structured_output:
        raise ProviderCapabilityUnsupportedError(
            message="Provider does not support structured output",
        )

    if request.system_prompt and not capabilities.supports_system_prompt:
        raise ProviderCapabilityUnsupportedError(
            message="Provider does not support system prompt",
        )
