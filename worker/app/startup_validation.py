"""Startup validation for worker runtime dependencies."""

from __future__ import annotations

from pathlib import Path

from app.config import WorkerConfig


class WorkerStartupValidationError(RuntimeError):
    """Raised when required worker runtime assets are missing or invalid."""

    code = "WORKER_STARTUP_VALIDATION_FAILED"


def validate_worker_startup(
    config: WorkerConfig,
    *,
    prompts_root: Path | None = None,
    schemas_root: Path | None = None,
) -> None:
    """Validate active V2 runtime assets before heartbeat initialization or job claims."""
    from app.trade_workspace.ai.context_builder import RebuildAnalysisType
    from app.trade_workspace.ai.prompt_loader import (
        PromptLoaderError,
        RebuildPromptLoader,
    )
    from app.trade_workspace.workers.analysis_processor import (
        SchemaLoadError,
        _load_schema,
    )

    # 1. Validate active V2 prompts via existing RebuildPromptLoader
    prompt_loader = RebuildPromptLoader(prompts_root=prompts_root)
    for prompt_type in prompt_loader.supported_prompt_types():
        try:
            prompt_loader.load(prompt_type)
        except PromptLoaderError as exc:
            msg = (
                "Prompt rebuild produksi wajib tidak tersedia atau tidak valid "
                f"({prompt_type.value}): {exc}"
            )
            raise WorkerStartupValidationError(msg) from exc
        except Exception as exc:
            raise WorkerStartupValidationError(
                f"Gagal memuat prompt rebuild ({prompt_type.value}): {exc}"
            ) from exc

    # 2. Validate active V2 response schemas via existing _load_schema
    if schemas_root is None:
        repo_root = Path(__file__).resolve().parents[2]
        schemas_root = repo_root / "schemas" / "rebuild" / "v1"

    for analysis_type in (
        RebuildAnalysisType.INITIAL_ANALYSIS,
        RebuildAnalysisType.WAIT_UPDATE,
        RebuildAnalysisType.POSITION_UPDATE,
    ):
        try:
            _load_schema(schemas_root, analysis_type)
        except SchemaLoadError as exc:
            msg = (
                "Schema rebuild produksi wajib tidak tersedia atau tidak valid "
                f"({analysis_type.value}): {exc}"
            )
            raise WorkerStartupValidationError(msg) from exc
        except Exception as exc:
            raise WorkerStartupValidationError(
                f"Gagal memuat schema rebuild ({analysis_type.value}): {exc}"
            ) from exc

    # 3. Validate Gemini configuration
    if not config.gemini_model:
        raise WorkerStartupValidationError(
            "Konfigurasi provider analisis produksi tidak valid: Gemini model is not configured"
        )

    if config.app_env == "production" and not config.gemini_api_key:
        raise WorkerStartupValidationError(
            "Konfigurasi provider analisis produksi tidak valid: Gemini API key is not configured"
        )
