# UX0.2 — Current Main-Branch UI/UX Impact Audit

Date: 2026-08-04
Status: **PASS**
Scope: read-only current-state repository audit for the approved guided session experience and metadata-only Archive redesign.

## 1. Metadata and Source Lock

Authoritative sources reread directly:

- `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
- `docs/TradePilot AI PRD Amendment.md`
- `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
- `docs/redesign/TradePilot_AI_UI_UX_PRD_Guided_Session_Experience_and_Archive_FINAL.docx`
- `docs/redesign/TradePilot_AI_UI_UX_Detailed_Task_Plan_FINAL.docx`
- `docs/ui-ux/UX0.1_AUTHORITATIVE_SOURCE_LOCK_AND_REQUIREMENT_MATRIX_2026-08-04.md`
- `.agent-skills/tradepilot-source-lock/SKILL.md`
- `.agent-skills/tradepilot-focused-testing/SKILL.md`

The approved redesign baseline remains the UX0.1 source lock: V2 is authoritative at `trade_sessions_v2` and `backend/app/trade_workspace/`; `trade_sessions`, legacy services/routes/models, and `TradeSessionStatus.ARCHIVED` are legacy only. Archive is metadata-only and must not alter lifecycle, evidence, analysis, decision, request, Gemini, authentication, or ownership behavior. No source conflict was found.

## 2. Scope Diff

The approved target adds a guided multi-page experience, route-level recovery, explicit session-list/archive surfaces, and a metadata-only Archive capability. The current branch instead concentrates the active experience in `/trade-workspace`, keeps `/sessions*` as redirects, owns selected-session state locally, and exposes Archive only through legacy code. This audit records those deltas; it does not implement them.

## 3. Repository Baseline

- Branch: `main`
- Commit inspected: `d20ca8e5ee283b55c8e8572f77984539c448c06c`
- Working tree: pre-existing modified and untracked files were present, including application, test, migration, storage, redesign, and skill paths. They were not changed by UX0.2.
- New audit file: `docs/ui-ux/UX0.2_CURRENT_MAIN_BRANCH_UI_UX_IMPACT_AUDIT_2026-08-04.md`.

## 4. Executive Summary

1. The current post-login destination is `/trade-workspace`; `/`, `login` safe-next logic, `/sessions`, `/sessions/new`, and `/sessions/[sessionId]` all converge on that legacy-shaped workspace surface.
2. The current workspace is functional but monolithic: `TradeWorkspace` owns the session collection, selected session, per-session evidence cache, and status projection; `SessionWorkspace` owns detail, forms, request state, and lifecycle rendering.
3. Polling has four owners: `JobStatus` at 3 seconds, and initial-analysis, WAIT Update, and Position Update loops at 5, 4, and 4 seconds respectively. Each uses a component-local timeout and cleanup, so a guided route migration must preserve cancellation and session identity.
4. The V2 backend already covers create/list/detail, evidence, initial analysis, BUY/WAIT/SKIP, WAIT Update, Position Update, Close, ownership, and aggregate reads. V2 has no Archive field, service, route, response field, filter, or restore path.
5. Legacy Archive is unsafe to reuse for the redesign: it changes `TradeSessionStatus` to `ARCHIVED`, records `SESSION_ARCHIVED`, and is served under `/api/trade-sessions`, while the approved target is V2 and metadata-only.
6. There are focused tests for most V2 lifecycle and polling behavior, but no focused tests for the future V2 Archive contract, guided route recovery, archive filtering/restore, mobile/browser verification, or the complete multi-page flow.

## 5. Frontend Route and Screen Inventory

| Route | Exact current target and responsibility | Classification | Redesign impact |
|---|---|---|---|
| `/` | `frontend/src/app/page.tsx:Home`; authenticated users are client-redirected with `router.replace("/trade-workspace")`; unauthenticated users see landing copy. | `REUSE_WITH_ADAPTATION` | Post-login target is UX2.2; preserve auth boundary while changing destination. |
| `/login` | `frontend/src/app/login/page.tsx:LoginPage`, nested `LoginForm`; `safeNext` rejects `/sessions*` and defaults to `/trade-workspace`. | `REUSE_WITH_ADAPTATION` | UX2.2 must update redirect contract and direct-entry recovery. |
| `/trade-workspace` | `frontend/src/app/trade-workspace/page.tsx:TradeWorkspacePage` renders `TradeWorkspace`. | `REPLACE_FOR_GUIDED_FLOW` | Current single-surface composition is the primary UX0.2 cutover target. |
| `/sessions` | `frontend/src/app/sessions/page.tsx:SessionsPage`; server redirect to `/trade-workspace`. | `REPLACE_FOR_GUIDED_FLOW` | UX2.1/UX3.x need a real sessions surface. |
| `/sessions/new` | `frontend/src/app/sessions/new/page.tsx:NewSessionPage`; server redirect to `/trade-workspace`. | `REPLACE_FOR_GUIDED_FLOW` | UX3.4 needs a dedicated create route. |
| `/sessions/[sessionId]` | `frontend/src/app/sessions/[sessionId]/page.tsx:SessionDetailPage`; server redirect to `/trade-workspace`. | `REPLACE_FOR_GUIDED_FLOW` | UX4/UX5 need route-backed detail and lifecycle surfaces. |
| `/evaluations` | `frontend/src/app/evaluations/page.tsx`; separate evaluation surface. | `REUSE_AS_IS` | Not part of the approved guided-session scope unless a later task discovers a dependency. |

