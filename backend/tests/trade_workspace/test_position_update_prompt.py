from app.trade_workspace.ai.prompt_loader import RebuildPromptLoader, RebuildPromptType


def test_position_update_v1_prompt_resolves_with_approved_contract() -> None:
    prompt = RebuildPromptLoader().load(RebuildPromptType.POSITION_UPDATE)
    text = " ".join(prompt.prompt_text.lower().split())

    assert prompt.prompt_version == "v1"
    assert prompt.prompt_text.strip()
    for phrase in (
        "all user-facing text values must be concise indonesian",
        "return exactly one valid json object",
        "schemas/rebuild/v1/position_update.schema.json",
        "do not use markdown code fences",
        "current position update orderbook image",
        "confirmed current price",
        "observation period",
        "observation timestamp",
        "confirmed open position facts",
        "latest accepted initial analysis",
        "latest accepted wait update, when available",
        "latest accepted prior position update, when available",
        "the current request and current image are not prior history",
        "do not restart with a full analysis from zero",
        "newly observed facts",
        "conditions that remain unchanged",
        "uncertainty caused by limited or unclear evidence",
        "do not require or request new charts",
        "live market data",
        "web research",
        "must not persist or execute buy, wait, skip, or close",
        "do not create a decision",
        "do not introduce partial exit",
        "return a lifecycle command",
    ):
        assert phrase in text


def test_position_update_prompt_preserves_facts_and_prohibits_unsupported_actions() -> None:
    text = RebuildPromptLoader().load(RebuildPromptType.POSITION_UPDATE).prompt_text.lower()

    for phrase in (
        "entry price",
        "entry timestamp",
        "quantity",
        "stop loss",
        "target price",
        "must not be changed",
        "do not fabricate or replace",
        "must not close the position",
        "do not infer current price from the screenshot",
        "do not fabricate unreadable orderbook quantities",
        "no extra fields",
        "hidden reasoning",
    ):
        assert phrase in text
    assert "provider" not in text
    assert "fallback" not in text
    assert "open_position_update" not in text
    assert "watching_update" not in text


def test_initial_and_wait_prompt_resolution_remain_unchanged() -> None:
    loader = RebuildPromptLoader()
    initial = loader.load(RebuildPromptType.INITIAL_ANALYSIS)
    wait = loader.load(RebuildPromptType.WAIT_UPDATE)

    assert initial.prompt_version == wait.prompt_version == "v1"
    assert "one three-month chart image" in initial.prompt_text.lower()
    assert "current wait update orderbook image" in wait.prompt_text.lower()


def test_position_prompt_handles_optional_broker_flow_without_fabrication() -> None:
    text = " ".join(
        RebuildPromptLoader()
        .load(RebuildPromptType.POSITION_UPDATE)
        .prompt_text.lower()
        .split()
    )
    for phrase in (
        "optional broker flow 1d image supplied as the second image",
        "accumulation",
        "neutral",
        "distribution",
        "accumulation is continuing or distribution is emerging",
        "aligns or conflicts with the orderbook",
        "implication for risk to the current position",
        "do not prove one investor or institution",
        "one-day broker flow can be noisy",
        "do not invent unreadable broker codes",
        "if image 2 is absent",
        "do not fabricate broker flow commentary",
        "omit `broker_flow_analysis`",
        "do not apply fixed arithmetic bonuses or penalties",
    ):
        assert phrase in text
