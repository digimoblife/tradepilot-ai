from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.ai.gemini_adapter import GeminiAdapterResult, GeminiImagePart
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.analysis_request_queue import (
    AnalysisRequestQueueService,
    DuplicateActiveRequestError,
)
from app.trade_workspace.workers.analysis_processor import (
    AnalysisRequestNotPendingError,
    RebuildAnalysisProcessor,
)


class RecordingQueue:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def enqueue(self, *, analysis_request_id: uuid.UUID) -> None:
        self.calls.append({"analysis_request_id": analysis_request_id})


class RecordingImageResolver:
    def __init__(self) -> None:
        self.evidence_types: list[tuple[EvidenceUploadV2Type, ...]] = []

    async def resolve(self, evidence: tuple[object, ...]) -> tuple[GeminiImagePart, ...]:
        self.evidence_types.append(tuple(item.evidence_type for item in evidence))
        return tuple(
            GeminiImagePart(data=f"image-{index}".encode(), mime_type=item.mime_type)
            for index, item in enumerate(evidence, start=1)
        )


class RecordingAdapter:
    def __init__(self, model: str, processed_response: dict[str, object]) -> None:
        self.model = model
        self.processed_response = processed_response
        self.calls: list[dict[str, object]] = []

    async def generate(self, **kwargs: object) -> GeminiAdapterResult:
        self.calls.append(kwargs)
        return GeminiAdapterResult(
            provider="gemini",
            model=self.model,
            raw_response={"mock": "raw", "secret": "must-not-be-logged"},
            processed_response=self.processed_response,
        )


def _initial_response(*, valid: bool) -> dict[str, object]:
    if not valid:
        return {"summary": "incomplete"}
    return {
        "summary": "Summary",
        "orderbook_analysis": "Orderbook",
        "three_month_chart_analysis": "3M chart",
        "six_month_chart_analysis": "6M chart",
        "support": {"level": 100},
        "resistance": {"level": 110},
        "entry_area": {"low": 101, "high": 103},
        "stop_recommendation": {"level": 98},
        "target_recommendation": {"level": 115},
        "probabilities": {"upside": 0.6, "downside": 0.4},
        "risks": ["volatility"],
        "trading_plan": "Monitor entry area",
        "conclusion": "WAIT",
    }


async def _create_fixture(
    factory: async_sessionmaker[AsyncSession],
    suffix: str,
) -> tuple[uuid.UUID, uuid.UUID, tuple[uuid.UUID, ...]]:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    evidence_ids: list[uuid.UUID] = []
    async with factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"gate-c-{suffix}-{user_id}@example.test",
                    password_hash="test",
                )
            )
            session.add(
                TradeSessionV2(
                    id=session_id,
                    user_id=user_id,
                    ticker="BBRI",
                    company_name="Bank BRI",
                    status=TradeSessionV2Status.DRAFT,
                )
            )
            await session.flush()
            for evidence_type in (
                EvidenceUploadV2Type.ORDERBOOK,
                EvidenceUploadV2Type.CHART_3_MONTH,
                EvidenceUploadV2Type.CHART_6_MONTH,
            ):
                evidence = EvidenceUploadV2(
                    session_id=session_id,
                    evidence_type=evidence_type,
                    file_path=f"local/gate-c-{evidence_type.value.lower()}.png",
                    original_filename=f"{evidence_type.value.lower()}.png",
                    mime_type="image/png",
                    size_bytes=128,
                    uploaded_at=datetime.now(timezone.utc),
                )
                session.add(evidence)
                await session.flush()
                evidence_ids.append(evidence.id)
    return user_id, session_id, tuple(evidence_ids)


async def _read_request(
    factory: async_sessionmaker[AsyncSession], request_id: uuid.UUID
) -> AnalysisRequestV2:
    async with factory() as session:
        request = await session.scalar(
            select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
        )
        assert request is not None
        return request


async def _cleanup(
    factory: async_sessionmaker[AsyncSession], user_id: uuid.UUID, session_id: uuid.UUID
) -> None:
    async with factory() as session:
        async with session.begin():
            request_ids = select(AnalysisRequestV2.id).where(
                AnalysisRequestV2.session_id == session_id
            )
            await session.execute(
                update(EvidenceUploadV2)
                .where(EvidenceUploadV2.session_id == session_id)
                .values(analysis_request_id=None)
            )
            await session.execute(
                delete(AnalysisRequestV2).where(AnalysisRequestV2.id.in_(request_ids))
            )
            await session.execute(
                delete(EvidenceUploadV2).where(EvidenceUploadV2.session_id == session_id)
            )
            await session.execute(delete(TradeSessionV2).where(TradeSessionV2.id == session_id))
            await session.execute(delete(User).where(User.id == user_id))


