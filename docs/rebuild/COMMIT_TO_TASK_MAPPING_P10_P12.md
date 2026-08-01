# Stage 2C — Commit-to-Task Mapping for P10.1–P12.6

## Audit metadata

- Baseline: `fdb1563efa835e9eb3075ce385c7d0ea98dffc06`
- Audited HEAD before this audit: `c91a7c81a859a5a6f0d11c21e4482ce0e7a4fc17`
- Branch: `main`
- Audit date: `2026-08-01`
- Audited task range: executable P10.1–P12.6 tasks, including P12.5a–P12.5g;
  P12.5 umbrella is non-executable and is not separately statused
- History inspected: `fdb1563efa835e9eb3075ce385c7d0ea98dffc06..HEAD`

## Methodology

The PRD is product authority, the Detailed Task Plan is sequence and task-body
authority, the ledger is task-control authority, and the Stage 2A/2B mappings
are prior committed audit context. I began with a commit-to-path inventory,
then inspected the final committed rebuild frontend, routes, legacy surfaces,
focused tests, and committed Gate D–F verification records. Commit messages
were supporting evidence only.

No application tests, browser automation, migrations, Docker, production
requests, or Gemini requests were run. Existing committed verification records
were treated as supplementary evidence and never as a substitute for the exact
required implementation or acceptance evidence. Uncommitted work received no
credit.

## Summary

| Status | Count |
| --- | ---: |
| COMPLETED | 2 |
| PARTIAL | 5 |
| NOT IMPLEMENTED | 16 |
| NOT AUDITABLE | 0 |
| BLOCKED | 0 |

| Task | Status | Mapped commit(s) |
| --- | --- | --- |
| P10.1 | NOT IMPLEMENTED | NONE |
| P10.2 | PARTIAL | `84e01d0` |
| P10.3 | NOT IMPLEMENTED | NONE |
| P10.4 | COMPLETED | `84e01d0`, `4d25ae9`, `9034c0c`, `9716d87` |
| P10.5 | COMPLETED | `62a4d00`, `2a4bce8`, `9034c0c` |
| P11.1 | NOT IMPLEMENTED | NONE |
| P11.2 | NOT IMPLEMENTED | NONE |
| P11.3 | NOT IMPLEMENTED | NONE |
| P11.4 | NOT IMPLEMENTED | NONE |
| P11.5 | PARTIAL | `14fd234`, `9bafd72` |
| P11.6 | PARTIAL | `5087d9a`, `14fd234`, `974fb6f` |
| P12.1 | NOT IMPLEMENTED | NONE |
| P12.2 | PARTIAL | `08e1700` |
| P12.3 | NOT IMPLEMENTED | NONE |
| P12.4 | PARTIAL | `08e1700` |
| P12.5a | NOT IMPLEMENTED | NONE |
| P12.5b | NOT IMPLEMENTED | NONE |
| P12.5c | NOT IMPLEMENTED | NONE |
| P12.5d | NOT IMPLEMENTED | NONE |
| P12.5e | NOT IMPLEMENTED | NONE |
| P12.5f | NOT IMPLEMENTED | NONE |
| P12.5g | NOT IMPLEMENTED | NONE |
| P12.6 | NOT IMPLEMENTED | NONE |

## Phase 10 mappings

### P10.1 — Create Session Detail Aggregate API

- Previous: `P9.3`; next: `P10.2`.
- Authoritative scope: one ownership-safe aggregate response containing session,
  initial evidence, Initial Analysis, decisions, WAIT Updates, position,
  Position Updates, and closure, in chronological form with bounded efficient
  queries and no old workflow records.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant changed files: none matching an aggregate API. The rebuild route
  exposes separate session, evidence, analysis, decision, WAIT, Position, and
  close endpoints.
- Repository evidence: `backend/app/trade_workspace/api/routes/trade_sessions.py`
  has separate handlers; the frontend calls `getSession`,
  `readInitialEvidence`, `readInitialAnalysis`, and separate update reads.
  No aggregate response model or query service exists. Legacy timeline routes
  are outside the rebuild boundary.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: create and verify one V2 aggregate endpoint with chronological,
  ownership-safe, bounded data loading.

