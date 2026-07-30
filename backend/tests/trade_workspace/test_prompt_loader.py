from __future__ import annotations

from pathlib import Path

import pytest

from app.trade_workspace.ai.prompt_loader import (
    PROMPT_FILES,
    EmptyPromptFileError,
    PromptFileNotFoundError,
    RebuildPromptLoader,
    RebuildPromptType,
    UnsupportedPromptTypeError,
)


def test_each_approved_prompt_loads_as_v1() -> None:
    loader = RebuildPromptLoader()

    prompts = [loader.load(prompt_type) for prompt_type in loader.supported_prompt_types()]

    assert len(PROMPT_FILES) == 3
    assert {prompt.prompt_type for prompt in prompts} == {
        RebuildPromptType.INITIAL_ANALYSIS,
        RebuildPromptType.WAIT_UPDATE,
        RebuildPromptType.POSITION_UPDATE,
    }
    assert all(prompt.prompt_version == "v1" for prompt in prompts)
    assert all(prompt.prompt_text.strip() for prompt in prompts)


def test_loader_rejects_unsupported_type() -> None:
    with pytest.raises(UnsupportedPromptTypeError):
        RebuildPromptLoader().load("CLOSING_ANALYSIS")


def test_loader_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PromptFileNotFoundError):
        RebuildPromptLoader(tmp_path).load(RebuildPromptType.INITIAL_ANALYSIS)


def test_loader_rejects_empty_file(tmp_path: Path) -> None:
    (tmp_path / "initial_analysis.md").write_text(" \n", encoding="utf-8")

    with pytest.raises(EmptyPromptFileError):
        RebuildPromptLoader(tmp_path).load(RebuildPromptType.INITIAL_ANALYSIS)


def test_prompts_contain_shared_authority_and_language_rules() -> None:
    loader = RebuildPromptLoader()

    for prompt_type in loader.supported_prompt_types():
        text = loader.load(prompt_type).prompt_text
        lowered = " ".join(text.lower().split())
        assert "gemini is advisory only" in lowered
        assert "user-owned facts are authoritative" in lowered
        assert "must not persist or execute buy, wait, skip, or close" in lowered
        assert "all user-facing text values must be in indonesian" in lowered
        assert "provided" in lowered and "json schema exactly" in lowered
        assert "do not invent missing facts" in lowered
        assert "no extra fields" in lowered
        assert "provider" not in lowered
        assert "fallback" not in lowered


def test_wait_and_position_prompts_protect_their_authority_rules() -> None:
    loader = RebuildPromptLoader()
    wait_text = loader.load(RebuildPromptType.WAIT_UPDATE).prompt_text.lower()
    position_text = loader.load(RebuildPromptType.POSITION_UPDATE).prompt_text.lower()

    assert "no position exists" in wait_text
    assert "current price is authoritative" in wait_text
    assert "do not fabricate entry price" in wait_text
    assert "one confirmed open position exists" in position_text
    assert "confirmed entry price" in position_text
    assert "must not be changed" in position_text
    assert "must not close the position" in position_text


def test_initial_analysis_prompt_has_the_approved_contract() -> None:
    text = RebuildPromptLoader().load(RebuildPromptType.INITIAL_ANALYSIS).prompt_text
    lowered = " ".join(text.lower().split())

    for phrase in (
        "ticker",
        "company name",
        "optional initial note",
        "one orderbook image",
        "one three-month chart image",
        "one six-month chart image",
        "current price is not supplied separately",
        "no position exists",
        "initial orderbook screenshot",
        "three-month chart screenshot",
        "six-month chart screenshot",
        "exactly one json object",
        "no extra fields",
        "do not use markdown code fences",
        "do not use markdown code fences, a markdown wrapper, or prose before or after the json",
        "only the user may make and confirm a trading decision",
        "must not claim that an order was executed",
        "must not invent an entry price, quantity, or execution timestamp",
        "must not create a position",
        "must not be persisted as user decisions",
        "dashboard-oriented",
        "tidak tersedia",
        "tidak dapat disimpulkan",
        "bukti visual belum cukup jelas",
        "partial exit",
        "closing analysis",
        "wait update",
        "position update",
    ):
        assert phrase in lowered

    assert lowered.index("initial orderbook screenshot") < lowered.index(
        "three-month chart screenshot"
    ) < lowered.index("six-month chart screenshot")


def test_initial_analysis_prompt_covers_exact_schema_sections() -> None:
    text = RebuildPromptLoader().load(RebuildPromptType.INITIAL_ANALYSIS).prompt_text.lower()
    for section in (
        "summary",
        "orderbook_analysis",
        "three_month_chart_analysis",
        "six_month_chart_analysis",
        "support",
        "resistance",
        "entry_area",
        "stop_recommendation",
        "target_recommendation",
        "probabilities",
        "risks",
        "trading_plan",
        "conclusion",
    ):
        assert section in text


def test_initial_analysis_prompt_has_no_provider_or_fallback_instruction() -> None:
    text = RebuildPromptLoader().load(RebuildPromptType.INITIAL_ANALYSIS).prompt_text.lower()
    assert "provider" not in text
    assert "fallback" not in text
