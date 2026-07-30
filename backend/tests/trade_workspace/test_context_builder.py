from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.ai.context_builder import (
    HISTORY_LIMIT,
    AnalysisRequestOwnershipMismatchError,
    EvidenceOwnershipMismatchError,
    MissingInitialAnalysisError,
    MissingObservationFactsError,
    MissingPositionError,
    MissingRequiredEvidenceError,
    OwnershipMismatchError,
    RebuildAnalysisContextBuilder,
    RebuildAnalysisType,
    UnexpectedPositionError,
    UnsupportedAnalysisTypeError,
)
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2
from app.trade_workspace.models.trade_session import TradeSessionV2


def request_data(
    session_id: uuid.UUID,
    analysis_type: AnalysisRequestV2Type,
    **overrides: object,
) -> dict[str, object]:
    data: dict[str, object] = {
        "session_id": session_id,
        "analysis_type": analysis_type,
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "prompt_version": "v1",
        "input_snapshot": {"ticker": "BBRI"},
        "status": AnalysisRequestV2Status.COMPLETED,
        "processed_response": {"summary": analysis_type.value},
        "created_at": datetime.now(timezone.utc),
    }
    if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS:
        data.update(
            {
                "current_price": Decimal("123.45"),
                "observation_period": AnalysisRequestV2ObservationPeriod.MORNING,
                "observation_at": datetime.now(timezone.utc),
            }
        )
    data.update(overrides)
    return data


