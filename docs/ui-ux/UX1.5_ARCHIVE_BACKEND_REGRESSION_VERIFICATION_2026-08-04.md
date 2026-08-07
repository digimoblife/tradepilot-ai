# UX1.5 — Archive Backend Regression Verification

**Date:** 4 August 2026
**Official task:** `UX1.5 — Archive Backend Regression Verification`
**Status:** PASS
**Branch:** `main`
**Starting commit:** `d20ca8e5ee283b55c8e8572f77984539c448c06c`

## 1. Metadata and Repository Baseline

The canonical redesign target is V2 under `backend/app/trade_workspace/`. The working tree already contained unrelated user changes, accepted UX1.1–UX1.4 changes, and untracked diagnostic/documentation files. No unrelated changes were reverted.

The repository currently has two migration heads: `e1f2a3b4c5d6` for the V2 archive metadata chain and pre-existing `a1b2c3d4e5f6` for the evidence-batch current-price branch. The archive migration tests verified the V2 archive revision directly on the disposable `tradepilot_test` database.

## 2. Sources Reviewed

- `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
- `docs/TradePilot AI PRD Amendment.md`
- `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
- `docs/redesign/TradePilot_AI_UI_UX_PRD_Guided_Session_Experience_and_Archive_FINAL.docx` (actual `word/document.xml` contents)
- `docs/redesign/TradePilot_AI_UI_UX_Detailed_Task_Plan_FINAL.docx` (actual `word/document.xml` contents)
- `docs/ui-ux/UX0.1_AUTHORITATIVE_SOURCE_LOCK_AND_REQUIREMENT_MATRIX_2026-08-04.md`
- `docs/ui-ux/UX0.2_CURRENT_MAIN_BRANCH_UI_UX_IMPACT_AUDIT_2026-08-04.md`
- `docs/ui-ux/UX0-G_AUTHORITY_AND_REPOSITORY_ALIGNMENT_GATE_2026-08-04.md`
- `.agent-skills/tradepilot-source-lock/SKILL.md`
- `.agent-skills/tradepilot-focused-testing/SKILL.md`
- Accepted UX1.1–UX1.4 model, migration, service, route, schema, and focused test files.

UX0-G and UX1.1–UX1.4 were confirmed PASS from the gate records, accepted implementation, and focused tests.

## 3. Scope Diff

This task performed focused regression verification, one stale V2 response-shape test update caused by UX1.4, and this report. No product behavior, lifecycle, queue, analysis, evidence, provider, worker, or Gemini behavior was changed.

## 4. UX1.1–UX1.4 Implementation Inventory

- `backend/app/trade_workspace/models/trade_session.py` — nullable `archived_at`; canonical statuses unchanged.
- `backend/migrations/versions/e1f2a3b4c5d6_p72_archive_metadata.py` — nullable V2 archive metadata migration.
- `backend/app/trade_workspace/services/trade_sessions.py` — terminal-only Archive/Restore and separated owned queries.
- `backend/app/trade_workspace/api/routes/trade_sessions.py` — V2 archive, restore, archived-list, and response/error contract.
- `backend/app/trade_workspace/api/schemas.py` — nullable `archived_at` and minimal action response.
- UX1.1–UX1.4 focused tests under `backend/tests/database/`, `backend/tests/trade_workspace/`, and `backend/tests/api/`.

## 5. Static Diff-Safety Review

- Worker paths changed by UX1: no.
- Gemini/provider paths changed by UX1: no.
- Queue contracts changed: no.
- Lifecycle enums or transitions changed: no.
- Evidence contracts changed: no.
- Legacy Archive reused: no.
- Destructive delete/cascade behavior introduced: no.
- New event/history record introduced by Archive/Restore: no.
- Existing non-Archive endpoint renamed: no.
- Existing response meanings changed: no; `archived_at` was added as approved metadata.
- Archive failures expose internal data: no; routes map them to controlled safe errors.

## 6. Focused Test Selection and Rationale

The selected tests cover Archive metadata, migration safety, Archive/Restore eligibility, list separation, V2 session creation/list/detail, ownership/authentication, BUY/WAIT/SKIP, WAIT and Position Updates, Close, evidence exact-set behavior, analysis request lifecycle, retries, queue submission/claiming, duplicate protection, and processing boundaries.