Direct URL and refresh behavior is therefore currently redirect-based for the session routes, not route-level state recovery. The app-wide auth owner is `frontend/src/lib/auth-context.tsx:AuthProvider/useAuth`; the global shell is `frontend/src/app/layout.tsx:RootLayout` plus `frontend/src/components/header.tsx:Header`.

## 6. Workspace Composition and Symbol Map

| Current responsibility | Exact repo target and symbol | Current dependency/caller | Classification / finding |
|---|---|---|---|
| Workspace composition | `frontend/src/features/trade-workspace/trade-workspace.tsx:TradeWorkspace` | `/trade-workspace` page | `REPLACE_FOR_GUIDED_FLOW`; owns list, create, selection, evidence cache, and active detail in one tree. |
| Session list/selection | `frontend/src/features/trade-workspace/session-list.tsx:TradeWorkspaceSessionList` | `TradeWorkspace` | `REUSE_WITH_ADAPTATION`; local button selection, no route identity or archive grouping. |
| Create | `frontend/src/features/trade-workspace/create-session.tsx:CreateTradeSession` and `frontend/src/features/trade-workspace/api.ts:createSession` | `TradeWorkspace` callback prepends session and selects it | `REUSE_WITH_ADAPTATION`; UX3.4/3.5 need dedicated route and success navigation. |
| Active detail | `frontend/src/features/trade-workspace/workspace.tsx:SessionWorkspace` | keyed by `selected` in `TradeWorkspace` | `REPLACE_FOR_GUIDED_FLOW`; owns all lifecycle branches and server reads. |
| Initial Evidence | `frontend/src/features/trade-workspace/initial-evidence-panel.tsx:InitialEvidencePanel`; `frontend/src/features/evidence/evidence-upload-form.tsx:EvidenceUploadForm` | `SessionWorkspace` and V2 evidence API | `REUSE_WITH_ADAPTATION`; surface can feed UX5.1 but is coupled to current shell. |
| Initial Analysis | `SessionWorkspace` functions `readInitialAnalysis`, `submitInitialAnalysis`, `retryInitialAnalysis` | V2 routes/services | `REUSE_WITH_ADAPTATION`; processing/recovery logic is present but not route-owned. |
| Analysis reading/history | `frontend/src/features/analysis/initial-analysis-view.tsx:InitialAnalysisView`, `watching-update-view.tsx:WatchingUpdateView`, `open-position-update-view.tsx:OpenPositionUpdateView`, `closing-analysis-view.tsx:ClosingAnalysisView`, `history/analysis-history.tsx:AnalysisHistory` | Workspace/session shell callers | `REUSE_WITH_ADAPTATION`; UX5.3/5.11 need page-level placement. |
| BUY/WAIT/SKIP | `frontend/src/features/trade-workspace/decision-panel.tsx:DecisionPanel`, `buy-decision-form.tsx:BuyDecisionForm`, `wait-update-form.tsx:WaitUpdateForm`, `skip-decision-form.tsx:SkipDecisionForm` | `SessionWorkspace` and V2 decision endpoints | `REUSE_WITH_ADAPTATION`; decision rules are already V2-authoritative. |
| WAIT Update | `frontend/src/features/trade-workspace/wait-update.tsx:WaitUpdatePanel` | `SessionWorkspace` | `REUSE_WITH_ADAPTATION`; local analysis polling and form state must survive route transitions. |
| Position Update/Close | `frontend/src/features/trade-workspace/position-update.tsx:PositionUpdatePanel`, `close-position-form.tsx:ClosePositionForm` | `SessionWorkspace` | `REUSE_WITH_ADAPTATION`; V2 endpoint coverage exists, guided focused surfaces do not. |
| Terminal/history/timeline | `frontend/src/features/trade-session/lifecycle-status.tsx:LifecycleStatus`, `trade-session-shell.tsx:TradeSessionShell`, `frontend/src/features/trade-workspace/timeline.tsx:Timeline`, `frontend/src/features/analysis/history/analysis-history.tsx:AnalysisHistory` | Current workspace/session detail callers | `REUSE_WITH_ADAPTATION`; UX5.10/5.11 require read-only and dedicated history behavior. |