### P10.2 — Build Session Header and Status Display

- Previous: `P10.1`; next: `P10.3`.
- Authoritative scope: display ticker, company name, current status, created
  time, latest update, closed time, and active decision state.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commit: `84e01d0`.
- Relevant files: `frontend/src/features/trade-workspace/workspace.tsx`,
  `trade-workspace.tsx`, and workspace types.
- Repository evidence: the workspace header displays ticker, company name, and
  status. It does not display created time, latest update, closed time, or an
  active decision state, and the session API response is not an aggregate
  header contract.
- Supplementary evidence: none.
- Status: **PARTIAL**.
- Remaining gap: complete the required header fields and active decision state,
  preferably from the aggregate API.

### P10.3 — Build Chronological Timeline

- Previous: `P10.2`; next: `P10.4`.
- Authoritative scope: one readable chronological timeline containing evidence,
  Initial Analysis, WAIT, WAIT Update, BUY, Position Update, SKIP, and CLOSE,
  without overwriting events and with Indonesian labels.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant changed files: none. The workspace renders separate result and
  update panels without a unified event model or timeline component.
- Repository evidence: `frontend/src/features/trade-workspace/workspace.tsx`
  has no chronological event list; `frontend/src/lib/api/timeline.ts` points to
  the legacy `/api/trade-sessions/{id}/timeline` endpoint, not rebuild history.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: implement a V2 timeline sourced from preserved session events
  and verify all eight required event categories and ordering.

### P10.4 — Build Status-Based Action Panel

- Previous: `P10.3`; next: `P10.5`.
- Authoritative scope: DRAFT upload; ANALYZING processing; ANALYZED BUY/WAIT/SKIP;
  WAITING WAIT form plus BUY/SKIP; OPEN_POSITION update plus CLOSE; and
  read-only CLOSED/CLOSED_SKIPPED.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `84e01d0`, `4d25ae9`, `9034c0c`, `9716d87`.
- Relevant files: rebuild workspace, decision UI, WAIT/Position panels, close
  UI, and focused component tests.
- Repository evidence: committed UI behavior selects actions from V2
  availability, exposes DRAFT upload/ANALYZING progress, decision controls,
  WAIT and Position forms, CLOSE, and suppresses actions for terminal states.
  Focused tests cover the decision, Position, and CLOSE behavior.
- Supplementary evidence: none.
- Status: **COMPLETED**.
- Remaining gap: no gap identified in the action-visibility scope; aggregate
  data and timeline remain separate P10 tasks.

### P10.5 — Build Failure and Retry UI

- Previous: `P10.4`; next: `P11.1`.
- Authoritative scope: clearly show failed analysis, preserve evidence and user
  input, offer manual retry, prevent duplicate requests, and avoid status
  corruption for all three analysis types.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `62a4d00` (Initial Analysis retry), `2a4bce8` (WAIT retry and
  recovery), `9034c0c` (Position Update UI), with worker failure handling in
  `974fb6f`.
- Relevant files: initial retry service/UI, WAIT retry/read UI, Position Update
  UI, worker failure path, and focused tests.
- Repository evidence: committed Gate D and Gate F records show preserved
  evidence, sanitized failures, explicit retry, same-request recovery, and no
  duplicate request; Position Update tests cover failed result rendering. The
  rebuild processor restores DRAFT, WAITING, or OPEN_POSITION after failure.
- Supplementary evidence: Gate D/F were disposable or mocked, not production.
- Status: **COMPLETED**.
- Remaining gap: the P7.2/P8.2 temporary ANALYZING submission deviations remain
  carry-forward lifecycle issues, not missing retry UI.

## Phase 11 mappings

### P11.1 — Verify Direct BUY Path

- Previous: `P10.5`; next: `P11.2`.
- Authoritative scope: Create → Initial Analysis → BUY → Position Update →
  CLOSE, with real Initial Analysis and Position Update Gemini requests and
  verification of files, stored responses, Indonesian output, user facts, and
  closure.
- Authoritative acceptance criteria: files sent; responses stored; Indonesian
  output; user facts preserved; session closes.
