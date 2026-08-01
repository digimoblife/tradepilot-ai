# Stage 2A — Commit-to-Task Mapping for P0.1–P4.6

## Audit metadata

- Baseline commit: `fdb1563efa835e9eb3075ce385c7d0ea98dffc06`
- Audited HEAD before this audit: `7c48348b8e2dfd40098c38076c90870f8ab518e1`
- Branch: `main`
- Audit date: `2026-08-01`
- Audited task range: `P0.1` through `P4.6`, inclusive
- History range inspected for post-checkpoint changes: `fdb1563efa835e9eb3075ce385c7d0ea98dffc06..HEAD`

## Methodology

The Detailed Task Plan is the authoritative task sequence and body. The PRD is
the authoritative product definition, and the ledger is the task-control
record. Each status below compares the exact task scope and acceptance
criteria with committed repository artifacts, path-focused history, relevant
diffs, and focused source evidence. Commit messages are supporting evidence
only.

The locked baseline is a state boundary, not a replacement for history. The
P0.2–P4.3 implementation commits and the P3.7 verification document were
created before the baseline and are cited as committed baseline-state evidence.
Post-baseline commits were inspected separately and are credited only where
they directly complete or repair the same authoritative scope. Uncommitted
changes are never completion evidence.

## Summary

| Status | Count |
| --- | ---: |
| COMPLETED | 22 |
| PARTIAL | 1 |
| NOT IMPLEMENTED | 0 |
| NOT AUDITABLE | 0 |
| BLOCKED | 0 |

| Task | Status | Primary commit(s) |
| --- | --- | --- |
| P0.1 | PARTIAL | `9e13160` |
| P0.2 | COMPLETED | `e2e8db1` |
| P0.3 | COMPLETED | `880f587` |
| P1.1 | COMPLETED | `9954a57` |
| P1.2 | COMPLETED | `3a5e800` |
| P1.3 | COMPLETED | `48a9a7d` |
| P2.1 | COMPLETED | `15ea90f` |
| P2.2 | COMPLETED | `8781781` |
| P2.3 | COMPLETED | `62a503a` |
| P2.4 | COMPLETED | `d0dc706` |
| P3.1 | COMPLETED | `d958695` |
| P3.2 | COMPLETED | `108e1a5` |
| P3.3 | COMPLETED | `45f8e9f` |
| P3.4 | COMPLETED | `154d25f` |
| P3.5 | COMPLETED | `efafd17` |
| P3.6 | COMPLETED | `6d6d022` |
| P3.7 | COMPLETED | `19af49c` |
| P4.1 | COMPLETED | `99f7758` |
| P4.2 | COMPLETED | `677c778` |
| P4.3 | COMPLETED | `075f80c`, `1c7d728`, `0026a44` |
| P4.4 | COMPLETED | `c1adacd`, `75657c0`, `59b75ed` |
| P4.5 | COMPLETED | `f8d93e3`, `974fb6f`, `6666cd3` |
| P4.6 | COMPLETED | `e3a9276` |

## Task mappings

### P0.1 — Create Rebuild Baseline

- Previous task: `NONE`; next task: `P0.2`.
- Authoritative scope: verify branch, commit, tracked/untracked changes;
  preserve uncommitted P9 work; create a rebuild branch and baseline tag.
- Acceptance criteria: `main` unchanged; rebuild branch and baseline tag exist;
  no credentials committed; diagnostics preserved; Docker volumes untouched.
- Mapped commits: `9e13160` (`pre-simple-session-rebuild` tag).
- Relevant changed files: none credited as implementation; the tag points to
  the pre-rebuild checkpoint.
- Repository evidence: the required checkpoint `fdb1563` exists, and the
  `pre-simple-session-rebuild` tag exists. Repository history contains only
  `main` and its remote, with no rebuild branch.
- Status: **PARTIAL**.
- Remaining gap: no rebuild branch is proven by committed repository state;
  preservation of the then-current uncommitted work and untouched volumes is
  not auditable from the tag commit alone.

### P0.2 — Record Existing Runtime Assets

- Previous task: `P0.1`; next task: `P0.3`.
- Authoritative scope: inspect and document existing authentication, ownership,
  uploads, storage, Gemini, prompts, worker, polling, frontend, Compose,
  gateway, PostgreSQL, migrations, and session page.
