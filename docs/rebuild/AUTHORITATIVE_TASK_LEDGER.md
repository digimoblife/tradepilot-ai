# TradePilot AI Authoritative Task Ledger

## Authority and use

- Product authority: `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
- Sequence authority: `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
- Historical-only source: `docs/TradePilot AI PRD Amendment.md`
- Stage 0 checkpoint: `fdb1563efa835e9eb3075ce385c7d0ea98dffc06`

Before issuing an implementation prompt, read the active entry below and confirm its ID, exact title, official scope, acceptance criteria, and next task. The plan is authoritative for the verbatim task body. A field absent from that task body is `NOT SPECIFIED BY AUTHORITATIVE PLAN`. Implementation status and commit must remain `NOT AUDITED` until an authorized Stage 2 mapping or execution-tracking task.

## Official task control list

### Phase 0 — Freeze and Protect the Existing System

### P0.1 — Create Rebuild Baseline
Previous task: NONE  
Next task: P0.2  
Official scope: verify current branch; verify current commit; verify tracked and untracked changes; preserve uncommitted P9 work safely; create a rebuild branch; create a baseline tag.  
Official acceptance criteria: current `main` remains unchanged; rebuild branch exists; baseline tag exists; no credential is committed; all untracked diagnostic files are preserved; current Docker volumes remain untouched.  
Implementation status: PARTIAL
Commit: 9e13160

### P0.2 — Record Existing Runtime Assets
Previous task: P0.1  
Next task: P0.3  
Official scope: Document technical assets that may be reused; inspect authentication, user isolation, file upload, evidence storage, Gemini SDK adapter, prompt loading, background worker, job polling, frontend layout, Docker Compose, gateway, PostgreSQL, migrations, and existing session page; create `docs/rebuild/EXISTING_ASSET_INVENTORY.md`.  
Official acceptance criteria: The document describes existing code only. It does not propose new product features.  
Implementation status: COMPLETED
Commit: e2e8db1

### P0.3 — Record Old Workflow Components
Previous task: P0.2  
Next task: P1.1  
Official scope: Identify existing components that belong to the old architecture; create `docs/rebuild/OLD_WORKFLOW_COMPONENTS.md`; classifications: REUSE, ADAPT, BYPASS, DEPRECATE, REMOVE_AFTER_CUTOVER.  
Official acceptance criteria: No code is deleted.  
Implementation status: COMPLETED
Commit: 880f587

### Phase 1 — Rebuild Mapping and Boundaries

### P1.1 — Create PRD-to-Code Mapping
Previous task: P0.3  
Next task: P1.2  
Official scope: Map every approved PRD requirement to existing or new code ownership; create `docs/rebuild/PRD_CODE_MAPPING.md`.  
Official acceptance criteria: Every approved PRD flow has an owner. No out-of-scope feature is mapped.  
Implementation status: COMPLETED
Commit: 9954a57

### P1.2 — Define the Rebuild Module Boundary
Previous task: P1.1  
Next task: P1.3  
Official scope: Define where new business code will live without mixing it with old lifecycle code; create `docs/rebuild/REBUILD_MODULE_BOUNDARY.md`.  
Official acceptance criteria: New business code does not depend on the old lifecycle engine. Shared infrastructure may still be reused.  
Implementation status: COMPLETED
Commit: 3a5e800

### P1.3 — Define Scope Guardrails
Previous task: P1.2  
Next task: P2.1  
Official scope: Create `docs/rebuild/SCOPE_GUARDRAILS.md` with the required rules in the Detailed Task Plan.  
Official acceptance criteria: The document is short and unambiguous.  
Implementation status: COMPLETED
Commit: 48a9a7d

### Phase 2 — Simplified Architecture

### P2.1 — Define the Simplified Backend Architecture
Previous task: P1.3  
Next task: P2.2  
Official scope: Document the minimal backend flow; create `docs/rebuild/SIMPLE_ARCHITECTURE.md`.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 15ea90f

### P2.2 — Define Session Status Rules
Previous task: P2.1  
Next task: P2.3  
Official scope: Define the approved status transitions only; create `docs/rebuild/SESSION_STATUS_RULES.md`.  
Official acceptance criteria: No other business transition exists.  
Implementation status: COMPLETED
Commit: 8781781

### P2.3 — Define Analysis Types and Input Contracts
Previous task: P2.2  
Next task: P2.4  
Official scope: Define only the approved AI analysis types; create `docs/rebuild/ANALYSIS_INPUT_CONTRACTS.md`.  
Official acceptance criteria: User-owned and Gemini-owned data are clearly separated.  
Implementation status: COMPLETED
Commit: 62a503a

