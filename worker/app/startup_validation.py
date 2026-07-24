"""Startup validation for worker runtime dependencies."""

from __future__ import annotations

from pathlib import Path

from app.config import WorkerConfig


class WorkerStartupValidationError(RuntimeError):
    """Raised when required worker runtime assets are missing or invalid."""

    code = "WORKER_STARTUP_VALIDATION_FAILED"


def validate_worker_startup(config: WorkerConfig) -> None:
    """Validate runtime assets before heartbeat initialization or job claims."""
    from app.ai.prompts import PromptRegistry
    from app.ai.providers import validate_analysis_provider_startup

    prompts_root = Path(config.prompts_root)
    try:
        PromptRegistry(prompts_root=prompts_root)
    except Exception as exc:
        raise WorkerStartupValidationError(
            f"Prompt produksi wajib tidak tersedia atau tidak valid di {prompts_root}: {exc}"
        ) from exc

    try:
        validate_analysis_provider_startup(config)
    except Exception as exc:
        raise WorkerStartupValidationError(
            f"Konfigurasi provider analisis produksi tidak valid: {exc}"
        ) from exc
