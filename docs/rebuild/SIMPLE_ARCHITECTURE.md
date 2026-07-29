# Simplified Backend Architecture

## 1. Purpose

Document the minimum backend architecture required for the approved TradePilot AI rebuild. This document defines component responsibility boundaries only; it does not implement code or define schemas, payloads, tables, prompts, or internal layers.

## 2. Scope and Authorities

The PRD and the TradePilot AI Rebuild Detailed Task Plan are the authorities. Supporting evidence is `docs/rebuild/EXISTING_ASSET_INVENTORY.md`, `docs/rebuild/OLD_WORKFLOW_COMPONENTS.md`, `docs/rebuild/PRD_CODE_MAPPING.md`, `docs/rebuild/REBUILD_MODULE_BOUNDARY.md`, and `docs/rebuild/SCOPE_GUARDRAILS.md`. The architecture supports only Create Session, Upload Initial Evidence, Initial Analysis, BUY, WAIT, SKIP, WAIT Update, Position Update, CLOSE, and complete session history.

## 3. Architecture Principles

- Only `INITIAL_ANALYSIS`, `WAIT_UPDATE`, and `POSITION_UPDATE` are supported.
- Only `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, and `CLOSED_SKIPPED` are supported.
- Gemini is the only provider, with production default `gemini-3.1-flash-lite`.
- BUY, WAIT, SKIP, and CLOSE are user actions. Gemini output is advisory and cannot mutate user-owned facts.
- One session has at most one position.
- Analysis failures belong to the analysis request and do not create a permanent extra session business state.
- The architecture has no provider router, fallback, generic workflow engine, generic lifecycle platform, generic schema registry, generic validation framework, Partial Exit, or Closing Analysis requirement.
- Existing infrastructure may be reused only without importing old workflow authority.

## 4. High-Level Backend Flow

```text
Frontend
→ Rebuild API
→ Rebuild Services
→ PostgreSQL / File Storage
→ Analysis Queue
→ Worker
→ Gemini
→ PostgreSQL
→ Frontend
```

For an analysis request, the high-level flow is:

```text
API
→ persist user input
→ queue analysis request
→ worker loads database context and evidence files
→ Gemini request
→ persist raw and processed response
→ expose result to frontend
```

Non-AI actions are user initiated: BUY, WAIT, SKIP, and CLOSE persist user-owned facts, update approved session state, and do not automatically call Gemini.

## 5. API Layer

Purpose: Expose the rebuild business boundary under `/api/v2/trade-sessions`.

Owns: Authentication handoff, request presence/basic-format checks, session ownership enforcement, delegation to approved rebuild services, and result exposure.

Inputs: Authenticated user context and user requests for approved session, evidence, decision, position, close, history, and analysis operations.

Outputs: Authenticated rebuild responses and analysis-request/result visibility; detailed endpoint contracts are deferred.

Allowed Dependencies: Authentication, user identity, ownership primitives, rebuild services, basic logging, and PostgreSQL/file-storage mechanics through approved services.

Prohibited Dependencies: Old lifecycle engine, old workflow routes as delegation targets, provider routing, automated decisions, and legacy status/type authorities.

User-Owned Data Handled: Session input, evidence metadata, decisions, execution facts, notes, and ownership context.

Gemini-Owned Data Handled: None; the API accepts or exposes advisory analysis but does not assign decisions or execution facts.

Repository Evidence: Existing routes under `backend/app/api/routes/` authenticate and scope owners; `REBUILD_MODULE_BOUNDARY.md` defines `/api/v2/trade-sessions` as the separate rebuild prefix.

## 6. Session Service

Purpose: Own the complete-session business state for the approved lifecycle.

Owns: Session creation, approved status changes, status eligibility, ownership coordination, one-session/one-ticker identity, and complete-session state.

Inputs: User session creation and user actions, current session state, and authorized compatibility context when explicitly required.

Outputs: Approved session state and history association; exact response shapes are deferred.

Allowed Dependencies: Ownership primitives, PostgreSQL connection mechanics, evidence service, decision service, position service, close service, and analysis request service.

Prohibited Dependencies: `backend/app/lifecycle/` as business authority, generic state-machine frameworks, old statuses, EvidenceBatch state machine, and AI decisions.

User-Owned Data Handled: Ticker/session identity, user notes, lifecycle decisions, and ownership.

Gemini-Owned Data Handled: None.

Repository Evidence: `backend/app/services/trade_session.py` and `backend/app/repositories/trade_session.py` provide existing session/owner behavior; P0.3 records the old lifecycle service as workflow-coupled.

## 7. Evidence Service

Purpose: Own evidence metadata and private evidence handling for rebuild sessions.

Owns: Evidence metadata, file references, ownership, required initial evidence checks, and immutability after submission where required.

Inputs: User-uploaded orderbook, three-month chart, six-month chart, later WAIT/Position Update evidence, and user notes where approved.

Outputs: Ownership-safe evidence references and availability for analysis context.

Allowed Dependencies: File storage mechanics, ownership checks, PostgreSQL connection mechanics, and basic upload validation.

Prohibited Dependencies: EvidenceBatch state machine as rebuild authority, legacy analysis-type gating, Partial Exit/Closing rules, and AI mutation of evidence metadata.

User-Owned Data Handled: Uploaded files, filenames, timestamps, captions, evidence type, and ownership.

Gemini-Owned Data Handled: None; Gemini reads supplied evidence but does not own the files or metadata.

Repository Evidence: `backend/app/storage/local.py` provides safe user/session file references; `backend/app/services/evidence.py` owns current evidence lifecycle but is classified as legacy-coupled in P0.2/P1.1.

## 8. Decision Service

Purpose: Persist explicit user decisions before or after analysis.

Owns: BUY, WAIT, and SKIP decisions, idempotent user action recording, repeated WAIT decisions, and eligibility checks.

Inputs: Explicit authenticated user action, session state, and user-provided notes/reasons.

Outputs: Persisted user decision and approved session-state update.

Allowed Dependencies: Session service, ownership, PostgreSQL connection mechanics, and chronological history persistence.

Prohibited Dependencies: Gemini execution, automated decisions, old post-initial lifecycle authority, Partial Exit, Closing Analysis, and generic workflow engines.

User-Owned Data Handled: BUY/WAIT/SKIP, decision time, notes, reasons, and decision ownership.

Gemini-Owned Data Handled: Recommendations are read-only inputs to the user; they are never persisted as user decisions by Gemini.

Repository Evidence: `backend/app/services/actions/post_initial_decision.py` and `/api/actions/wait`/`skip` show explicit user actions, but currently depend on legacy `WATCHING`/`INITIAL_ANALYZED` states and therefore are not rebuild authorities.

## 9. Position Service

Purpose: Own creation and state of exactly one open position after confirmed BUY.

Owns: Position creation, user-confirmed entry price, entry timestamp, quantity, stop loss, target price, current price ownership, open/closed position state, and prevention of duplicate positions.

Inputs: Explicit user BUY and user-entered/confirmed position facts.

Outputs: One user-owned position and its approved session association.

Allowed Dependencies: Session service, decision service, ownership, PostgreSQL connection mechanics, and chronological history.

Prohibited Dependencies: Gemini mutation, Partial Exit, automated position creation, multiple-position behavior, and old `PARTIALLY_CLOSED` lifecycle authority.

User-Owned Data Handled: Entry price, entry timestamp, quantity, stop loss, target price, current price, and position status.

Gemini-Owned Data Handled: Position observations and recommendations only; no confirmed position facts.

Repository Evidence: Existing `OpenPositionService` and `TradeState` show user-confirmed position mechanics; P0.3 identifies the current open-position transport and Partial Exit paths as old/P9-coupled.

## 10. Close Service

Purpose: Own manual closure of one open position.

Owns: CLOSE eligibility, user-provided close facts, close reason, realized-result responsibility, and transition to `CLOSED`.

Inputs: Explicit authenticated user CLOSE and close price, timestamp, reason, and notes.

Outputs: Closed user-owned position and `CLOSED` session state.

Allowed Dependencies: Session service, position service, ownership, PostgreSQL connection mechanics, and history persistence.

Prohibited Dependencies: Gemini approval, Closing Analysis requirement, Partial Exit prerequisite, automated close decisions, and legacy specialized terminal statuses as new authority.

User-Owned Data Handled: Close price, close timestamp, close reason, notes, and closure decision.

Gemini-Owned Data Handled: None; Gemini is not required for CLOSE.

Repository Evidence: Existing `FullExitService` provides a user-action reference; P0.3 records Closing Analysis and specialized close states as old workflow dependencies.

## 11. Analysis Request Service

Purpose: Own the lifecycle of one approved analysis request before and after worker processing.

Owns: Request creation, approved type eligibility, duplicate active-request prevention, persistence before queueing, request status, session-context association, evidence association, and failure storage.

Inputs: Authenticated user request, approved analysis type, session context, and evidence references.

Outputs: Queued/processing/completed/failed request visibility and association to raw/processed analysis results.

Allowed Dependencies: Session service, evidence service, PostgreSQL connection mechanics, queue mechanics, and Gemini adapter boundary.

Prohibited Dependencies: Legacy analysis types, generic schema registry as authority, generic validation framework, provider router/fallback, and automatic user decisions.

User-Owned Data Handled: Requesting user, session/evidence association, request intent, and explicit retry intent where later approved.

Gemini-Owned Data Handled: Raw and processed advisory analysis response, observations, probabilities, risks, plans, and conclusions.

Repository Evidence: Existing `backend/app/jobs/queue.py`, `backend/app/models/analysis_job.py`, and `backend/app/services/analysis_jobs.py` show queue/request mechanics; P1.1 requires replacement of legacy analysis ownership.

## 12. Gemini Adapter

Purpose: Provide one explicit rebuild-facing boundary to Gemini.

Owns: Gemini-only request execution, configured model use with production default `gemini-3.1-flash-lite`, text/image input support, structured JSON output handling, and Gemini-specific errors.

Inputs: Approved analysis context, text, evidence images, and one approved analysis request.

Outputs: Raw Gemini response and processed advisory response for persistence; no user decision or position mutation.

Allowed Dependencies: Google GenAI SDK mechanics, file-reference reading through approved storage, basic logging, and analysis request service.

Prohibited Dependencies: Provider router, fallback, DeepSeek/other providers, generic multi-provider abstraction as business authority, and old transport/canonical dual pipelines.

User-Owned Data Handled: User facts are read as context and remain authoritative; the adapter does not write them.

Gemini-Owned Data Handled: Analysis summaries, observations, probabilities, risks, recommendations, plans, and conclusions.

Repository Evidence: `backend/app/ai/providers/gemini.py` contains the direct Google GenAI wrapper and production model default; `backend/app/ai/providers/router.py` is explicitly excluded by P0.3/P1.3.

## 13. Background Worker

Purpose: Process one pending approved analysis request at a time without owning user decisions.

Owns: Claiming one pending request, marking processing, loading approved database context/evidence files, calling Gemini once, minimally parsing/validating, persisting raw/processed output, and marking completed/failed.

Inputs: One pending analysis request and its approved session/evidence context.

Outputs: Completed or failed analysis request with preserved raw/sanitized failure information.

Allowed Dependencies: Queue mechanics, PostgreSQL connection mechanics, file storage, analysis request service, Gemini adapter, worker runtime, logging, and basic observability.

Prohibited Dependencies: Retry/fallback frameworks, old lifecycle restoration, generic validation authority, provider routing, and decision/position mutation.

User-Owned Data Handled: Context is read; user-owned facts remain unchanged on success or failure.

Gemini-Owned Data Handled: Raw/processed advisory response and request failure information.

Repository Evidence: `worker/app/runtime.py` and `worker/app/consumers/analysis_jobs.py` provide operational polling/claiming references; P0.3 classifies the existing processor path as legacy-coupled.

## 14. File Storage

Purpose: Preserve and provide ownership-safe references to evidence files.

Owns: Evidence file storage, reads, file references, preservation, and path safety.

Inputs: User-uploaded evidence bytes and ownership/session context.

Outputs: Durable file reference and readable evidence bytes for the analysis pipeline.

Allowed Dependencies: Filesystem/object-storage mechanics, basic logging, and evidence service.

Prohibited Dependencies: EvidenceBatch state machine, old workflow status decisions, and deletion of old evidence during rebuild.

User-Owned Data Handled: Evidence files and file metadata.

Gemini-Owned Data Handled: None; Gemini receives copies/reads of supplied evidence only.

Repository Evidence: `backend/app/storage/base.py` defines a storage contract and `backend/app/storage/local.py` implements ownership/session pathing and safe references; P0.2 marks this as infrastructure candidate.

## 15. PostgreSQL

Purpose: Persist rebuild-owned business records and durable analysis history.

Owns: Rebuild-owned session, evidence, decision, position, analysis-request/result, and history persistence at the database infrastructure boundary.

Inputs: Service-owned business records and worker analysis results.

Outputs: Durable records, ownership-scoped reads, and transaction boundaries.

Allowed Dependencies: PostgreSQL, SQLAlchemy connection/session mechanics, approved rebuild services, and queue mechanics.

Prohibited Dependencies: Old lifecycle tables as new business authority, implicit data mixing, and schema design introduced in this task.

User-Owned Data Handled: All persisted user/session/evidence/decision/position/history facts.

Gemini-Owned Data Handled: Raw/processed advisory analysis and request failures.

Repository Evidence: `backend/app/database/session.py` provides async connection/session mechanics; P1.2 states rebuild-owned tables remain separate and exact definitions belong to Phase 3.

## 16. Shared Infrastructure

Allowed supporting infrastructure is limited to authentication, user identity/ownership primitives, PostgreSQL connection mechanics, storage adapter mechanics, queue mechanics, worker runtime, migration tooling, Docker Compose runtime, gateway routing, logging, and basic observability. Shared infrastructure MUST NOT bring old lifecycle/status/type decisions into the rebuild.

Evidence: P0.2 identifies these areas as infrastructure candidates; P1.2 defines shared-infrastructure-only access and excludes old workflow authority.

## 17. Data and Authority Boundaries

User-owned facts are: BUY, WAIT, SKIP, CLOSE decisions; current price entered by the user; entry price; entry timestamp; quantity; stop loss; target price; close price; close timestamp; close reason; and user notes.

Gemini-owned output is: analysis summaries, observations, probabilities, risks, recommendations, trading plans, and conclusions.

Gemini output is advisory. It MUST NOT overwrite user-owned facts, create a position, change a position, close a position, replace current price, or alter position status.

## 18. Failure Handling

- Analysis request failures are stored on the analysis request.
- Raw or sanitized failure information is preserved.
- User input and evidence remain preserved.
- User-owned position facts remain unchanged on failure.
- No fallback provider is attempted.
- No duplicate analysis is created automatically.
- Retry is explicit and user-controlled where the PRD later permits it.

No generic failure framework is defined here.

## 19. Prohibited Architecture

The architecture explicitly excludes provider routers, provider fallback, multi-provider business abstraction, generic workflow engines, generic lifecycle platforms, generic state-machine frameworks, generic schema registries as business authority, canonical-versus-transport response pipelines, generic domain validation frameworks, evaluation platforms as runtime requirements, the EvidenceBatch state machine, Partial Exit, Closing Analysis requirements, automated trading decisions, unapproved statuses, and unapproved analysis types.

## 20. Unresolved Architecture Questions

- Exact rebuild-owned tables and columns, deferred to Phase 3.
- Exact queue persistence and worker isolation while old jobs remain present.
- Minimal response parsing/validation needed without introducing a generic framework.
- Exact compatibility reads for historical records without allowing old tables to control new behavior.
- Deployment wiring for the rebuild API prefix and worker process.

## 21. P2.1 Conclusion

The minimum architecture consists of the API layer, session service, evidence service, decision service, position service, close service, analysis request service, Gemini adapter, background worker, file storage, and PostgreSQL. It preserves user authority, isolates old workflow behavior, supports only the approved statuses and analysis types, and defines no additional service, engine, registry, platform, abstraction, schema, API payload, or implementation code.