- Acceptance criteria: `docs/rebuild/EXISTING_ASSET_INVENTORY.md` describes
  existing code only and proposes no new product features.
- Mapped commit: `e2e8db1`.
- Relevant changed file: `docs/rebuild/EXISTING_ASSET_INVENTORY.md`.
- Repository evidence: the inventory records component location, responsibility,
  reuse decision, dependency risk, old-workflow coupling, and recommendation;
  its content is an inventory of repository assets rather than feature design.
- Status: **COMPLETED**.
- Remaining gap: none identified against the authoritative scope.

### P0.3 — Record Old Workflow Components

- Previous task: `P0.2`; next task: `P1.1`.
- Authoritative scope: identify lifecycle, EvidenceBatch, old analysis,
  registries, normalizers, validation, evaluation, routing, Partial Exit,
  Closing Analysis, WAIT, and SKIP components; classify them.
- Acceptance criteria: no code is deleted.
- Mapped commit: `880f587`.
- Relevant changed file: `docs/rebuild/OLD_WORKFLOW_COMPONENTS.md`.
- Repository evidence: the document classifies legacy components with the
  required `REUSE`, `ADAPT`, `BYPASS`, `DEPRECATE`, and
  `REMOVE_AFTER_CUTOVER` vocabulary; the commit adds documentation only.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P1.1 — Create PRD-to-Code Mapping

- Previous task: `P0.3`; next task: `P1.2`.
- Authoritative scope: map every approved flow and requirement to code
  ownership, including session, evidence, all three analysis types, decisions,
  CLOSE, history, Gemini, worker, and session page.
- Acceptance criteria: every approved flow has an owner and no out-of-scope
  feature is mapped.
- Mapped commit: `9954a57`.
- Relevant changed file: `docs/rebuild/PRD_CODE_MAPPING.md`.
- Repository evidence: the mapping contains each required area, current
  implementation, reuse/replacement decision, migration and frontend impact,
  and focused test requirement; it explicitly excludes legacy and prohibited
  features.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P1.2 — Define the Rebuild Module Boundary

- Previous task: `P1.1`; next task: `P1.3`.
- Authoritative scope: define backend/frontend packages, table ownership, API
  prefix, old-code restrictions, shared infrastructure, and prohibited
  dependencies.
- Acceptance criteria: new business code does not depend on the old lifecycle
  engine; shared infrastructure may be reused.
- Mapped commit: `3a5e800`.
- Relevant changed file: `docs/rebuild/REBUILD_MODULE_BOUNDARY.md`.
- Repository evidence: the document names `backend/app/trade_workspace/`,
  `frontend/src/features/trade-workspace/`, `/api/v2/trade-sessions`, allowed
  shared infrastructure, and prohibited lifecycle/provider/registry
  dependencies.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P1.3 — Define Scope Guardrails

- Previous task: `P1.2`; next task: `P2.1`.
- Authoritative scope: document Gemini-only, no routing/fallback, no Partial
  Exit, no automation, no generic workflow/schema/lifecycle abstractions, and
  only approved statuses/types.
- Acceptance criteria: short and unambiguous.
- Mapped commit: `48a9a7d`.
- Relevant changed file: `docs/rebuild/SCOPE_GUARDRAILS.md`.
- Repository evidence: the document states each required prohibition and the
  exact approved provider, model, statuses, and analysis types.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P2.1 — Define the Simplified Backend Architecture

- Previous task: `P1.3`; next task: `P2.2`.
- Authoritative scope: document API, session/evidence/decision/position/close
  services, request service, Gemini adapter, worker, storage, PostgreSQL, and
  the persist → queue → worker → Gemini → persist flow.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `15ea90f`.
- Relevant changed file: `docs/rebuild/SIMPLE_ARCHITECTURE.md`.
- Repository evidence: the document defines all required components and flow,
  and excludes provider routing, fallback, generic state machines, transport
  compilers, and evaluation platforms.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P2.2 — Define Session Status Rules

- Previous task: `P2.1`; next task: `P2.3`.
- Authoritative scope: define only the seven approved statuses and ten approved
  transitions.