## 7. Test Commands and Results

All commands used the disposable `tradepilot_test` database with `APP_ENV=test`; no real Gemini request was made.

- Stage 1 Archive suite: `12 passed`.
- Clean Stage 2 session/ownership suite: `35 passed`.
- Clean Stage 3 lifecycle/WAIT-flow subgroup: `8 passed`.
- Clean Stage 3 update/Close subgroup: `87 passed`.
- Clean Stage 4 evidence/analysis/queue/processing suite: `68 passed`.
- Archive migration upgrade/representative-data/downgrade test: `1 passed`.
- Ruff on UX1 Python files: passed.
- Python compilation on UX1 Python files: passed.
- `git diff --check`: passed.

## 8. Archive Contract Verification

The focused Archive tests verify metadata-only mutation, terminal-only eligibility, repeated Archive/Restore conflicts, owner-scoped access, indistinguishable cross-owner/missing responses, main/archived list separation, deterministic ordering, direct archived detail, and canonical `CLOSED`/`CLOSED_SKIPPED` preservation.

## 9. Session and Ownership Regression Verification

V2 creation remains owned and starts as `DRAFT`. Main list, archived list, direct detail, aggregate detail, authentication, cross-owner access, and missing-session behavior passed. The stale existing V2 response-shape assertions were updated only to include the approved `archived_at` field.

## 10. Lifecycle Regression Verification

BUY, WAIT, SKIP, decision availability, WAITING, OPEN_POSITION, CLOSED, CLOSED_SKIPPED, WAIT Update, Position Update, and V2 Close tests passed. Archive and Restore do not introduce or expose `ARCHIVED`, reopen sessions, or change action availability.

## 11. Evidence, Analysis, Queue, and Worker Verification

Initial evidence exact-set, ownership, metadata, and persistence tests passed. Initial Analysis submission/read/retry, analysis request status, duplicate protection, queue serialization/submission, atomic claim behavior, rollback/commit boundaries, and processing tests passed. Static review found no UX1 changes under worker, provider, Gemini, queue, prompt, or evidence-contract implementation areas.

## 12. Migration Verification

The archive migration test passed for revision contract, empty/representative upgrade behavior, default-null existing rows, timezone-aware nullable column shape, downgrade removal, and re-upgrade. Legacy tables are not referenced by the V2 archive migration. The pre-existing second migration head was recorded but not changed.

## 13. Failures and Archive-Caused Fixes

One Archive-caused compatibility failure was found: two existing V2 API tests expected the pre-UX1 response field set. The tests were updated to include `archived_at`; the corrected Stage 2 suite passed with 35 tests.

Unrelated shared-database global-count failures were isolated and resolved by resetting the disposable test database between groups; no production or application fix was made. Legacy `backend/tests/api/test_closing_analysis.py` remains outside the canonical V2 boundary and fails before execution because the legacy `evidence_batches.current_price` column is absent. It was not modified or treated as an Archive regression.

## 14. Remaining Risks

The working tree contains unrelated dirty changes and a pre-existing second migration head. These are outside UX1.5 and must be separated before committing the UX1 candidate.

## 15. Acceptance-Criteria Evaluation

1. All focused tests pass — **PASS**. Clean grouped runs passed all mapped UX1 and V2 regression tests.
2. No analysis or queue contract changed — **PASS**. Analysis, queue, claim, and processing tests passed; static diff review found no UX1 changes in those areas.
3. No real Gemini request is used — **PASS**. Verification used fixtures, fakes, and static inspection only.

## 16. Commit-Candidate Summary

The complete scoped UX1.1–UX1.5 backend work is ready as a commit candidate. Do not commit automatically because the working tree contains unrelated user changes.

## 17. Change Confirmation

UX1.5 changed only:

- this regression report;
- the two stale V2 response-shape assertions in `backend/tests/api/test_trade_sessions_v2.py`.

No frontend, lifecycle, analysis, queue, worker, Gemini, provider, evidence-contract, legacy Archive, migration, model, or authoritative source file was changed by UX1.5.

## 18. Next Official Task

`UX1-G — Phase Gate — Archive Backend Foundation`