def evidence_data(
    session_id: uuid.UUID,
    evidence_type: EvidenceUploadV2Type,
    **overrides: object,
) -> dict[str, object]:
    data: dict[str, object] = {
        "session_id": session_id,
        "evidence_type": evidence_type,
        "file_path": f"local/{evidence_type.value.lower()}.png",
        "original_filename": f"{evidence_type.value.lower()}.png",
        "mime_type": "image/png",
        "size_bytes": 100,
        "uploaded_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return data


def position_data(session_id: uuid.UUID) -> dict[str, object]:
    return {
        "session_id": session_id,
        "entry_price": Decimal("100.25"),
        "entry_at": datetime.now(timezone.utc) - timedelta(days=1),
        "quantity": Decimal("10.5"),
        "stop_loss": Decimal("95.00"),
        "target_price": Decimal("110.00"),
    }


@pytest.mark.database
async def test_rebuild_context_builder_uses_bounded_rebuild_context(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    async with factory() as session:
        async with session.begin():
            session.add_all(
                [
                    User(
                        id=user_id,
                        email=f"p43-{user_id}@example.test",
                        password_hash="test-only",
                    ),
                    User(
                        id=other_user_id,
                        email=f"p43-other-{other_user_id}@example.test",
                        password_hash="test-only",
                    ),
                ]
            )
            trade_session = TradeSessionV2(
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                note="Initial session note",
            )
            other_session = TradeSessionV2(
                user_id=other_user_id,
                ticker="BBCA",
                company_name="Bank Central Asia",
            )
            missing_initial_session = TradeSessionV2(
                user_id=user_id,
                ticker="BMRI",
                company_name="Bank Mandiri",
            )
            session.add_all([trade_session, other_session, missing_initial_session])
            await session.flush()
            session_id = trade_session.id
            other_session_id = other_session.id
            missing_initial_session_id = missing_initial_session.id

            initial_request = AnalysisRequestV2(
                **request_data(
                    session_id,
                    AnalysisRequestV2Type.INITIAL_ANALYSIS,
                    created_at=datetime.now(timezone.utc) - timedelta(days=3),
                    processed_response={"summary": "initial accepted"},
                )
            )
            wait_one = AnalysisRequestV2(
                **request_data(
                    session_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=datetime.now(timezone.utc) - timedelta(days=2),
                    processed_response={"summary": "wait one"},
                )
            )
            wait_two = AnalysisRequestV2(
                **request_data(
                    session_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=datetime.now(timezone.utc) - timedelta(days=1, hours=20),
                    processed_response={"summary": "wait two"},
                )
            )
            pending_wait = AnalysisRequestV2(
                **request_data(
                    session_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    status=AnalysisRequestV2Status.PENDING,
                    processed_response=None,
                )
            )
            failed_wait = AnalysisRequestV2(
                **request_data(
                    session_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    status=AnalysisRequestV2Status.FAILED,
                    processed_response={"summary": "must exclude"},
                )
            )
            processing_wait = AnalysisRequestV2(
                **request_data(
                    session_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response={"summary": "must exclude"},
                )
            )
            current_wait = AnalysisRequestV2(
                **request_data(
                    session_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    status=AnalysisRequestV2Status.PENDING,
                    current_price=Decimal("127.75"),
                    observation_period=AnalysisRequestV2ObservationPeriod.AFTERNOON,
                    observation_at=datetime.now(timezone.utc),
                    input_snapshot={"user_note": "Pantau bid tebal"},
                    processed_response=None,
                )
            )
            position_history = AnalysisRequestV2(
                **request_data(
                    session_id,
                    AnalysisRequestV2Type.POSITION_UPDATE,
                    created_at=datetime.now(timezone.utc) - timedelta(hours=3),
                    processed_response={"summary": "position history"},
                )
            )
            current_position = AnalysisRequestV2(
                **request_data(
                    session_id,
                    AnalysisRequestV2Type.POSITION_UPDATE,
                    status=AnalysisRequestV2Status.PENDING,
                    current_price=Decimal("129.50"),
                    observation_period=AnalysisRequestV2ObservationPeriod.MIDDAY,
                    observation_at=datetime.now(timezone.utc),
                    input_snapshot={"note": "Perhatikan resistance"},
                    processed_response=None,
                )
            )
            missing_initial_request = AnalysisRequestV2(
                **request_data(
                    missing_initial_session_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    status=AnalysisRequestV2Status.PENDING,
                    processed_response=None,
                )
            )
            missing_position_request = AnalysisRequestV2(
                **request_data(
                    missing_initial_session_id,
                    AnalysisRequestV2Type.POSITION_UPDATE,
                    status=AnalysisRequestV2Status.PENDING,
                    processed_response=None,
                )
            )
            no_evidence_request = AnalysisRequestV2(
                **request_data(
                    missing_initial_session_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    status=AnalysisRequestV2Status.PENDING,
                    processed_response=None,
                )
            )
            session.add_all(
                [
                    initial_request,
                    wait_one,
                    wait_two,
                    pending_wait,
                    failed_wait,
                    processing_wait,
                    current_wait,
                    position_history,
                    current_position,
                    missing_initial_request,
                    missing_position_request,
                    no_evidence_request,
                ]
            )
            await session.flush()

            initial_evidence = [
                EvidenceUploadV2(
                    **evidence_data(
                        session_id,
                        evidence_type,
                        uploaded_at=datetime.now(timezone.utc) - timedelta(days=4, minutes=index),
                    )
                )
                for index, evidence_type in enumerate(
                    [
                        EvidenceUploadV2Type.ORDERBOOK,
                        EvidenceUploadV2Type.CHART_3_MONTH,
                        EvidenceUploadV2Type.CHART_6_MONTH,
                    ]
                )
            ]
            current_wait_orderbook = EvidenceUploadV2(
                **evidence_data(
                    session_id,
                    EvidenceUploadV2Type.ORDERBOOK,
                    analysis_request_id=current_wait.id,
                    file_path="local/current-wait.png",
                    original_filename="current-wait.png",
                )
            )
            current_position_orderbook = EvidenceUploadV2(
                **evidence_data(
                    session_id,
                    EvidenceUploadV2Type.ORDERBOOK,
                    analysis_request_id=current_position.id,
                    file_path="local/current-position.png",
                    original_filename="current-position.png",
                )
            )
            missing_initial_orderbook = EvidenceUploadV2(
                **evidence_data(
                    missing_initial_session_id,
                    EvidenceUploadV2Type.ORDERBOOK,
                    analysis_request_id=missing_initial_request.id,
                )
            )
            missing_position_orderbook = EvidenceUploadV2(
                **evidence_data(
                    missing_initial_session_id,
                    EvidenceUploadV2Type.ORDERBOOK,
                    analysis_request_id=missing_position_request.id,
                )
            )
            session.add_all(
                [
                    *initial_evidence,
                    current_wait_orderbook,
                    current_position_orderbook,
                    missing_initial_orderbook,
                    missing_position_orderbook,
                ]
            )
            await session.flush()

            builder = RebuildAnalysisContextBuilder(session)
            initial_context = await builder.build(
                user_id=user_id,
                session_id=session_id,
                analysis_type=RebuildAnalysisType.INITIAL_ANALYSIS,
                analysis_request_id=initial_request.id,
            )
            assert initial_context.session.ticker == "BBRI"
            assert initial_context.session.company_name == "Bank BRI"
            assert initial_context.session.note == "Initial session note"
            assert [item.evidence_type for item in initial_context.evidence] == [
                EvidenceUploadV2Type.ORDERBOOK,
                EvidenceUploadV2Type.CHART_3_MONTH,
                EvidenceUploadV2Type.CHART_6_MONTH,
            ]
            assert initial_context.position is None
            assert initial_context.current_observation is None

            wait_context = await builder.build(
                user_id=user_id,
                session_id=session_id,
                analysis_type=RebuildAnalysisType.WAIT_UPDATE,
                analysis_request_id=current_wait.id,
            )
            assert wait_context.current_observation is not None
            assert wait_context.current_observation.current_price == Decimal("127.75")
            assert (
                wait_context.current_observation.observation_period
                is AnalysisRequestV2ObservationPeriod.AFTERNOON
            )
            assert wait_context.current_observation.user_note == "Pantau bid tebal"
            assert [item.evidence_id for item in wait_context.evidence] == [
                current_wait_orderbook.id
            ]
            assert wait_context.initial_analysis is not None
            assert wait_context.position is None
            assert all(
                item.analysis_type
                in {AnalysisRequestV2Type.INITIAL_ANALYSIS, AnalysisRequestV2Type.WAIT_UPDATE}
                for item in wait_context.history
            )
            assert [item.created_at for item in wait_context.history] == sorted(
                item.created_at for item in wait_context.history
            )
            assert len(wait_context.history) <= HISTORY_LIMIT
            assert pending_wait.id not in {item.analysis_id for item in wait_context.history}
            assert failed_wait.id not in {item.analysis_id for item in wait_context.history}
            assert processing_wait.id not in {item.analysis_id for item in wait_context.history}

            position = PositionV2(**position_data(session_id))
            session.add(position)
            await session.flush()

            position_context = await builder.build(
                user_id=user_id,
                session_id=session_id,
                analysis_type=RebuildAnalysisType.POSITION_UPDATE,
                analysis_request_id=current_position.id,
            )
            assert position_context.current_observation is not None
            assert position_context.current_observation.current_price == Decimal("129.50")
            assert (
                position_context.current_observation.observation_period
                is AnalysisRequestV2ObservationPeriod.MIDDAY
            )
            assert position_context.current_observation.user_note == "Perhatikan resistance"
            assert position_context.evidence[0].evidence_id == current_position_orderbook.id
            assert position_context.initial_analysis is not None
            assert position_context.position is not None
            assert position_context.position.entry_price == Decimal("100.25")
            assert position_context.position.quantity == Decimal("10.500000")
            assert position_context.position.stop_loss == Decimal("95.000000")
            assert position_context.position.target_price == Decimal("110.000000")
            assert position_context.position.session_id == session_id
            assert position_history.id in {item.analysis_id for item in position_context.history}

            with pytest.raises(OwnershipMismatchError):
                await builder.build(
                    user_id=other_user_id,
                    session_id=session_id,
                    analysis_type=RebuildAnalysisType.INITIAL_ANALYSIS,
                    analysis_request_id=initial_request.id,
                )

            with pytest.raises(AnalysisRequestOwnershipMismatchError):
                await builder.build(
                    user_id=user_id,
                    session_id=session_id,
                    analysis_type=RebuildAnalysisType.INITIAL_ANALYSIS,
                    analysis_request_id=missing_initial_request.id,
                )

            with pytest.raises(MissingRequiredEvidenceError):
                await builder.build(
                    user_id=user_id,
                    session_id=missing_initial_session_id,
                    analysis_type=RebuildAnalysisType.WAIT_UPDATE,
                    analysis_request_id=no_evidence_request.id,
                )

            with pytest.raises(UnsupportedAnalysisTypeError):
                await builder.build(
                    user_id=user_id,
                    session_id=session_id,
                    analysis_type="CLOSING_ANALYSIS",
                    analysis_request_id=initial_request.id,
                )

            with pytest.raises(UnexpectedPositionError):
                await builder.build(
                    user_id=user_id,
                    session_id=session_id,
                    analysis_type=RebuildAnalysisType.WAIT_UPDATE,
                    analysis_request_id=current_wait.id,
                )

            with pytest.raises(MissingPositionError):
                await builder.build(
                    user_id=user_id,
                    session_id=missing_initial_session_id,
                    analysis_type=RebuildAnalysisType.POSITION_UPDATE,
                    analysis_request_id=missing_position_request.id,
                )

            with pytest.raises(MissingInitialAnalysisError):
                await builder.build(
                    user_id=user_id,
                    session_id=missing_initial_session_id,
                    analysis_type=RebuildAnalysisType.WAIT_UPDATE,
                    analysis_request_id=missing_initial_request.id,
                )

            mismatch_evidence = EvidenceUploadV2(
                **evidence_data(
                    other_session_id,
                    EvidenceUploadV2Type.ORDERBOOK,
                    analysis_request_id=current_wait.id,
                )
            )
            session.add(mismatch_evidence)
            await session.flush()

            with pytest.raises(EvidenceOwnershipMismatchError):
                await builder.build(
                    user_id=user_id,
                    session_id=session_id,
                    analysis_type=RebuildAnalysisType.WAIT_UPDATE,
                    analysis_request_id=current_wait.id,
                )

        async with factory() as cleanup_session:
            async with cleanup_session.begin():
                await cleanup_session.execute(
                    delete(EvidenceUploadV2).where(
                        EvidenceUploadV2.session_id.in_(
                            [session_id, other_session_id, missing_initial_session_id]
                        )
                    )
                )
                await cleanup_session.execute(
                    delete(AnalysisRequestV2).where(
                        AnalysisRequestV2.session_id.in_(
                            [session_id, other_session_id, missing_initial_session_id]
                        )
                    )
                )
                await cleanup_session.execute(
                    delete(PositionV2).where(PositionV2.session_id == session_id)
                )
                await cleanup_session.execute(
                    delete(TradeSessionV2).where(
                        TradeSessionV2.id.in_(
                            [session_id, other_session_id, missing_initial_session_id]
                        )
                    )
                )
                await cleanup_session.execute(
                    delete(User).where(User.id.in_([user_id, other_user_id]))
                )


def test_observation_fact_validation_rejects_missing_values() -> None:
    missing_values = [
        {
            "current_price": None,
            "observation_period": AnalysisRequestV2ObservationPeriod.MORNING,
            "observation_at": datetime.now(timezone.utc),
        },
        {
            "current_price": Decimal("1"),
            "observation_period": None,
            "observation_at": datetime.now(timezone.utc),
        },
        {
            "current_price": Decimal("1"),
            "observation_period": AnalysisRequestV2ObservationPeriod.MORNING,
            "observation_at": None,
        },
    ]
    for values in missing_values:
        with pytest.raises(MissingObservationFactsError):
            RebuildAnalysisContextBuilder._observation_facts(  # type: ignore[arg-type]
                SimpleNamespace(**values, input_snapshot={})
            )