### P2.4 — Define Compact AI Output Contracts
Previous task: P2.3  
Next task: P3.1  
Official scope: Define one compact response structure per approved analysis type; create the three `schemas/rebuild/v1` schema files named in the plan.  
Official acceptance criteria: Schemas are compatible with Gemini structured output. No request is sent yet.  
Implementation status: COMPLETED
Commit: d0dc706

### Phase 3 — Simplified Database Model

### P3.1 — Add Rebuild Trade Sessions Table
Previous task: P2.4  
Next task: P3.2  
Official scope: Create the new session table, `trade_sessions_v2`, with the required fields and requirements in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: d958695

### P3.2 — Add Analysis Requests Table
Previous task: P3.1  
Next task: P3.3  
Official scope: Create `analysis_requests_v2` with the required fields, analysis statuses, and requirements in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 108e1a5

### P3.3 — Add Evidence Uploads Table
Previous task: P3.2  
Next task: P3.4  
Official scope: Create `evidence_uploads_v2` with the required fields, evidence types, and requirements in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 45f8e9f

### P3.4 — Add Session Decisions Table
Previous task: P3.3  
Next task: P3.5  
Official scope: Create `session_decisions_v2` with the required fields, decisions, and requirements in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 154d25f

### P3.5 — Add Positions Table
Previous task: P3.4  
Next task: P3.6  
Official scope: Create `positions_v2` with the required fields, position statuses, and requirements in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: efafd17

### P3.6 — Add Trade Closures Table
Previous task: P3.5  
Next task: P3.7  
Official scope: Create `trade_closures_v2` with the required fields and requirements in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 6d6d022

### P3.7 — Verify Full Migration Chain
Previous task: P3.6  
Next task: P4.1  
Official scope: Verify all new tables on a disposable database; create `docs/rebuild/MIGRATION_VERIFICATION.md`.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 19af49c

### Phase 4 — Shared Gemini Analysis Pipeline

### P4.1 — Create Gemini-Only Adapter Boundary
Previous task: P3.7  
Next task: P4.2  
Official scope: Expose one explicit Gemini client for the rebuild with the requirements in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 99f7758

### P4.2 — Create Prompt Loader
Previous task: P4.1  
Next task: P4.3  
Official scope: Load exactly three approved prompts and meet the plan requirements.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 677c778

### P4.3 — Create Analysis Context Builder
Previous task: P4.2  
Next task: P4.4  
Official scope: Build the correct request context for each analysis type with the responsibilities in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 075f80c, 1c7d728, 0026a44

### P4.4 — Create Analysis Request Queue Service
Previous task: P4.3  
Next task: P4.5  
Official scope: Create exactly one analysis request with status `PENDING` in `analysis_requests_v2` as the durable database-backed queue source, transition session to `ANALYZING`, commit state, and return HTTP 202 without external brokers, in-process queues, or publishing to other transports.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: c1adacd, 75657c0, 59b75ed

### P4.5 — Create Worker Processing Flow
Previous task: P4.4  
Next task: P4.6  
Official scope: Poll `analysis_requests_v2` at configured worker interval, atomically claim one `PENDING` request using PostgreSQL locking, mark `PROCESSING`, call Gemini once, store responses, mark `COMPLETED` or `FAILED`, and transition session to approved status without legacy `analysis_jobs` delegation or external queue infrastructure.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: f8d93e3, 974fb6f, 6666cd3

### P4.6 — Create Compact Response Validation
Previous task: P4.5  
Next task: P5.1  
Official scope: Validate only fields required by the dashboard; do not add the listed components.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: e3a9276

### Phase 5 — Initial Analysis

### P5.1 — Create Session API
Previous task: P4.6  
Next task: P5.2  
Official scope: POST /api/v2/trade-sessions; GET /api/v2/trade-sessions; GET /api/v2/trade-sessions/{session_id}.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: c63e288

### P5.2 — Create Initial Evidence Upload API
Previous task: P5.1  
Next task: P5.3  
Official scope: Upload the three required evidence types.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: b6cfd3c, 7525782

### P5.3 — Create Initial Analysis Submission API
Previous task: P5.2  
Next task: P5.4  
Official scope: POST /api/v2/trade-sessions/{session_id}/initial-analysis; require all three evidence files; create one analysis request; set session to `ANALYZING`; queue one request; block duplicate active submission.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 18e0611, 75657c0

### P5.4 — Implement Initial Analysis Prompt
Previous task: P5.3  
Next task: P5.5  
Official scope: Required Output and Authority as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: bfd4538

### P5.5 — Persist and Complete Initial Analysis
Previous task: P5.4  
Next task: P5.6  
Official scope: Complete the success and failure behavior specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 1a1ecda, 265b63f, 62a4d00

