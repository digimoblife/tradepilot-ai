from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import app.trade_workspace.services.evidence_uploads as evidence_service
from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.storage import LocalFileStorage
from app.storage.base import StorageError
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.analysis_request import AnalysisRequestV2
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database

_PNG = b"\x89PNG\r\n\x1a\ninitial-evidence"


async def _make_user_and_session(
    engine: AsyncEngine,
    *,
    status: TradeSessionV2Status = TradeSessionV2Status.DRAFT,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    email = f"p52-{user_id}@example.test"
    async with engine.begin() as connection:
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


def _build_app(db_session: AsyncSession) -> FastAPI:
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
async def client(db_session: AsyncSession) -> AsyncClient:
    app = _build_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def _login(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    assert response.status_code == 200


def _files(*, omit: str | None = None, content: bytes = _PNG) -> dict[str, tuple[str, bytes, str]]:
    all_files = {
        "orderbook": ("orderbook.png", content, "image/png"),
        "chart_3_month": ("three-month.png", content, "image/png"),
        "chart_6_month": ("six-month.png", content, "image/png"),
        "foreign_flow_1w": ("foreign-flow.png", content, "image/png"),
    }
    if omit is not None:
        del all_files[omit]
    return all_files


def _storage_factory(root: Path) -> Callable[[object], LocalFileStorage]:
    return lambda _config: LocalFileStorage(root)


async def _evidence_rows(session: AsyncSession, session_id: uuid.UUID) -> list[EvidenceUploadV2]:
    return list(
        (
            await session.scalars(
                select(EvidenceUploadV2)
                .where(EvidenceUploadV2.session_id == session_id)
                .order_by(EvidenceUploadV2.id)
            )
        ).all()
    )


def _stored_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


async def test_owner_uploads_exact_initial_set_and_persists_metadata(
    client: AsyncClient,
    engine: AsyncEngine,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, session_id, email = await _make_user_and_session(engine)
    monkeypatch.setattr(evidence_service, "create_file_storage", _storage_factory(tmp_path))
    await _login(client, email)

    response = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence",
        files=_files(),
    )

    assert response.status_code == 201
    items = response.json()["evidence"]
    assert [item["evidence_type"] for item in items] == [
        "ORDERBOOK",
        "CHART_3_MONTH",
        "CHART_6_MONTH",
        "FOREIGN_FLOW_1W",
    ]
    required_fields = {
        "id",
        "evidence_type",
        "original_filename",
        "mime_type",
        "size_bytes",
        "uploaded_at",
    }
    assert all(set(item) == required_fields for item in items)
    assert [item["original_filename"] for item in items] == [
        "orderbook.png",
        "three-month.png",
        "six-month.png",
        "foreign-flow.png",
    ]
    assert all(item["mime_type"] == "image/png" and item["size_bytes"] > 0 for item in items)
    assert len(_stored_files(tmp_path)) == 4

    rows = await _evidence_rows(db_session, session_id)
    assert len(rows) == 4
    assert {row.session_id for row in rows} == {session_id}
    assert {row.evidence_type for row in rows} == {
        EvidenceUploadV2Type.ORDERBOOK,
        EvidenceUploadV2Type.CHART_3_MONTH,
        EvidenceUploadV2Type.CHART_6_MONTH,
        EvidenceUploadV2Type.FOREIGN_FLOW_1W,
    }
    assert all(row.analysis_request_id is None for row in rows)
    assert all(row.observation_period is None for row in rows)
    assert all(row.file_path and not Path(row.file_path).is_absolute() for row in rows)
    assert all(row.size_bytes == len(_PNG) for row in rows)
    assert all(row.uploaded_at is not None for row in rows)
    assert all(row.session_id == session_id for row in rows)
    owner = await db_session.scalar(
        select(TradeSessionV2.user_id).where(TradeSessionV2.id == session_id)
    )
    assert user_id == owner
    assert (
        await db_session.scalar(
            select(func.count(AnalysisRequestV2.id)).where(
                AnalysisRequestV2.session_id == session_id
            )
        )
        == 0
    )


@pytest.mark.parametrize(
    "omit", ["orderbook", "chart_3_month", "chart_6_month", "foreign_flow_1w"]
)
async def test_missing_required_file_is_rejected_without_side_effects(
    client: AsyncClient,
    engine: AsyncEngine,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omit: str,
) -> None:
    _, session_id, email = await _make_user_and_session(engine)
    monkeypatch.setattr(evidence_service, "create_file_storage", _storage_factory(tmp_path))
    await _login(client, email)

    response = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence",
        files=_files(omit=omit),
    )

    assert response.status_code == 422
    assert len(await _evidence_rows(db_session, session_id)) == 0
    assert _stored_files(tmp_path) == []


async def test_broker_flow_is_rejected_as_initial_evidence(
    client: AsyncClient,
    engine: AsyncEngine,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session_id, email = await _make_user_and_session(engine)
    monkeypatch.setattr(evidence_service, "create_file_storage", _storage_factory(tmp_path))
    await _login(client, email)
    files = _files()
    files["broker_flow_1d"] = ("broker-flow.png", _PNG, "image/png")

    response = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence",
        files=files,
    )

    assert response.status_code == 422
    assert len(await _evidence_rows(db_session, session_id)) == 0
    assert _stored_files(tmp_path) == []


@pytest.mark.parametrize(
    ("content", "mime_type"),
    [(b"", "image/png"), (_PNG, "application/pdf"), (_PNG, "image/gif")],
)
async def test_invalid_file_is_rejected_without_side_effects(
    client: AsyncClient,
    engine: AsyncEngine,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: bytes,
    mime_type: str,
) -> None:
    _, session_id, email = await _make_user_and_session(engine)
    monkeypatch.setattr(evidence_service, "create_file_storage", _storage_factory(tmp_path))
    await _login(client, email)
    files = {key: (filename, content, mime_type) for key, (filename, _, _) in _files().items()}

    response = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence",
        files=files,
    )

    assert response.status_code == 422
    assert len(await _evidence_rows(db_session, session_id)) == 0
    assert _stored_files(tmp_path) == []


