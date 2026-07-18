import uuid
from datetime import datetime, timezone

import pytest

from app.models.analysis import Analysis
from app.models.enums import AcceptanceStatus, AnalysisType
from app.repositories.analysis import AnalysisRepository


@pytest.mark.database
async def test_add_and_retrieve(
    session, session_a, user_a, job_a
):
    repo = AnalysisRepository(session)
    analysis = Analysis(
        session_id=session_a,
        analysis_job_id=job_a,
        analysis_type=AnalysisType.INITIAL_ANALYSIS,
        acceptance_status=AcceptanceStatus.ACCEPTED,
        prompt_name="v1",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
    )
    saved = await repo.add(analysis)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(
    session, session_a, user_a, analysis_a
):
    repo = AnalysisRepository(session)
    found = await repo.get_by_id_for_user(analysis_a, user_a)
    assert found is not None
    assert found.id == analysis_a


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(
    session, analysis_a, user_b
):
    repo = AnalysisRepository(session)
    found = await repo.get_by_id_for_user(analysis_a, user_b)
    assert found is None


@pytest.mark.database
async def test_latest_accepted(session, session_a, user_a, job_a):
    repo = AnalysisRepository(session)
    a1 = Analysis(
        session_id=session_a,
        analysis_job_id=job_a,
        analysis_type=AnalysisType.INITIAL_ANALYSIS,
        acceptance_status=AcceptanceStatus.ACCEPTED,
        prompt_name="v1",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
        accepted_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
    )
    await repo.add(a1)
    a2 = Analysis(
        session_id=session_a,
        analysis_job_id=job_a,
        analysis_type=AnalysisType.WATCHING_UPDATE,
        acceptance_status=AcceptanceStatus.ACCEPTED,
        prompt_name="v2",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
        accepted_at=datetime(2026, 7, 18, 11, 0, 0, tzinfo=timezone.utc),
    )
    await repo.add(a2)
    latest = await repo.get_latest_accepted_for_user(session_a, user_a)
    assert latest is not None
    assert latest.prompt_name == "v2"


@pytest.mark.database
async def test_rejected_excluded_from_accepted(
    session, session_a, user_a, job_a
):
    repo = AnalysisRepository(session)
    rejected = Analysis(
        session_id=session_a,
        analysis_job_id=job_a,
        analysis_type=AnalysisType.INITIAL_ANALYSIS,
        acceptance_status=AcceptanceStatus.REJECTED,
        prompt_name="v1",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
    )
    await repo.add(rejected)
    latest = await repo.get_latest_accepted_for_user(session_a, user_a)
    assert latest is None


@pytest.mark.database
async def test_superseded_history(
    session, session_a, user_a, job_a
):
    repo = AnalysisRepository(session)
    a1 = Analysis(
        session_id=session_a,
        analysis_job_id=job_a,
        analysis_type=AnalysisType.INITIAL_ANALYSIS,
        acceptance_status=AcceptanceStatus.ACCEPTED,
        prompt_name="v1",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
    )
    await repo.add(a1)
    a2 = Analysis(
        session_id=session_a,
        analysis_job_id=job_a,
        analysis_type=AnalysisType.WATCHING_UPDATE,
        acceptance_status=AcceptanceStatus.SUPERSEDED,
        prompt_name="v2",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
    )
    await repo.add(a2)
    # Both should be listable
    rows = await repo.list_for_session_for_user(session_a, user_a)
    assert len(rows) == 2


@pytest.mark.database
async def test_no_raw_provider_output(session, session_a, user_a, analysis_a):
    repo = AnalysisRepository(session)
    found = await repo.get_by_id_for_user(analysis_a, user_a)
    assert found is not None
    # Analysis payload is distinct from raw provider output
    # Verification: we don't have a raw_text or raw_payload field on Analysis
    assert not hasattr(found, "raw_text")
