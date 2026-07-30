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
from app.trade_workspace.models.position import PositionV2
from app.trade_workspace.models.session_decision import SessionDecisionV2
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services import wait_update_input as wait_update_module
from app.trade_workspace.services.wait_update_input import (
    WaitUpdateInputPersistenceError,
    WaitUpdateInputService,
)

pytestmark = pytest.mark.database

IMAGE = b"\x89PNG\r\n\x1a\n" + b"gate-p71-image"
FORM = {
    "current_price": "1234.567890",
    "observation_period": "MIDDAY",
    "observation_timestamp": "2026-07-30T09:15:00.123456+07:00",
}


async def _seed(
    engine: AsyncEngine,
    status: TradeSessionV2Status,
    *,
    owner: tuple[uuid.UUID, str] | None = None,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    if owner is None:
        user_id, email = uuid.uuid4(), f"p71-{uuid.uuid4()}@example.test"
        create_user = True
    else:
        user_id, email = owner
        create_user = False
    session_id = uuid.uuid4()
    async with engine.begin() as connection:
        if create_user:
            await connection.execute(
                User.__table__.insert().values(
                    id=user_id,
                    email=email,
                    password_hash=hash_password("testpass123"),
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
    return user_id, session_id, email


def _app(db_session: AsyncSession) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)

    async def override_db() -> AsyncSession:
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
        wait_update_module,
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
    file: tuple[str, bytes, str] | None = ("orderbook.png", IMAGE, "image/png"),
) -> tuple[int, dict[str, object]]:
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if email is not None:
            login = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "testpass123"},
            )
            assert login.status_code == 200
        files = {"orderbook": file} if file is not None else None
        response = await client.post(
            f"/api/v2/trade-sessions/{session_id}/wait-update-input",
            data=FORM if form is None else form,
            files=files,
        )
    return response.status_code, response.json()


async def _count(db_session: AsyncSession, model: type[object], session_id: uuid.UUID) -> int:
    return int(
        await db_session.scalar(
            select(func.count()).select_from(model).where(model.session_id == session_id)  # type: ignore[attr-defined]
        )
    )


async def test_owner_can_submit_wait_update_input_and_repeat(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.WAITING)
    code, payload = await _post_input(db_session, session_id, email)
    assert code == 201
    assert payload["session_id"] == str(session_id)
    assert payload["evidence_type"] == "ORDERBOOK"
    assert payload["original_filename"] == "orderbook.png"
    assert payload["mime_type"] == "image/png"
    assert payload["size_bytes"] == len(IMAGE)
    assert payload["current_price"] == "1234.567890"
    assert payload["observation_period"] == "MIDDAY"
    assert payload["observation_timestamp"] == "2026-07-30T09:15:00.123456+07:00"
    assert payload["session_status"] == "WAITING"
    assert len([path for path in isolated_storage._root.rglob("*") if path.is_file()]) == 1  # noqa: SLF001
    assert await _count(db_session, EvidenceUploadV2, session_id) == 1
    evidence = await db_session.scalar(
        select(EvidenceUploadV2).where(EvidenceUploadV2.session_id == session_id)
    )
    assert evidence is not None
    assert evidence.evidence_type is EvidenceUploadV2Type.ORDERBOOK
    assert evidence.analysis_request_id is None
    assert evidence.current_price == Decimal("1234.567890")
    assert evidence.observation_timestamp == datetime(
        2026, 7, 30, 2, 15, 0, 123456, tzinfo=timezone.utc
    )
    assert evidence.uploaded_at is not None
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None and session.status is TradeSessionV2Status.WAITING
    assert await _count(db_session, AnalysisRequestV2, session_id) == 0
    assert await _count(db_session, SessionDecisionV2, session_id) == 0
    assert await _count(db_session, PositionV2, session_id) == 0
    assert await _count(db_session, TradeClosureV2, session_id) == 0

    second_code, _ = await _post_input(
        db_session,
        session_id,
        email,
        file=("../second-orderbook.png", IMAGE + b"2", "image/png"),
    )
    assert second_code == 201
    assert await _count(db_session, EvidenceUploadV2, session_id) == 2
    assert len([path for path in isolated_storage._root.rglob("*") if path.is_file()]) == 2  # noqa: SLF001


@pytest.mark.parametrize(
    "form, file, expected_code, expected_error_code",
    [
        (
            {
                "observation_period": "MIDDAY",
                "observation_timestamp": FORM["observation_timestamp"],
            },
            ("x.png", IMAGE, "image/png"),
            422,
            "VALIDATION_ERROR",
        ),
        (
            {**FORM, "current_price": "not-a-price"},
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
            "WAIT_UPDATE_INPUT_INVALID",
        ),
        (FORM, None, 422, "VALIDATION_ERROR"),
        (FORM, ("empty.png", b"", "image/png"), 422, "WAIT_UPDATE_INPUT_INVALID"),
        (FORM, ("text.txt", IMAGE, "text/plain"), 422, "WAIT_UPDATE_INPUT_INVALID"),
        (
            FORM,
            ("large.png", b"x" * (10 * 1024 * 1024 + 1), "image/png"),
            422,
            "WAIT_UPDATE_INPUT_INVALID",
        ),
    ],
)
async def test_invalid_wait_update_input_is_rejected_without_persistence(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
    form: dict[str, str],
    file: tuple[str, bytes, str] | None,
    expected_code: int,
    expected_error_code: str,
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.WAITING)
    code, payload = await _post_input(
        db_session, session_id, email, form=form, file=file
    )
    assert code == expected_code
    assert payload["error"]["code"] == expected_error_code
    assert await _count(db_session, EvidenceUploadV2, session_id) == 0
    assert not [path for path in isolated_storage._root.rglob("*") if path.is_file()]  # noqa: SLF001


