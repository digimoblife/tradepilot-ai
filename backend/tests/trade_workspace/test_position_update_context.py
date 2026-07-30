from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.ai.context_builder import (
    EvidenceOwnershipMismatchError,
    MissingInitialAnalysisError,
    MissingRequiredEvidenceError,
    MultiplePositionsError,
    PositionNotOpenError,
    PositionRequestMismatchError,
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
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database

NOW = datetime(2026, 7, 30, 4, 0, tzinfo=timezone.utc)


def _request(
    session_id: uuid.UUID,
    request_id: uuid.UUID,
    analysis_type: AnalysisRequestV2Type,
    *,
    created_at: datetime,
    status: AnalysisRequestV2Status,
    processed_response: dict[str, object] | None,
    completed_at: datetime | None = None,
    position_id: uuid.UUID | None = None,
) -> dict[str, object]:
    values: dict[str, object] = {
        "id": request_id,
        "session_id": session_id,
        "analysis_type": analysis_type,
        "status": status,
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "prompt_version": "v1",
        "input_snapshot": (
            {"position_id": str(position_id), "user_note": "Pantau antrean beli"}
            if position_id is not None
            else {}
        ),
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
    request_id: uuid.UUID,
    *,
    file_path: str = "local/position-current.png",
) -> dict[str, object]:
    return {
        "id": uuid.uuid4(),
        "session_id": session_id,
        "analysis_request_id": request_id,
        "evidence_type": EvidenceUploadV2Type.ORDERBOOK,
        "current_price": Decimal("1234.567890"),
        "observation_period": AnalysisRequestV2ObservationPeriod.MIDDAY,
        "observation_timestamp": NOW,
        "file_path": file_path,
        "original_filename": "position-current.png",
        "mime_type": "image/png",
        "size_bytes": 12,
        "uploaded_at": NOW,
    }


async def _seed(
    engine, *, include_initial: bool = True
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id, session_id, position_id, request_id = (uuid.uuid4() for _ in range(4))
    async with engine.begin() as connection:
        await connection.execute(
            User.__table__.insert().values(
                id=user_id,
                email=f"p84-{user_id}@example.test",
                password_hash="test-only",
            )
        )
        await connection.execute(
            TradeSessionV2.__table__.insert().values(
                id=session_id,
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                status=TradeSessionV2Status.OPEN_POSITION,
            )
        )
        await connection.execute(
            PositionV2.__table__.insert().values(
                id=position_id,
                session_id=session_id,
                entry_price=Decimal("1200.125000"),
                entry_at=NOW - timedelta(days=2),
                quantity=Decimal("10.500000"),
                stop_loss=Decimal("1150.000000"),
                target_price=Decimal("1300.000000"),
                status=PositionV2Status.OPEN,
            )
        )
        if include_initial:
            await connection.execute(
                AnalysisRequestV2.__table__.insert().values(
                    **_request(
                        session_id,
                        uuid.uuid4(),
                        AnalysisRequestV2Type.INITIAL_ANALYSIS,
                        created_at=NOW - timedelta(days=3),
                        completed_at=NOW - timedelta(days=3),
                        status=AnalysisRequestV2Status.COMPLETED,
                        processed_response={"summary": "initial"},
                    )
                )
            )
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                **_request(
                    session_id,
                    request_id,
                    AnalysisRequestV2Type.POSITION_UPDATE,
                    created_at=NOW,
                    status=AnalysisRequestV2Status.PROCESSING,
                    processed_response=None,
                    position_id=position_id,
                )
            )
        )
        await connection.execute(
            EvidenceUploadV2.__table__.insert().values(**_evidence(session_id, request_id))
        )
    return user_id, session_id, position_id, request_id


async def _build(engine, user_id: uuid.UUID, session_id: uuid.UUID, request_id: uuid.UUID):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        return await RebuildAnalysisContextBuilder(session).build(
            user_id=user_id,
            session_id=session_id,
            analysis_type=RebuildAnalysisType.POSITION_UPDATE,
            analysis_request_id=request_id,
        )