## 7. Selected-Session State Ownership

| State | Current owner | Source of truth | Risk observed |
|---|---|---|---|
| Session collection | `TradeWorkspace` `sessions` state | `listSessions()` from `frontend/src/features/trade-workspace/api.ts` | Refresh is explicit only; list and detail can diverge after mutations. |
| Selected session | `TradeWorkspace` `selected` state and `setSelected` | Local state; first list item is selected when null | High: selection is not encoded in URL, so refresh/direct URL cannot recover it. |
| Active detail identity | `SessionWorkspace` `sessionId` prop, keyed by selected ID | Parent local selection | Key remount clears child state on selection, but stale async callbacks are only guarded by local cancellation. |
| Evidence cache | `TradeWorkspace` `evidence` record keyed by session ID | Child callback `onEvidence` | Medium: cache is parent-local and not server-authoritative after navigation. |
| Auth | `AuthProvider` and `useAuth` | Auth API/session state | Login safe-next currently excludes `/sessions*`. |
| Server detail/availability/aggregate | `SessionWorkspace` states `session`, `availability`, `aggregate` | V2 `getSession`, `getAvailableActions`, `getSessionDetail` | Multiple reads can temporarily represent different server revisions. |
| Form and processing state | `SessionWorkspace`, `WaitUpdatePanel`, `PositionUpdatePanel`, individual form components | Local `useState` | Medium/high on refresh: in-progress form input is not route-persisted. |
| Duplicate submission guard | `SessionWorkspace.inFlight`, panel `busy` states | Local refs/state | Present for some reads/submits; coverage is component-specific, not global. |

## 8. Polling and Request-Recovery Map

| Owner | Interval | Request/status | Start/stop and cleanup | Gap |
|---|---:|---|---|---|
| `frontend/src/features/jobs/job-status.tsx:JobStatus` | 3,000 ms | `getJobStatus(jobId)`; terminal `COMPLETED/FAILED/CANCELLED` | Initial `poll()`; timeout on nonterminal/error; `cancelledRef` and `clearTimeout` on unmount | Legacy job API surface; session ID is a prop, not the polling key. |
| `frontend/src/features/trade-workspace/workspace.tsx:SessionWorkspace` initial-analysis effect | 5,000 ms | `readInitialAnalysis(sessionId)` while session `ANALYZING` and request nonterminal | Timeout after each read; stops on completed/failed or effect cleanup; `inFlight` ref | Request/status and active session are component-local; no route recovery. |
| `frontend/src/features/trade-workspace/wait-update.tsx:WaitUpdatePanel` | 4,000 ms | `readWaitUpdateAnalysis(sessionId)` while request is active | Timeout after read/error; cleanup clears timer; depends on `requestStatus`, `sessionId`, callbacks | Retry and finish callbacks are local; cross-route ownership is absent. |
| `frontend/src/features/trade-workspace/position-update.tsx:PositionUpdatePanel` | 4,000 ms | `readPositionUpdates(sessionId)` while processing | Timeout after read/error; cleanup clears timer; effect depends on `isProcessing`, `sessionId` | Same local ownership and refresh-loss issue. |

No `setInterval` polling owner was found in the audited frontend scope. The required future discovery is to make route-level identity and request recovery explicit without changing V2 lifecycle semantics. Existing polling tests include `frontend/src/features/jobs/job-status.test.tsx`, `frontend/src/features/trade-workspace/polling-loop.test.tsx`, `wait-update.test.tsx`, and `position-update.test.tsx`.

## 9. Backend V2 Inventory

