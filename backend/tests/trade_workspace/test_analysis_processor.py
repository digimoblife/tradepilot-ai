from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.ai.context_builder import (
    AnalysisContext,
    EvidenceReference,
    RebuildAnalysisType,
    SessionFacts,
)
from app.trade_workspace.ai.gemini_adapter import (
    GeminiAdapterError,
    GeminiAdapterResult,
    GeminiImagePart,
)
from app.trade_workspace.ai.prompt_loader import (
    PromptLoaderError,
    RebuildPrompt,
    RebuildPromptType,
)
from app.trade_workspace.ai.response_validator import ResponseValidationResult
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.trade_session import TradeSessionV2
from app.trade_workspace.workers.analysis_processor import (
    AnalysisRequestNotFoundError,
    AnalysisRequestNotPendingError,
    RebuildAnalysisProcessor,
)


class FakeContextBuilder:
    def __init__(
        self,
        context: AnalysisContext | None = None,
        error: Exception | None = None,
    ) -> None:
        self.context = context
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def build(self, **kwargs: object) -> AnalysisContext:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        assert self.context is not None
        return self.context


class FakePromptLoader:
    def __init__(self, *, version: str = "v1", error: Exception | None = None) -> None:
        self.version = version
        self.error = error
        self.calls: list[object] = []

    def load(self, prompt_type: object) -> RebuildPrompt:
        self.calls.append(prompt_type)
        if self.error is not None:
            raise self.error
        return RebuildPrompt(
            prompt_type=RebuildPromptType(prompt_type),
            prompt_version=self.version,
            prompt_text="Approved prompt text",
        )


class FakeImageResolver:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[object, ...]] = []

    async def resolve(self, evidence: tuple[object, ...]) -> tuple[GeminiImagePart, ...]:
        self.calls.append(evidence)
        if self.error is not None:
            raise self.error
        return (
            GeminiImagePart(data=b"first", mime_type="image/png"),
            GeminiImagePart(data=b"second", mime_type="image/jpeg"),
        )


class RecordingValidator:
    def __init__(self, result: ResponseValidationResult) -> None:
        self.result = result
        self.calls: list[tuple[object, object]] = []

    def validate(
        self,
        analysis_type: object,
        processed_response: object,
    ) -> ResponseValidationResult:
        self.calls.append((analysis_type, processed_response))
        return self.result