async def test_size_limit_and_auth_ownership_and_status_are_enforced(
    client: AsyncClient,
    engine: AsyncEngine,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session_id, owner_email = await _make_user_and_session(engine)
    _, _, other_email = await _make_user_and_session(engine)
    monkeypatch.setattr(evidence_service, "create_file_storage", _storage_factory(tmp_path))

    unauthenticated = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=_files()
    )
    assert unauthenticated.status_code == 401

    await _login(client, other_email)
    cross_user = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=_files()
    )
    assert cross_user.status_code == 404

    await client.post("/api/auth/logout")
    await _login(client, owner_email)
    oversized = _files(content=b"x" * (10 * 1024 * 1024 + 1))
    too_large = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=oversized
    )
    assert too_large.status_code == 422
    assert _stored_files(tmp_path) == []

    await db_session.execute(
        TradeSessionV2.__table__.update()
        .where(TradeSessionV2.id == session_id)
        .values(status=TradeSessionV2Status.ANALYZED)
    )
    await db_session.commit()
    ineligible = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=_files()
    )
    assert ineligible.status_code == 409
    assert len(await _evidence_rows(db_session, session_id)) == 0


async def test_duplicate_complete_or_partial_set_is_rejected_unchanged(
    client: AsyncClient,
    engine: AsyncEngine,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session_id, email = await _make_user_and_session(engine)
    monkeypatch.setattr(evidence_service, "create_file_storage", _storage_factory(tmp_path))
    await _login(client, email)
    first = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=_files()
    )
    assert first.status_code == 201
    before_rows = [(row.id, row.file_path) for row in await _evidence_rows(db_session, session_id)]
    before_files = sorted(str(path.relative_to(tmp_path)) for path in _stored_files(tmp_path))

    duplicate = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=_files()
    )
    assert duplicate.status_code == 409
    assert [
        (row.id, row.file_path) for row in await _evidence_rows(db_session, session_id)
    ] == before_rows
    after_files = sorted(str(path.relative_to(tmp_path)) for path in _stored_files(tmp_path))
    assert after_files == before_files

    _, partial_session_id, partial_email = await _make_user_and_session(engine)
    partial_storage = LocalFileStorage(tmp_path)
    partial_owner = await db_session.scalar(
        select(TradeSessionV2.user_id).where(TradeSessionV2.id == partial_session_id)
    )
    assert partial_owner is not None
    seeded = partial_storage.store(
        user_id=partial_owner,
        session_id=partial_session_id,
        original_filename="existing.png",
        content=_PNG,
    )
    db_session.add(
        EvidenceUploadV2(
            session_id=partial_session_id,
            evidence_type=EvidenceUploadV2Type.ORDERBOOK,
            file_path=seeded.file_reference,
            original_filename="existing.png",
            mime_type="image/png",
            size_bytes=len(_PNG),
        )
    )
    await db_session.commit()
    await client.post("/api/auth/logout")
    await _login(client, partial_email)
    partial_duplicate = await client.post(
        f"/api/v2/trade-sessions/{partial_session_id}/initial-evidence", files=_files()
    )
    assert partial_duplicate.status_code == 409
    assert len(await _evidence_rows(db_session, partial_session_id)) == 1


