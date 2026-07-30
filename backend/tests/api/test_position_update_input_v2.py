from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.storage import LocalFileStorage, StorageWriteError
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.session_decision import SessionDecisionV2
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services import position_update_input as position_input_module
from app.trade_workspace.services.position_update_input import (
    PositionUpdateInputPersistenceError,
    PositionUpdateInputService,
)

pytestmark = pytest.mark.database

IMAGE = b"\x89PNG\r\n\x1a\n-position-update"
FORM = {
    "current_price": "1234.567890",
    "observation_period": "MIDDAY",
    "observation_timestamp": "2026-07-30T09:15:00.123456+07:00",
}


async def _seed(
    engine: AsyncEngine,
    *,
    status: TradeSessionV2Status = TradeSessionV2Status.OPEN_POSITION,
    position_status: PositionV2Status | None = PositionV2Status.OPEN,
    with_prior_evidence: bool = True,
    owner: tuple[uuid.UUID, str] | None = None,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID | None, str]:
    if owner is None:
        user_id, email = uuid.uuid4(), f"p81-{uuid.uuid4()}@example.test"
        create_user = True
    else:
        user_id, email = owner
        create_user = False
    session_id = uuid.uuid4()
    position_id = uuid.uuid4() if position_status is not None else None
    async with engine.begin() as connection:
        if create_user:
            await connection.execute(
                User.__table__.insert().values(
                    id=user_id, email=email, password_hash=hash_password("testpass123")
                )
            )
        await connection.execute(
            TradeSessionV2.__table__.insert().values(
                id=session_id,
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                status=status,
            )
        )
        if position_id is not None:
            await connection.execute(
                PositionV2.__table__.insert().values(
                    id=position_id,
                    session_id=session_id,
                    entry_price=Decimal("1200.000000"),
                    entry_at=datetime(2026, 7, 29, 2, 0, tzinfo=timezone.utc),
                    quantity=Decimal("10.000000"),
                    stop_loss=Decimal("1100.000000"),
                    target_price=Decimal("1400.000000"),
                    note="immutable position facts",
                    status=position_status,
                )
            )
        if with_prior_evidence:
            await connection.execute(
                EvidenceUploadV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    evidence_type=EvidenceUploadV2Type.ORDERBOOK,
                    analysis_request_id=None,
                    observation_period=AnalysisRequestV2ObservationPeriod.MORNING,
                    current_price=Decimal("1201.000000"),
                    observation_timestamp=datetime(2026, 7, 29, 2, 30, tzinfo=timezone.utc),
                    file_path=f"{user_id}/{session_id}/prior.png",
                    original_filename="prior.png",
                    mime_type="image/png",
                    size_bytes=8,
                )
            )
    return user_id, session_id, position_id, email


def _app(db_session: AsyncSession) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)

    async def override_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = override_db
    return app


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LocalFileStorage:
    storage = LocalFileStorage(tmp_path)
    monkeypatch.setattr(
        position_input_module,
        "create_file_storage",
        lambda _config=None: storage,
    )
    return storage


async def _post_input(
    db_session: AsyncSession,
    session_id: uuid.UUID,
    email: str | None,
    *,
    form: dict[str, str] | None = None,
    file: tuple[str, bytes, str] | None = ("position.png", IMAGE, "image/png"),
) -> tuple[int, dict[str, object]]:
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if email is not None:
            login = await client.post(
                "/api/auth/login", json={"email": email, "password": "testpass123"}
            )
            assert login.status_code == 200
        files = {"orderbook": file} if file is not None else None
        response = await client.post(
            f"/api/v2/trade-sessions/{session_id}/position-update-input",
            data=FORM if form is None else form,
            files=files,
        )
    return response.status_code, response.json()


async def _count(
    db_session: AsyncSession,
    model: type[object],
    session_id: uuid.UUID,
) -> int:
    return int(
        await db_session.scalar(
            select(func.count()).select_from(model).where(model.session_id == session_id)  # type: ignore[attr-defined]
        )
    )


