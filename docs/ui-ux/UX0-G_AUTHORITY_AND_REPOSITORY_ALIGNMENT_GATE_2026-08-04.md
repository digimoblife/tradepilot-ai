# UX0-G — Phase Gate — Authority and Repository Alignment

Date: 2026-08-04
Official task: `UX0-G — Phase Gate — Authority and Repository Alignment`
Final status: **PASS**

## 1. Metadata and Repository Baseline

- Branch inspected: `main`
- Commit inspected: `d20ca8e5ee283b55c8e8572f77984539c448c06c`
- Canonical redesign target: `trade_sessions_v2` and `backend/app/trade_workspace/`
- Existing working tree: pre-existing modified and untracked application, test, migration, skill, redesign, documentation, and storage paths were present. They were not changed by UX0-G.
- This gate adds only `docs/ui-ux/UX0-G_AUTHORITY_AND_REPOSITORY_ALIGNMENT_GATE_2026-08-04.md`.

## 2. Sources Reviewed

Authoritative product and task sources reread directly:

1. `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
2. `docs/TradePilot AI PRD Amendment.md`
3. `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
4. `docs/redesign/TradePilot_AI_UI_UX_PRD_Guided_Session_Experience_and_Archive_FINAL.docx`
5. `docs/redesign/TradePilot_AI_UI_UX_Detailed_Task_Plan_FINAL.docx`

Prior gate artifacts and required skills reread directly:

6. `docs/ui-ux/UX0.1_AUTHORITATIVE_SOURCE_LOCK_AND_REQUIREMENT_MATRIX_2026-08-04.md`
7. `docs/ui-ux/UX0.2_CURRENT_MAIN_BRANCH_UI_UX_IMPACT_AUDIT_2026-08-04.md`
8. `.agent-skills/tradepilot-source-lock/SKILL.md`
9. `.agent-skills/tradepilot-focused-testing/SKILL.md`

The DOCX files were read from their actual `word/document.xml` contents. Their approved redesign scope, Archive rules, route model, acceptance criteria, official task IDs/titles, dependencies, and gates agree with the UX0 artifacts.

## 3. Scope Diff Confirmation

This was verification only. The review compared the approved sources with UX0.1, UX0.2, and load-bearing repository evidence. No application, test, migration, schema, API, configuration, dependency, skill, design, refactor, cleanup, or product decision work was performed. UX1.1 was not started.

## 4. UX0.1 Verification

Result: **PASS**.

- UX0.1 records all nine required source/skill paths and states that the DOCX files were read from actual content.
- Its requirement matrix represents the approved guided multi-page journey, backend-authoritative lifecycle, mobile/accessibility/content requirements, V2 target, metadata-only Archive, terminal-only eligibility, read-only preservation, restore semantics, and non-goals.
- Its AC matrix covers all 22 redesign PRD acceptance criteria with official task IDs and gates.
- Its task and gate mappings preserve the approved IDs, titles, order, boundaries, dependencies, and terminology. No task was renamed, merged, split, or reordered.
- It correctly preserves `trade_sessions_v2`, `backend/app/trade_workspace/`, `CLOSED`/`CLOSED_SKIPPED` Archive eligibility, nullable Archive metadata, and the prohibition on V2 `ARCHIVED`.
- It explicitly treats repository behavior as evidence rather than product authority and records conflicts as resolved by authority or blocked when unresolved.
- The recorded prior conflicts are non-blocking: approval-state correction, legacy/V2 lifecycle vocabulary, and competing legacy/V2 entities are resolved by the approved source hierarchy and canonical V2 boundary. Endpoint naming remains a documented implementation-task ambiguity, not a product conflict.

No material deviation was found.

## 5. UX0.2 Verification

Result: **PASS**.

- Baseline is recorded as `main` at `d20ca8e5ee283b55c8e8572f77984539c448c06c`.
- The route inventory identifies `/login`, `/trade-workspace`, `/sessions`, `/sessions/new`, `/sessions/[sessionId]`, `/`, and `/evaluations` with exact page symbols and redirect behavior.
- Selected-session ownership is explicit: `frontend/src/features/trade-workspace/trade-workspace.tsx:TradeWorkspace` owns `selected`, session collection, and per-session evidence cache; `SessionWorkspace` owns keyed detail state.
- All four polling owners are mapped: `frontend/src/features/jobs/job-status.tsx:JobStatus` at 3,000 ms; `SessionWorkspace` initial-analysis polling at 5,000 ms; `frontend/src/features/trade-workspace/wait-update.tsx:WaitUpdatePanel` at 4,000 ms; and `frontend/src/features/trade-workspace/position-update.tsx:PositionUpdatePanel` at 4,000 ms. Start/stop conditions, cleanup, and recovery/stale-session risks are recorded.
- V2 and legacy are distinguishable by paths, prefixes, models, statuses, services, migrations, and tests.
- V2 Archive gaps are accurately recorded: no archive metadata, eligibility service, filter, Archive/Restore handlers, response fields, UI, or V2 Archive tests.
- Every UX1.1–UX8.5 task has an exact current target, expected new area, or explicit discovery step.
- The audit states that no implementation, broad test suite, or real Gemini request was performed.