@pytest.mark.parametrize(
    "status",
    [
        TradeSessionV2Status.DRAFT,
        TradeSessionV2Status.ANALYZING,
        TradeSessionV2Status.ANALYZED,
        TradeSessionV2Status.OPEN_POSITION,
        TradeSessionV2Status.CLOSED,
        TradeSessionV2Status.CLOSED_SKIPPED,
    ],
)
async def test_wait_update_input_rejects_inactive_statuses(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
    status: TradeSessionV2Status,
) -> None:
    _, session_id, email = await _seed(engine, status)
    code, payload = await _post_input(db_session, session_id, email)
    assert code == 409
    assert payload["error"]["code"] == "WAIT_UPDATE_INPUT_NOT_ALLOWED"
    assert await _count(db_session, EvidenceUploadV2, session_id) == 0
    assert not [path for path in isolated_storage._root.rglob("*") if path.is_file()]  # noqa: SLF001


async def test_wait_update_input_enforces_ownership_and_authentication(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
) -> None:
    _, session_id, owner_email = await _seed(engine, TradeSessionV2Status.WAITING)
    _, other_session_id, other_email = await _seed(engine, TradeSessionV2Status.WAITING)
    cross_code, cross_payload = await _post_input(db_session, session_id, other_email)
    missing_code, missing_payload = await _post_input(db_session, uuid.uuid4(), owner_email)
    unauth_code, unauth_payload = await _post_input(db_session, other_session_id, None)
    assert cross_code == missing_code == 404
    assert (
        cross_payload["error"]["code"]
        == missing_payload["error"]["code"]
        == "SESSION_NOT_FOUND"
    )
    assert unauth_code == 401
    assert unauth_payload["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert not [path for path in isolated_storage._root.rglob("*") if path.is_file()]  # noqa: SLF001


async def test_storage_failure_leaves_no_partial_row_or_file(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.WAITING)

    class FailingStorage:
        def store(self, **kwargs: object) -> object:
            raise StorageWriteError(message="test storage failure")

    monkeypatch.setattr(
        wait_update_module,
        "create_file_storage",
        lambda _config=None: FailingStorage(),
    )
    code, payload = await _post_input(db_session, session_id, email)
    assert code == 500
    assert payload["error"]["code"] == "WAIT_UPDATE_INPUT_STORAGE_FAILED"
    assert await _count(db_session, EvidenceUploadV2, session_id) == 0
    assert not [path for path in isolated_storage._root.rglob("*") if path.is_file()]  # noqa: SLF001


async def test_persistence_failure_removes_only_current_file(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
) -> None:
    _, session_id, _ = await _seed(engine, TradeSessionV2Status.WAITING)

    async def fail_flush(*args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("test persistence failure")

    db_session.flush = fail_flush  # type: ignore[method-assign]
    service = WaitUpdateInputService(db_session, storage=isolated_storage)
    with pytest.raises(WaitUpdateInputPersistenceError):
        user_id = await db_session.scalar(
            select(TradeSessionV2.user_id).where(TradeSessionV2.id == session_id)
        )
        await service.submit(
            user_id=user_id,
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


async def test_concurrent_inputs_and_multi_session_independence(
    engine: AsyncEngine,
    isolated_storage: LocalFileStorage,
) -> None:
    owner = await _seed(engine, TradeSessionV2Status.WAITING)
    _, session_b, _ = await _seed(
        engine,
        TradeSessionV2Status.WAITING,
        owner=(owner[0], owner[2]),
    )
    session_a = owner[1]
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def submit(session_id: uuid.UUID, filename: str) -> int:
        async with factory() as session:
            code, _ = await _post_input(
                session,
                session_id,
                owner[2],
                file=(filename, IMAGE + filename.encode(), "image/png"),
            )
            return code

    results = await asyncio.gather(
        submit(session_a, "a.png"),
        submit(session_b, "b.png"),
    )
    assert results == [201, 201]
    async with factory() as session:
        assert await _count(session, EvidenceUploadV2, session_a) == 1
        assert await _count(session, EvidenceUploadV2, session_b) == 1
        statuses = list(
            (
                await session.scalars(
                    select(TradeSessionV2.status).where(
                        TradeSessionV2.id.in_([session_a, session_b])
                    )
                )
            ).all()
        )
        assert statuses == [TradeSessionV2Status.WAITING, TradeSessionV2Status.WAITING]
    assert len([path for path in isolated_storage._root.rglob("*") if path.is_file()]) == 2  # noqa: SLF001