- Acceptance criteria: no other business transition exists.
- Mapped commit: `8781781`.
- Relevant changed file: `docs/rebuild/SESSION_STATUS_RULES.md`.
- Repository evidence: the document enumerates the seven statuses, transition
  matrix, prohibited transitions, user authority, and request-level failure
  handling without adding a permanent failure status.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P2.3 — Define Analysis Types and Input Contracts

- Previous task: `P2.2`; next task: `P2.4`.
- Authoritative scope: define `INITIAL_ANALYSIS`, `WAIT_UPDATE`, and
  `POSITION_UPDATE` inputs and distinguish user-owned from Gemini-owned data.
- Acceptance criteria: authority separation is clear.
- Mapped commit: `62a503a`.
- Relevant changed file: `docs/rebuild/ANALYSIS_INPUT_CONTRACTS.md`.
- Repository evidence: the document specifies inputs and eligibility for all
  three types and explicitly protects current price, position facts, decisions,
  and session state as user/application-owned.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P2.4 — Define Compact AI Output Contracts

- Previous task: `P2.3`; next task: `P3.1`.
- Authoritative scope: create one compact schema for each approved analysis
  type, with no external refs, dual schema pipeline, or execution facts.
- Acceptance criteria: Gemini-compatible structured output and no request sent.
- Mapped commit: `d0dc706`.
- Relevant changed files: the three `schemas/rebuild/v1/*.schema.json` files.
- Repository evidence: the commit creates exactly the three named schemas; they
  use self-contained JSON Schema and protect user-owned current price and
  execution facts. The request-execution commits occur later in history.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P3.1 — Add Rebuild Trade Sessions Table

- Previous task: `P2.4`; next task: `P3.2`.
- Authoritative scope: add `trade_sessions_v2` with owner, ticker, company,
  note, timestamps, approved status, indexes, and no old lifecycle dependency.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `d958695`.
- Relevant changed files: `trade_session.py`, migration
  `7f3a9c2d1b4e_p31_trade_sessions_v2.py`, and focused model tests.
- Repository evidence: the model/migration define the required fields and
  approved status constraint; tests cover create/read, ownership, status, and
  ordering.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P3.2 — Add Analysis Requests Table

- Previous task: `P3.1`; next task: `P3.3`.
- Authoritative scope: add `analysis_requests_v2`, required request/response
  fields, four statuses, current-price rules, multi-evidence association, and
  no evaluation record.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `108e1a5`.
- Relevant changed files: `analysis_request.py`, migration
  `8c4d2e6f1a3b_p32_analysis_requests_v2.py`, and focused tests.
- Repository evidence: the model/migration contain the required metadata,
  snapshots, responses, timestamps, error fields, statuses, and relationships;
  no evaluation record is added.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P3.3 — Add Evidence Uploads Table

- Previous task: `P3.2`; next task: `P3.4`.
- Authoritative scope: add immutable `evidence_uploads_v2` references with
  session/request ownership, three evidence types, metadata, and no batch state
  machine.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `45f8e9f`.
- Relevant changed files: `evidence_upload.py`, migration
  `9d5e7f1a3c2b_p33_evidence_uploads_v2.py`, and focused tests.
- Repository evidence: required file and ownership fields, evidence types,
  immutability behavior, and tests are committed.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P3.4 — Add Session Decisions Table

- Previous task: `P3.3`; next task: `P3.5`.
- Authoritative scope: persist user-owned BUY, WAIT, and SKIP decisions with
  repeated WAIT allowed, one BUY, and SKIP-before-BUY rules.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `154d25f`.
- Relevant changed files: `session_decision.py`, migration
  `a7b8c9d0e1f2_p34_session_decisions_v2.py`, and focused tests.
- Repository evidence: the model/migration and tests encode the decision
  vocabulary, ownership, and uniqueness/lifecycle rules; no Gemini decision
  writer is introduced.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P3.5 — Add Positions Table

- Previous task: `P3.4`; next task: `P3.6`.
- Authoritative scope: persist one user-confirmed position with OPEN/CLOSED
  status and required entry, quantity, risk, note, and timestamps.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `efafd17`.