async def test_owner_persists_position_update_input_without_lifecycle_changes(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
) -> None:
    _, session_id, position_id, email = await _seed(engine)
    code, payload = await _post_input(db_session, session_id, email)

    assert code == 201
    assert payload["evidence_id"]
    assert payload["session_id"] == str(session_id)
    assert payload["position_id"] == str(position_id)
    assert payload["evidence_type"] == "ORDERBOOK"
    assert payload["original_filename"] == "position.png"
    assert payload["mime_type"] == "image/png"
    assert payload["size_bytes"] == len(IMAGE)
    assert payload["current_price"] == "1234.567890"
    assert payload["observation_period"] == "MIDDAY"
    assert payload["observation_timestamp"] == FORM["observation_timestamp"]
    assert payload["uploaded_at"]
    assert payload["session_status"] == "OPEN_POSITION"
    assert payload["position_status"] == "OPEN"
    assert len([path for path in isolated_storage._root.rglob("*") if path.is_file()]) == 1  # noqa: SLF001

    evidence = await db_session.scalar(
        select(EvidenceUploadV2)
        .where(EvidenceUploadV2.session_id == session_id)
        .order_by(EvidenceUploadV2.uploaded_at.desc())
    )
    assert evidence is not None
    assert evidence.session_id == session_id
    assert evidence.evidence_type is EvidenceUploadV2Type.ORDERBOOK
    assert evidence.analysis_request_id is None
    assert evidence.current_price == Decimal("1234.567890")
    assert evidence.observation_period is AnalysisRequestV2ObservationPeriod.MIDDAY
    assert evidence.observation_timestamp == datetime(
        2026, 7, 30, 2, 15, 0, 123456, tzinfo=timezone.utc
    )
    assert evidence.original_filename == "position.png"
    assert evidence.mime_type == "image/png"
    assert evidence.size_bytes == len(IMAGE)
    assert evidence.uploaded_at is not None

    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    position = await db_session.scalar(select(PositionV2).where(PositionV2.id == position_id))
    assert session is not None and session.status is TradeSessionV2Status.OPEN_POSITION
    assert session.closed_at is None
    assert position is not None and position.status is PositionV2Status.OPEN
    assert position.entry_price == Decimal("1200.000000")
    assert position.quantity == Decimal("10.000000")
    assert position.stop_loss == Decimal("1100.000000")
    assert position.target_price == Decimal("1400.000000")
    assert position.note == "immutable position facts"
    assert await _count(db_session, AnalysisRequestV2, session_id) == 0
    assert await _count(db_session, SessionDecisionV2, session_id) == 0
    assert await _count(db_session, TradeClosureV2, session_id) == 0


@pytest.mark.parametrize(
    "form, file, expected_code, error_code",
    [
        (
            {**FORM, "current_price": "not-a-price"},
            ("x.png", IMAGE, "image/png"),
            422,
            "VALIDATION_ERROR",
        ),
        (
            {**FORM, "current_price": "0"},
            ("x.png", IMAGE, "image/png"),
            422,
            "POSITION_UPDATE_INPUT_INVALID",
        ),
        (
            {**FORM, "current_price": "1234.1234567"},
            ("x.png", IMAGE, "image/png"),
            422,
            "POSITION_UPDATE_INPUT_INVALID",
        ),
        (
            {**FORM, "current_price": "NaN"},
            ("x.png", IMAGE, "image/png"),
            422,
            "VALIDATION_ERROR",
        ),
        (
            {"current_price": "1234.00", "observation_period": "MIDDAY"},
            ("x.png", IMAGE, "image/png"),
            422,
            "VALIDATION_ERROR",
        ),
        (
            {**FORM, "observation_period": "EVENING"},
            ("x.png", IMAGE, "image/png"),
            422,
            "VALIDATION_ERROR",
        ),
        (
            {**FORM, "observation_timestamp": "2026-07-30T09:15:00"},
            ("x.png", IMAGE, "image/png"),
            422,
            "POSITION_UPDATE_INPUT_INVALID",
        ),
        (FORM, None, 422, "VALIDATION_ERROR"),
        (FORM, ("empty.png", b"", "image/png"), 422, "POSITION_UPDATE_INPUT_INVALID"),
        (FORM, ("text.txt", IMAGE, "text/plain"), 422, "POSITION_UPDATE_INPUT_INVALID"),
        (
            FORM,
            ("large.png", b"x" * (10 * 1024 * 1024 + 1), "image/png"),
            422,
            "POSITION_UPDATE_INPUT_INVALID",
        ),
    ],
)
async def test_invalid_position_update_input_is_rejected_without_persistence(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
    form: dict[str, str],
    file: tuple[str, bytes, str] | None,
    expected_code: int,
    error_code: str,
) -> None:
    _, session_id, _, email = await _seed(engine, with_prior_evidence=False)
    code, payload = await _post_input(db_session, session_id, email, form=form, file=file)
    assert code == expected_code
    assert payload["error"]["code"] == error_code
    assert await _count(db_session, EvidenceUploadV2, session_id) == 0
    assert not [path for path in isolated_storage._root.rglob("*") if path.is_file()]  # noqa: SLF001


@pytest.mark.parametrize(
    "status",
    [
        TradeSessionV2Status.DRAFT,
        TradeSessionV2Status.ANALYZING,
        TradeSessionV2Status.ANALYZED,
        TradeSessionV2Status.WAITING,
        TradeSessionV2Status.CLOSED,
        TradeSessionV2Status.CLOSED_SKIPPED,
    ],
)
async def test_position_update_input_rejects_inactive_session_statuses(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
    status: TradeSessionV2Status,
) -> None:
    _, session_id, _, email = await _seed(engine, status=status, with_prior_evidence=False)
    code, payload = await _post_input(db_session, session_id, email)
    assert code == 409
    assert payload["error"]["code"] == "POSITION_UPDATE_INPUT_NOT_ALLOWED"
    assert await _count(db_session, EvidenceUploadV2, session_id) == 0
    assert not [path for path in isolated_storage._root.rglob("*") if path.is_file()]  # noqa: SLF001