| Area | Exact files/symbols | Current responsibility | Finding |
|---|---|---|---|
| Session model/status | `backend/app/trade_workspace/models/trade_session.py:TradeSessionV2Status`, `TradeSessionV2` | Canonical V2 lifecycle and `trade_sessions_v2` row | Seven approved statuses; no archive metadata. |
| Session persistence | `backend/app/trade_workspace/services/trade_sessions.py:RebuildTradeSessionService.create/list_owned/get_owned` | Creates, lists, and owner-scopes sessions | `list_owned` returns every owned V2 row; no archive filter. |
| API route boundary | `backend/app/trade_workspace/api/routes/trade_sessions.py:router`, `create_trade_session`, `list_trade_sessions`, `get_trade_session`, `get_session_detail_aggregate` | `/api/v2/trade-sessions` create/list/detail/aggregate | Ownership is `get_current_user` plus `current_user.id`; no Archive/restore handlers. |
| Response schemas | `backend/app/trade_workspace/api/schemas.py:TradeSessionResponse`, `TradeSessionListResponse`, `SessionDetailAggregateResponse` | V2 response contract | Response has no archive metadata. |
| Lifecycle/evidence | `backend/app/trade_workspace/services/{decision_availability,evidence_uploads,initial_analysis_submission,initial_analysis_read,initial_analysis_retry,wait_decision,wait_update_input,wait_update_analysis_submission,wait_update_analysis_read,wait_update_analysis_retry,buy_decision,skip_decision,position_update_input,position_update_analysis_submission,position_update_read,close}.py` | V2 lifecycle, evidence, request, decision, position, closure operations | Reusable domain behavior; Archive must remain orthogonal. |
| Request/worker | `backend/app/trade_workspace/services/analysis_request_queue.py:AnalysisRequestQueueService`, `analysis_request_claim.py:AnalysisRequestClaimService`, `backend/app/trade_workspace/workers/analysis_processor.py:RebuildAnalysisProcessor` | Queue, claim, process, validate, persist analysis | No redesign change is authorized here. |
| Aggregate | `backend/app/trade_workspace/services/session_detail_aggregate.py:SessionDetailAggregateService` | Joins V2 session, evidence, requests, decisions, position, closure | Candidate read source for guided detail; exact UI mapping remains task work. |

The V2 routes consistently pass `user_id` into service methods and query owner fields. The audit found no V2 Archive path to reuse.

## 10. Database and Migration Impact

The V2 migration chain is explicit and sequential: `backend/migrations/versions/7f3a9c2d1b4e_p31_trade_sessions_v2.py` creates `trade_sessions_v2` with owner, status, ticker/company, note, timestamps, and `closed_at`, followed by `8c4d2e6f1a3b_p32_analysis_requests_v2.py`, `9d5e7f1a3c2b_p33_evidence_uploads_v2.py`, `a7b8c9d0e1f2_p34_session_decisions_v2.py`, `b8c9d0e1f2a3_p35_positions_v2.py`, and `c9d0e1f2a3b4_p36_trade_closures_v2.py`. Model indexes cover owner, status, and creation time; child tables use restrictive session foreign keys and relevant uniqueness constraints.

`TradeSessionV2` and its migration have no `archived_at` or equivalent metadata. The minimal future Archive location is therefore the V2 session row/model and its migration path, but UX0.2 does not design or edit that migration. Legacy `backend/app/models/trade_session.py` and its migrations must not be treated as the V2 schema.

## 11. Archive Gaps

Confirmed V2 gaps: no archive metadata column/model field, no V2 archive eligibility service, no V2 list filtering, no V2 archive/restore route, no V2 response field, no V2 frontend archive action/list/detail surface, and no V2 archive regression tests.

Legacy Archive exists at `backend/app/services/actions/archive_session.py:ArchiveSessionActionService`, `backend/app/api/routes/trade_sessions.py` under `/api/trade-sessions/{session_id}/archive`, `frontend/src/lib/api/trade-sessions.ts:archiveSession`, and `backend/tests/services/actions/test_cancel_archive.py`. It transitions the legacy status to `TradeSessionStatus.ARCHIVED` and records `ActionType.SESSION_ARCHIVED`; this is `LEGACY_COUPLING_ONLY`, not a safe implementation target.

## 12. Legacy versus V2 Coupling

| Coupling | Evidence | Classification | Risk |
|---|---|---|---|
| Frontend session API | `frontend/src/lib/api/trade-sessions.ts` uses `/api/trade-sessions` for create/list/detail and `archiveSession`; `frontend/src/features/trade-workspace/api.ts` uses `/api/v2/trade-sessions` for the active workspace. | `LEGACY_COUPLING_ONLY` plus V2 reuse | HIGH; screens can silently target different contracts. |
| Route cutover | `/sessions*` redirect to `/trade-workspace`; root/login also target workspace. | `REPLACE_FOR_GUIDED_FLOW` | HIGH; every entry point bypasses future page hierarchy. |
| Legacy status/archive | `backend/app/models/enums.py:TradeSessionStatus` includes `ARCHIVED`; legacy route/action service owns transition. | `LEGACY_COUPLING_ONLY` | HIGH/BLOCKING for Archive implementation if reused. |
| Shared UI/domain names | `TradeSession`, `TradeSessionStatus`, and session API names exist in both feature and legacy paths. | `DISCOVERY_REQUIRED` | MEDIUM; imports must be traced during UX8.1. |
| V2 lifecycle | `backend/app/trade_workspace` routes/services/models and focused V2 tests. | `REUSE_AS_IS` for domain behavior | LOW for redesign, provided UI stays on V2. |