- Relevant changed files: `position.py`, migration
  `b8c9d0e1f2a3_p35_positions_v2.py`, and focused tests.
- Repository evidence: the model/migration define the required position facts,
  one-position relationship, statuses, and user-owned behavior.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P3.6 — Add Trade Closures Table

- Previous task: `P3.5`; next task: `P3.7`.
- Authoritative scope: persist one manual closure per open position, without
  Gemini, and transition the session to CLOSED after persistence.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `6d6d022`.
- Relevant changed files: `trade_closure.py`, migration
  `c9d0e1f2a3b4_p36_trade_closures_v2.py`, and focused tests.
- Repository evidence: the model/migration define close facts and the required
  session/position relationships; focused tests cover closure integrity.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P3.7 — Verify Full Migration Chain

- Previous task: `P3.6`; next task: `P4.1`.
- Authoritative scope: verify upgrade from current head, zero-to-head creation,
  rollback, old-table preservation, and old-record readability on a disposable
  database; create the verification document.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `19af49c`.
- Relevant changed file: `docs/rebuild/MIGRATION_VERIFICATION.md`.
- Repository evidence: the committed report records disposable PostgreSQL
  verification, zero upgrade, rollback/re-upgrade, preserved historical tables,
  and all six V2 tables. No migration was run during this audit.
- Status: **COMPLETED**.
- Remaining gap: none identified in the committed task evidence.

### P4.1 — Create Gemini-Only Adapter Boundary

- Previous task: `P3.7`; next task: `P4.2`.
- Authoritative scope: one Gemini client, configured model, text/images,
  structured JSON, sanitized credential errors, no routing or fallback.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commits: `99f7758`; focused readiness test `bbd88b1`.
- Relevant changed files: `backend/app/trade_workspace/ai/gemini_adapter.py`,
  package exports, and adapter tests.
- Repository evidence: the adapter hardcodes provider identity to Gemini, defaults
  to `gemini-3.1-flash-lite`, sends text/image parts and JSON schema, calls once,
  and sanitizes errors. Tests use injected clients and do not make real requests.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P4.2 — Create Prompt Loader

- Previous task: `P4.1`; next task: `P4.3`.
- Authoritative scope: load exactly three versioned prompts with English
  instructions, Indonesian output, authority protection, concise output, and
  explicit image roles.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `677c778`.
- Relevant changed files: `prompt_loader.py`, the three
  `prompts/rebuild/*.md` files, and loader tests.
- Repository evidence: the loader exposes exactly three enum/file mappings and
  v1; each prompt states authority, language, compact schema-only output, and
  image roles.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P4.3 — Create Analysis Context Builder

- Previous task: `P4.2`; next task: `P4.4`.
- Authoritative scope: load owned session/evidence/history/position facts,
  include user current price, bound history, and never invent missing facts.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commits: `075f80c` (initial), `1c7d728` (WAIT context), `0026a44`
  (Position context).
- Relevant changed files: `backend/app/trade_workspace/ai/context_builder.py`
  and its focused context tests.
- Repository evidence: the builder validates ownership and request type,
  resolves required evidence, loads ordered completed analyses, includes
  position facts only for Position Update, and raises explicit missing-fact or
  ownership errors.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P4.4 — Create Analysis Request Queue Service

- Previous task: `P4.3`; next task: `P4.5`.
- Authoritative scope: validate ownership/lifecycle/evidence, reject duplicate
  active requests, create exactly one PENDING V2 request, assign evidence,
  transition to ANALYZING transactionally, commit, and return 202 without an
  external or in-process queue.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commits: `c1adacd` (service), `75657c0` (durability and submission
  corrections), `59b75ed` (transaction/lock correction).
- Relevant changed files: `analysis_request_queue.py`, submission services,
  route wiring, database session handling, and focused queue/API tests.
- Repository evidence: the service writes `analysis_requests_v2` as PENDING,
  links evidence, guards duplicate active requests, sets ANALYZING, and commits;
  the later fixes close transaction/advisory-lock gaps. No broker or legacy
  `analysis_jobs` delegation is used by the rebuild queue path.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P4.5 — Create Worker Processing Flow

