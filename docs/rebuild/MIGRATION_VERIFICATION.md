# Rebuild Migration Verification

## 1. Purpose

Verify the complete rebuild migration chain from P3.1 through P3.6 without
changing migration history, old tables, old records, or application behavior.

## 2. Verification Environment

All verification used disposable PostgreSQL-only `postgres:17` containers with
no persistent volumes and no application stack:

| Scenario | Container | Database | Port | Start | End | Result |
| --- | --- | --- | ---: | --- | --- | --- |
| Upgrade from pre-rebuild boundary | `tradepilot-p37-head` | `tradepilot_p37_head` | 55438 | `f6a7b8c9d0e1` | `c9d0e1f2a3b4` | passed |
| New database from zero | `tradepilot-p37-zero` | `tradepilot_p37_zero` | 55439 | empty | `c9d0e1f2a3b4` | passed |
| Rollback and re-upgrade | `tradepilot-p37-rollback` | `tradepilot_p37_rollback` | 55440 | empty | `c9d0e1f2a3b4` | passed |

PostgreSQL version was `17.10` for all three databases. Production access was
not used, production volumes were not used, and all containers were removed
after verification.

## 3. Migration Boundary

The migration immediately before P3.1 is `f6a7b8c9d0e1` (P7 evaluation
records). The rebuild chain begins at that revision. Alembic reports one
unrelated preserved head, `a1b2c3d4e5f6`, for existing P9 work; it was not
merged or changed.

## 4. Rebuild Migration Chain

The verified order is:

1. P3.1 — `7f3a9c2d1b4e` — `trade_sessions_v2`
2. P3.2 — `8c4d2e6f1a3b` — `analysis_requests_v2`
3. P3.3 — `9d5e7f1a3c2b` — `evidence_uploads_v2`
4. P3.4 — `a7b8c9d0e1f2` — `session_decisions_v2`
5. P3.5 — `b8c9d0e1f2a3` — `positions_v2`
6. P3.6 — `c9d0e1f2a3b4` — `trade_closures_v2`

The current rebuild head is `c9d0e1f2a3b4`. No revision identifiers were
changed, reordered, merged, or squashed.

## 5. Upgrade From Current Head

The upgrade-from-boundary database was first migrated to `f6a7b8c9d0e1`, then
upgraded with:

```text
DATABASE_SYNC_URL=postgresql+psycopg://...@127.0.0.1:55438/tradepilot_p37_head \
  backend/.venv/bin/alembic -c backend/alembic.ini upgrade c9d0e1f2a3b4
```

Result: passed. All six rebuild tables were present at revision
`c9d0e1f2a3b4`. Historical tables remained present: `users`, `trade_sessions`,
`analyses`, `analysis_jobs`, `evidence`, `evidence_batches`,
`evaluation_records`, `trade_actions`, and `trade_states`.

The metadata inspection confirmed the rebuild foreign keys, enums, checks,
unique indexes, and practical indexes. No old table was altered by the rebuild
migrations.

## 6. New Database From Zero

The clean database was migrated with:

```text
DATABASE_SYNC_URL=postgresql+psycopg://...@127.0.0.1:55439/tradepilot_p37_zero \
  backend/.venv/bin/alembic -c backend/alembic.ini upgrade c9d0e1f2a3b4
```

Result: passed from an empty database with no manual data preparation. The
database reached `c9d0e1f2a3b4`, contained all six rebuild tables, and retained
the historical tables created by earlier migrations.

## 7. Rollback Verification

The rollback database was downgraded with:

```text
DATABASE_SYNC_URL=postgresql+psycopg://...@127.0.0.1:55440/tradepilot_p37_rollback \
  backend/.venv/bin/alembic -c backend/alembic.ini downgrade f6a7b8c9d0e1
```

Result: passed. All six rebuild tables, their rebuild-owned indexes and
constraints, and all eight rebuild-owned enums were removed. The historical
tables remained present. The upgrade-from-boundary database also preserved a
seeded old `users` record and its old `trade_sessions` record after rollback;
the records remained readable at `f6a7b8c9d0e1`.

## 8. Re-Upgrade Verification

Both rollback-capable databases were re-upgraded with:

```text
DATABASE_SYNC_URL=postgresql+psycopg://...@127.0.0.1:55438/tradepilot_p37_head \
  backend/.venv/bin/alembic -c backend/alembic.ini upgrade c9d0e1f2a3b4

DATABASE_SYNC_URL=postgresql+psycopg://...@127.0.0.1:55440/tradepilot_p37_rollback \
  backend/.venv/bin/alembic -c backend/alembic.ini upgrade c9d0e1f2a3b4
```

Result: passed. All six rebuild tables returned and the chain was repeatable.

## 9. Historical Table Preservation

The following old tables remained available before and after rebuild rollback:

- old session: `trade_sessions`;
- old evidence: `evidence`, `evidence_batches`;
- old analysis/job: `analyses`, `analysis_jobs`, `evaluation_records`;
- old decision/action: `trade_actions`, `session_events`;
- old position/lifecycle: `trade_states`;
- old identity: `users`.

This repository has no old closure table in the verified pre-rebuild chain.
No old records were migrated, deleted, or mutated. The seeded old user and
session remained readable after rollback.

## 10. Rebuild Tables Verified

The following tables existed after each successful upgrade:

- `trade_sessions_v2`
- `analysis_requests_v2`
- `evidence_uploads_v2`
- `session_decisions_v2`
- `positions_v2`
- `trade_closures_v2`

Verified relationships:

- analysis requests → `trade_sessions_v2`;
- evidence uploads → `trade_sessions_v2`;
- evidence uploads → `analysis_requests_v2`, nullable;
- session decisions → `trade_sessions_v2`;
- positions → `trade_sessions_v2`;
- trade closures → `trade_sessions_v2`;
- trade closures → `positions_v2`.

Verified database objects include approved session statuses, analysis types and
statuses, Gemini-only provider constraint, evidence types and observation
periods, decision and skip-reason enums, one BUY per session, one position per
session, one closure per position, required positive numeric checks, and
required nonblank checks.

## 11. Issues and Limitations

No direct P3.1–P3.6 migration defect was found. No migration correction,
merge migration, or history change was required. Verification used disposable
PostgreSQL containers only and did not exercise application APIs, services,
workers, frontend behavior, or Gemini.

## 12. P3.7 Conclusion

P3.1 through P3.6 form a repeatable migration chain from the pre-rebuild
revision `f6a7b8c9d0e1` to rebuild head `c9d0e1f2a3b4`. Upgrade from the
boundary, upgrade from zero, rollback, historical-table preservation, and
re-upgrade all passed. No product behavior or old migration was changed.