No material deviation was found.

## 6. UX0.1 versus UX0.2 Consistency Review

The artifacts are mutually consistent:

| Check | Result | Evidence |
|---|---|---|
| Authority hierarchy | PASS | Both preserve PRD/Amendment/task-plan authority over repository behavior. |
| Canonical V2 target | PASS | Both name `trade_sessions_v2` and `backend/app/trade_workspace/`. |
| Archive semantics | PASS | Both define nullable organizational metadata, terminal-only eligibility, status/record preservation, and metadata-only Restore. |
| Legacy boundary | PASS | Both reject legacy `trade_sessions`, legacy Archive services/routes, and `TradeSessionStatus.ARCHIVED` as V2 targets. |
| Lifecycle/AI/evidence/decision invariants | PASS | Both preserve lifecycle, analysis types, evidence rules, BUY/WAIT/SKIP, request processing, Gemini provider, and `gemini-3.1-flash-lite`. |
| Task coverage/order | PASS | UX0.1 maps all 22 ACs; UX0.2 maps every UX1.1–UX8.5 task to evidence or discovery. |
| Current-state evidence | PASS | UX0.2’s route, state, polling, V2, legacy, migration, and test findings match spot-checks below. |

No material contradiction or unresolved implementation-affecting conflict was found.

## 7. UX1 Prerequisite Traceability Matrix

| Task | Authoritative requirement | Current repository target or discovery step | Upstream dependency | Relevant risk | Focused verification required | Status |
|---|---|---|---|---|---|---|
| `UX1.1 — Archive Persistence Model and Migration` | UX0.1 `ARCH-001`, `ARCH-003`, `AC-13`; redesign PRD Archive section: nullable metadata, terminal preservation, no V2 `ARCHIVED`. | `backend/app/trade_workspace/models/trade_session.py:TradeSessionV2` and `TradeSessionV2Status`; `backend/migrations/versions/7f3a9c2d1b4e_p31_trade_sessions_v2.py` through P36 V2 migrations. New V2 archive migration location is the task’s bounded implementation area. | UX0-G; V2/legacy boundary. | R1/R2: legacy lifecycle Archive and absent V2 metadata. | Empty and representative migration checks, default-null behavior, status preservation, related-record integrity, rollback per repository convention. | **READY** |
| `UX1.2 — Archive Domain Eligibility Service` | UX0.1 `ARCH-002`, `ARCH-004`, `ARCH-009`, `ARCH-010`; only `CLOSED`/`CLOSED_SKIPPED`, preserve terminal state and records, clear metadata only on Restore. | `backend/app/trade_workspace/services/trade_sessions.py:RebuildTradeSessionService` and V2 status model; new V2 eligibility/service symbol is an explicit task discovery point. | UX1.1. | R1: accidental status mutation, reopening, or record changes. | Every eligible/ineligible status, owner isolation, repeated action/idempotency, status/action preservation, related-record checks. | **READY** |
| `UX1.3 — Session List Archive Filtering` | UX0.1 `ARCH-006`, `SESSION-001`, `AC-02`, `AC-14`; default list excludes archived owned sessions and archived list is separate. | `backend/app/trade_workspace/services/trade_sessions.py:RebuildTradeSessionService.list_owned`; `backend/app/trade_workspace/api/routes/trade_sessions.py:list_trade_sessions`; `TradeSessionListResponse` in `backend/app/trade_workspace/api/schemas.py`. | UX1.1 and UX1.2. | R2: current V2 `list_owned` returns all owned rows because no archive metadata/filter exists. | Active/archived separation, owner isolation, ordering, empty/populated lists, direct archived read. | **READY** |
| `UX1.4 — Archive and Restore API Contract` | UX0.1 `ARCH-002`, `ARCH-009`, `ARCH-010`, `AC-12`, `AC-14`, `AC-16`; backend-enforced eligibility and metadata-only Archive/Restore. | `backend/app/trade_workspace/api/routes/trade_sessions.py:router`, `list_trade_sessions`, `get_trade_session`; `backend/app/trade_workspace/api/schemas.py:TradeSessionResponse`. New V2 handlers/fields are the task target; exact endpoint names are intentionally not invented at UX0-G. | UX1.1–UX1.3. | R1/R2 and legacy endpoint confusion. | Contract, authentication/ownership, ineligible status, repeated actions, status preservation, response shape, error behavior. | **READY** |
| `UX1.5 — Archive Backend Regression Verification` | UX0.1 `ARCH-004`, `ARCH-005`, `AC-13`, `AC-15`; all related records remain intact and terminal behavior remains unchanged. | V2 API/service/model tests under `backend/tests/api/`, `backend/tests/trade_workspace/`, and `backend/tests/database/`; legacy Archive test remains a boundary/isolation reference only. | UX1.1–UX1.4. | Regression risk across lifecycle, ownership, related records, and list separation. | Focused V2 Archive regression matrix plus nearest lifecycle/ownership/migration boundaries; no real Gemini. | **READY** |