### P5.6 — Build Initial Analysis Frontend
Previous task: P5.5  
Next task: P6.1  
Official scope: Build the UI specified in the Detailed Task Plan.  
Official acceptance criteria: The complete initial flow works through the browser.  
Implementation status: COMPLETED
Commit: test(rebuild): verify initial analysis browser flow

### Phase 6 — BUY, WAIT, and SKIP

### P6.1 — Add Decision Availability API
Previous task: P5.6  
Next task: P6.2  
Official scope: Expose valid actions based on session status using the rules in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: c379017

### P6.2 — Implement WAIT Decision
Previous task: P6.1  
Next task: P6.3  
Official scope: POST /api/v2/trade-sessions/{session_id}/decisions/wait with the behavior in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: b5675ea

### P6.3 — Implement SKIP Decision
Previous task: P6.2  
Next task: P6.4  
Official scope: POST /api/v2/trade-sessions/{session_id}/decisions/skip with the input and behavior in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 03d2ceb, d05a1da

### P6.4 — Implement BUY Decision
Previous task: P6.3  
Next task: P6.5  
Official scope: POST /api/v2/trade-sessions/{session_id}/decisions/buy with the input and behavior in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 295fce0

### P6.5 — Build Decision UI
Previous task: P6.4  
Next task: P7.1  
Official scope: Build the UI and forms specified in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 4d25ae9, d73f5b6, 3e15868

### Phase 7 — WAIT Updates

### P7.1 — Create WAIT Update Input API
Previous task: P6.5  
Next task: P7.2  
Official scope: Required Input and Conditions as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: a879c03, 0934304

### P7.2 — Create WAIT Update Submission
Previous task: P7.1  
Next task: P7.3  
Official scope: POST /api/v2/trade-sessions/{session_id}/wait-updates with the behavior in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: dfed279, e331a60, 0cbe24c, 8d42a41, 587e9a7, 7205121, f6be8de

### P7.3 — Implement WAIT Update Prompt
Previous task: P7.2  
Next task: P7.4  
Official scope: Context and Required Output as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 138465e, 1c7d728

### P7.4 — Persist WAIT Update Results
Previous task: P7.3  
Next task: P7.5  
Official scope: Verify the requirements specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 85173c1, 2a4bce8, 0cbe24c, d6d1f12

### P7.5 — Build WAIT Update Frontend
Previous task: P7.4  
Next task: P8.1  
Official scope: Build the UI specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 1efc09f, 14fd234, 57f088e

### Phase 8 — Position Updates

### P8.1 — Create Position Update Input API
Previous task: P7.5  
Next task: P8.2  
Official scope: Required Input and Conditions as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 23c34c5

### P8.2 — Create Position Update Submission
Previous task: P8.1  
Next task: P8.3  
Official scope: POST /api/v2/trade-sessions/{session_id}/position-updates with the behavior in the plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 95fa494, e8a11ee, 150dd57

### P8.3 — Implement Position Update Prompt
Previous task: P8.2  
Next task: P8.4  
Official scope: Context, Required Output, and Authority Rule as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: b5aee29, 0026a44

### P8.4 — Persist Position Update Results
Previous task: P8.3  
Next task: P8.5  
Official scope: Verify the requirements specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: d6d1f12, 9bafd72

### P8.5 — Build Position Update Frontend
Previous task: P8.4  
Next task: P9.1  
Official scope: position summary; update form; timeline; current price; period; analysis sections; CLOSE button; no BUY/WAIT/SKIP buttons.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 0ceebc1, 9034c0c

### Phase 9 — CLOSE

### P9.1 — Create CLOSE API
Previous task: P8.5  
Next task: P9.2  
Official scope: POST /api/v2/trade-sessions/{session_id}/close with Required Input, Optional input, and Behavior as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 46d2adb

### P9.2 — Verify Close Calculations
Previous task: P9.1  
Next task: P9.3  
Official scope: Verify realized price difference, percentage result, quantity handling, decimal precision, timezone, no position overwrite, and one closure only.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: cf473df

### P9.3 — Build CLOSE Frontend
Previous task: P9.2  
Next task: P10.1  
Official scope: Build the UI specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 9716d87, 7c48348

### Phase 10 — Complete Session Page

### P10.1 — Create Session Detail Aggregate API
Previous task: P9.3  
Next task: P10.2  
Official scope: Response Sections and Requirements as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P10.2 — Build Session Header and Status Display
Previous task: P10.1  
Next task: P10.3  
Official scope: Display the items specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: PARTIAL
Commit: 84e01d0

