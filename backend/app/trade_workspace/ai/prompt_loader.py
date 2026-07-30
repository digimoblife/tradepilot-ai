from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path


class RebuildPromptType(str, enum.Enum):
    INITIAL_ANALYSIS = "INITIAL_ANALYSIS"
    WAIT_UPDATE = "WAIT_UPDATE"
    POSITION_UPDATE = "POSITION_UPDATE"


@dataclass(frozen=True, slots=True)
class RebuildPrompt:
    prompt_type: RebuildPromptType
    prompt_version: str
    prompt_text: str


class PromptLoaderError(Exception):
    """Base error for the explicit rebuild prompt loader."""


class UnsupportedPromptTypeError(PromptLoaderError):
    pass


class PromptFileNotFoundError(PromptLoaderError):
    pass


class EmptyPromptFileError(PromptLoaderError):
    pass


PROMPT_VERSION = "v1"
PROMPT_FILES: dict[RebuildPromptType, str] = {
    RebuildPromptType.INITIAL_ANALYSIS: "initial_analysis.md",
    RebuildPromptType.WAIT_UPDATE: "wait_update.md",
    RebuildPromptType.POSITION_UPDATE: "position_update.md",
}


class RebuildPromptLoader:
    """Load exactly the three versioned prompts owned by the rebuild."""

    def __init__(self, prompts_root: Path | None = None) -> None:
        repository_root = Path(__file__).resolve().parents[4]
        self._prompts_root = prompts_root or repository_root / "prompts" / "rebuild"

    @staticmethod
    def supported_prompt_types() -> tuple[RebuildPromptType, ...]:
        return tuple(PROMPT_FILES)

    def load(self, prompt_type: RebuildPromptType | str) -> RebuildPrompt:
        try:
            resolved_type = (
                prompt_type
                if isinstance(prompt_type, RebuildPromptType)
                else RebuildPromptType(prompt_type)
            )
        except (TypeError, ValueError) as exc:
            raise UnsupportedPromptTypeError(
                f"Unsupported rebuild prompt type: {prompt_type!r}"
            ) from exc

        prompt_path = self._prompts_root / PROMPT_FILES[resolved_type]
        if not prompt_path.is_file():
            raise PromptFileNotFoundError(
                f"Rebuild prompt file is missing: {prompt_path.name}"
            )

        prompt_text = prompt_path.read_text(encoding="utf-8")
        if not prompt_text.strip():
            raise EmptyPromptFileError(f"Rebuild prompt file is empty: {prompt_path.name}")

        return RebuildPrompt(
            prompt_type=resolved_type,
            prompt_version=PROMPT_VERSION,
            prompt_text=prompt_text,
        )
