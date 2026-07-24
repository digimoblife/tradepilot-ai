from __future__ import annotations

from typing import Any

from app.jobs.processor import AnalysisProcessor


def test_analysis_processor_builds_job_scoped_validation_callback() -> None:
    captured: dict[str, Any] = {}

    def validate_factory(**kwargs: Any) -> Any:
        captured.update(kwargs)

        def validate(payload: dict[str, object]) -> tuple[bool, tuple[object, ...]]:
            return payload.get("ok") is True, ()

        return validate

    processor = AnalysisProcessor(
        session=object(),
        validate_factory=validate_factory,
    )

    validate = processor._build_validate_callback(
        analysis_type="INITIAL_ANALYSIS",
        session_status_before_job="READY_FOR_ANALYSIS",
        canonical_facts={"session_id": "session-1", "ticker": "BBRI"},
    )

    assert validate({"ok": True}) == (True, ())
    assert captured == {
        "analysis_type": "INITIAL_ANALYSIS",
        "session_status_before_job": "READY_FOR_ANALYSIS",
        "canonical_facts": {"session_id": "session-1", "ticker": "BBRI"},
    }
