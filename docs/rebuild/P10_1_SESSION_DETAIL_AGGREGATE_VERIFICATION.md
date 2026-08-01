# P10.1 Session Detail Aggregate Verification

- Official task: P10.1 — Create Session Detail Aggregate API
- Previous task: P9.3
- Next task: P10.2
- Starting commit: `cc9e66b5e0f8268608ab87ddfd69e8468ae12063`
- Selected endpoint: `GET /api/v2/trade-sessions/{session_id}/detail`

## Scope and contract

The existing `GET /api/v2/trade-sessions/{session_id}` returns the established session summary, so the aggregate uses the backward-compatible `/detail` child endpoint. It returns exactly `session`, `initial_evidence`, `initial_analysis`, `decisions`, `wait_updates`, `position`, `position_updates`, and `closure`.

The service reads only V2 entities: `trade_sessions_v2`, `evidence_uploads_v2`, `analysis_requests_v2`, `session_decisions_v2`, `positions_v2`, and `trade_closures_v2`. No legacy records are queried.

## Safety and ordering

- Ownership is enforced by `(session_id, user_id)` before any aggregate data is read.
- Cross-user and unknown sessions use the existing V2 not-found response.
- Lists are ordered oldest-to-newest with `id` as the deterministic tie-breaker.
- Queries are bounded to the requested session: one session query, one query each for evidence, requests, decisions, position, and closure; no N+1 loop.
- Initial evidence excludes WAIT/Position-linked evidence and never exposes filesystem paths.
- The endpoint is read-only; repeated reads do not change session timestamps or records.

## Disposable verification

- Container: `tradepilot-p101-postgres`
- Host port: `55434`
- Database: `tradepilot_test`
- `pg_isready` and `SELECT 1` passed.
- Migrations: `DATABASE_SYNC_URL=... backend/.venv/bin/alembic -c backend/alembic.ini upgrade heads`
- Cleanup: `docker rm -f tradepilot-p101-postgres`

## Tests

`TEST_DATABASE_URL=... backend/.venv/bin/pytest -q backend/tests/trade_workspace/test_session_detail_aggregate.py`

Result: `1 passed`.

The focused test covers V2 ownership, all top-level sections, initial-evidence filtering, Initial Analysis, repeated WAIT decisions, WAIT updates, advisory processed output, repeated read no-mutation behavior, and cross-user rejection.

Python compilation and `git diff --check` passed. No frontend files were changed, so frontend tests were not run. No real Gemini request occurred.

Final result: P10.1 aggregate API verification passed.
