# ruff: noqa: E501
import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import AppConfig
from app.database.session import create_async_engine_from_config
from app.models.enums import EvidenceStatus, EvidenceType, ExtractionStatus
from app.models.evidence import Evidence, normalize_storage_object_key

_DEFAULT_URL = "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"


@pytest.fixture
def db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_URL)


async def _make_user_and_session(
    engine: AsyncEngine,
    label: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM session_events"))
        await conn.execute(text("DELETE FROM context_summaries"))
        await conn.execute(text("DELETE FROM validation_attempts"))
        await conn.execute(text("DELETE FROM provider_responses"))
        await conn.execute(text("DELETE FROM provider_requests"))
        await conn.execute(text("DELETE FROM trade_actions"))
        await conn.execute(text("DELETE FROM analyses"))
        await conn.execute(text("DELETE FROM analysis_jobs"))
        await conn.execute(text("DELETE FROM evidence"))
        await conn.execute(text("DELETE FROM trade_states"))
        await conn.execute(text("DELETE FROM trade_sessions"))
        await conn.execute(text("DELETE FROM users"))
    async with engine.begin() as conn:
        ur = (
            await conn.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
                {"e": f"{label}_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        assert ur is not None
        sr = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": ur[0], "t": "BBRI"},
            )
        ).first()
        assert sr is not None
    return ur[0], sr[0]


# --- Basic CRUD ---


@pytest.mark.database
async def test_evidence_can_be_inserted(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "ev")
    async with engine.begin() as conn:
        r = (
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type) VALUES (:s, :o, :t) RETURNING id"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT"},
            )
        ).first()
        assert r is not None and isinstance(r[0], uuid.UUID)
    await engine.dispose()


@pytest.mark.database
async def test_defaults() -> None:
    ev = Evidence(evidence_type=EvidenceType.USER_NOTE)
    assert ev.evidence_status == EvidenceStatus.PENDING
    assert ev.extraction_status == ExtractionStatus.NOT_REQUESTED


@pytest.mark.database
async def test_unknown_session_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, _ = await _make_user_and_session(engine, "unk")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type) VALUES (:s, :o, :t)"
                ),
                {"s": uuid.uuid4(), "o": uid, "t": "ORDERBOOK_SCREENSHOT"},
            )
    await engine.dispose()


@pytest.mark.database
async def test_invalid_evidence_type_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "iet")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type) VALUES (:s, :o, :t)"
                ),
                {"s": sid, "o": uid, "t": "INVALID_TYPE"},
            )
    await engine.dispose()


# --- Storage object key validation ---


def test_normalize_storage_object_key_valid() -> None:
    assert normalize_storage_object_key("users/123/file.png") == "users/123/file.png"
    assert (
        normalize_storage_object_key("sessions/456/evidence/abc.webp")
        == "sessions/456/evidence/abc.webp"
    )
    assert normalize_storage_object_key("  nested/path/file.jpg  ") == "nested/path/file.jpg"


def test_normalize_storage_object_key_invalid() -> None:
    with pytest.raises(ValueError, match="empty"):
        normalize_storage_object_key("")
    with pytest.raises(ValueError, match="empty"):
        normalize_storage_object_key("   ")
    with pytest.raises(ValueError, match="not contain null"):
        normalize_storage_object_key("file\x00.png")
    with pytest.raises(ValueError, match="relative"):
        normalize_storage_object_key("/data/evidence/file.png")
    with pytest.raises(ValueError, match="relative"):
        normalize_storage_object_key("/Users/cahyo/file.png")
    with pytest.raises(ValueError, match="traversal"):
        normalize_storage_object_key("../file.png")
    with pytest.raises(ValueError, match="traversal"):
        normalize_storage_object_key("sessions/456/../../file.png")
    with pytest.raises(ValueError, match="current-directory"):
        normalize_storage_object_key("./file.png")
    with pytest.raises(ValueError, match="Windows drive"):
        normalize_storage_object_key("C:\\uploads\\file.png")
    with pytest.raises(ValueError, match="Windows drive"):
        normalize_storage_object_key("D:/path/file.png")
    with pytest.raises(ValueError, match="UNC path"):
        normalize_storage_object_key("//server/share/file.png")
    with pytest.raises(ValueError, match="UNC path"):
        normalize_storage_object_key("\\\\server\\share\\file.png")


@pytest.mark.database
async def test_storage_key_db_constraint_rejects_absolute(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "abs")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type, storage_object_key) VALUES (:s, :o, :t, :k)"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT", "k": "/etc/passwd"},
            )
    await engine.dispose()


# --- File size constraint ---


