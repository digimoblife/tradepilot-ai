from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.ai.context_builder import (
    EvidenceOwnershipMismatchError,
    MissingInitialAnalysisError,
    MissingRequiredEvidenceError,
    RebuildAnalysisContextBuilder,
    RebuildAnalysisType,
)
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database

NOW = datetime(2026, 7, 30, 2, 15, tzinfo=timezone.utc)


def _request(
    session_id: uuid.UUID,
    request_id: uuid.UUID,
    analysis_type: AnalysisRequestV2Type,
    *,
    created_at: datetime,
    status: AnalysisRequestV2Status,
    processed_response: dict[str, object] | None,
    completed_at: datetime | None = None,
) -> dict[str, object]:
    values: dict[str, object] = {
        "id": request_id,
        "session_id": session_id,
        "analysis_type": analysis_type,
        "status": status,
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "prompt_version": "v1",
        "input_snapshot": {"user_note": "Pantau bid"},
        "processed_response": processed_response,
        "created_at": created_at,
        "completed_at": completed_at,
    }
    if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS:
        values.update(
            {
                "current_price": Decimal("1234.567890"),
                "observation_period": AnalysisRequestV2ObservationPeriod.MIDDAY,
                "observation_at": NOW,
            }
        )
    return values


def _evidence(
    session_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request_id: uuid.UUID | None,
    *,
    current_price: Decimal | None = Decimal("1234.567890"),
    observation_period: AnalysisRequestV2ObservationPeriod | None = (
        AnalysisRequestV2ObservationPeriod.MIDDAY
    ),
    observation_timestamp: datetime | None = NOW,
    file_path: str = "local/wait-current.png",
    uploaded_at: datetime = NOW,
    evidence_type: EvidenceUploadV2Type = EvidenceUploadV2Type.ORDERBOOK,
) -> dict[str, object]:
    return {
        "id": evidence_id,
        "session_id": session_id,
        "analysis_request_id": request_id,
        "evidence_type": evidence_type,
        "observation_period": observation_period,
        "current_price": current_price,
        "observation_timestamp": observation_timestamp,
        "file_path": file_path,
        "original_filename": "wait-current.png",
        "mime_type": "image/png",
        "size_bytes": 12,
        "uploaded_at": uploaded_at,
    }


async def _seed_base(engine, *, include_initial: bool = True) -> tuple[uuid.UUID, uuid.UUID]:
    user_id, session_id = uuid.uuid4(), uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            User.__table__.insert().values(
                id=user_id,
                email=f"p74-{user_id}@example.test",
                password_hash="test-only",
            )
        )
        await connection.execute(
            TradeSessionV2.__table__.insert().values(
                id=session_id,
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                status=TradeSessionV2Status.WAITING,
            )
        )
        if include_initial:
            initial_id = uuid.uuid4()
            await connection.execute(
                AnalysisRequestV2.__table__.insert().values(
                    **_request(
                        session_id,
                        initial_id,
                        AnalysisRequestV2Type.INITIAL_ANALYSIS,
                        created_at=NOW - timedelta(days=2),
                        completed_at=NOW - timedelta(days=2),
                        status=AnalysisRequestV2Status.COMPLETED,
                        processed_response={"summary": "initial accepted"},
                    )
                )
            )
    return user_id, session_id


async def _build(engine, user_id: uuid.UUID, session_id: uuid.UUID, request_id: uuid.UUID):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        return await RebuildAnalysisContextBuilder(session).build(
            user_id=user_id,
            session_id=session_id,
            analysis_type=RebuildAnalysisType.WAIT_UPDATE,
            analysis_request_id=request_id,
        )


async def test_wait_update_context_contains_only_current_image_and_latest_prior_update(
    engine,
) -> None:
    user_id, session_id = await _seed_base(engine)
    prior_old_id, prior_latest_id, current_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert(),
            [
                _request(
                    session_id,
                    prior_old_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW - timedelta(days=1),
                    completed_at=NOW - timedelta(days=1),
                    status=AnalysisRequestV2Status.COMPLETED,
                    processed_response={"summary": "old wait"},
                ),
                _request(
                    session_id,
                    prior_latest_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW - timedelta(hours=3),
                    completed_at=NOW - timedelta(hours=2),
                    status=AnalysisRequestV2Status.COMPLETED,
                    processed_response={"summary": "latest wait"},
                ),
                _request(
                    session_id,
                    current_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response=None,
                ),
            ],
        )
        await connection.execute(
            EvidenceUploadV2.__table__.insert().values(
                **_evidence(session_id, uuid.uuid4(), current_id)
            )
        )

    context = await _build(engine, user_id, session_id, current_id)

    assert context.analysis_type is RebuildAnalysisType.WAIT_UPDATE
    assert context.session.session_id == session_id
    assert context.session.ticker == "BBRI"
    assert context.session.company_name == "Bank BRI"
    assert context.current_observation is not None
    assert context.current_observation.current_price == Decimal("1234.567890")
    assert (
        context.current_observation.observation_period is AnalysisRequestV2ObservationPeriod.MIDDAY
    )
    assert context.current_observation.observation_at == NOW
    assert len(context.evidence) == 1
    assert context.evidence[0].evidence_type is EvidenceUploadV2Type.ORDERBOOK
    assert context.evidence[0].analysis_request_id == current_id
    assert context.evidence[0].file_path == "local/wait-current.png"
    assert context.initial_analysis is not None
    assert context.initial_analysis.processed_response == {"summary": "initial accepted"}
    assert [item.analysis_id for item in context.history] == [prior_latest_id]
    assert context.history[0].processed_response == {"summary": "latest wait"}