async def test_position_update_context_uses_one_current_image_and_compact_history(engine) -> None:
    user_id, session_id, position_id, current_id = await _seed(engine)
    latest_wait_id, latest_position_id = uuid.uuid4(), uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert(),
            [
                _request(
                    session_id,
                    uuid.uuid4(),
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW - timedelta(days=2),
                    completed_at=NOW - timedelta(days=2),
                    status=AnalysisRequestV2Status.COMPLETED,
                    processed_response={"summary": "old wait"},
                ),
                _request(
                    session_id,
                    latest_wait_id,
                    AnalysisRequestV2Type.WAIT_UPDATE,
                    created_at=NOW - timedelta(days=1),
                    completed_at=NOW - timedelta(hours=5),
                    status=AnalysisRequestV2Status.COMPLETED,
                    processed_response={"summary": "latest wait"},
                ),
                _request(
                    session_id,
                    latest_position_id,
                    AnalysisRequestV2Type.POSITION_UPDATE,
                    created_at=NOW - timedelta(hours=4),
                    completed_at=NOW - timedelta(hours=3),
                    status=AnalysisRequestV2Status.COMPLETED,
                    processed_response={"summary": "latest position"},
                    position_id=position_id,
                ),
                _request(
                    session_id,
                    uuid.uuid4(),
                    AnalysisRequestV2Type.POSITION_UPDATE,
                    created_at=NOW - timedelta(hours=2),
                    status=AnalysisRequestV2Status.FAILED,
                    processed_response={"summary": "exclude"},
                    position_id=position_id,
                ),
            ],
        )

    context = await _build(engine, user_id, session_id, current_id)

    assert context.session.session_id == session_id
    assert context.session.ticker == "BBRI"
    assert context.position is not None
    assert context.position.position_id == position_id
    assert context.position.status is PositionV2Status.OPEN
    assert context.position.entry_price == Decimal("1200.125000")
    assert context.position.entry_at == NOW - timedelta(days=2)
    assert context.position.quantity == Decimal("10.500000")
    assert context.position.stop_loss == Decimal("1150.000000")
    assert context.position.target_price == Decimal("1300.000000")
    assert context.current_observation is not None
    assert context.current_observation.current_price == Decimal("1234.567890")
    assert (
        context.current_observation.observation_period is AnalysisRequestV2ObservationPeriod.MIDDAY
    )
    assert context.current_observation.observation_at == NOW
    assert len(context.evidence) == 1
    assert context.evidence[0].evidence_type is EvidenceUploadV2Type.ORDERBOOK
    assert context.evidence[0].analysis_request_id == current_id
    assert context.evidence[0].file_path == "local/position-current.png"
    assert context.initial_analysis is not None
    assert context.initial_analysis.processed_response == {"summary": "initial"}
    assert [(item.analysis_type, item.analysis_id) for item in context.history] == [
        (AnalysisRequestV2Type.WAIT_UPDATE, latest_wait_id),
        (AnalysisRequestV2Type.POSITION_UPDATE, latest_position_id),
    ]


async def test_first_position_update_succeeds_without_optional_history(engine) -> None:
    user_id, session_id, _, current_id = await _seed(engine)

    context = await _build(engine, user_id, session_id, current_id)

    assert context.initial_analysis is not None
    assert context.history == ()


@pytest.mark.parametrize(
    ("snapshot_position_id", "status", "error"),
    [
        (None, PositionV2Status.OPEN, PositionRequestMismatchError),
        (uuid.uuid4(), PositionV2Status.OPEN, PositionRequestMismatchError),
        (None, PositionV2Status.CLOSED, PositionNotOpenError),
    ],
)
def test_position_update_rejects_invalid_position_contract(
    snapshot_position_id: uuid.UUID | None,
    status: PositionV2Status,
    error: type[Exception],
) -> None:
    session_id, position_id = uuid.uuid4(), uuid.uuid4()
    position = SimpleNamespace(id=position_id, session_id=session_id, status=status)
    request = SimpleNamespace(
        input_snapshot=(
            {"position_id": str(snapshot_position_id)} if snapshot_position_id is not None else {}
        )
    )

    with pytest.raises(error):
        RebuildAnalysisContextBuilder._position_update_position(  # type: ignore[arg-type]
            [position], request, session_id
        )

    with pytest.raises(MultiplePositionsError):
        RebuildAnalysisContextBuilder._position_update_position(  # type: ignore[arg-type]
            [position, position], request, session_id
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_price", None),
        ("observation_period", None),
        ("observation_timestamp", None),
        ("file_path", "/private/absolute/position-current.png"),
    ],
)
async def test_position_update_rejects_incomplete_or_unsafe_current_evidence(
    engine, field: str, value: object
) -> None:
    user_id, session_id, _, current_id = await _seed(engine)
    async with engine.begin() as connection:
        values = _evidence(session_id, current_id)
        values[field] = value
        await connection.execute(
            EvidenceUploadV2.__table__.delete().where(
                EvidenceUploadV2.analysis_request_id == current_id
            )
        )
        await connection.execute(EvidenceUploadV2.__table__.insert().values(**values))

    with pytest.raises(MissingRequiredEvidenceError):
        await _build(engine, user_id, session_id, current_id)


async def test_position_update_rejects_multiple_current_evidence_rows(engine) -> None:
    user_id, session_id, _, current_id = await _seed(engine)
    async with engine.begin() as connection:
        await connection.execute(
            EvidenceUploadV2.__table__.insert().values(**_evidence(session_id, current_id))
        )

    with pytest.raises(MissingRequiredEvidenceError):
        await _build(engine, user_id, session_id, current_id)


async def test_position_update_is_session_scoped_and_read_only(engine) -> None:
    user_id, session_id, position_id, current_id = await _seed(engine)
    _, other_session_id, _, _ = await _seed(engine)
    async with engine.begin() as connection:
        await connection.execute(
            EvidenceUploadV2.__table__.insert().values(**_evidence(other_session_id, current_id))
        )

    with pytest.raises(EvidenceOwnershipMismatchError):
        await _build(engine, user_id, session_id, current_id)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        position = await session.scalar(select(PositionV2).where(PositionV2.id == position_id))
        request = await session.scalar(
            select(AnalysisRequestV2).where(AnalysisRequestV2.id == current_id)
        )
        assert position is not None and request is not None
        assert position.status is PositionV2Status.OPEN
        assert position.entry_price == Decimal("1200.125000")
        assert request.status is AnalysisRequestV2Status.PROCESSING


async def test_position_update_requires_completed_initial_analysis(engine) -> None:
    user_id, session_id, _, current_id = await _seed(engine, include_initial=False)

    with pytest.raises(MissingInitialAnalysisError):
        await _build(engine, user_id, session_id, current_id)