- Mapped commits: `NONE`.
- Relevant changed files: no committed authoritative end-to-end acceptance
  record for this exact path. Older legacy E2E tests are not rebuild evidence.
- Repository evidence: Gate D covers Initial Analysis and Gate E covers
  decisions, but no committed record joins this full path with real Gemini and
  Position Update through CLOSE.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: execute and commit production-like acceptance evidence after
  recovery and after the authoritative lifecycle gaps are repaired.

### P11.2 — Verify WAIT Then BUY Path

- Previous: `P11.1`; next: `P11.3`.
- Authoritative scope: Create → Initial Analysis → WAIT → WAIT Update → BUY →
  Position Update → CLOSE, including three real Gemini requests.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant changed files: none matching a committed full-path acceptance
  record.
- Repository evidence: Gate E and Gate F separately cover decision and WAIT
  behavior, but no committed end-to-end record proves this exact path,
  Position Update, CLOSE, and real Gemini together.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: add a dedicated committed acceptance record after recovery.

### P11.3 — Verify WAIT Then SKIP Path

- Previous: `P11.2`; next: `P11.4`.
- Authoritative scope: Create → Initial Analysis → WAIT → WAIT Update → SKIP.
- Authoritative acceptance criteria: no position; CLOSED_SKIPPED; history
  preserved; no further uploads.
- Mapped commits: `NONE`.
- Relevant changed files: no authoritative full-path acceptance artifact.
- Repository evidence: Gate E verifies WAIT and SKIP separately and Gate F
  verifies WAIT updates, but no committed exact path verifies the combined
  flow and final read-only state.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: add a dedicated committed combined-path verification.

### P11.4 — Verify Direct SKIP Path

- Previous: `P11.3`; next: `P11.5`.
- Authoritative scope: Create → Initial Analysis → SKIP.
- Authoritative acceptance criteria: no position; no close price; skip reason;
  session read-only.
- Mapped commits: `NONE`.
- Relevant changed files: no authoritative full-path acceptance artifact.
- Repository evidence: Gate E covers SKIP from an ANALYZED/WAITING decision
  perspective, but no committed direct Initial Analysis-to-SKIP path record.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: add a dedicated direct-SKIP acceptance record.

### P11.5 — Verify Multiple Updates

- Previous: `P11.4`; next: `P11.6`.
- Authoritative scope: multiple WAIT Updates across MORNING/MIDDAY/AFTERNOON,
  multiple Position Updates, chronology, preserved evidence, and no duplicate
  requests.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `14fd234`, `9bafd72`.
- Relevant changed files: Gate F WAIT flow verification and Position Update
  processor persistence tests.
- Repository evidence: Gate F records repeated WAIT cycles and chronological
  history; Position Update tests cover multiple persisted results. No committed
  single production-like verification joins all periods and both update types.
- Supplementary evidence: none.
- Status: **PARTIAL**.
- Remaining gap: commit one combined multiple-update acceptance record covering
  all periods, both analysis types, chronology, and duplicate protection.

### P11.6 — Verify Failure Recovery

- Previous: `P11.5`; next: `P12.1`.
- Authoritative scope: invalid image, Gemini error, malformed response,
  interrupted worker, manual retry, duplicate submit, and frontend refresh.
- Authoritative acceptance criteria: user data preserved; no duplicate
  lifecycle action; session remains usable.
- Mapped commits: `5087d9a`, `14fd234`, `974fb6f`.
- Relevant changed files: Gate D/F recovery documents, worker runtime/failure
  tests, retry tests, and frontend polling tests.
- Repository evidence: committed records cover malformed response, mocked
  Gemini failure, retry, duplicate submission, worker terminalization, and
  controlled polling. They do not prove invalid-image, interrupted-worker
  recovery as a full path, or browser refresh during processing in one
  production-like acceptance record.
- Supplementary evidence: none.
- Status: **PARTIAL**.
- Remaining gap: commit a complete failure matrix including interrupted worker,
  invalid image, refresh, and all three analysis types.

## Phase 12 mappings

### P12.1 — Add Rebuild Feature Switch