## 13. Test Inventory and Gaps

Static inventory found 40 frontend test files and 155 backend test files.

Existing focused coverage includes login and cutover (`frontend/src/__tests__/login.test.tsx`, `cutover.test.tsx`), header, sessions create/list/card, workspace selection/evidence/polling, JobStatus polling/failure, trade-session shell/summary/history, and V2 API tests for session create/list/detail, evidence, initial analysis, recovery/retry, decisions, WAIT Update, Position Update, Close, ownership, and decision-flow gates.

Not found as focused current tests: `/sessions*` real route rendering and refresh recovery; URL-owned selection; archive metadata migration/model; V2 archive eligibility/filter/API/restore; archive-only non-lifecycle assertions; mobile viewport/browser evidence; keyboard semantics across the guided flow; Indonesian copy consistency; and one end-to-end guided multi-page flow covering request recovery and terminal read-only history. No broad test suite was run.

## 14. Reuse and Replacement Classification Matrix

| Classification | Audited targets | Evidence/rationale |
|---|---|---|
| `REUSE_AS_IS` | V2 lifecycle services and V2 focused backend tests; evaluations route | Existing authoritative behavior is already V2-aligned and outside redesign change. |
| `REUSE_WITH_ADAPTATION` | `AuthProvider`, `Header`, session cards/forms, evidence/analysis/decision forms, V2 API client, V2 aggregate service | Behavior is useful, but ownership, route placement, copy, and recovery need guided-flow adaptation. |
| `REPLACE_FOR_GUIDED_FLOW` | `/trade-workspace` composition, `/sessions*` redirects, `TradeWorkspace`, `SessionWorkspace` | Current single-page/local-selection architecture conflicts with approved multi-page routing. |
| `LEGACY_COUPLING_ONLY` | legacy `/api/trade-sessions`, `archiveSession`, `ArchiveSessionActionService`, `TradeSessionStatus.ARCHIVED` | Wrong data model and lifecycle semantics for metadata-only V2 Archive. |
| `NEW_IMPLEMENTATION_REQUIRED` | V2 Archive metadata/eligibility/filter/API, archived routes, restore action, route-level recovery | No authoritative current implementation exists. |
| `DISCOVERY_REQUIRED` | UX8.1 shared imports/cutover and exact future nested route/component boundaries | Current files exist, but final ownership must be confirmed during the named task. |

## 15. Dependency Map

| Dependency | Current target | Official task | Risk/failure mode | Mitigation/discovery |
|---|---|---|---|---|
| Authority/repository alignment | UX0.1 matrix, current branch/source lock | UX0-G | High if sources drift | Gate rereads and conflict register. |
| Archive persistence | `TradeSessionV2`, V2 migration chain | UX1.1 | High: no metadata to filter | Add only through approved task; migration tests required. |
| Archive eligibility/domain | `RebuildTradeSessionService`, V2 status | UX1.2 | High: lifecycle could be mutated | Explicit metadata-only eligibility discovery. |
| Active list filtering | `list_owned`, V2 list route | UX1.3 | High: archived rows leak into active list | Focused list/filter tests. |
| Archive/restore contract | V2 route/schemas | UX1.4 | High: legacy endpoint may be reused | Contract and ownership tests. |
| Route hierarchy | `frontend/src/app/*`, current redirects | UX2.1–2.4 | High: direct URL loses context | Route and refresh tests. |
| Selected-session identity | `TradeWorkspace.selected` | UX2.4, UX4.4 | High: wrong session detail after navigation | URL/session identity discovery and focused tests. |
| Guided Session Flow Surfaces | `SessionWorkspace` and child panels | UX4.1–UX5.11 | Medium/high: duplicated lifecycle behavior | Reuse V2 APIs; preserve state rules and polling tests. |
| Archive UI | no V2 frontend implementation | UX6.1–6.4 | High: archive may become session state | Depend on UX1 contract and read-only assertions. |
| Responsive/accessibility/copy/state | global CSS and all feature components | UX7.1–7.5 | Medium: visual/semantic regressions | Targeted browser/viewport evidence. |
| Legacy cutover | `/api/trade-sessions`, `/trade-workspace`, shared imports | UX8.1–8.3 | Blocking if old endpoint remains reachable for target flow | Inventory first, then focused regression. |

## 16. Risk Register