async def test_initial_evidence_cannot_be_appended_or_replaced_after_submission(
    client: AsyncClient,
    engine: AsyncEngine,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session_id, email = await _make_user_and_session(engine)
    monkeypatch.setattr(evidence_service, "create_file_storage", _storage_factory(tmp_path))
    await _login(client, email)
    first = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=_files()
    )
    assert first.status_code == 201
    submitted = await client.post(f"/api/v2/trade-sessions/{session_id}/initial-analysis")
    assert submitted.status_code == 202
    before = [(item.id, item.file_path) for item in await _evidence_rows(db_session, session_id)]

    repeated = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=_files()
    )

    assert repeated.status_code == 409
    assert [
        (item.id, item.file_path) for item in await _evidence_rows(db_session, session_id)
    ] == before
    assert len(before) == 4


class _FailingStorage:
    def __init__(self, root: Path) -> None:
        self._delegate = LocalFileStorage(root)
        self.created: list[str] = []
        self.deleted: list[str] = []

    def store(self, **kwargs: object):
        if len(self.created) == 1:
            raise StorageError(code="STORAGE_WRITE_FAILED", message="test failure")
        result = self._delegate.store(**kwargs)  # type: ignore[arg-type]
        self.created.append(result.file_reference)
        return result

    def delete(self, *, file_reference: str) -> None:
        self.deleted.append(file_reference)
        self._delegate.delete(file_reference=file_reference)


async def test_storage_failure_cleans_current_operation(
    client: AsyncClient,
    engine: AsyncEngine,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session_id, email = await _make_user_and_session(engine)
    storage = _FailingStorage(tmp_path)
    monkeypatch.setattr(evidence_service, "create_file_storage", lambda _config: storage)
    await _login(client, email)

    response = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=_files()
    )

    assert response.status_code == 500
    assert len(storage.deleted) == 1
    assert _stored_files(tmp_path) == []
    assert len(await _evidence_rows(db_session, session_id)) == 0


async def test_persistence_failure_rolls_back_and_cleans_files(
    client: AsyncClient,
    engine: AsyncEngine,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, session_id, email = await _make_user_and_session(engine)
    monkeypatch.setattr(evidence_service, "create_file_storage", _storage_factory(tmp_path))
    original_commit = db_session.commit

    async def fail_commit() -> None:
        raise SQLAlchemyError("test persistence failure")

    await _login(client, email)
    monkeypatch.setattr(db_session, "commit", fail_commit)
    response = await client.post(
        f"/api/v2/trade-sessions/{session_id}/initial-evidence", files=_files()
    )
    assert response.status_code == 500
    assert _stored_files(tmp_path) == []
    monkeypatch.setattr(db_session, "commit", original_commit)
    assert len(await _evidence_rows(db_session, session_id)) == 0