### P10.3 — Build Chronological Timeline
Previous task: P10.2  
Next task: P10.4  
Official scope: Timeline Items and Requirements as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P10.4 — Build Status-Based Action Panel
Previous task: P10.3  
Next task: P10.5  
Official scope: Rules as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 84e01d0, 4d25ae9, 9034c0c, 9716d87

### P10.5 — Build Failure and Retry UI
Previous task: P10.4  
Next task: P11.1  
Official scope: Behavior as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: COMPLETED
Commit: 62a4d00, 2a4bce8, 9034c0c

### Phase 11 — End-to-End Verification

### P11.1 — Verify Direct BUY Path
Previous task: P10.5  
Next task: P11.2  
Official scope: Create → Initial Analysis → BUY → Position Update → CLOSE.  
Official acceptance criteria: files sent; responses stored; Indonesian output; user facts preserved; session closes.  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P11.2 — Verify WAIT Then BUY Path
Previous task: P11.1  
Next task: P11.3  
Official scope: Create → Initial Analysis → WAIT → WAIT Update → BUY → Position Update → CLOSE.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P11.3 — Verify WAIT Then SKIP Path
Previous task: P11.2  
Next task: P11.4  
Official scope: Create → Initial Analysis → WAIT → WAIT Update → SKIP.  
Official acceptance criteria: no position; status `CLOSED_SKIPPED`; history preserved; no further uploads.  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P11.4 — Verify Direct SKIP Path
Previous task: P11.3  
Next task: P11.5  
Official scope: Create → Initial Analysis → SKIP.  
Official acceptance criteria: no position; no close price; skip reason stored; session read-only.  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P11.5 — Verify Multiple Updates
Previous task: P11.4  
Next task: P11.6  
Official scope: Verify repeated update behavior and the listed scenarios.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: PARTIAL
Commit: 14fd234, 9bafd72

### P11.6 — Verify Failure Recovery
Previous task: P11.5  
Next task: P12.1  
Official scope: Cases and Verify requirements as specified in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: PARTIAL
Commit: 5087d9a, 14fd234, 974fb6f

### Phase 12 — Cutover and Cleanup

### P12.1 — Add Rebuild Feature Switch
Previous task: P11.6  
Next task: P12.2  
Official scope: Allow controlled routing to the new workflow with the plan requirements.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P12.2 — Switch Frontend to V2 APIs
Previous task: P12.1  
Next task: P12.3  
Official scope: Move session creation and session detail to the rebuild flow.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: PARTIAL
Commit: 08e1700

### P12.3 — Mark Old APIs Deprecated
Previous task: P12.2  
Next task: P12.4  
Official scope: Prevent new usage of old business endpoints with the plan behavior.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P12.4 — Remove Old Frontend Workflow
Previous task: P12.3  
Next task: P12.5a  
Official scope: Remove or Disable the items specified in the Detailed Task Plan.  
Official acceptance criteria: New workflow remains complete.  
Implementation status: PARTIAL
Commit: 08e1700

P12.5 is a non-executable umbrella heading. Its executable tasks follow.

### P12.5a — remove Partial Exit routes
Previous task: P12.4  
Next task: P12.5b  
Official scope: remove Partial Exit routes. Each removal must have focused dependency tests.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P12.5b — remove old Closing Analysis requirement
Previous task: P12.5a  
Next task: P12.5c  
Official scope: remove old Closing Analysis requirement. Each removal must have focused dependency tests.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P12.5c — remove unused provider routing
Previous task: P12.5b  
Next task: P12.5d  
Official scope: remove unused provider routing. Each removal must have focused dependency tests.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P12.5d — remove old transport registry
Previous task: P12.5c  
Next task: P12.5e  
Official scope: remove old transport registry. Each removal must have focused dependency tests.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P12.5e — remove unused canonical normalizers
Previous task: P12.5d  
Next task: P12.5f  
Official scope: remove unused canonical normalizers. Each removal must have focused dependency tests.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P12.5f — remove old lifecycle transitions
Previous task: P12.5e  
Next task: P12.5g  
Official scope: remove old lifecycle transitions. Each removal must have focused dependency tests.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P12.5g — remove obsolete evaluation flow
Previous task: P12.5f  
Next task: P12.6  
Official scope: remove obsolete evaluation flow. Each removal must have focused dependency tests.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

### P12.6 — Final Production-Like Acceptance
Previous task: P12.5g  
Next task: NONE  
Official scope: Run one complete clean session after cutover using the Required Path in the Detailed Task Plan.  
Official acceptance criteria: NOT SPECIFIED BY AUTHORITATIVE PLAN  
Implementation status: NOT IMPLEMENTED
Commit: NONE

## Current execution pointer

- Current active official task: NONE
- Next recovery stage after ledger completion: Resume P10.1 — Create Session Detail Aggregate API