| ID | Level | Evidence | Official task | Failure mode / mitigation | Blocks |
|---|---|---|---|---|---|
| R1 | BLOCKING | Legacy Archive is session status/action, not metadata | UX1.1–1.4 | Reusing it changes domain semantics; keep it legacy-only and define V2 contract first | UX1; UX6 |
| R2 | HIGH | V2 list returns all owner rows; no archive field | UX1.1–1.3 | Active/archived separation cannot be proven until V2 persistence/filter exists | UX1; UX0-G review |
| R3 | HIGH | `selected` is local state in `TradeWorkspace` | UX2.4, UX4.4 | Refresh/direct URL loses selected session; route recovery discovery/tests required | UX2; UX4 |
| R4 | HIGH | Four independent polling owners with local timers | UX5.2, UX5.6, UX5.8, UX8.3 | Duplicate/stale requests or wrong session display during navigation; retain cleanup and add focused identity tests | UX5; UX8 |
| R5 | HIGH | Frontend legacy and V2 API helpers coexist | UX8.1–8.2 | A redesigned screen may call the wrong contract; import/cutover audit required | UX8 |
| R6 | MEDIUM | Form/request state is component-local | UX2.4, UX5.x | Browser refresh loses in-progress context; discovery and recovery behavior required | UX2; UX5 |
| R7 | MEDIUM | No focused mobile/browser/keyboard matrix | UX7.1–7.5, UX8.4 | Responsive/accessibility defects escape unit tests | UX7; UX8 |
| R8 | LOW | V2 lifecycle and ownership tests are broad across many focused files | UX8.3 | Reuse is likely, but task-level coverage mapping remains required | UX8 |

## 17. Future-Task Target Matrix

The following maps every official implementation task UX1.1–UX8.5. “Discovery” is explicit wherever a target is absent or its final ownership is unresolved.

