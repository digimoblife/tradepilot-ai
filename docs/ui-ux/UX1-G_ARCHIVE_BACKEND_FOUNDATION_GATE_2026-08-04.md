# UX1-G — Phase Gate — Archive Backend Foundation

**Date:** 4 August 2026
**Official task:** `UX1-G — Phase Gate — Archive Backend Foundation`
**Final gate status:** **PASS**
**Branch:** `main`
**Starting commit:** `d20ca8e5ee283b55c8e8572f77984539c448c06c`

## 1. Metadata and Repository Baseline

The canonical target is the V2 session entity `trade_sessions_v2` under `backend/app/trade_workspace/`. The working tree contains accepted UX1 changes plus unrelated user changes and untracked diagnostics/documentation. These sets remain distinguishable; no unrelated change was reverted or modified.

The repository has two migration heads:

- Archive V2 head: `e1f2a3b4c5d6`, descending from `d0e1f2a3b4c5`.
- Pre-existing unrelated head: `a1b2c3d4e5f6`, descending from `f6a7b8c9d0e1`.

The unrelated head predates UX1, was not created or modified by UX1, and does not invalidate the Archive migration chain.

## 2. Sources Reviewed

- `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
- `docs/TradePilot AI PRD Amendment.md`
- `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
- `docs/redesign/TradePilot_AI_UI_UX_PRD_Guided_Session_Experience_and_Archive_FINAL.docx` — actual `word/document.xml` contents
- `docs/redesign/TradePilot_AI_UI_UX_Detailed_Task_Plan_FINAL.docx` — actual `word/document.xml` contents
- `docs/ui-ux/UX0.1_AUTHORITATIVE_SOURCE_LOCK_AND_REQUIREMENT_MATRIX_2026-08-04.md`
- `docs/ui-ux/UX0.2_CURRENT_MAIN_BRANCH_UI_UX_IMPACT_AUDIT_2026-08-04.md`
- `docs/ui-ux/UX0-G_AUTHORITY_AND_REPOSITORY_ALIGNMENT_GATE_2026-08-04.md`
- `docs/ui-ux/UX1.5_ARCHIVE_BACKEND_REGRESSION_VERIFICATION_2026-08-04.md`
- `.agent-skills/tradepilot-source-lock/SKILL.md`
- `.agent-skills/tradepilot-focused-testing/SKILL.md`
- Accepted UX1.1–UX1.5 implementation and test paths listed in the official task prompt.

UX0-G and UX1.1–UX1.5 were confirmed PASS from the gate/report artifacts, direct implementation inspection, and focused test evidence.

## 3. Scope Diff Confirmation

This gate performed source comparison, artifact review, static symbol/import checks, migration-head review, working-tree review, and focused-evidence verification. No implementation, test, configuration, migration, model, route, schema, frontend, refactor, commit, or UX2 work was performed.

## 4. UX1.1 Verification — Persistence

**PASS.**

- `TradeSessionV2.archived_at` is nullable and timezone-aware.
- `e1f2a3b4c5d6_p72_archive_metadata.py` adds/removes only V2 `archived_at` metadata.
- Existing and new sessions default to `archived_at = NULL`.
- Migration tests passed representative upgrade, default-null, downgrade, and re-upgrade checks.
- No `ARCHIVED` enum value or state transition was added.
- Legacy `trade_sessions` is not referenced by the Archive migration.

## 5. UX1.2 Verification — Domain Service

**PASS.**

- `RebuildTradeSessionService.archive()` allows only `CLOSED` and `CLOSED_SKIPPED`.
- Archive uses owner-scoped lookup and row/advisory locking.
- Archive sets only `archived_at` and preserves status.
- Restore clears only `archived_at` and preserves terminal status.
- Repeated Archive, Restore when not archived, ineligible statuses, missing sessions, and ownership boundaries use accepted controlled errors.
- No related records, timeline entries, or audit events are created or deleted.

## 6. UX1.3 Verification — Query Filtering

**PASS.**

- `list_owned()` filters `archived_at IS NULL`.
- `list_owned_archived()` filters `archived_at IS NOT NULL`.
- Both queries are owner-scoped and use deterministic `created_at DESC, id DESC` ordering.
- `get_owned()` remains available for archived and non-archived direct reads.
- Focused query tests verify separation, ownership, ordering, empty results, and no mutation.

## 7. UX1.4 Verification — API Contract

**PASS.**

- `POST /api/v2/trade-sessions/{session_id}/archive`
- `POST /api/v2/trade-sessions/{session_id}/restore`
- `GET /api/v2/trade-sessions/archived`
- Existing `GET /api/v2/trade-sessions` and `GET /api/v2/trade-sessions/{session_id}` remain in place.
- Authentication is required for all routes.
- Responses expose canonical status and nullable `archived_at`.
- Missing/cross-owner requests return controlled 404 responses.
- Ineligible/repeated operations return controlled 409 responses.
- Persistence failures return controlled 500 responses without database or exception leakage.

