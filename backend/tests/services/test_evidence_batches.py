"""Focused tests for P2 Evidence Batches."""

from __future__ import annotations

import asyncio
import io
import uuid
from datetime import datetime, timezone

import pytest
from PIL import Image
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.ai.context_builder import ProviderContextBuilder
from app.ai.providers import ProviderCapabilities
from app.models.analysis import Analysis
from app.models.analysis_job import AnalysisJob
from app.models.enums import AcceptanceStatus, AnalysisType, EvidenceBatchStatus
from app.models.evidence import Evidence
from app.models.evidence_batch import EvidenceBatch
from app.services.analysis_jobs import AnalysisJobCreationService
from app.services.evidence import EvidenceDuplicateActiveError, EvidenceService
from app.services.evidence_batches import EvidenceBatchService

pytestmark = pytest.mark.database


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buf, format="PNG")
    return buf.getvalue()


async def _make_user_and_session(engine: AsyncEngine, status: str = "DRAFT") -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        user = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, 'pw') RETURNING id"),
            {"e": f"p2_{uuid.uuid4().hex}@t.com"},
        )
        user_id = user.scalar_one()
        session = await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:owner_id, 'BBRI', :status, :status) RETURNING id"
            ),
            {"owner_id": user_id, "status": status},
        )
        session_id = session.scalar_one()
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status, state_version) "
                "VALUES (:session_id, 'NOT_OPENED', 'INTACT', 1)"
            ),
            {"session_id": session_id},
        )
        return user_id, session_id