- Previous: `P11.6`; next: `P12.2`.
- Authoritative scope: environment-controlled safe-default routing, old system
  available during verification, and no data mixing.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant changed files: no rebuild feature-switch configuration or routing
  abstraction exists in committed history.
- Repository evidence: `08e1700` performs a direct frontend cutover and does not
  add an environment-controlled switch or safe default.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: create and verify the controlled switch before cleanup.

### P12.2 — Switch Frontend to V2 APIs

- Previous: `P12.1`; next: `P12.3`.
- Authoritative scope: move session creation/detail to rebuild flow; remove old
  lifecycle/EvidenceBatch/provider-router calls from the active frontend and
  preserve approved paths.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commit: `08e1700`.
- Relevant files: app session routes, header, middleware, cutover tests, and
  rebuild workspace route.
- Repository evidence: authenticated primary routes redirect to
  `/trade-workspace`; old session pages are no longer primary entry points, and
  cutover tests preserve access behavior. However, the repository still has old
  API clients and no full approved-path acceptance record.
- Supplementary evidence: none.
- Status: **PARTIAL**.
- Remaining gap: add controlled routing coverage and prove all approved paths
  use V2 APIs without old dependencies.

### P12.3 — Mark Old APIs Deprecated

- Previous: `P12.2`; next: `P12.4`.
- Authoritative scope: documentation warning, optional read-only historical
  access, no new old-workflow sessions, and preserved history.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant changed files: no deprecation documentation or API guard commit.
- Repository evidence: legacy routes remain active and no committed warning or
  old-session creation guard was added.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: explicitly deprecate/guard old business APIs while preserving
  historical reads.

### P12.4 — Remove Old Frontend Workflow

- Previous: `P12.3`; next: `P12.5a`.
- Authoritative scope: remove or disable old lifecycle controls, Partial Exit,
  old analysis types, batch controls, provider selection, and obsolete polling;
  keep rebuild workflow complete.
- Authoritative acceptance criteria: new workflow remains complete.
- Mapped commit: `08e1700`.
- Relevant files: old session route pages, primary navigation, cutover tests,
  and still-present legacy frontend feature modules.
- Repository evidence: the primary session routes redirect to the rebuild
  workspace, but legacy feature components and API clients remain in the
  repository, including Partial Exit, Closing Analysis, old analysis, and old
  trade-action surfaces. No focused removal/dependency test proves the entire
  old workflow is disabled.
- Supplementary evidence: none.
- Status: **PARTIAL**.
- Remaining gap: complete controlled disabling/removal and verify no obsolete
  frontend control or polling path remains reachable.

### P12.5a — remove Partial Exit routes

- Previous: `P12.4`; next: `P12.5b`.
- Authoritative scope: remove Partial Exit routes with focused dependency tests.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant files still present: `backend/app/services/actions/partial_exit.py`,
  `backend/app/api/routes/trade_actions.py`, and frontend Partial Exit modules.
- Repository evidence: the old `/api/actions/partial-exit` route and service
  remain committed; no removal commit or focused dependency test exists.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: remove the route/service/UI only after downstream dependencies
  are proven clear.

### P12.5b — remove old Closing Analysis requirement

- Previous: `P12.5a`; next: `P12.5c`.
- Authoritative scope: remove the old Closing Analysis requirement with focused
  dependency tests.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant files still present: legacy closing-analysis route, service, prompt,
  schemas, and frontend views.
- Repository evidence: `/closing-analysis` remains in the legacy route and the
  `closing-analysis-view` remains in frontend code; no removal commit exists.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: remove the requirement and verify CLOSE has no legacy analysis
  dependency.

### P12.5c — remove unused provider routing

- Previous: `P12.5b`; next: `P12.5d`.
- Authoritative scope: remove unused provider routing with focused dependency
  tests.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant files still present: `backend/app/ai/providers/router.py`, provider
  selection/capability modules, and DeepSeek provider.
- Repository evidence: provider routing remains in committed source and tests;
  no removal or dependency-proof commit exists. The rebuild bypass is not
  removal.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: remove unused routing only after all legacy dependencies are
  inventoried and tested.

### P12.5d — remove old transport registry