@pytest.mark.database
async def test_gate_c_success_path_and_duplicate_protection(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id, session_id, evidence_ids = await _create_fixture(factory, "success")
    queue = RecordingQueue()
    try:
        async with factory() as request_session:
            service = AnalysisRequestQueueService(request_session, queue)  # type: ignore[arg-type]
            result = await service.submit(
                user_id=user_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                prompt_version="v1",
                input_snapshot={"ticker": "BBRI"},
                evidence_ids=evidence_ids,
            )
            assert result.status is AnalysisRequestV2Status.PENDING
            with pytest.raises(DuplicateActiveRequestError):
                await service.submit(
                    user_id=user_id,
                    session_id=session_id,
                    analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                    prompt_version="v1",
                    input_snapshot={"ticker": "BBRI"},
                    evidence_ids=(),
                )

        persisted = await _read_request(factory, result.request_id)
        assert persisted.status is AnalysisRequestV2Status.PENDING
        assert await _linked_evidence_count(factory, result.request_id) == 3

        resolver = RecordingImageResolver()
        adapter = RecordingAdapter("gemini-3.1-flash-lite", _initial_response(valid=True))
        observed_claim: list[AnalysisRequestV2Status] = []

        async with factory() as processing_session:
            async def observe_claim() -> None:
                async with factory() as observer:
                    request = await observer.scalar(
                        select(AnalysisRequestV2).where(AnalysisRequestV2.id == result.request_id)
                    )
                    assert request is not None
                    observed_claim.append(request.status)

            original_generate = adapter.generate

            async def generate_and_observe(**kwargs: object) -> GeminiAdapterResult:
                await observe_claim()
                return await original_generate(**kwargs)

            adapter.generate = generate_and_observe  # type: ignore[method-assign]
            processor = RebuildAnalysisProcessor(
                processing_session,
                image_resolver=resolver,  # type: ignore[arg-type]
                adapter_factory=lambda model: adapter,  # type: ignore[arg-type]
            )
            processed = await processor.process(analysis_request_id=result.request_id)

        assert processed.status is AnalysisRequestV2Status.COMPLETED
        assert observed_claim == [AnalysisRequestV2Status.PROCESSING]
        assert resolver.evidence_types == [
            (
                EvidenceUploadV2Type.ORDERBOOK,
                EvidenceUploadV2Type.CHART_3_MONTH,
                EvidenceUploadV2Type.CHART_6_MONTH,
            )
        ]
        assert len(adapter.calls) == 1
        assert adapter.calls[0]["image_parts"] == (
            GeminiImagePart(data=b"image-1", mime_type="image/png"),
            GeminiImagePart(data=b"image-2", mime_type="image/png"),
            GeminiImagePart(data=b"image-3", mime_type="image/png"),
        )
        assert adapter.calls[0]["output_schema"]["title"] == "Initial Analysis"  # type: ignore[index]
        assert "Canonical rebuild context" in str(adapter.calls[0]["prompt_text"])
        persisted = await _read_request(factory, result.request_id)
        assert persisted.status is AnalysisRequestV2Status.COMPLETED
        assert persisted.raw_response == {"mock": "raw", "secret": "must-not-be-logged"}
        assert persisted.processed_response["summary"] == "Summary"
        assert persisted.completed_at is not None

        async with factory() as duplicate_session:
            processor = RebuildAnalysisProcessor(
                duplicate_session,
                image_resolver=resolver,  # type: ignore[arg-type]
                adapter_factory=lambda model: adapter,  # type: ignore[arg-type]
            )
            with pytest.raises(AnalysisRequestNotPendingError):
                await processor.process(analysis_request_id=result.request_id)
        assert len(adapter.calls) == 1

        async with factory() as verify:
            trade_session = await verify.scalar(
                select(TradeSessionV2).where(TradeSessionV2.id == session_id)
            )
            assert trade_session is not None
            assert trade_session.status is TradeSessionV2Status.ANALYZED
            assert await verify.scalar(
                select(func.count(AnalysisRequestV2.id)).where(
                    AnalysisRequestV2.session_id == session_id
                )
            ) == 1
    finally:
        await _cleanup(factory, user_id, session_id)


@pytest.mark.database
async def test_gate_c_critical_failure_is_terminal_without_retry(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id, session_id, evidence_ids = await _create_fixture(factory, "failure")
    queue = RecordingQueue()
    try:
        async with factory() as request_session:
            result = await AnalysisRequestQueueService(request_session, queue).submit(
                user_id=user_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                prompt_version="v1",
                input_snapshot={"ticker": "BBRI"},
                evidence_ids=evidence_ids,
            )
        adapter = RecordingAdapter("gemini-3.1-flash-lite", _initial_response(valid=False))
        async with factory() as processing_session:
            processor = RebuildAnalysisProcessor(
                processing_session,
                image_resolver=RecordingImageResolver(),  # type: ignore[arg-type]
                adapter_factory=lambda model: adapter,  # type: ignore[arg-type]
            )
            processed = await processor.process(analysis_request_id=result.request_id)
        assert processed.status is AnalysisRequestV2Status.FAILED
        assert len(adapter.calls) == 1
        persisted = await _read_request(factory, result.request_id)
        assert persisted.status is AnalysisRequestV2Status.FAILED
        assert persisted.completed_at is not None
        assert persisted.raw_response == {"mock": "raw", "secret": "must-not-be-logged"}
        assert persisted.processed_response is None
        assert persisted.error_code == "RESPONSE_VALIDATION_FAILED"
        assert persisted.error_message is not None
        assert "must-not-be-logged" not in persisted.error_message
    finally:
        await _cleanup(factory, user_id, session_id)


async def _linked_evidence_count(
    factory: async_sessionmaker[AsyncSession], request_id: uuid.UUID
) -> int:
    async with factory() as session:
        return int(
            await session.scalar(
                select(func.count(EvidenceUploadV2.id)).where(
                    EvidenceUploadV2.analysis_request_id == request_id
                )
            )
        )