async def _upload_required_evidence(
    svc: EvidenceService,
    *,
    session_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> list[Evidence]:
    created: list[Evidence] = []
    for evidence_type in ("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"):
        result = await svc.create(
            session_id=session_id,
            owner_id=owner_id,
            evidence_type=evidence_type,
            content=_png_bytes(),
            original_filename=f"{evidence_type}.png",
            declared_mime_type="image/png",
            market_timestamp=datetime.now(timezone.utc),
        )
        created.append(result.evidence)
    return created


async def test_uploads_create_one_draft_batch_and_enforce_batch_scoped_duplicates(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
    tmp_path,
) -> None:
    owner_id, session_id = await _make_user_and_session(engine)

    async with factory() as s:
        svc = EvidenceService(s, storage_root=tmp_path)
        created = await _upload_required_evidence(svc, session_id=session_id, owner_id=owner_id)

        batch_ids = {item.evidence_batch_id for item in created}
        assert len(batch_ids) == 1
        batch = await s.get(EvidenceBatch, created[0].evidence_batch_id)
        assert batch is not None
        assert batch.status == EvidenceBatchStatus.DRAFT
        assert batch.sequence_number == 1

        with pytest.raises(EvidenceDuplicateActiveError):
            await svc.create(
                session_id=session_id,
                owner_id=owner_id,
                evidence_type="ORDERBOOK_SCREENSHOT",
                content=_png_bytes(),
                original_filename="duplicate.png",
                declared_mime_type="image/png",
            )


async def test_concurrent_draft_creation_resolves_to_one_batch(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
) -> None:
    owner_id, session_id = await _make_user_and_session(engine)

    async def create_draft() -> uuid.UUID:
        async with factory() as s:
            batch = await EvidenceBatchService(s).get_or_create_current_draft(
                session_id=session_id,
                owner_id=owner_id,
            )
            await s.commit()
            return batch.id

    batch_ids = await asyncio.gather(*(create_draft() for _ in range(8)))

    async with factory() as s:
        rows = await s.execute(
            select(EvidenceBatch).where(
                EvidenceBatch.session_id == session_id,
                EvidenceBatch.analysis_type == AnalysisType.INITIAL_ANALYSIS,
            )
        )
        batches = rows.scalars().all()
        draft_count = await s.scalar(
            select(func.count(EvidenceBatch.id)).where(
                EvidenceBatch.session_id == session_id,
                EvidenceBatch.analysis_type == AnalysisType.INITIAL_ANALYSIS,
                EvidenceBatch.status == EvidenceBatchStatus.DRAFT,
            )
        )

    assert len(set(batch_ids)) == 1
    assert len(batches) == 1
    assert batches[0].sequence_number == 1
    assert draft_count == 1


async def test_concurrent_watching_draft_creation_resolves_to_one_batch(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
) -> None:
    owner_id, session_id = await _make_user_and_session(engine, status="WATCHING")

    async def create_draft() -> uuid.UUID:
        async with factory() as s:
            batch = await EvidenceBatchService(s).get_or_create_current_draft(
                session_id=session_id,
                owner_id=owner_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
            )
            await s.commit()
            return batch.id

    batch_ids = await asyncio.gather(*(create_draft() for _ in range(8)))

    async with factory() as s:
        rows = await s.execute(
            select(EvidenceBatch).where(
                EvidenceBatch.session_id == session_id,
                EvidenceBatch.analysis_type == AnalysisType.WATCHING_UPDATE,
            )
        )
        batches = rows.scalars().all()

    assert len(set(batch_ids)) == 1
    assert len(batches) == 1
    assert batches[0].sequence_number == 1


async def test_watching_upload_uses_explicit_watching_batch(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
    tmp_path,
) -> None:
    owner_id, session_id = await _make_user_and_session(engine, status="WATCHING")

    async with factory() as s:
        batch = await EvidenceBatchService(s).get_or_create_current_draft(
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=AnalysisType.WATCHING_UPDATE,
        )
        result = await EvidenceService(s, storage_root=tmp_path).create(
            session_id=session_id,
            owner_id=owner_id,
            evidence_type="ORDERBOOK_SCREENSHOT",
            content=_png_bytes(),
            original_filename="watching-orderbook.png",
            declared_mime_type="image/png",
            market_timestamp=datetime.now(timezone.utc),
            evidence_batch_id=batch.id,
        )
        batch = await s.get(EvidenceBatch, result.evidence.evidence_batch_id)

        assert batch is not None
        assert batch.analysis_type == AnalysisType.WATCHING_UPDATE
        assert batch.status == EvidenceBatchStatus.DRAFT


async def test_watching_readiness_is_isolated_to_selected_batch(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
    tmp_path,
) -> None:
    owner_id, session_id = await _make_user_and_session(engine, status="WATCHING")

    async with factory() as s:
        evidence_svc = EvidenceService(s, storage_root=tmp_path)
        batch_svc = EvidenceBatchService(s)
        first_batch = await batch_svc.get_or_create_current_draft(
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=AnalysisType.WATCHING_UPDATE,
        )
        created = await evidence_svc.create(
            session_id=session_id,
            owner_id=owner_id,
            evidence_type="ORDERBOOK_SCREENSHOT",
            content=_png_bytes(),
            original_filename="orderbook.png",
            declared_mime_type="image/png",
            evidence_batch_id=first_batch.id,
        )
        first_batch = await s.get(EvidenceBatch, created.evidence.evidence_batch_id)
        assert first_batch is not None
        complete = await evidence_svc.get_required_evidence(
            session_id,
            owner_id,
            AnalysisType.WATCHING_UPDATE,
            evidence_batch_id=first_batch.id,
        )
        assert complete.complete

        await batch_svc.mark_ready(first_batch)
        second_batch = await batch_svc.get_or_create_current_draft(
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=AnalysisType.WATCHING_UPDATE,
        )
        isolated = await evidence_svc.get_required_evidence(
            session_id,
            owner_id,
            AnalysisType.WATCHING_UPDATE,
            evidence_batch_id=second_batch.id,
        )

        assert second_batch.id != first_batch.id
        assert not isolated.complete


async def test_readiness_is_isolated_to_selected_batch(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
    tmp_path,
) -> None:
    owner_id, session_id = await _make_user_and_session(engine)

    async with factory() as s:
        evidence_svc = EvidenceService(s, storage_root=tmp_path)
        batch_svc = EvidenceBatchService(s)
        first = await evidence_svc.create(
            session_id=session_id,
            owner_id=owner_id,
            evidence_type="ORDERBOOK_SCREENSHOT",
            content=_png_bytes(),
            original_filename="orderbook.png",
            declared_mime_type="image/png",
        )
        first_batch_id = first.evidence.evidence_batch_id
        first_required = await evidence_svc.get_required_evidence(
            session_id,
            owner_id,
            AnalysisType.INITIAL_ANALYSIS,
            evidence_batch_id=first_batch_id,
        )
        assert not first_required.complete

        first_batch = await s.get(EvidenceBatch, first_batch_id)
        assert first_batch is not None
        await batch_svc.mark_ready(first_batch)
        created = await _upload_required_evidence(
            evidence_svc,
            session_id=session_id,
            owner_id=owner_id,
        )
        second_batch_id = created[0].evidence_batch_id
        second_required = await evidence_svc.get_required_evidence(
            session_id,
            owner_id,
            AnalysisType.INITIAL_ANALYSIS,
            evidence_batch_id=second_batch_id,
        )

        assert first_batch_id != second_batch_id
        assert second_required.complete


async def test_job_creation_references_ready_batch_and_marks_processing(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
    tmp_path,
) -> None:
    owner_id, session_id = await _make_user_and_session(engine)

    async with factory() as s:
        evidence_svc = EvidenceService(s, storage_root=tmp_path)
        batch_svc = EvidenceBatchService(s)
        created = await _upload_required_evidence(
            evidence_svc,
            session_id=session_id,
            owner_id=owner_id,
        )
        batch = await s.get(EvidenceBatch, created[0].evidence_batch_id)
        assert batch is not None
        await batch_svc.mark_ready(batch)
        await s.execute(
            text(
                "UPDATE trade_sessions SET lifecycle_status = 'READY_FOR_INITIAL_ANALYSIS', "
                "stable_status = 'READY_FOR_INITIAL_ANALYSIS' WHERE id = :session_id"
            ),
            {"session_id": session_id},
        )

        result = await AnalysisJobCreationService(s).create(
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
        )
        job = await s.get(AnalysisJob, result.job_id)
        await s.refresh(batch)

        assert result.evidence_batch_id == batch.id
        assert job is not None
        assert job.evidence_batch_id == batch.id
        assert batch.status == EvidenceBatchStatus.PROCESSING


async def test_provider_context_loads_only_job_batch_evidence(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
    tmp_path,
) -> None:
    owner_id, session_id = await _make_user_and_session(engine)

    async with factory() as s:
        evidence_svc = EvidenceService(s, storage_root=tmp_path)
        batch_svc = EvidenceBatchService(s)
        selected = await _upload_required_evidence(
            evidence_svc,
            session_id=session_id,
            owner_id=owner_id,
        )
        selected_batch_id = selected[0].evidence_batch_id
        selected_ids = {str(item.id) for item in selected}
        selected_batch = await s.get(EvidenceBatch, selected_batch_id)
        assert selected_batch is not None
        await batch_svc.mark_ready(selected_batch)
        extra = await evidence_svc.create(
            session_id=session_id,
            owner_id=owner_id,
            evidence_type="ORDERBOOK_SCREENSHOT",
            content=_png_bytes(),
            original_filename="new-orderbook.png",
            declared_mime_type="image/png",
        )

        ctx = await ProviderContextBuilder(s).build(
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
            provider_capabilities=ProviderCapabilities(
                supports_images=True,
                supports_multi_image=True,
                maximum_images=10,
            ),
            evidence_batch_id=selected_batch_id,
        )

        assert set(ctx.metadata["evidence_ids"]) == selected_ids
        assert str(extra.evidence.id) not in ctx.metadata["evidence_ids"]
        assert ctx.metadata["evidence_batch_id"] == str(selected_batch_id)


async def test_watching_provider_context_uses_batch_and_compact_prior_analyses(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
    tmp_path,
) -> None:
    owner_id, session_id = await _make_user_and_session(engine, status="WATCHING")

    async with factory() as s:
        initial = Analysis(
            session_id=session_id,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
            acceptance_status=AcceptanceStatus.ACCEPTED,
            accepted_at=datetime.now(timezone.utc),
            prompt_name="initial_analysis",
            prompt_version="2.0.0",
            schema_name="initial_analysis_v2",
            schema_version="2.0.0",
            payload={"recommendation": "WAIT", "trade_plan": {"entry": 1000}},
        )
        watching = Analysis(
            session_id=session_id,
            analysis_type=AnalysisType.WATCHING_UPDATE,
            acceptance_status=AcceptanceStatus.ACCEPTED,
            accepted_at=datetime.now(timezone.utc),
            prompt_name="watching_update",
            prompt_version="1.0.0",
            schema_name="watching_update",
            schema_version="1.0.0",
            payload={"next_action": "WAIT", "thesis_update": "Still valid"},
        )
        s.add_all([initial, watching])
        await s.flush()

        evidence_svc = EvidenceService(s, storage_root=tmp_path)
        batch_svc = EvidenceBatchService(s)
        selected_batch = await batch_svc.get_or_create_current_draft(
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=AnalysisType.WATCHING_UPDATE,
        )
        selected = await evidence_svc.create(
            session_id=session_id,
            owner_id=owner_id,
            evidence_type="ORDERBOOK_SCREENSHOT",
            content=_png_bytes(),
            original_filename="selected-orderbook.png",
            declared_mime_type="image/png",
            evidence_batch_id=selected_batch.id,
        )
        selected_batch_id = selected.evidence.evidence_batch_id
        selected_batch = await s.get(EvidenceBatch, selected_batch_id)
        assert selected_batch is not None
        await batch_svc.mark_ready(selected_batch)
        extra = await evidence_svc.create(
            session_id=session_id,
            owner_id=owner_id,
            evidence_type="ORDERBOOK_SCREENSHOT",
            content=_png_bytes(),
            original_filename="extra-orderbook.png",
            declared_mime_type="image/png",
            evidence_batch_id=(
                await batch_svc.get_or_create_current_draft(
                    session_id=session_id,
                    owner_id=owner_id,
                    analysis_type=AnalysisType.WATCHING_UPDATE,
                )
            ).id,
        )

        ctx = await ProviderContextBuilder(s).build(
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=AnalysisType.WATCHING_UPDATE,
            provider_capabilities=ProviderCapabilities(
                supports_images=True,
                supports_multi_image=True,
                maximum_images=10,
            ),
            evidence_batch_id=selected_batch_id,
        )

        assert ctx.metadata["evidence_ids"] == [str(selected.evidence.id)]
        assert str(extra.evidence.id) not in ctx.metadata["evidence_ids"]
        assert ctx.metadata["latest_initial_analysis_id"] == str(initial.id)
        assert ctx.metadata["latest_watching_update_id"] == str(watching.id)
        assert str(initial.id) in ctx.user_prompt
        assert str(watching.id) in ctx.user_prompt


async def test_processing_batches_freeze_or_fail_without_touching_legacy(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
) -> None:
    owner_id, session_id = await _make_user_and_session(engine)

    async with factory() as s:
        batch_svc = EvidenceBatchService(s)
        freeze_batch = EvidenceBatch(
            id=uuid.uuid4(),
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
            status=EvidenceBatchStatus.PROCESSING,
            sequence_number=1,
        )
        fail_batch = EvidenceBatch(
            id=uuid.uuid4(),
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
            status=EvidenceBatchStatus.PROCESSING,
            sequence_number=2,
        )
        s.add_all([freeze_batch, fail_batch])
        await s.flush()

        await batch_svc.freeze(freeze_batch.id)
        await batch_svc.fail(fail_batch.id)
        legacy_required = await EvidenceService(s).get_required_evidence(
            session_id,
            owner_id,
            AnalysisType.INITIAL_ANALYSIS,
            evidence_batch_id=None,
        )

        assert freeze_batch.status == EvidenceBatchStatus.FROZEN
        assert fail_batch.status == EvidenceBatchStatus.FAILED
        assert legacy_required.complete is False


async def test_legacy_unbatched_evidence_remains_readable(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
) -> None:
    owner_id, session_id = await _make_user_and_session(engine)
    async with engine.begin() as conn:
        for evidence_type in ("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"):
            await conn.execute(
                text(
                    "INSERT INTO evidence "
                    "(session_id, owner_id, evidence_type, evidence_status, "
                    "storage_object_key, mime_type, file_size_bytes) "
                    "VALUES (:session_id, :owner_id, :evidence_type, 'AVAILABLE', "
                    ":key, 'image/png', 100)"
                ),
                {
                    "session_id": session_id,
                    "owner_id": owner_id,
                    "evidence_type": evidence_type,
                    "key": f"legacy/{evidence_type}.png",
                },
            )

    async with factory() as s:
        required = await EvidenceService(s).get_required_evidence(
            session_id,
            owner_id,
            AnalysisType.INITIAL_ANALYSIS,
        )
        rows = await s.execute(
            select(Evidence).where(Evidence.session_id == session_id)
        )

        assert required.complete
        assert {row.evidence_batch_id for row in rows.scalars().all()} == {None}