- Previous task: `P4.4`; next task: `P4.6`.
- Authoritative scope: poll V2 requests, atomically claim one with PostgreSQL
  locking, mark PROCESSING, call Gemini once, persist raw/processed output,
  terminalize COMPLETED/FAILED, and update only approved session status.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commits: `f8d93e3` (processor), `974fb6f` (database claim/worker
  integration), `6666cd3` (setup-failure terminalization).
- Relevant changed files: rebuild processor, claim service, worker consumer and
  runtime, plus focused worker/processor tests.
- Repository evidence: claim code uses PostgreSQL `FOR UPDATE SKIP LOCKED`, the
  worker polls at configured interval and claims one request, processing calls
  the Gemini adapter once, and both setup and processing failures persist
  FAILED state. The flow does not delegate to legacy `analysis_jobs`.
- Status: **COMPLETED**.
- Remaining gap: none identified.

### P4.6 — Create Compact Response Validation

- Previous task: `P4.5`; next task: `P5.1`.
- Authoritative scope: validate only dashboard-required fields; critical missing
  fields fail the request, non-critical fields are retained with empty/warning
  display; do not add canonical/transport, domain, or evaluation frameworks.
- Acceptance criteria: not specified by the authoritative plan.
- Mapped commit: `e3a9276`.
- Relevant changed files: `response_validator.py`, processor integration, and
  focused validator/processor tests.
- Repository evidence: the validator has per-analysis critical field rules,
  returns warnings for non-critical gaps, and the processor persists failure or
  processed response. No separate canonical schema, transport schema, domain
  framework, or evaluation record is added.
- Status: **COMPLETED**.
- Remaining gap: none identified.

## Cross-task scope-discipline findings

- The pre-baseline task commits are generally one task per commit, matching the
  Detailed Task Plan sequence.
- `6913c97` changed authoritative documents and ledger text while documenting
  the database-backed queue. It is a cross-task documentation concern, but it
  is not used as primary implementation evidence for P4.4.
- P4.3 spans an initial builder and two focused extensions because the official
  task covers three analysis contexts.
- P4.4/P4.5 share queue, claim, worker, and submission-path corrections in
  `75657c0`, `974fb6f`, and `6666cd3`; these are credited only to the acceptance
  criteria they directly repair.
- Later product work after P4.6 is not used to establish P0–P4 completion.

## Tasks relying on later correction commits

- P4.4 relies on `75657c0` and `59b75ed` for durable transaction and lock
  behavior beyond the initial `c1adacd` implementation.
- P4.5 relies on `974fb6f` and `6666cd3` for PostgreSQL claim integration and
  guaranteed terminal failure handling beyond `f8d93e3`.
- P4.3 uses the later same-task context extensions `1c7d728` and `0026a44`.
- P4.6 is integrated by `e3a9276`; later worker corrections preserve its
  failure/validation path but do not add new response-validation scope.

## Uncommitted changes excluded from completion credit

The audit started with these changes and did not modify them:

- modified legacy/backend files: `backend/app/ai/context_builder.py`,
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
- modified frontend files: `frontend/src/features/analysis/request-analysis.tsx`,
  `frontend/src/lib/api/trade-sessions.ts`,
  `frontend/src/types/trade-session.ts`;
- untracked: `.agent-skills/`,
  `backend/migrations/versions/a1b2c3d4e5f6_p96p_open_position_current_price.py`,
  `docs/TradePilot AI PRD Amendment.md`, `docs/archive/`,
  `scripts/e2e_p9_smoke.py`, and `storage/local/`.

These are `UNCOMMITTED — NOT ELIGIBLE FOR COMPLETION CREDIT`.

## Unresolved conflicts or uncertainties

- P0.1 cannot be proven complete because the tag exists but no rebuild branch
  exists in the current repository history. The locked checkpoint itself is
  valid and present.
- The migration verification report is committed evidence of its claimed
  disposable-database checks; this audit intentionally did not re-run them.
- The audit did not inspect or update P5.1 or later.

## Recommended next Stage 2 mapping segment

`Stage 2B — Map committed implementation evidence for P5.1 through P9.3`.

## Ledger-control confirmations

- Only P0.1–P4.6 status and commit fields are intended for the companion ledger
  update.
- P5.1 and later are untouched.
- The current execution pointer remains `NONE`.