## 8. UX1.5 Verification — Regression Evidence

**PASS.**

The UX1.5 report records passing focused groups for Archive, sessions, ownership, lifecycle, updates, Close, evidence, analysis requests, queue, processing, and migrations. The only implementation-caused test adjustment was adding the approved `archived_at` field to two existing V2 response-shape assertions.

The legacy closing-analysis failure was not hidden or fixed: it occurs outside the canonical V2 boundary because the legacy `evidence_batches.current_price` column is absent. It does not block trustworthy V2 Archive verification.

No analysis or queue contract changed, and no real Gemini request was used.

## 9. End-to-End Archive Contract Matrix

| Contract | Evidence | Result |
|---|---|---|
| Nullable persistence metadata | V2 model and migration tests | PASS |
| Existing rows remain non-archived | Representative migration test | PASS |
| Terminal-only eligibility | Archive service matrix and API tests | PASS |
| Metadata-only Archive | Service/API status and metadata assertions | PASS |
| Metadata-only Restore | Service/API status and metadata assertions | PASS |
| Main list excludes archived | Query and API tests | PASS |
| Archived list excludes active | Query and API tests | PASS |
| Owner isolation | Service and API ownership tests | PASS |
| Archived direct detail | V2 API test | PASS |
| Controlled 404/409/500/auth errors | API contract tests and route mapping | PASS |
| Related-record preservation | Archive service and regression evidence | PASS |
| No V2 `ARCHIVED` status | Model/status inspection and tests | PASS |

## 10. Lifecycle and Related-Record Preservation Review

No V2 lifecycle enum, transition, or action-availability rule changed. Archive preserves `CLOSED` or `CLOSED_SKIPPED`; Restore does not reopen or re-enable trading. Evidence, analyses, requests, decisions, positions, closures, and history remain attached. Archive and Restore create no timeline or audit events.

## 11. Ownership and Error-Contract Review

Archive, Restore, main list, archived list, and direct detail all use authenticated owner identity. Cross-owner and missing sessions are indistinguishable through the controlled `SESSION_NOT_FOUND` 404 contract. Authentication remains dependency-enforced. Internal exception text, database details, owner IDs, and stack traces are not exposed.

## 12. Migration and Migration-Head Review

The Archive migration is internally valid and reversible. Its focused test passed empty/representative upgrade, nullable timezone-aware column verification, default-null preservation, downgrade, and re-upgrade. The pre-existing `a1b2c3d4e5f6` head is unrelated to UX1 and was neither merged nor altered. It requires normal commit/deployment handling but does not prevent UX2 from beginning safely.

## 13. Regression Evidence Review

UX1.5 selected focused, load-bearing tests rather than the full backend suite. Recorded clean results were:

- Archive suite: 12 passed.
- Session/ownership suite: 35 passed.
- Lifecycle/WAIT-flow suite: 8 passed.
- Update/Close suite: 87 passed.
- Evidence/analysis/queue/processing suite: 68 passed.
- Migration verification: 1 passed.
- Ruff, compilation, and `git diff --check`: passed.

No full backend suite and no real Gemini request were run.

## 14. Working-Tree and Commit-Candidate Review

The complete UX1 file set is identifiable under the V2 model, migration, service, API, and focused-test paths. Unrelated worker/provider/frontend/legacy changes are distinguishable and are not required for Archive correctness. UX1 is technically ready as a scoped commit candidate. No commit was created.

## 15. Conflict and Risk Register

### Resolved conflicts

- Legacy `ARCHIVED` lifecycle behavior is excluded by the V2/legacy authority boundary.
- Existing V2 response-shape assertions were updated only for approved `archived_at` exposure.

### Explicitly deferred items

- Pre-existing migration-head reconciliation remains deployment/commit handling, not UX1-G implementation.
- Frontend routes and Archive UI remain future tasks.

### Unresolved blocking conflicts

None.

### Product Owner decision required

None.

## 16. Acceptance-Criteria Evaluation

1. Archive backend foundation is complete and safe for frontend integration — **PASS**.
2. Archive and Restore preserve lifecycle and related data — **PASS**.
3. Ownership and API contracts are enforced — **PASS**.
4. Focused backend regression verification passes — **PASS**.
5. No unresolved blocking conflict prevents the next phase — **PASS**.

## 17. Final Gate Decision

**PASS.** The UX1 Archive backend foundation is approved, and the next phase may begin.

## 18. Change Confirmation

Only this UX1-G gate record was added. No implementation, test, model, migration, service, query, route, schema, frontend, configuration, commit, or authoritative source file was changed during UX1-G.

## 19. Next Official Task

`UX2.1 — New Route Skeletons`