@pytest.mark.database
async def test_negative_file_size_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "fs")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as exc:
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type, file_size_bytes) VALUES (:s, :o, :t, :b)"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT", "b": -100},
            )
        assert "check constraint" in str(exc.value).lower()
    await engine.dispose()


# --- Extraction confidence constraint ---


@pytest.mark.database
async def test_confidence_below_zero_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "cl")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as exc:
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type, extraction_confidence) VALUES (:s, :o, :t, :c)"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT", "c": -1},
            )
        assert "check constraint" in str(exc.value).lower()
    await engine.dispose()


@pytest.mark.database
async def test_confidence_above_100_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "ch")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as exc:
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type, extraction_confidence) VALUES (:s, :o, :t, :c)"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT", "c": 101},
            )
        assert "check constraint" in str(exc.value).lower()
    await engine.dispose()


# --- Checksum constraint ---


@pytest.mark.database
async def test_invalid_checksum_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "chk")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as exc:
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type, checksum_sha256) VALUES (:s, :o, :t, :c)"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT", "c": "not-a-hex"},
            )
        assert "check constraint" in str(exc.value).lower()
    await engine.dispose()


# --- Replacement integrity ---


@pytest.mark.database
async def test_replacement_history(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "rep")
    async with engine.begin() as conn:
        r1 = (
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type) VALUES (:s, :o, :t) RETURNING id"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT"},
            )
        ).first()
        assert r1 is not None
        eid1 = r1[0]
        r2 = (
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type, supersedes_evidence_id) VALUES (:s, :o, :t, :sup) RETURNING id"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT", "sup": eid1},
            )
        ).first()
        assert r2 is not None
        eid2 = r2[0]
        rows = (
            await conn.execute(
                text(
                    "SELECT id, supersedes_evidence_id FROM evidence WHERE session_id = :s ORDER BY created_at"
                ),
                {"s": sid},
            )
        ).all()
        assert len(rows) == 2
        assert rows[0][0] == eid1
        assert rows[0][1] is None
        assert rows[1][0] == eid2
        assert rows[1][1] == eid1
    await engine.dispose()


@pytest.mark.database
async def test_nonexistent_supersedes_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "nsr")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type, supersedes_evidence_id) VALUES (:s, :o, :t, :sup)"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT", "sup": uuid.uuid4()},
            )
    await engine.dispose()


@pytest.mark.database
async def test_self_replacement_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "slf")
    async with engine.begin() as conn:
        r = (
            await conn.execute(
                text(
                    "INSERT INTO evidence (session_id, owner_id, evidence_type) VALUES (:s, :o, :t) RETURNING id"
                ),
                {"s": sid, "o": uid, "t": "ORDERBOOK_SCREENSHOT"},
            )
        ).first()
        assert r is not None
        eid = r[0]
        with pytest.raises(Exception) as exc:
            await conn.execute(
                text("UPDATE evidence SET supersedes_evidence_id = :self WHERE id = :id"),
                {"self": eid, "id": eid},
            )
        assert "check constraint" in str(exc.value).lower()
    await engine.dispose()


# --- JSONB and timestamps ---


@pytest.mark.database
async def test_extraction_payload_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "jrt")
    async with engine.begin() as conn:
        payload = {"key": "value", "numbers": [1, 2, 3]}
        await conn.execute(
            text(
                "INSERT INTO evidence (session_id, owner_id, evidence_type, extraction_payload) VALUES (:s, :o, :t, CAST(:p AS JSONB))"
            ),
            {"s": sid, "o": uid, "t": "USER_NOTE", "p": str(payload).replace("'", '"')},
        )
        row = (
            await conn.execute(
                text("SELECT extraction_payload FROM evidence WHERE session_id = :s"),
                {"s": sid},
            )
        ).first()
        assert row is not None
        assert row[0] == payload
    await engine.dispose()


@pytest.mark.database
async def test_market_and_upload_timestamps_distinct(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    uid, sid = await _make_user_and_session(engine, "tsd")
    async with engine.begin() as conn:
        mt = datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc)
        await conn.execute(
            text(
                "INSERT INTO evidence (session_id, owner_id, evidence_type, market_timestamp) VALUES (:s, :o, :t, :mt)"
            ),
            {"s": sid, "o": uid, "t": "CHART_THREE_MONTH", "mt": mt},
        )
        row = (
            await conn.execute(
                text("SELECT market_timestamp, uploaded_at FROM evidence WHERE session_id = :s"),
                {"s": sid},
            )
        ).first()
        assert row is not None
        assert row[0] == mt
        assert row[1] is not None
        assert row[1].tzinfo is not None
    await engine.dispose()
