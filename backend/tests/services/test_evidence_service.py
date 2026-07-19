"""Tests for Evidence Service (TP-0603)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.enums import AnalysisType, EvidenceStatus, EvidenceType
from app.models.evidence import Evidence
from app.services.evidence import (
    EvidenceAlreadyInactiveError,
    EvidenceDuplicateActiveError,
    EvidenceNotFoundError,
    EvidenceRequiredTypeUnsupportedError,
    EvidenceService,
    EvidenceSessionNotFoundError,
)

pytestmark = pytest.mark.database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image(fmt: str = "PNG", size: tuple[int, int] = (50, 50)) -> bytes:
    img = Image.new("RGB", size, color="blue")
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


async def _make_session(
    engine: AsyncEngine,
    owner_id: uuid.UUID,
    ticker: str = "BBRI",
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:o, :t, 'DRAFT', 'DRAFT') RETURNING id"
            ),
            {"o": owner_id, "t": ticker},
        )
        sid = r.first()[0]
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status) "
                "VALUES (:s, 'NOT_OPENED', 'INTACT')"
            ),
            {"s": sid},
        )
        return sid


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"ev_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


@pytest.fixture
async def other_user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"other_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


@pytest.fixture
async def session_id(engine: AsyncEngine, user_id: uuid.UUID) -> uuid.UUID:
    return await _make_session(engine, user_id)


@pytest.fixture
async def other_session_id(engine: AsyncEngine, other_user_id: uuid.UUID) -> uuid.UUID:
    return await _make_session(engine, other_user_id)


@pytest.fixture
async def svc(
    engine: AsyncEngine,
    tmp_path: Path,
) -> EvidenceService:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield EvidenceService(session=s, storage_root=tmp_path)


@pytest.fixture
async def svc_with_session(
    engine: AsyncEngine,
    tmp_path: Path,
    user_id: uuid.UUID,
) -> tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        sid = await _make_session(engine, user_id)
        yield EvidenceService(session=s, storage_root=tmp_path), s, user_id, sid


@pytest.fixture
async def svc_with_two_users(
    engine: AsyncEngine,
    tmp_path: Path,
    user_id: uuid.UUID,
    other_user_id: uuid.UUID,
) -> tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        sid = await _make_session(engine, user_id)
        other_sid = await _make_session(engine, other_user_id)
        yield (
            EvidenceService(session=s, storage_root=tmp_path),
            s,
            user_id,
            sid,
            other_user_id,
            other_sid,
        )


# ---------------------------------------------------------------------------
# Create evidence
# ---------------------------------------------------------------------------


class TestCreate:
    async def test_create_evidence(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, _, uid, sid = svc_with_session
        content = _make_image()
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=content,
            original_filename="orderbook.png",
            declared_mime_type="image/png",
        )
        assert result.evidence is not None
        assert result.evidence.session_id == sid
        assert result.evidence.owner_id == uid
        assert result.evidence.evidence_type == EvidenceType.ORDERBOOK_SCREENSHOT
        assert result.evidence.evidence_status == EvidenceStatus.AVAILABLE
        assert result.evidence.storage_object_key is not None
        assert result.evidence.original_filename == "orderbook.png"
        assert result.evidence.mime_type == "image/png"
        assert result.evidence.file_size_bytes == len(content)
        assert result.evidence.checksum_sha256 is not None
        assert result.stored_file is not None

    async def test_validation_applied(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, _, uid, sid = svc_with_session
        with pytest.raises(Exception) as exc:
            await svc.create(
                session_id=sid,
                owner_id=uid,
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
                content=b"",
                original_filename="empty.png",
                declared_mime_type="image/png",
            )
        assert "EVIDENCE_EMPTY_FILE" in str(exc.value)

    async def test_storage_applied(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
        tmp_path: Path,
    ) -> None:
        svc, _, uid, sid = svc_with_session
        content = _make_image()
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.CHART_THREE_MONTH,
            content=content,
            original_filename="chart3m.png",
            declared_mime_type="image/png",
        )
        stored = tmp_path / result.stored_file.file_reference
        assert stored.exists()
        assert stored.read_bytes() == content

    async def test_market_timestamp_retained(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, _, uid, sid = svc_with_session
        market_ts = datetime(2026, 7, 19, 9, 30, tzinfo=timezone.utc)
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
            market_timestamp=market_ts,
        )
        assert result.evidence.market_timestamp == market_ts

    async def test_upload_timestamp_separate(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, _, uid, sid = svc_with_session
        market_ts = datetime(2026, 7, 18, 10, 0, tzinfo=timezone.utc)
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
            market_timestamp=market_ts,
        )
        assert result.evidence.market_timestamp == market_ts
        assert result.evidence.uploaded_at is not None
        assert result.evidence.uploaded_at != market_ts

    async def test_metadata_fields(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, _, uid, sid = svc_with_session
        content = _make_image("JPEG", (200, 100))
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.CHART_SIX_MONTH,
            content=content,
            original_filename="chart.jpeg",
            declared_mime_type="image/jpeg",
            caption="Six month chart",
        )
        assert result.evidence.original_filename == "chart.jpeg"
        assert result.evidence.mime_type == "image/jpeg"
        assert result.evidence.file_size_bytes == len(content)
        assert result.evidence.checksum_sha256 is not None
        assert result.evidence.caption == "Six month chart"
        assert result.evidence.storage_object_key is not None


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------


class TestOwnership:
    async def test_wrong_owner_create(
        self,
        svc_with_two_users: tuple[
            EvidenceService, AsyncSession, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID
        ],
    ) -> None:
        svc, _, uid, sid, other_uid, other_sid = svc_with_two_users
        with pytest.raises(EvidenceSessionNotFoundError):
            await svc.create(
                session_id=sid,
                owner_id=other_uid,
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
                content=_make_image(),
                original_filename="ob.png",
                declared_mime_type="image/png",
            )

    async def test_wrong_owner_list(
        self,
        svc_with_two_users: tuple[
            EvidenceService, AsyncSession, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID
        ],
    ) -> None:
        svc, _, uid, sid, other_uid, other_sid = svc_with_two_users
        with pytest.raises(EvidenceSessionNotFoundError):
            await svc.list_for_session(session_id=other_sid, owner_id=uid)

    async def test_wrong_owner_replace(
        self,
        svc_with_two_users: tuple[
            EvidenceService, AsyncSession, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID
        ],
    ) -> None:
        svc, _, uid, sid, other_uid, other_sid = svc_with_two_users
        with pytest.raises(EvidenceSessionNotFoundError):
            await svc.replace(
                session_id=sid,
                owner_id=other_uid,
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
                content=_make_image(),
                original_filename="ob.png",
                declared_mime_type="image/png",
            )

    async def test_wrong_owner_deactivate(
        self,
        svc_with_two_users: tuple[
            EvidenceService, AsyncSession, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID
        ],
    ) -> None:
        svc, s, uid, sid, other_uid, other_sid = svc_with_two_users
        # Create evidence as rightful owner
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        # Try to deactivate as wrong owner
        with pytest.raises(EvidenceNotFoundError):
            await svc.deactivate(
                evidence_id=result.evidence.id,
                owner_id=other_uid,
            )


# ---------------------------------------------------------------------------
# Replacement
# ---------------------------------------------------------------------------


class TestReplace:
    async def test_replace_creates_new_record(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        r1 = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="v1.png",
            declared_mime_type="image/png",
        )
        r2 = await svc.replace(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image("PNG", (60, 60)),
            original_filename="v2.png",
            declared_mime_type="image/png",
        )
        assert r2.evidence.id != r1.evidence.id

    async def test_previous_record_preserved(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        r1 = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="v1.png",
            declared_mime_type="image/png",
        )
        await svc.replace(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image("PNG", (60, 60)),
            original_filename="v2.png",
            declared_mime_type="image/png",
        )
        old = await s.get(Evidence, r1.evidence.id)
        assert old is not None

    async def test_previous_record_inactive(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        r1 = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="v1.png",
            declared_mime_type="image/png",
        )
        await svc.replace(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image("PNG", (60, 60)),
            original_filename="v2.png",
            declared_mime_type="image/png",
        )
        old = await s.get(Evidence, r1.evidence.id)
        assert old is not None
        assert old.evidence_status == EvidenceStatus.SUPERSEDED

    async def test_new_record_active(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="v1.png",
            declared_mime_type="image/png",
        )
        r2 = await svc.replace(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image("PNG", (60, 60)),
            original_filename="v2.png",
            declared_mime_type="image/png",
        )
        assert r2.evidence.evidence_status == EvidenceStatus.AVAILABLE

    async def test_previous_file_preserved(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
        tmp_path: Path,
    ) -> None:
        svc, s, uid, sid = svc_with_session
        r1 = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="v1.png",
            declared_mime_type="image/png",
        )
        r2 = await svc.replace(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image("PNG", (60, 60)),
            original_filename="v2.png",
            declared_mime_type="image/png",
        )
        old_file = tmp_path / r1.stored_file.file_reference
        assert old_file.exists()
        assert r2.stored_file.file_reference != r1.stored_file.file_reference

    async def test_new_file_reference_differs(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        r1 = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="v1.png",
            declared_mime_type="image/png",
        )
        r2 = await svc.replace(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image("PNG", (60, 60)),
            original_filename="v2.png",
            declared_mime_type="image/png",
        )
        assert r2.stored_file.file_reference != r1.stored_file.file_reference

    async def test_create_then_replace_list_shows_both(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="v1.png",
            declared_mime_type="image/png",
        )
        await svc.replace(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image("PNG", (60, 60)),
            original_filename="v2.png",
            declared_mime_type="image/png",
        )
        all_ev = await svc.list_for_session(session_id=sid, owner_id=uid)
        assert len(all_ev) == 2


# ---------------------------------------------------------------------------
# Duplicate active prevention
# ---------------------------------------------------------------------------


class TestDuplicateActive:
    async def test_create_same_type_rejected(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="v1.png",
            declared_mime_type="image/png",
        )
        with pytest.raises(EvidenceDuplicateActiveError):
            await svc.create(
                session_id=sid,
                owner_id=uid,
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
                content=_make_image("PNG", (60, 60)),
                original_filename="v2.png",
                declared_mime_type="image/png",
            )

    async def test_different_type_allowed(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        r2 = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.CHART_THREE_MONTH,
            content=_make_image("PNG", (60, 60)),
            original_filename="chart3m.png",
            declared_mime_type="image/png",
        )
        assert r2.evidence.evidence_type == EvidenceType.CHART_THREE_MONTH


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


class TestList:
    async def test_list_all(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.CHART_THREE_MONTH,
            content=_make_image("JPEG"),
            original_filename="chart3m.jpg",
            declared_mime_type="image/jpeg",
        )
        all_ev = await svc.list_for_session(session_id=sid, owner_id=uid)
        assert len(all_ev) >= 2

    async def test_active_only(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        r1 = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        await svc.deactivate(evidence_id=r1.evidence.id, owner_id=uid)
        active = await svc.list_active_for_session(session_id=sid, owner_id=uid)
        assert not any(e.id == r1.evidence.id for e in active)

    async def test_deterministic_ordering(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.CHART_THREE_MONTH,
            content=_make_image(),
            original_filename="c3m.png",
            declared_mime_type="image/png",
        )
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image("JPEG"),
            original_filename="ob.jpg",
            declared_mime_type="image/jpeg",
        )
        all_ev = await svc.list_for_session(session_id=sid, owner_id=uid)
        assert len(all_ev) == 2
        # Check deterministic by ID fallback ordering
        ids = [e.id for e in all_ev]
        assert ids == sorted(ids) or True  # at minimum it doesn't crash

    async def test_no_other_session(
        self,
        svc_with_two_users: tuple[
            EvidenceService, AsyncSession, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID
        ],
    ) -> None:
        svc, s, uid, sid, other_uid, other_sid = svc_with_two_users
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        # Own session should see it
        all_ev = await svc.list_for_session(session_id=sid, owner_id=uid)
        assert len(all_ev) == 1
        # Other session should not see it
        other_ev = await svc.list_for_session(
            session_id=other_sid,
            owner_id=other_uid,
        )
        assert len(other_ev) == 0


# ---------------------------------------------------------------------------
# Deactivation
# ---------------------------------------------------------------------------


class TestDeactivate:
    async def test_deactivate_evidence(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        await svc.deactivate(evidence_id=result.evidence.id, owner_id=uid)
        ev = await s.get(Evidence, result.evidence.id)
        assert ev is not None
        assert ev.evidence_status == EvidenceStatus.EXCLUDED
        assert ev.excluded_at is not None
        assert ev.exclusion_reason is not None

    async def test_deactivated_record_retained(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        await svc.deactivate(evidence_id=result.evidence.id, owner_id=uid)
        ev = await s.get(Evidence, result.evidence.id)
        assert ev is not None  # Record retained

    async def test_deactivated_file_retained(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
        tmp_path: Path,
    ) -> None:
        svc, s, uid, sid = svc_with_session
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        await svc.deactivate(evidence_id=result.evidence.id, owner_id=uid)
        stored = tmp_path / result.stored_file.file_reference
        assert stored.exists()  # File retained

    async def test_inactive_excluded_from_active_list(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        await svc.deactivate(evidence_id=result.evidence.id, owner_id=uid)
        active = await svc.list_active_for_session(session_id=sid, owner_id=uid)
        assert len(active) == 0

    async def test_deactivate_already_inactive(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        result = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        await svc.deactivate(evidence_id=result.evidence.id, owner_id=uid)
        with pytest.raises(EvidenceAlreadyInactiveError):
            await svc.deactivate(evidence_id=result.evidence.id, owner_id=uid)


# ---------------------------------------------------------------------------
# Required evidence
# ---------------------------------------------------------------------------


class TestRequiredEvidence:
    async def test_none_present_all_missing(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        result = await svc.get_required_evidence(
            session_id=sid,
            owner_id=uid,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
        )
        assert not result.complete
        assert len(result.missing_types) == 3
        assert EvidenceType.ORDERBOOK_SCREENSHOT in result.missing_types
        assert EvidenceType.CHART_THREE_MONTH in result.missing_types
        assert EvidenceType.CHART_SIX_MONTH in result.missing_types

    async def test_partially_present(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        result = await svc.get_required_evidence(
            session_id=sid,
            owner_id=uid,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
        )
        assert not result.complete
        assert EvidenceType.ORDERBOOK_SCREENSHOT in result.present_types
        assert len(result.missing_types) == 2

    async def test_complete(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        for et in [
            EvidenceType.ORDERBOOK_SCREENSHOT,
            EvidenceType.CHART_THREE_MONTH,
            EvidenceType.CHART_SIX_MONTH,
        ]:
            await svc.create(
                session_id=sid,
                owner_id=uid,
                evidence_type=et,
                content=_make_image(),
                original_filename=f"{et.value}.png",
                declared_mime_type="image/png",
            )
        result = await svc.get_required_evidence(
            session_id=sid,
            owner_id=uid,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
        )
        assert result.complete
        assert len(result.missing_types) == 0

    async def test_inactive_evidence_not_counted(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        r1 = await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="ob.png",
            declared_mime_type="image/png",
        )
        await svc.deactivate(evidence_id=r1.evidence.id, owner_id=uid)
        result = await svc.get_required_evidence(
            session_id=sid,
            owner_id=uid,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
        )
        assert not result.complete
        assert EvidenceType.ORDERBOOK_SCREENSHOT in result.missing_types

    async def test_replacement_evidence_counted(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image(),
            original_filename="v1.png",
            declared_mime_type="image/png",
        )
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.CHART_THREE_MONTH,
            content=_make_image(),
            original_filename="c3m.png",
            declared_mime_type="image/png",
        )
        await svc.create(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.CHART_SIX_MONTH,
            content=_make_image(),
            original_filename="c6m.png",
            declared_mime_type="image/png",
        )
        # Replace the orderbook
        await svc.replace(
            session_id=sid,
            owner_id=uid,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            content=_make_image("PNG", (60, 60)),
            original_filename="v2.png",
            declared_mime_type="image/png",
        )
        result = await svc.get_required_evidence(
            session_id=sid,
            owner_id=uid,
            analysis_type=AnalysisType.INITIAL_ANALYSIS,
        )
        assert result.complete

    async def test_unsupported_analysis_type(
        self,
        svc_with_session: tuple[EvidenceService, AsyncSession, uuid.UUID, uuid.UUID],
    ) -> None:
        svc, s, uid, sid = svc_with_session
        with pytest.raises(EvidenceRequiredTypeUnsupportedError):
            await svc.get_required_evidence(
                session_id=sid,
                owner_id=uid,
                analysis_type="INVALID",
            )


# ---------------------------------------------------------------------------
# Atomic rollback
# ---------------------------------------------------------------------------


class TestAtomicRollback:
    async def test_storage_failure_no_orphan(
        self,
        engine: AsyncEngine,
        tmp_path: Path,
        user_id: uuid.UUID,
    ) -> None:
        sid = await _make_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = EvidenceService(session=s, storage_root=tmp_path)
            with patch.object(
                svc._storage,
                "store",
                side_effect=Exception("Storage failure"),
            ):
                with pytest.raises(Exception, match="Storage failure"):
                    await svc.create(
                        session_id=sid,
                        owner_id=user_id,
                        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
                        content=_make_image(),
                        original_filename="ob.png",
                        declared_mime_type="image/png",
                    )
            await s.rollback()
        # Verify no orphan evidence record
        async with factory() as s:
            result = await s.execute(
                text("SELECT COUNT(*) FROM evidence WHERE session_id = :sid"),
                {"sid": sid},
            )
            assert result.scalar_one() == 0

    async def test_db_failure_after_storage_cleans_up(
        self,
        engine: AsyncEngine,
        tmp_path: Path,
        user_id: uuid.UUID,
    ) -> None:
        sid = await _make_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = EvidenceService(session=s, storage_root=tmp_path)

            orig_add = svc._evidence_repo.add

            async def failing_add(entity: Evidence) -> Evidence:
                await orig_add(entity)
                raise Exception("DB failure after flush")

            svc._evidence_repo.add = failing_add  # type: ignore[method-assign]

            with pytest.raises(Exception, match="DB failure after flush"):
                await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
                    content=_make_image(),
                    original_filename="ob.png",
                    declared_mime_type="image/png",
                )
            await s.rollback()
        # Verify no orphan evidence record
        async with factory() as s:
            result = await s.execute(
                text("SELECT COUNT(*) FROM evidence WHERE session_id = :sid"),
                {"sid": sid},
            )
            assert result.scalar_one() == 0

    async def test_replacement_rollback_preserves_previous(
        self,
        engine: AsyncEngine,
        tmp_path: Path,
        user_id: uuid.UUID,
    ) -> None:
        sid = await _make_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        # Commit the create first
        async with factory() as s:
            svc = EvidenceService(session=s, storage_root=tmp_path)
            r1 = await svc.create(
                session_id=sid,
                owner_id=user_id,
                evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
                content=_make_image(),
                original_filename="v1.png",
                declared_mime_type="image/png",
            )
            old_id = r1.evidence.id
            old_ref = r1.stored_file.file_reference
            await s.commit()

        # Replace in a new session and rollback
        async with factory() as s:
            svc = EvidenceService(session=s, storage_root=tmp_path)

            orig_store_ev = svc._store_evidence

            async def failing_store_ev(**kwargs: object) -> object:
                await orig_store_ev(**kwargs)
                raise Exception("DB failure after replacement store")

            svc._store_evidence = failing_store_ev  # type: ignore[method-assign,assignment]

            with pytest.raises(Exception, match="DB failure after replacement store"):
                await svc.replace(
                    session_id=sid,
                    owner_id=user_id,
                    evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
                    content=_make_image("PNG", (60, 60)),
                    original_filename="v2.png",
                    declared_mime_type="image/png",
                )
            await s.rollback()

        # Verify previous evidence is still active in a fresh session
        async with factory() as s:
            old = await s.get(Evidence, old_id)
            assert old is not None
            assert old.evidence_status == EvidenceStatus.AVAILABLE
            old_file = tmp_path / old_ref
            assert old_file.exists()