async def test_position_eligibility_ownership_and_repeated_inputs(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
) -> None:
    _, session_id, _, owner_email = await _seed(engine, with_prior_evidence=True)
    _, other_session_id, _, other_email = await _seed(engine, with_prior_evidence=False)
    first_code, _ = await _post_input(db_session, session_id, owner_email)
    second_code, _ = await _post_input(
        db_session,
        session_id,
        owner_email,
        file=("second.png", IMAGE + b"2", "image/png"),
    )
    assert first_code == second_code == 201
    assert await _count(db_session, EvidenceUploadV2, session_id) == 3
    assert await _count(db_session, EvidenceUploadV2, other_session_id) == 0
    assert len([path for path in isolated_storage._root.rglob("*") if path.is_file()]) == 2  # noqa: SLF001

    cross_code, cross_payload = await _post_input(db_session, session_id, other_email)
    assert cross_code == 404
    assert cross_payload["error"]["code"] == "SESSION_NOT_FOUND"

    missing_code, missing_payload = await _post_input(db_session, uuid.uuid4(), owner_email)
    assert missing_code == 404
    assert missing_payload["error"]["code"] == "SESSION_NOT_FOUND"

    unauth_code, unauth_payload = await _post_input(db_session, other_session_id, None)
    assert unauth_code == 401
    assert unauth_payload["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.parametrize("position_status", [None, PositionV2Status.CLOSED])
async def test_position_update_input_rejects_missing_or_non_open_position(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
    position_status: PositionV2Status | None,
) -> None:
    _, session_id, _, email = await _seed(
        engine, position_status=position_status, with_prior_evidence=False
    )
    code, payload = await _post_input(db_session, session_id, email)
    assert code == 409
    assert payload["error"]["code"] == "POSITION_UPDATE_INPUT_NOT_ALLOWED"
    assert await _count(db_session, EvidenceUploadV2, session_id) == 0
    assert not [path for path in isolated_storage._root.rglob("*") if path.is_file()]  # noqa: SLF001


async def test_storage_and_persistence_failures_leave_no_partial_state(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session_id, _, email = await _seed(engine, with_prior_evidence=False)

    class FailingStorage:
        def store(self, **kwargs: object) -> object:
            raise StorageWriteError(message="test storage failure")

    monkeypatch.setattr(
        position_input_module,
        "create_file_storage",
        lambda _config=None: FailingStorage(),
    )
    code, payload = await _post_input(db_session, session_id, email)
    assert code == 500
    assert payload["error"]["code"] == "POSITION_UPDATE_INPUT_STORAGE_FAILED"
    assert await _count(db_session, EvidenceUploadV2, session_id) == 0

    monkeypatch.setattr(
        position_input_module, "create_file_storage", lambda _config=None: isolated_storage
    )

    async def fail_flush(*args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("test persistence failure")

    db_session.flush = fail_flush  # type: ignore[method-assign]
    service = PositionUpdateInputService(db_session, storage=isolated_storage)
    with pytest.raises(PositionUpdateInputPersistenceError):
        await service.submit(
            user_id=await db_session.scalar(
                select(TradeSessionV2.user_id).where(TradeSessionV2.id == session_id)
            ),
            session_id=session_id,
            original_filename="current.png",
            mime_type="image/png",
            content=IMAGE,
            current_price=Decimal("1234.567890"),
            observation_period=AnalysisRequestV2ObservationPeriod.MIDDAY,
            observation_timestamp=datetime(2026, 7, 30, 2, 15, tzinfo=timezone.utc),
        )
    assert await _count(db_session, EvidenceUploadV2, session_id) == 0
    assert not [path for path in isolated_storage._root.rglob("*") if path.is_file()]  # noqa: SLF001


async def test_concurrent_position_update_inputs_are_session_scoped(
    engine: AsyncEngine,
    isolated_storage: LocalFileStorage,
) -> None:
    owner = await _seed(engine, with_prior_evidence=False)
    _, session_b, _, _ = await _seed(engine, owner=(owner[0], owner[3]), with_prior_evidence=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def submit(session_id: uuid.UUID, filename: str) -> int:
        async with factory() as session:
            code, _ = await _post_input(
                session,
                session_id,
                owner[3],
                file=(filename, IMAGE + filename.encode(), "image/png"),
            )
            return code

    assert await asyncio.gather(
        submit(owner[1], "a.png"),
        submit(session_b, "b.png"),
    ) == [201, 201]
    async with factory() as session:
        assert await _count(session, EvidenceUploadV2, owner[1]) == 1
        assert await _count(session, EvidenceUploadV2, session_b) == 1
        positions = list(
            (
                await session.scalars(
                    select(PositionV2).where(PositionV2.session_id.in_([owner[1], session_b]))
                )
            ).all()
        )
        assert all(position.status is PositionV2Status.OPEN for position in positions)
    assert len([path for path in isolated_storage._root.rglob("*") if path.is_file()]) == 2  # noqa: SLF001
