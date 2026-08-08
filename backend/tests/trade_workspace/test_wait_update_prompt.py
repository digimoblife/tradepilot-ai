from app.trade_workspace.ai.prompt_loader import RebuildPromptLoader, RebuildPromptType


def test_wait_update_v1_prompt_resolves_and_has_approved_contract() -> None:
    prompt = RebuildPromptLoader().load(RebuildPromptType.WAIT_UPDATE)
    text = " ".join(prompt.prompt_text.lower().split())

    assert prompt.prompt_version == "v1"
    assert prompt.prompt_text.strip()
    for phrase in (
        "all user-facing string values must be concise indonesian",
        "return exactly one json object",
        "schemas/rebuild/v1/wait_update.schema.json",
        "latest accepted initial analysis",
        "latest accepted prior wait update",
        "current wait update orderbook image",
        "confirmed current price",
        "confirmed observation period",
        "confirmed observation timestamp",
        "do not restart with a full analysis from zero",
        "newly observed facts",
        "material changes from prior analysis",
        "conditions that remain unchanged",
        "uncertainty caused by limited or unclear evidence",
        "latest orderbook image",
        "the `current_price` output field",
        "the observation period and observation timestamp",
        "do not require or request new charts",
        "live market data",
        "do not persist a buy, wait, or skip decision",
        "do not change session status",
        "create a position",
        "recommended_action",
        "return the json object only",
    ):
        assert phrase in text


def test_wait_update_prompt_has_no_legacy_or_routing_instructions() -> None:
    text = RebuildPromptLoader().load(RebuildPromptType.WAIT_UPDATE).prompt_text.lower()

    assert "provider" not in text
    assert "fallback" not in text
    assert "watching_update" not in text
    assert "open_position_update" not in text
    assert "markdown" not in text


def test_initial_analysis_prompt_resolution_and_content_are_unchanged() -> None:
    prompt = RebuildPromptLoader().load(RebuildPromptType.INITIAL_ANALYSIS)
    text = prompt.prompt_text.lower()

    assert prompt.prompt_version == "v1"
    assert "one orderbook image" in text
    assert "one three-month chart image" in text
    assert "one six-month chart image" in text


def test_wait_prompt_handles_optional_broker_flow_without_fabrication() -> None:
    text = " ".join(
        RebuildPromptLoader().load(RebuildPromptType.WAIT_UPDATE).prompt_text.lower().split()
    )
    for phrase in (
        "optional broker flow 1d image supplied as the second image",
        "accumulation",
        "neutral",
        "distribution",
        "dominant visible buying or selling",
        "concentrated or mixed",
        "confirms or weakens the current wait thesis",
        "expected confirmation is starting to appear",
        "do not prove one investor or institution",
        "one-day broker flow can be noisy",
        "do not invent unreadable broker codes",
        "if image 2 is absent",
        "do not fabricate broker flow commentary",
        "omit `broker_flow_analysis`",
        "do not apply fixed arithmetic bonuses or penalties",
    ):
        assert phrase in text