class FakeAdapter:
    def __init__(
        self,
        model: str,
        result: GeminiAdapterResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.model = model
        self.result = result or GeminiAdapterResult(
            provider="gemini",
            model=model,
            raw_response={"raw": model},
            processed_response={
                "summary": "Ringkasan",
                "orderbook_analysis": "Orderbook",
                "three_month_chart_analysis": "Chart 3M",
                "six_month_chart_analysis": "Chart 6M",
                "support": {"low": 100},
                "resistance": {"high": 110},
                "entry_area": {"low": 102},
                "stop_recommendation": {"level": 99},
                "target_recommendation": {"level": 115},
                "probabilities": {"upside": 0.6},
                "risks": ["risk"],
                "trading_plan": "plan",
                "conclusion": "WAIT",
                "update_summary": "Update",
                "current_price": 105,
                "orderbook_assessment": "Orderbook",
                "change_from_previous_analysis": "Stable",
                "current_entry_condition": "Wait",
                "upside_probability": 0.6,
                "downside_probability": 0.4,
                "key_risks": ["risk"],
                "recommended_action": "WAIT",
                "next_plan": "Monitor",
                "position_condition": "Open",
                "target_realism": "Realistic",
                "downside_risk": "Limited",
                "target_probability": 0.6,
                "monitoring_points": ["support"],
                "warnings": ["volatility"],
            },
        )
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def generate(self, **kwargs: object) -> GeminiAdapterResult:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


def _context(analysis_type: RebuildAnalysisType) -> AnalysisContext:
    evidence = (
        EvidenceReference(
            evidence_id=uuid.uuid4(),
            evidence_type="ORDERBOOK",  # type: ignore[arg-type]
            analysis_request_id=None,
            file_path="local/first.png",
            original_filename="first.png",
            mime_type="image/png",
            observation_period=None,
            uploaded_at=datetime.now(timezone.utc),
        ),
        EvidenceReference(
            evidence_id=uuid.uuid4(),
            evidence_type="CHART_3_MONTH",  # type: ignore[arg-type]
            analysis_request_id=None,
            file_path="local/second.png",
            original_filename="second.png",
            mime_type="image/jpeg",
            observation_period=None,
            uploaded_at=datetime.now(timezone.utc),
        ),
    )
    return AnalysisContext(
        analysis_type=analysis_type,
        session=SessionFacts(
            session_id=uuid.uuid4(), ticker="BBRI", company_name="Bank BRI", note=None
        ),
        current_observation=None,
        evidence=evidence,
        initial_analysis=None,
        history=(),
        position=None,
    )


async def _setup_request(
    factory: async_sessionmaker[AsyncSession],
    *,
    analysis_type: AnalysisRequestV2Type,
    status: AnalysisRequestV2Status = AnalysisRequestV2Status.PENDING,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    request_id = uuid.uuid4()
    async with factory() as session:
        async with session.begin():
            session.add(
                User(id=user_id, email=f"p45-{user_id}@example.test", password_hash="test")
            )
            await session.flush()
            session.add(
                TradeSessionV2(
                    id=session_id,
                    user_id=user_id,
                    ticker="BBRI",
                    company_name="Bank BRI",
                )
            )
            await session.flush()
            session.add(
                AnalysisRequestV2(
                    id=request_id,
                    session_id=session_id,
                    analysis_type=analysis_type,
                    observation_period=(
                        AnalysisRequestV2ObservationPeriod.MORNING
                        if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
                        else None
                    ),
                    current_price=(
                        Decimal("123.45")
                        if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
                        else None
                    ),
                    observation_at=(
                        datetime.now(timezone.utc)
                        if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
                        else None
                    ),
                    status=status,
                    provider="gemini",
                    model="gemini-persisted",
                    prompt_version="v1",
                    input_snapshot={"ticker": "BBRI"},
                )
            )
    return user_id, session_id, request_id


async def _read_request(
    factory: async_sessionmaker[AsyncSession], request_id: uuid.UUID
) -> AnalysisRequestV2:
    async with factory() as session:
        request = await session.scalar(
            select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
        )
        assert request is not None
        return request


@pytest.mark.database
async def test_processor_claims_builds_calls_once_and_completes(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id, session_id, request_id = await _setup_request(
        factory, analysis_type=AnalysisRequestV2Type.WAIT_UPDATE
    )
    context_builder = FakeContextBuilder(_context(RebuildAnalysisType.WAIT_UPDATE))
    prompt_loader = FakePromptLoader()
    image_resolver = FakeImageResolver()
    validator = RecordingValidator(ResponseValidationResult(is_valid=True))
    adapters: list[FakeAdapter] = []
    observed_claim_status: list[AnalysisRequestV2Status] = []

    def adapter_factory(model: str) -> FakeAdapter:
        adapter = FakeAdapter(model)
        adapters.append(adapter)
        return adapter

    async with factory() as processing_session:
        async def observe_claim() -> None:
            async with factory() as observer:
                request = await observer.scalar(
                    select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
                )
                assert request is not None
                observed_claim_status.append(request.status)

        original_factory = adapter_factory

        def observing_factory(model: str) -> FakeAdapter:
            adapter = original_factory(model)
            original_generate = adapter.generate

            async def generate(**kwargs: object) -> GeminiAdapterResult:
                await observe_claim()
                return await original_generate(**kwargs)

            adapter.generate = generate  # type: ignore[method-assign]
            return adapter

        processor = RebuildAnalysisProcessor(
            processing_session,
            image_resolver=image_resolver,  # type: ignore[arg-type]
            context_builder=context_builder,  # type: ignore[arg-type]
            prompt_loader=prompt_loader,  # type: ignore[arg-type]
            validator=validator,  # type: ignore[arg-type]
            adapter_factory=observing_factory,  # type: ignore[arg-type]
        )
        result = await processor.process(analysis_request_id=request_id)

    assert result.status is AnalysisRequestV2Status.COMPLETED
    assert observed_claim_status == [AnalysisRequestV2Status.PROCESSING]
    assert len(context_builder.calls) == 1
    assert len(validator.calls) == 1
    assert context_builder.calls[0] == {
        "user_id": user_id,
        "session_id": session_id,
        "analysis_type": RebuildAnalysisType.WAIT_UPDATE,
        "analysis_request_id": request_id,
    }
    assert prompt_loader.calls == ["WAIT_UPDATE"]
    assert image_resolver.calls[0] == context_builder.context.evidence
    assert len(adapters) == 1
    assert adapters[0].model == "gemini-persisted"
    assert len(adapters[0].calls) == 1
    assert adapters[0].calls[0]["image_parts"] == (
        GeminiImagePart(data=b"first", mime_type="image/png"),
        GeminiImagePart(data=b"second", mime_type="image/jpeg"),
    )
    assert adapters[0].calls[0]["output_schema"]
    assert "Approved prompt text" in str(adapters[0].calls[0]["prompt_text"])

    persisted = await _read_request(factory, request_id)
    assert persisted.status is AnalysisRequestV2Status.COMPLETED
    assert persisted.raw_response == {"raw": "gemini-persisted"}
    assert persisted.processed_response["summary"] == "Ringkasan"
    assert persisted.completed_at is not None
    assert persisted.error_code is None
    assert persisted.error_message is None
    async with factory() as verify:
        session = await verify.scalar(
            select(TradeSessionV2).where(TradeSessionV2.id == session_id)
        )
        assert session is not None
        assert session.status.value == "DRAFT"

    await _cleanup(factory, user_id, session_id, request_id)


@pytest.mark.database
async def test_critical_validation_failure_preserves_raw_response(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id, session_id, request_id = await _setup_request(
        factory, analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS
    )
    adapter = FakeAdapter(
        "gemini-persisted",
        result=GeminiAdapterResult(
            provider="gemini",
            model="gemini-persisted",
            raw_response={"raw": "safe"},
            processed_response={"summary": "only"},
        ),
    )
    async with factory() as session:
        processor = RebuildAnalysisProcessor(
            session,
            image_resolver=FakeImageResolver(),  # type: ignore[arg-type]
            context_builder=FakeContextBuilder(_context(RebuildAnalysisType.INITIAL_ANALYSIS)),  # type: ignore[arg-type]
            adapter_factory=lambda model: adapter,  # type: ignore[arg-type]
        )
        result = await processor.process(analysis_request_id=request_id)

    assert result.status is AnalysisRequestV2Status.FAILED
    assert len(adapter.calls) == 1
    persisted = await _read_request(factory, request_id)
    assert persisted.status is AnalysisRequestV2Status.FAILED
    assert persisted.error_code == "RESPONSE_VALIDATION_FAILED"
    assert persisted.raw_response == {"raw": "safe"}
    assert persisted.processed_response is None
    assert persisted.completed_at is not None
    await _cleanup(factory, user_id, session_id, request_id)


@pytest.mark.database
@pytest.mark.parametrize(
    ("analysis_type", "rebuild_type", "schema_title"),
    [
        (
            AnalysisRequestV2Type.INITIAL_ANALYSIS,
            RebuildAnalysisType.INITIAL_ANALYSIS,
            "Initial Analysis",
        ),
        (AnalysisRequestV2Type.WAIT_UPDATE, RebuildAnalysisType.WAIT_UPDATE, "WAIT Update"),
        (
            AnalysisRequestV2Type.POSITION_UPDATE,
            RebuildAnalysisType.POSITION_UPDATE,
            "Position Update",
        ),
    ],
)
async def test_processor_selects_exact_schema_for_each_analysis_type(
    engine,
    analysis_type: AnalysisRequestV2Type,
    rebuild_type: RebuildAnalysisType,
    schema_title: str,
) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id, session_id, request_id = await _setup_request(
        factory, analysis_type=analysis_type
    )
    adapter = FakeAdapter("gemini-persisted")
    async with factory() as session:
        processor = RebuildAnalysisProcessor(
            session,
            image_resolver=FakeImageResolver(),  # type: ignore[arg-type]
            context_builder=FakeContextBuilder(_context(rebuild_type)),  # type: ignore[arg-type]
            adapter_factory=lambda model: adapter,  # type: ignore[arg-type]
        )
        result = await processor.process(analysis_request_id=request_id)
    assert result.status is AnalysisRequestV2Status.COMPLETED
    assert len(adapter.calls) == 1
    assert adapter.calls[0]["output_schema"]["title"] == schema_title  # type: ignore[index]
    await _cleanup(factory, user_id, session_id, request_id)


@pytest.mark.database
async def test_processor_rejects_duplicate_delivery_and_sanitizes_failures(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    for status in (
        AnalysisRequestV2Status.PROCESSING,
        AnalysisRequestV2Status.COMPLETED,
        AnalysisRequestV2Status.FAILED,
    ):
        user_id, session_id, request_id = await _setup_request(
            factory, analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS, status=status
        )
        adapter = FakeAdapter("gemini-persisted")
        async with factory() as session:
            processor = RebuildAnalysisProcessor(
                session,
                image_resolver=FakeImageResolver(),  # type: ignore[arg-type]
                context_builder=FakeContextBuilder(_context(RebuildAnalysisType.INITIAL_ANALYSIS)),  # type: ignore[arg-type]
                adapter_factory=lambda model: adapter,  # type: ignore[arg-type]
            )
            with pytest.raises(AnalysisRequestNotPendingError):
                await processor.process(analysis_request_id=request_id)
        assert adapter.calls == []
        await _cleanup(factory, user_id, session_id, request_id)

    user_id, session_id, request_id = await _setup_request(
        factory, analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS
    )
    prompt_loader = FakePromptLoader(version="v2")
    adapter = FakeAdapter("gemini-persisted")
    async with factory() as session:
        processor = RebuildAnalysisProcessor(
            session,
            image_resolver=FakeImageResolver(),  # type: ignore[arg-type]
            context_builder=FakeContextBuilder(_context(RebuildAnalysisType.INITIAL_ANALYSIS)),  # type: ignore[arg-type]
            prompt_loader=prompt_loader,  # type: ignore[arg-type]
            adapter_factory=lambda model: adapter,  # type: ignore[arg-type]
        )
        result = await processor.process(analysis_request_id=request_id)
    assert result.status is AnalysisRequestV2Status.FAILED
    assert adapter.calls == []
    persisted = await _read_request(factory, request_id)
    assert persisted.status is AnalysisRequestV2Status.FAILED
    assert persisted.error_code == "PROMPT_VERSION_MISMATCH"
    assert persisted.completed_at is not None
    await _cleanup(factory, user_id, session_id, request_id)

    failures: tuple[tuple[str, object], ...] = (
        ("context", FakeContextBuilder(error=RuntimeError("api_key=secret"))),
        ("prompt", FakePromptLoader(error=PromptLoaderError("token=secret"))),
        ("schema", FakePromptLoader()),
        ("images", FakePromptLoader()),
        ("adapter", FakePromptLoader()),
    )
    for label, component in failures:
        user_id, session_id, request_id = await _setup_request(
            factory, analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS
        )
        context_builder = (
            component
            if label == "context"
            else FakeContextBuilder(_context(RebuildAnalysisType.INITIAL_ANALYSIS))
        )
        prompt = (
            component
            if label in {"prompt", "schema", "images", "adapter"}
            else FakePromptLoader()
        )
        resolver = (
            FakeImageResolver(error=RuntimeError("authorization=Bearer secret"))
            if label == "images"
            else FakeImageResolver()
        )
        adapter = FakeAdapter(
            "gemini-persisted",
            error=GeminiAdapterError("api_key=secret"),
        )
        schemas_root = Path("/missing") if label == "schema" else None
        async with factory() as session:
            processor = RebuildAnalysisProcessor(
                session,
                image_resolver=resolver,  # type: ignore[arg-type]
                context_builder=context_builder,  # type: ignore[arg-type]
                prompt_loader=prompt if label != "prompt" else component,  # type: ignore[arg-type]
                adapter_factory=lambda model: adapter,  # type: ignore[arg-type]
                schemas_root=schemas_root,
            )
            result = await processor.process(analysis_request_id=request_id)
        assert result.status is AnalysisRequestV2Status.FAILED, label
        persisted = await _read_request(factory, request_id)
        assert persisted.completed_at is not None
        assert persisted.error_code is not None
        assert "secret" not in (persisted.error_message or "")
        if label == "adapter":
            assert len(adapter.calls) == 1
        else:
            assert adapter.calls == []
        await _cleanup(factory, user_id, session_id, request_id)

    with pytest.raises(AnalysisRequestNotFoundError):
        async with factory() as session:
            processor = RebuildAnalysisProcessor(
                session,
                image_resolver=FakeImageResolver(),  # type: ignore[arg-type]
            )
            await processor.process(analysis_request_id=uuid.uuid4())


async def _cleanup(
    factory: async_sessionmaker[AsyncSession],
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    request_id: uuid.UUID,
) -> None:
    async with factory() as session:
        async with session.begin():
            await session.execute(
                delete(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
            )
            await session.execute(delete(TradeSessionV2).where(TradeSessionV2.id == session_id))
            await session.execute(delete(User).where(User.id == user_id))