| Task | Current repo target / expected new area | Dependencies and risks | Existing focused tests | Missing focused test/discovery |
|---|---|---|---|---|
| UX1.1 Archive Persistence Model and Migration | `TradeSessionV2`, `trade_sessions_v2`, P31 migration; new V2 archive metadata migration area | UX0-G; R1/R2 high | V2 model/migration inventories | Archive field/constraint migration test; do not reuse legacy schema. |
| UX1.2 Archive Domain Eligibility Service | `RebuildTradeSessionService`; new `trade_workspace` eligibility service | UX1.1; R1 | V2 lifecycle/service tests | Eligibility matrix and non-lifecycle assertion; exact new service symbol discovery. |
| UX1.3 Session List Archive Filtering | `list_owned`, V2 `list_trade_sessions`; frontend V2 list adapter | UX1.1/1.2; R2 | V2 session API tests | Active/archived filter tests and query contract. |
| UX1.4 Archive and Restore API Contract | V2 `trade_sessions.py`, `schemas.py`; new V2 handlers | UX1.1–1.3; R1/R2 | V2 route/ownership tests | Archive/restore API tests; exact endpoint names are intentionally not invented here. |
| UX1.5 Archive Backend Regression Verification | V2 API/service/model test areas | UX1.1–1.4 | V2 lifecycle, ownership, decision gate tests | Archive-only regression suite and legacy isolation test. |
| UX2.1 New Route Skeletons | `frontend/src/app/{sessions,sessions/new,sessions/[sessionId]}` currently redirect; new archived/nested route areas require discovery | UX1.4; R3 | Existing route files, login/cutover tests | Route render/404/refresh inventory; exact new route boundaries. |
| UX2.2 Post-Login Sessions Redirect | `page.tsx:Home`, `login/page.tsx:LoginForm.safeNext` | UX2.1; R3/R5 | `login.test.tsx`, `cutover.test.tsx` | Assert authenticated redirect to `/sessions`, safe-next behavior. |
| UX2.3 Global Navigation Shell | `layout.tsx:RootLayout`, `components/header.tsx:Header`, `globals.css` | UX2.1; R7 | `header.test.tsx` | Route-aware navigation and mobile keyboard tests. |
| UX2.4 Route-Level State Recovery Foundation | `AuthProvider`, API client, current local state owners | UX2.1–2.3; R3/R6 | client/auth tests | Direct URL, refresh, stale session, and request recovery tests. |
| UX3.1 Sessions List Data Integration | `features/sessions/session-list.tsx`, `lib/api/trade-sessions.ts`, V2 list route | UX1.3, UX2.4; R5 | session-list tests, V2 list tests | V2-only active list and archive exclusion test. |
| UX3.2 Sessions List Card and Status Presentation | `features/sessions/session-card.tsx`, `helpers.ts`, `trade-session/lifecycle-status.tsx` | UX3.1; R7 | card/list tests | All V2 statuses and Indonesian responsive fixtures. |
| UX3.3 Sessions UI Grouping | `features/sessions/session-list.tsx`, helpers; new grouping presentation area | UX1.3, UX3.1; R2 | list tests | Grouping/filter empty/loading tests. |
| UX3.4 Dedicated Create Session Form | `features/sessions/create-session-form.tsx`, `app/sessions/new/page.tsx` | UX2.1, V2 create route; R3 | create-session-form tests | Route-level form submit/error tests. |
| UX3.5 Create Success Navigation | create form/page and V2 create response | UX3.4, UX2.4; R3 | form tests | URL navigation and refresh after create. |
| UX4.1 Session Header and Identity Context | `app/sessions/[sessionId]/page.tsx`, `trade-session/session-header.tsx` | UX2.4/3.5; R3 | trade-session shell tests | Direct identity and owner mismatch tests. |
| UX4.2 Backend-Authoritative Current-Step Model | `decision_availability.py`, `session_detail_aggregate.py`, V2 response schemas | V2 lifecycle; R3/R4 | `test_decision_availability_v2.py`, gate tests | Full status/action-to-step matrix. |
| UX4.3 Session Summary Content | `trade-session-shell.tsx`, `canonical-position-summary.tsx`, `section-placeholder.tsx` | UX4.1/4.2 | shell/summary tests | Aggregate completeness/terminal read-only tests. |
| UX4.4 In-Session Navigation | current `[sessionId]` redirect and `trade-session` components; new nested route area discovery | UX2.4, UX4.1; R3/R4 | shell navigation-adjacent tests | Route map and back/forward/refresh identity tests. |
| UX5.1 Initial Evidence Focused Surface | `initial-evidence-panel.tsx`, `evidence-upload-form.tsx`, V2 evidence services/routes | UX4.2/4.3 | V2 evidence API and hydration tests | Guided route submit/reload coverage. |
| UX5.2 Initial Analysis Processing Recovery | `SessionWorkspace`, `JobStatus`, V2 initial analysis read/submit/retry | UX4.2; R4 | polling-loop, job-status, initial-analysis tests | Route refresh, duplicate submit, stale-session polling tests. |
| UX5.3 Analysis Reading Experience | `features/analysis/*`, V2 aggregate/read services | UX5.2; R4 | analysis/trade-session shell tests | Loading/failure/terminal reading fixtures. |
| UX5.4 Decision Surface — BUY, WAIT, SKIP | decision panel/forms, V2 buy/wait/skip services/routes | UX4.2/5.3 | V2 decision and frontend decision tests | Guided action matrix and duplicate submission tests. |
| UX5.5 WAITING Summary and WAIT Update Entry | `wait-update.tsx`, `wait-update-form.tsx`, summary components | UX5.4; R4 | wait-update tests | Entry/refresh/status recovery tests. |
| UX5.6 WAIT Update Focused Surface | `WaitUpdatePanel`, V2 wait input/submission/read/retry | UX5.5; R4 | wait-update input/submission/recovery tests | Route-owned polling identity and retry tests. |
| UX5.7 Open Position Summary and Actions | `open-position-panel.tsx`, `canonical-position-summary.tsx`, V2 buy/position services | UX5.4; R4 | open-position and V2 buy tests | Summary/action availability matrix. |
| UX5.8 Position Update Focused Surface | `PositionUpdatePanel`, `position-update-form.tsx`, V2 position services | UX5.7; R4 | position update/polling tests | Refresh, stale response, close transition tests. |
| UX5.9 Close Session Focused Surface | `close-position-form.tsx`, `PositionUpdatePanel`, V2 `CloseService`/`create_close` | UX5.8 | V2 close and close form tests | Guided close/terminal navigation test. |
| UX5.10 Terminal Session Read-Only Mode | `lifecycle-status.tsx`, `trade-session-shell.tsx`, terminal branches in `SessionWorkspace` | UX4.2, UX5.9 | shell/status tests | Mutation blocking and refresh read-only test. |
| UX5.11 Complete Session History View | `timeline.tsx`, `lib/api/timeline.ts`, analysis history components, V2 aggregate | UX5.10; R4 | timeline/history tests | Dedicated history route and full aggregate fixture. |
| UX6.1 Archive Confirmation and Action | No V2 UI; legacy `archiveSession` is not reusable; new V2 action surface after UX1.4 | UX1.4, UX4.3; R1 | legacy archive test only | V2 metadata-only confirmation test; discovery of final component location. |
| UX6.2 Archived Sessions List | No current route/surface; new archived list area after UX1.3 | UX2.1, UX1.3; R2 | none for V2 archive list | Route/list/filter/empty-state tests. |
| UX6.3 Archived Session Read-Only Detail | Current detail route redirects; new read-only route area | UX4.1, UX6.2; R1/R3 | terminal shell tests | Archive read-only and no session-state mutation tests. |
| UX6.4 Restore to Completed List | No V2 restore path; new V2 API/UI after UX1.4 | UX1.4, UX6.2/6.3; R1 | none for V2 restore | Restore eligibility, list return, ownership tests. |
| UX7.1 Mobile Responsive Foundation | `globals.css`, `layout.tsx`, all app/feature surfaces | UX2–6; R7 | component class assertions | Viewport/browser evidence matrix. |
| UX7.2 Mobile Forms and Upload Refinement | evidence and guided session form components | UX5.1/5.6/5.8; R7 | form/unit tests | Mobile upload/input/error browser tests. |
| UX7.3 Accessibility Semantics and Keyboard Flow | Header, session list/cards, forms, route surfaces | UX2–6; R7 | header/session list tests | Keyboard/focus/label/aria focused tests. |
| UX7.4 Indonesian UI Copy Consistency | copy in app/features/components; no centralized copy module identified | UX2–6; R7 | no copy inventory | Copy inventory and exact discovery of ownership. |
| UX7.5 System-State Visual Consistency | loading/error/processing components, `JobStatus`, feedback components | UX5; R4/R7 | job/analysis failure tests | Cross-screen state fixture and browser verification. |
| UX8.1 Legacy Workspace Dependency Audit | `frontend/src/app/trade-workspace`, feature imports, legacy API helpers, backend legacy routes/services | UX1–7; R5 | cutover and existing API tests | Complete import/redirect/status audit is the task itself. |
| UX8.2 Legacy Entry-Point Redirect | root/login/session redirect files and legacy API entry points | UX8.1; R5 | `cutover.test.tsx`, login tests | Redirect and legacy endpoint reachability tests. |
| UX8.3 Focused Full-Flow Regression | all guided routes/components plus V2 API tests | UX1–8.2; R4/R5 | extensive focused unit/API inventory | One guided full-flow test with polling/recovery/archive boundaries. |
| UX8.4 Production-Like Visual Verification | app routes, CSS, browser/local evidence areas | UX7, UX8.3; R7 | no current browser matrix | Browser/viewport evidence discovery and verification. |
| UX8.5 Documentation and Traceability Finalization | `docs/ui-ux/UX0.1...`, this audit, redesign docs | all prior tasks | UX0.1 matrix | Final traceability/AC matrix and document consistency check. |