All five UX1 tasks have an authoritative requirement, a concrete repository target or explicit discovery step, upstream dependencies, risk, and focused verification. None has an unresolved blocking conflict.

## 8. Official Task-Order Validation

The approved sequence remains valid:

`UX0.1 → UX0.2 → UX0-G → UX1.1 → UX1.2 → UX1.3 → UX1.4 → UX1.5 → UX1-G → UX2...`

UX0-G is the required authority/repository gate before UX1. UX1.1 correctly precedes eligibility, filtering, API contract, and regression verification. No later Archive UI task is authorized before the UX1 backend foundation and `UX1-G`.

## 9. Conflict and Risk Evaluation

### Resolved conflicts

- Legacy `trade_sessions` versus V2 `trade_sessions_v2`: resolved by the approved source hierarchy and explicit redesign target.
- Legacy `TradeSessionStatus.ARCHIVED` versus metadata-only Archive: resolved by prohibiting reuse in V2.
- Legacy `INITIAL_ANALYZED` vocabulary versus V2 `ANALYZED`: resolved by the V2 canonical boundary.
- Repository’s current `/trade-workspace` and legacy API usage versus the approved multi-page flow: recorded as future cutover work, not product authority.

### Explicitly deferred, non-blocking items

- Exact Archive/Restore endpoint names remain UX1.4 implementation detail.
- Exact new route/component file boundaries remain the discovery responsibility of the named UX2/UX6 tasks.
- Current local selected-session and polling architecture remains until the corresponding official route/state tasks.

### Unresolved blocking conflicts

None.

### UX0.2 R1 treatment

R1 is correctly labeled `BLOCKING` as a future implementation hazard, but it does not block UX0-G. It is controlled by the authoritative mitigation: legacy Archive is `LEGACY_COUPLING_ONLY`; only V2 is in scope; `ARCHIVED` cannot become a V2 session status; and UX1.1 must establish metadata persistence before later Archive tasks. UX1 may begin without reusing legacy lifecycle behavior.

Product Owner approval: not required for this gate. No product ambiguity remains that prevents UX1.1 from starting under the locked boundaries.

## 10. Gate Acceptance-Criteria Evaluation

1. **UX1 may start only with PASS or Product-Owner-approved limitations — PASS.** UX0.1 and UX0.2 both have final status PASS; all five UX1 prerequisites are traceable and READY; no Product Owner-approved limitation is needed.
2. **All blocking conflicts are resolved or explicitly deferred — PASS.** The legacy Archive conflict is resolved by authority and explicit V2-only mitigation. Endpoint and future file-boundary questions are explicitly deferred implementation details, not blockers.

## 11. Final Gate Decision

**PASS.** UX1 implementation may begin safely with `UX1.1`, subject to preserving the locked V2-only, metadata-only, terminal-only Archive boundaries and the focused verification listed in the prerequisite matrix.

## 12. Change Confirmation

Changed by UX0-G: `docs/ui-ux/UX0-G_AUTHORITY_AND_REPOSITORY_ALIGNMENT_GATE_2026-08-04.md` only.

No application, test, migration, schema, API, configuration, dependency, skill, or authoritative source file changed. No broad test suite and no real Gemini request were run.

## 13. Next Official Task

`UX1.1 — Archive Persistence Model and Migration`

UX1.1 was not executed and its prompt was not generated.
