from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import AppConfig
from app.models.user import User
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2
from app.trade_workspace.queue.analysis_request_queue import (
    AnalysisRequestQueueSubmissionError,
)
from app.trade_workspace.services.analysis_request_queue import (
    AnalysisRequestQueueService,
    DuplicateActiveRequestError,
    EvidenceAlreadyAssignedError,
    EvidenceOwnershipMismatchError,
    PersistenceError,
    QueueSubmissionError,
    SessionOwnershipMismatchError,
    UnsupportedAnalysisTypeError,
)


class RecordingQueue:
    def __init__(self, factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.factory = factory
        self.request_ids: list[uuid.UUID] = []
        self.persisted_before_enqueue = False

    async def enqueue(self, *, analysis_request_id: uuid.UUID) -> None:
        self.request_ids.append(analysis_request_id)
        if self.factory is not None:
            async with self.factory() as session:
                request = await session.scalar(
                    select(AnalysisRequestV2).where(AnalysisRequestV2.id == analysis_request_id)
                )
                linked_count = await session.scalar(
                    select(func.count(EvidenceUploadV2.id)).where(
                        EvidenceUploadV2.analysis_request_id == analysis_request_id
                    )
                )
                self.persisted_before_enqueue = request is not None and linked_count == 3


class FailingQueue:
    def __init__(self) -> None:
        self.calls = 0

    async def enqueue(self, *, analysis_request_id: uuid.UUID) -> None:
        self.calls += 1
        raise AnalysisRequestQueueSubmissionError("broker secret must not escape")


def _evidence(session_id: uuid.UUID, evidence_type: EvidenceUploadV2Type) -> EvidenceUploadV2:
    return EvidenceUploadV2(
        session_id=session_id,
        evidence_type=evidence_type,
        file_path=f"local/{evidence_type.value.lower()}.png",
        original_filename=f"{evidence_type.value.lower()}.png",
        mime_type="image/png",
        size_bytes=128,
        uploaded_at=datetime.now(timezone.utc),
    )


def _request(
    session_id: uuid.UUID,
    analysis_type: AnalysisRequestV2Type,
    *,
    status: AnalysisRequestV2Status,
) -> AnalysisRequestV2:
    return AnalysisRequestV2(
        session_id=session_id,
        analysis_type=analysis_type,
        current_price=(
            Decimal("123.45")
            if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
            else None
        ),
        observation_period=(
            AnalysisRequestV2ObservationPeriod.MORNING
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
        model="gemini-3.1-flash-lite",
        prompt_version="v1",
        input_snapshot={"ticker": "BBRI"},
    )


@pytest.mark.database
async def test_analysis_request_queue_service_persists_then_enqueues(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    other_session_id = uuid.uuid4()
    processing_session_id = uuid.uuid4()
    completed_session_id = uuid.uuid4()
    failed_session_id = uuid.uuid4()
    active_initial_session_id = uuid.uuid4()
    assigned_evidence_id: uuid.UUID | None = None

    async with factory() as setup:
        async with setup.begin():
            setup.add_all(
                [
                    User(id=user_id, email=f"p44-{user_id}@example.test", password_hash="test"),
                    User(
                        id=other_user_id,
                        email=f"p44-other-{other_user_id}@example.test",
                        password_hash="test",
                    ),
                    TradeSessionV2(
                        id=session_id,
                        user_id=user_id,
                        ticker="BBRI",
                        company_name="Bank BRI",
                    ),
                    TradeSessionV2(
                        id=other_session_id,
                        user_id=other_user_id,
                        ticker="BBCA",
                        company_name="Bank Central Asia",
                    ),
                    TradeSessionV2(
                        id=processing_session_id,
                        user_id=user_id,
                        ticker="BMRI",
                        company_name="Bank Mandiri",
                    ),
                    TradeSessionV2(
                        id=completed_session_id,
                        user_id=user_id,
                        ticker="TLKM",
                        company_name="Telkom Indonesia",
                    ),
                    TradeSessionV2(
                        id=failed_session_id,
                        user_id=user_id,
                        ticker="ASII",
                        company_name="Astra International",
                    ),
                    TradeSessionV2(
                        id=active_initial_session_id,
                        user_id=user_id,
                        ticker="ICBP",
                        company_name="Indofood CBP",
                    ),
                ]
            )
            await setup.flush()
            initial_evidence = [
                _evidence(session_id, evidence_type)
                for evidence_type in (
                    EvidenceUploadV2Type.ORDERBOOK,
                    EvidenceUploadV2Type.CHART_3_MONTH,
                    EvidenceUploadV2Type.CHART_6_MONTH,
                )
            ]
            cross_session_evidence = _evidence(other_session_id, EvidenceUploadV2Type.ORDERBOOK)
            assigned_evidence = _evidence(session_id, EvidenceUploadV2Type.ORDERBOOK)
            setup.add_all(initial_evidence + [cross_session_evidence, assigned_evidence])
            await setup.flush()
            assigned_evidence_id = assigned_evidence.id

            active_initial_request = _request(
                active_initial_session_id,
                AnalysisRequestV2Type.INITIAL_ANALYSIS,
                status=AnalysisRequestV2Status.PENDING,
            )
            setup.add_all(
                [
                    _request(
                        processing_session_id,
                        AnalysisRequestV2Type.WAIT_UPDATE,
                        status=AnalysisRequestV2Status.PROCESSING,
                    ),
                    _request(
                        completed_session_id,
                        AnalysisRequestV2Type.WAIT_UPDATE,
                        status=AnalysisRequestV2Status.COMPLETED,
                    ),
                    _request(
                        failed_session_id,
                        AnalysisRequestV2Type.WAIT_UPDATE,
                        status=AnalysisRequestV2Status.FAILED,
                    ),
                    _request(
                        other_session_id,
                        AnalysisRequestV2Type.WAIT_UPDATE,
                        status=AnalysisRequestV2Status.PENDING,
                    ),
                    active_initial_request,
                ]
            )
            await setup.flush()
            assigned_evidence.analysis_request_id = active_initial_request.id

    queue = RecordingQueue(factory)
    snapshot = {"ticker": "BBRI", "note": "preserve exactly", "nested": {"x": 1}}
    observation_at = datetime(2026, 7, 30, 3, 4, 5, tzinfo=timezone.utc)
    async with factory() as session:
        service = AnalysisRequestQueueService(
            session,
            queue,  # type: ignore[arg-type]
            config=AppConfig(gemini_model="gemini-custom-test"),
        )
        result = await service.submit(
            user_id=user_id,
            session_id=session_id,
            analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
            prompt_version="wait-v3",
            input_snapshot=snapshot,
            current_price=Decimal("127.75"),
            observation_period=AnalysisRequestV2ObservationPeriod.AFTERNOON,
            observation_at=observation_at,
            evidence_ids=[item.id for item in initial_evidence],
        )

    assert result.status is AnalysisRequestV2Status.PENDING
    assert result.provider == "gemini"
    assert result.model == "gemini-custom-test"
    assert len(queue.request_ids) == 1
    assert queue.persisted_before_enqueue is True

    async with factory() as verify:
        persisted = await verify.scalar(
            select(AnalysisRequestV2).where(AnalysisRequestV2.id == result.request_id)
        )
        assert persisted is not None
        assert persisted.input_snapshot == snapshot
        assert persisted.prompt_version == "wait-v3"
        assert persisted.current_price == Decimal("127.75")
        assert persisted.observation_period is AnalysisRequestV2ObservationPeriod.AFTERNOON
        assert persisted.observation_at == observation_at
        assert persisted.raw_response is None
        assert persisted.processed_response is None
        assert persisted.error_code is None
        assert persisted.error_message is None
        assert persisted.started_at is None
        assert persisted.completed_at is None
        assert await verify.scalar(
            select(func.count(EvidenceUploadV2.id)).where(
                EvidenceUploadV2.analysis_request_id == result.request_id
            )
        ) == 3
        assert (
            await verify.scalar(
                select(func.count(TradeSessionV2.id)).where(
                    TradeSessionV2.id.in_(
                        [
                            session_id,
                            other_session_id,
                            processing_session_id,
                            completed_session_id,
                            failed_session_id,
                            active_initial_session_id,
                        ]
                    )
                )
            )
            == 6
        )

    async with factory() as session:
        service = AnalysisRequestQueueService(
            session,
            RecordingQueue(),  # type: ignore[arg-type]
            config=AppConfig(gemini_model=""),
        )
        default_result = await service.submit(
            user_id=user_id,
            session_id=session_id,
            analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
            prompt_version="initial-v1",
            input_snapshot={"ticker": "BBRI"},
        )
    assert default_result.model == "gemini-3.1-flash-lite"

    async with factory() as session:
        service = AnalysisRequestQueueService(session, RecordingQueue())  # type: ignore[arg-type]
        with pytest.raises(DuplicateActiveRequestError):
            await service.submit(
                user_id=user_id,
                session_id=active_initial_session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                prompt_version="v1",
                input_snapshot={},
            )
        with pytest.raises(DuplicateActiveRequestError):
            await service.submit(
                user_id=user_id,
                session_id=processing_session_id,
                analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                prompt_version="v1",
                input_snapshot={},
                current_price=Decimal("1"),
                observation_period=AnalysisRequestV2ObservationPeriod.MORNING,
                observation_at=observation_at,
            )

    async with factory() as session:
        service = AnalysisRequestQueueService(session, RecordingQueue())  # type: ignore[arg-type]
        for allowed_session_id in (completed_session_id, failed_session_id):
            result = await service.submit(
                user_id=user_id,
                session_id=allowed_session_id,
                analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                prompt_version="v2",
                input_snapshot={},
                current_price=Decimal("2"),
                observation_period=AnalysisRequestV2ObservationPeriod.MIDDAY,
                observation_at=observation_at,
            )
            assert result.status is AnalysisRequestV2Status.PENDING

    async with factory() as session:
        service = AnalysisRequestQueueService(session, RecordingQueue())  # type: ignore[arg-type]
        with pytest.raises(UnsupportedAnalysisTypeError):
            await service.submit(
                user_id=user_id,
                session_id=session_id,
                analysis_type="CLOSING_ANALYSIS",
                prompt_version="v1",
                input_snapshot={},
            )
        with pytest.raises(SessionOwnershipMismatchError):
            await service.submit(
                user_id=other_user_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                prompt_version="v1",
                input_snapshot={},
            )
        with pytest.raises(EvidenceOwnershipMismatchError):
            await service.submit(
                user_id=user_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                prompt_version="v1",
                input_snapshot={},
                evidence_ids=[cross_session_evidence.id],
            )
        with pytest.raises(EvidenceAlreadyAssignedError):
            await service.submit(
                user_id=user_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                prompt_version="v1",
                input_snapshot={},
                evidence_ids=[assigned_evidence_id],
            )

    failing_queue = FailingQueue()
    async with factory() as session:
        service = AnalysisRequestQueueService(session, failing_queue)  # type: ignore[arg-type]
        with pytest.raises(QueueSubmissionError) as queue_error:
            await service.submit(
                user_id=user_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                prompt_version="queue-failure-v1",
                input_snapshot={"ticker": "BBRI"},
                current_price=Decimal("127.75"),
                observation_period=AnalysisRequestV2ObservationPeriod.AFTERNOON,
                observation_at=observation_at,
            )
        assert "secret" not in str(queue_error.value)
    assert failing_queue.calls == 1

    async with factory() as verify:
        preserved = await verify.scalar(
            select(AnalysisRequestV2).where(
                AnalysisRequestV2.prompt_version == "queue-failure-v1"
            )
        )
        assert preserved is not None
        assert preserved.status is AnalysisRequestV2Status.PENDING
        assert (
            await verify.scalar(
                    select(func.count(AnalysisRequestV2.id)).where(
                        AnalysisRequestV2.session_id == session_id,
                        AnalysisRequestV2.prompt_version == "queue-failure-v1",
                    )
            )
            == 1
        )

    async with factory() as session:
        service = AnalysisRequestQueueService(session, RecordingQueue())  # type: ignore[arg-type]
        original_commit = session.commit

        async def fail_commit() -> None:
            raise SQLAlchemyError("database password must not escape")

        session.commit = fail_commit  # type: ignore[method-assign]
        with pytest.raises(PersistenceError) as persistence_error:
            await service.submit(
                user_id=user_id,
                session_id=processing_session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                prompt_version="persistence-failure-v1",
                input_snapshot={},
            )
        session.commit = original_commit  # type: ignore[method-assign]
        assert "password" not in str(persistence_error.value)

    async with factory() as cleanup:
        async with cleanup.begin():
            await cleanup.execute(
                delete(EvidenceUploadV2).where(
                    EvidenceUploadV2.session_id.in_(
                        [
                            session_id,
                            other_session_id,
                            processing_session_id,
                            completed_session_id,
                            failed_session_id,
                            active_initial_session_id,
                        ]
                    )
                )
            )
            await cleanup.execute(
                delete(AnalysisRequestV2).where(
                    AnalysisRequestV2.session_id.in_(
                        [
                            session_id,
                            other_session_id,
                            processing_session_id,
                            completed_session_id,
                            failed_session_id,
                            active_initial_session_id,
                        ]
                    )
                )
            )
            await cleanup.execute(
                delete(TradeSessionV2).where(
                    TradeSessionV2.id.in_(
                        [
                            session_id,
                            other_session_id,
                            processing_session_id,
                            completed_session_id,
                            failed_session_id,
                            active_initial_session_id,
                        ]
                    )
                )
            )
            await cleanup.execute(delete(User).where(User.id.in_([user_id, other_user_id])))


@pytest.mark.database
async def test_duplicate_protection_serializes_same_session_submissions(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    async with factory() as setup:
        async with setup.begin():
            setup.add(
                User(
                    id=user_id,
                    email=f"p44-lock-{user_id}@example.test",
                    password_hash="test",
                )
            )
            await setup.flush()
            setup.add(
                TradeSessionV2(
                    id=session_id,
                    user_id=user_id,
                    ticker="BBRI",
                    company_name="Bank BRI",
                )
            )

    async def submit_one() -> AnalysisRequestV2Status | DuplicateActiveRequestError:
        async with factory() as session:
            service = AnalysisRequestQueueService(session, RecordingQueue())  # type: ignore[arg-type]
            try:
                result = await service.submit(
                    user_id=user_id,
                    session_id=session_id,
                    analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                    prompt_version="lock-v1",
                    input_snapshot={"ticker": "BBRI"},
                )
            except DuplicateActiveRequestError as exc:
                return exc
            return result.status

    outcomes = await asyncio.gather(submit_one(), submit_one())
    assert sum(isinstance(item, DuplicateActiveRequestError) for item in outcomes) == 1
    assert sum(item is AnalysisRequestV2Status.PENDING for item in outcomes) == 1

    async with factory() as verify:
        assert (
            await verify.scalar(
                select(func.count(AnalysisRequestV2.id)).where(
                    AnalysisRequestV2.session_id == session_id,
                    AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.INITIAL_ANALYSIS,
                )
            )
            == 1
        )

    async with factory() as cleanup:
        async with cleanup.begin():
            await cleanup.execute(
                delete(AnalysisRequestV2).where(AnalysisRequestV2.session_id == session_id)
            )
            await cleanup.execute(delete(TradeSessionV2).where(TradeSessionV2.id == session_id))
            await cleanup.execute(delete(User).where(User.id == user_id))