async def test_wait_update_context_orders_optional_broker_flow_after_orderbook(engine) -> None:
    user_id, session_id = await _seed_base(engine)
    current_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                **_request(
                    session_id,
                    current_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response=None,
                )
            )
        )
        await connection.execute(
            EvidenceUploadV2.__table__.insert(),
            [
                _evidence(session_id, uuid.uuid4(), current_id),
                _evidence(
                    session_id,
                    uuid.uuid4(),
                    current_id,
                    evidence_type=EvidenceUploadV2Type.BROKER_FLOW_1D,
                    file_path="local/wait-broker-flow.png",
                ),
            ],
        )

    context = await _build(engine, user_id, session_id, current_id)

    assert [item.evidence_type for item in context.evidence] == [
        EvidenceUploadV2Type.ORDERBOOK,
        EvidenceUploadV2Type.BROKER_FLOW_1D,
    ]
    assert all(item.analysis_request_id == current_id for item in context.evidence)
    assert context.current_observation is not None
    assert context.current_observation.current_price == Decimal("1234.567890")


async def test_wait_update_rejects_foreign_flow_and_missing_orderbook(engine) -> None:
    user_id, session_id = await _seed_base(engine)
    current_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                **_request(
                    session_id,
                    current_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response=None,
                )
            )
        )
        await connection.execute(
            EvidenceUploadV2.__table__.insert().values(
                **_evidence(
                    session_id,
                    uuid.uuid4(),
                    current_id,
                    evidence_type=EvidenceUploadV2Type.FOREIGN_FLOW_1W,
                )
            )
        )

    with pytest.raises(MissingRequiredEvidenceError):
        await _build(engine, user_id, session_id, current_id)


async def test_first_wait_update_succeeds_without_prior_and_excludes_noncompleted_history(
    engine,
) -> None:
    user_id, session_id = await _seed_base(engine)
    current_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert(),
            [
                _request(
                    session_id,
                    uuid.uuid4(),
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW - timedelta(hours=4),
                    status=AnalysisRequestV2Status.FAILED,
                    processed_response={"summary": "failed"},
                ),
                _request(
                    session_id,
                    uuid.uuid4(),
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW - timedelta(hours=3),
                    status=AnalysisRequestV2Status.PENDING,
                    processed_response=None,
                ),
                _request(
                    session_id,
                    uuid.uuid4(),
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW - timedelta(hours=2),
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response={"summary": "processing"},
                ),
                _request(
                    session_id,
                    current_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response=None,
                ),
            ],
        )
        await connection.execute(
            EvidenceUploadV2.__table__.insert().values(
                **_evidence(session_id, uuid.uuid4(), current_id)
            )
        )

    context = await _build(engine, user_id, session_id, current_id)
    assert context.initial_analysis is not None
    assert context.history == ()


@pytest.mark.parametrize(
    "field, expected_error",
    [
        ("current_price", MissingRequiredEvidenceError),
        ("observation_period", MissingRequiredEvidenceError),
        ("observation_timestamp", MissingRequiredEvidenceError),
        ("file_path", MissingRequiredEvidenceError),
    ],
)
async def test_invalid_current_evidence_fails_without_repair(
    engine, field: str, expected_error: type[Exception]
) -> None:
    user_id, session_id = await _seed_base(engine)
    current_id = uuid.uuid4()
    evidence_values = _evidence(session_id, uuid.uuid4(), current_id)
    evidence_values[field] = None if field != "file_path" else "/private/absolute/orderbook.png"
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                **_request(
                    session_id,
                    current_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response=None,
                )
            )
        )
        await connection.execute(EvidenceUploadV2.__table__.insert().values(**evidence_values))

    with pytest.raises(expected_error):
        await _build(engine, user_id, session_id, current_id)


async def test_multiple_linked_current_evidence_fails_and_absolute_path_is_rejected(
    engine,
) -> None:
    user_id, session_id = await _seed_base(engine)
    current_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                **_request(
                    session_id,
                    current_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response=None,
                )
            )
        )
        await connection.execute(
            EvidenceUploadV2.__table__.insert(),
            [
                _evidence(session_id, uuid.uuid4(), current_id),
                _evidence(
                    session_id,
                    uuid.uuid4(),
                    current_id,
                    file_path="/private/absolute/orderbook.png",
                ),
            ],
        )

    with pytest.raises(MissingRequiredEvidenceError):
        await _build(engine, user_id, session_id, current_id)


async def test_cross_session_linked_evidence_fails_safely(engine) -> None:
    user_id, session_id = await _seed_base(engine)
    other_user_id, other_session_id = await _seed_base(engine)
    current_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                **_request(
                    session_id,
                    current_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response=None,
                )
            )
        )
        await connection.execute(
            EvidenceUploadV2.__table__.insert().values(
                **_evidence(other_session_id, uuid.uuid4(), current_id)
            )
        )

    with pytest.raises(EvidenceOwnershipMismatchError):
        await _build(engine, user_id, session_id, current_id)
    assert other_user_id != user_id


async def test_missing_initial_analysis_fails_without_mutation(engine) -> None:
    user_id, session_id = await _seed_base(engine, include_initial=False)
    current_id = uuid.uuid4()
    evidence_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                **_request(
                    session_id,
                    current_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response=None,
                )
            )
        )
        await connection.execute(
            EvidenceUploadV2.__table__.insert().values(
                **_evidence(session_id, evidence_id, current_id)
            )
        )

    with pytest.raises(MissingInitialAnalysisError):
        await _build(engine, user_id, session_id, current_id)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        evidence = await session.scalar(
            select(EvidenceUploadV2).where(EvidenceUploadV2.id == evidence_id)
        )
        assert evidence is not None
        assert evidence.analysis_request_id == current_id