## 18. Conflict and BLOCKED Register

| Item | Result |
|---|---|
| Missing authoritative source | None. Actual approved DOCX files were readable and inspected. |
| V2 versus legacy indistinguishable | Resolved for this audit: prefixes, modules, models, statuses, migrations, and tests distinguish them. |
| Future task unmappable | None. All UX1.1–UX8.5 have a concrete current target or an explicit discovery/new-area entry. |
| Polling/session ownership undetermined | Resolved: four polling owners and `TradeWorkspace.selected` are identified above. |
| Product Owner decision required now | No. UX0.2 records that exact Archive endpoint names and final new route/component names remain future-task discovery, not unresolved source conflict. |
| Implementation blocked | Intentionally not applicable; UX0.2 is an audit, not implementation. |

## 19. UX0.2 Acceptance Criteria Evaluation

1. **Every future task has concrete repo targets or a documented discovery step — PASS.** The matrix in Section 17 contains all official implementation tasks UX1.1 through UX8.5 and gives each an exact current target, expected new area, or explicit discovery step.
2. **Polling and selected-session state ownership are explicitly mapped — PASS.** Sections 7 and 8 identify the parent/local owners, server sources, intervals, start/stop conditions, cleanup, and stale/refresh risks.
3. **No implementation started — PASS.** Only this new Markdown audit was added; no application, test, migration, configuration, dependency, skill, or authoritative source file was edited; no broad tests or real Gemini request were run.

All UX0.2 acceptance criteria pass. UX0.2 is complete.

## 20. Change Confirmation and Next Official Task

Changed file: `docs/ui-ux/UX0.2_CURRENT_MAIN_BRANCH_UI_UX_IMPACT_AUDIT_2026-08-04.md` only.

No application, test, migration, configuration, dependency, skill, or authoritative source file changed. No implementation, refactor, broad test run, or real Gemini request was performed.

Next official task: **UX0-G — Phase Gate — Authority and Repository Alignment**

UX0-G was not executed and no UX0-G prompt was generated.
