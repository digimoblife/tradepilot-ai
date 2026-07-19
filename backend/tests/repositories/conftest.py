# ruff: noqa: E501
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)


@dataclass(frozen=True)
class RepositorySeedData:
    user_a: uuid.UUID
    user_b: uuid.UUID
    session_a: uuid.UUID
    session_b: uuid.UUID
    trade_state_a: uuid.UUID
    trade_action_a: uuid.UUID
    analysis_job_a: uuid.UUID
    analysis_a: uuid.UUID


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


async def _seed(engine: AsyncEngine) -> RepositorySeedData:
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

        ua = (
            await conn.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
                {"e": f"ua_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        ub = (
            await conn.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
                {"e": f"ub_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        sa = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": ua[0], "t": "BBRI"},
            )
        ).first()
        sb = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": ub[0], "t": "TLKM"},
            )
        ).first()
        st = (
            await conn.execute(
                text("INSERT INTO trade_states (session_id) VALUES (:sid) RETURNING session_id"),
                {"sid": sa[0]},
            )
        ).first()
        ac = (
            await conn.execute(
                text(
                    "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key) "
                    "VALUES (:sid, :at, :ca, :ik) RETURNING id"
                ),
                {
                    "sid": sa[0],
                    "at": "POSITION_OPENED",
                    "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                    "ik": f"act_{uuid.uuid4().hex[:8]}",
                },
            )
        ).first()
        jb = (
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (session_id, analysis_type) VALUES (:sid, :at) RETURNING id"
                ),
                {"sid": sa[0], "at": "INITIAL_ANALYSIS"},
            )
        ).first()
        an = (
            await conn.execute(
                text(
                    "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, prompt_name, prompt_version, schema_name, schema_version, "
                    "accepted_at) "
                    "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv, :aa) RETURNING id"
                ),
                {
                    "sid": sa[0],
                    "jid": jb[0],
                    "at": "INITIAL_ANALYSIS",
                    "ast": "ACCEPTED",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                    "aa": datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
                },
            )
        ).first()
    return RepositorySeedData(
        user_a=ua[0],
        user_b=ub[0],
        session_a=sa[0],
        session_b=sb[0],
        trade_state_a=st[0],
        trade_action_a=ac[0],
        analysis_job_a=jb[0],
        analysis_a=an[0],
    )


@pytest.fixture
async def data(engine: AsyncEngine) -> RepositorySeedData:
    return await _seed(engine)
