"""Startup validation for worker runtime dependencies."""

from __future__ import annotations

from pathlib import Path

from app.config import WorkerConfig


class WorkerStartupValidationError(RuntimeError):
    """Raised when required worker runtime assets are missing or invalid."""

    code = "WORKER_STARTUP_VALIDATION_FAILED"


def validate_worker_startup(config: WorkerConfig) -> None:
    """Validate prompt files before heartbeat initialization or job claims."""
    from app.ai.prompts import PromptRegistry

    prompts_root = Path(config.prompts_root)
    try:
        PromptRegistry(prompts_root=prompts_root)
    except Exception as exc:
        raise WorkerStartupValidationError(
            f"Prompt produksi wajib tidak tersedia atau tidak valid di {prompts_root}: {exc}"
        ) from exc