- Previous: `P12.5c`; next: `P12.5e`.
- Authoritative scope: remove old transport registry with focused dependency
  tests.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant files still present: legacy transport/normalizer modules and their
  registry references.
- Repository evidence: old provider transport modules remain committed and no
  removal/dependency test commit exists.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: remove the registry after proving no historical read or
  rebuild path requires it.

### P12.5e — remove unused canonical normalizers

- Previous: `P12.5d`; next: `P12.5f`.
- Authoritative scope: remove unused canonical normalizers with focused
  dependency tests.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant files still present: legacy canonical/context normalization modules
  and provider transport consumers.
- Repository evidence: normalizer code remains present and current tracked
  changes were explicitly excluded from credit; no removal commit exists.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: establish dependency inventory and remove only unused
  normalizers with focused tests.

### P12.5f — remove old lifecycle transitions

- Previous: `P12.5e`; next: `P12.5g`.
- Authoritative scope: remove old lifecycle transitions with focused dependency
  tests.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant files still present: `backend/app/lifecycle/transitions.py`,
  lifecycle service/restoration, old lifecycle routes, and lifecycle tests.
- Repository evidence: old transition authorities remain committed and are
  still imported by legacy routes; no removal commit exists.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: remove legacy transitions only after V2 ownership and
  historical-read dependencies are proven.

### P12.5g — remove obsolete evaluation flow

- Previous: `P12.5f`; next: `P12.6`.
- Authoritative scope: remove obsolete evaluation flow with focused dependency
  tests.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant files still present: evaluation routes, services, models, migrations,
  repository, and frontend evaluation dashboard.
- Repository evidence: evaluation APIs and UI remain present; no removal or
  dependency test commit exists.
- Supplementary evidence: none.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: determine historical retention requirements, then remove the
  obsolete business flow with focused dependency coverage.

### P12.6 — Final Production-Like Acceptance

- Previous: `P12.5g`; next: `NONE`.
- Authoritative scope: complete Initial Analysis → WAIT → WAIT Update → BUY →
  Position Update → CLOSE after cutover, verifying images, Gemini-only use,
  persistence, no old workflow, full history, and database/storage preservation.
- Authoritative acceptance criteria: `NOT SPECIFIED BY AUTHORITATIVE PLAN`.
- Mapped commits: `NONE`.
- Relevant changed files: no committed final production-like acceptance record.
- Repository evidence: Gate D–F cover bounded earlier flows with disposable
  environments and mocked Gemini; there is no final post-cutover clean-path
  acceptance record and no aggregate/timeline/cutover cleanup completion.
- Supplementary evidence: none; uncommitted/manual production behavior cannot
  receive credit.
- Status: **NOT IMPLEMENTED**.
- Remaining gap: run and commit final acceptance only after recovery, Phase 10,
  Phase 11 path coverage, and cleanup gates are complete.

## Mixed-commit and scope-discipline findings

- `84e01d0` implements the initial workspace and overlaps P10.2/P10.4, but it
  does not implement a P10 aggregate API or timeline.
- `08e1700` is a broad frontend cutover commit. It directly supports P12.2 and
  partially P12.4, but it is not a feature switch, deprecation, or backend
  cleanup implementation.
- `9034c0c` and `9716d87` extend the status action surfaces and are credited to
  P10.4 only where their diff directly supplies required controls.
- Gate D, E, and F documents are verification artifacts for P5–P8 behavior;
  none is a substitute for the exact Phase 11 path or final Phase 12 gate.
- The old application still contains separate timeline, lifecycle, provider,
  evaluation, Partial Exit, and Closing Analysis authorities. Rebuild bypass is
  not equivalent to cleanup.

## Later correction dependencies

- P10.4/P10.5 depend on the P5–P9 frontend and retry corrections already mapped
  in Stage 2B, but no later P10-specific correction commit exists.
- P12.2/P12.4 depend on `08e1700`; the commit disables primary legacy entry
  routes but leaves old components and APIs present.
- No committed correction completes P10.1, P10.3, P11, P12.1, P12.3, or
  P12.5a–P12.6.

## Uncommitted work excluded from credit

The pre-audit worktree contained these unchanged unrelated modifications:

- modified backend: `backend/app/ai/context_builder.py`,
  `backend/app/ai/providers/open_position_transport.py`,
  `backend/app/api/routes/trade_sessions.py`,
  `backend/app/api/schemas/trade_sessions.py`,
  `backend/app/models/evidence_batch.py`,
  `backend/app/services/evidence_batches.py`;
- modified tests: `backend/tests/ai/test_open_position_transport.py`,
  `backend/tests/api/test_open_position_batches.py`,
  `backend/tests/trade_workspace/test_gemini_pipeline_verification.py`,
  `backend/tests/trade_workspace/test_position_v2.py`,
  `backend/tests/trade_workspace/test_trade_closure_v2.py`;
- modified frontend: `frontend/src/features/analysis/request-analysis.tsx`,
  `frontend/src/lib/api/trade-sessions.ts`,
  `frontend/src/types/trade-session.ts`;
- untracked: `.agent-skills/`,
  `backend/migrations/versions/a1b2c3d4e5f6_p96p_open_position_current_price.py`,
  `docs/TradePilot AI PRD Amendment.md`, `docs/archive/`,
  `scripts/e2e_p9_smoke.py`, and `storage/local/`.

These remain `UNCOMMITTED — NOT ELIGIBLE FOR COMPLETION CREDIT`.

## Unresolved conflicts and uncertainties

- P10.4/P10.5 are credited from distributed workspace behavior rather than a
  dedicated Phase 10 commit; P10.1 and P10.3 remain absent, so the page is not
  a complete aggregate/history page.
- P11 requires production-like exact-path evidence and real Gemini where
  specified. Gate D–F are not Gate G and use mocked/disposable infrastructure.
- P12.2/P12.4 are partial because the main entry points are cut over while
  legacy APIs/components remain and no feature switch or full-path proof exists.
- P0.1 remains the historical PARTIAL from Stage 2A. It is not repaired here
  and does not change the official task ordering.

## Gate F assessment

**PASS as a committed bounded verification record, not as final Stage 2
readiness.** `WAIT_UPDATE_FLOW_VERIFICATION.md` records repeated WAIT Update
input, queue, worker, result, failure, retry, and frontend checks using
disposable infrastructure and mocked Gemini. Its evidence is coupled to the
temporary ANALYZING behavior that leaves P7.2 PARTIAL, so Gate F does not clear
the recovery sequence.

## Gate G assessment

**NOT IMPLEMENTED / no committed Gate G record found.** No committed exact-path
verification covers the full Phase 11 suite or final post-cutover clean path
with the required real Gemini and persistence evidence.

## Exact recovery sequence after Stage 2

1. `P5.6a` — close the missing committed browser-acceptance evidence for the
   complete Initial Analysis flow.
2. `P7.2a` — align WAIT Update submission to the authoritative `/wait-updates`
   stable `WAITING` lifecycle, then update its coupled worker, response, tests,
   and polling evidence.
3. `P8.2a` — align Position Update submission to the authoritative
   `/position-updates` stable `OPEN_POSITION` lifecycle, then update coupled
   worker/response/test evidence without implementing unrelated scope.
4. Resume the normal official sequence at `P10.1` — Create Session Detail
   Aggregate API.

P0.1 remains a historical baseline-audit PARTIAL and is not actionable without
   rewriting the already-established checkpoint history; it is explicitly not
  skipped or reclassified by this mapping.

## Exact first recovery task

`P5.6a — close the missing committed browser-acceptance evidence for the complete Initial Analysis flow`.

## Exact first official task after recovery

`P10.1 — Create Session Detail Aggregate API`.

## Stage 2 completion conclusion

Stage 2 mapping is complete for P0.1–P12.6. The audit does not authorize normal
implementation to resume yet: the exact recovery sequence above must be handled
first, and the resulting evidence must be committed before beginning P10.1.

## Ledger-control confirmations

- Only P10.1–P12.6 executable task status/commit fields and the recovery pointer
  are intended for the companion ledger update.
- P12.5 remains a non-executable umbrella.
- P0.1–P9.3 are untouched by this audit.
- Current active official task remains `NONE`.
