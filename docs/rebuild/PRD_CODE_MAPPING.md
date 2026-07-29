# PRD-to-Code Mapping

## 1. Purpose

This document maps the approved TradePilot AI product requirements to existing repository evidence, reuse decisions, replacement or new ownership needs, migration impact, frontend impact, and focused requirement-level tests. It is a mapping artifact only; it does not define the rebuild architecture, module boundaries, APIs, schemas, or implementation steps.

## 2. Scope and Authorities

The product authority is `docs/PRD.md`; the approved implementation sequence is the supplied TradePilot AI Rebuild Detailed Task Plan. This mapping is constrained to the 13 requested product areas and the approved flow: create session, initial evidence, Initial Analysis, user BUY/WAIT/SKIP, WAIT Updates, Position Updates, and user CLOSE. Supporting evidence includes `docs/rebuild/EXISTING_ASSET_INVENTORY.md` and `docs/rebuild/OLD_WORKFLOW_COMPONENTS.md`. Existing unfinished P9 files remain untouched.

## 3. Mapping Method

Each area starts from approved behavior, identifies current repository evidence, states whether the evidence directly supports or conflicts with the requirement, and records the minimum ownership/change category without selecting module boundaries. Migration and frontend notes describe impact only. Focused tests are requirement-level checks; no application tests or Gemini calls are performed in P1.1.

## 4. Product Requirement Mapping

### 4.1 Create Session

PRD Requirement: Create one Trade Session for one ticker and one trading lifecycle, with private owner access.
Approved Behavior: A user creates a new session that begins in `DRAFT` and belongs to that user.
Existing Implementation: Trade-session creation route/service and owner-scoped repository.
Existing Locations: `backend/app/api/routes/trade_sessions.py` (`create_trade_session`), `backend/app/services/trade_session.py`, `backend/app/repositories/trade_session.py`, `backend/app/models/trade_session.py`, `frontend/src/features/sessions/create-session-form.tsx`.
Reuse Decision: ADAPT
Required Replacement or New Ownership: Adapt creation ownership and initial-state handling to the approved seven-status lifecycle; preserve one ticker/session identity without importing `READY_FOR_*`, `WATCHING`, or archive behavior.
Migration Impact: Existing sessions/status values remain readable; no existing rows are rewritten during mapping.
Frontend Impact: Adapt create form/list navigation to the approved `DRAFT` lifecycle and dedicated session page.
Focused Test Requirement: Session is created with `DRAFT` status, correct owner, one ticker, and no access across owners.
Old Workflow Dependencies to Avoid: `READY_FOR_INITIAL_ANALYSIS`, `READY_FOR_ANALYSIS`, `ARCHIVED`, generic lifecycle restoration.
Evidence: `TradeSessionRepository.list_for_user` and `get_by_id_for_user` scope by owner; `TradeSessionStatus` currently includes the expanded legacy set.

### 4.2 Initial Evidence Upload

PRD Requirement: User manually uploads the required initial orderbook, three-month chart, and six-month chart evidence.
Approved Behavior: Evidence is attached to the draft session; Initial Analysis cannot proceed without all three required types.
Existing Implementation: Multipart upload, evidence validation, local storage, and required-evidence mapping.
Existing Locations: `backend/app/api/routes/evidence.py`, `backend/app/services/evidence.py`, `backend/app/evidence/validation.py`, `backend/app/storage/local.py`, `frontend/src/features/evidence/evidence-upload-form.tsx`.
Reuse Decision: ADAPT
Required Replacement or New Ownership: Retain byte/file validation and private storage mechanics; replace batch/type gating that depends on legacy analysis types.
Migration Impact: Existing evidence files and `EvidenceBatch`/`Evidence` rows remain available; no storage records are moved by this task.
Frontend Impact: Adapt upload UI to show exactly the three initial requirements and draft ownership state.
Focused Test Requirement: Initial Analysis readiness fails when any required evidence type is missing and succeeds when all three are present.
Old Workflow Dependencies to Avoid: `WATCHING_UPDATE`, `OPEN_POSITION_UPDATE`, Partial Exit/Closing batch requirements, post-initial batch rules.
Evidence: `EvidenceService._REQUIRED_EVIDENCE` defines the three initial evidence types; `LocalFileStorage.store` uses user/session paths and SHA-256 metadata.

### 4.3 Initial Analysis

PRD Requirement: Generate the first longitudinal AI analysis from all required initial evidence and store it in the session history.
Approved Behavior: Use only `INITIAL_ANALYSIS`; Gemini may recommend BUY/WAIT/SKIP but cannot execute a decision.
Existing Implementation: Analysis job creation, prompt registry, provider router, Gemini adapter, schema validation, and initial-analysis partitioning.
Existing Locations: `backend/app/services/analysis_jobs.py`, `backend/app/jobs/processor.py`, `backend/app/ai/providers/gemini.py`, `backend/app/ai/providers/router.py`, `backend/app/ai/prompts/catalog.py`, `schemas/production/v1/initial_analysis_v2.schema.json`.
Reuse Decision: REPLACE
Required Replacement or New Ownership: New approved Initial Analysis ownership must replace legacy multi-type routing/validation while retaining only directly useful Gemini request and evidence-context mechanics.
Migration Impact: Existing analysis/job/provider rows remain historical; new processing must not create legacy analysis types or alter existing payloads.
Frontend Impact: Adapt request/progress/result presentation to one Initial Analysis and user decision controls, without fallback/repair workflow labels.
Focused Test Requirement: Initial Analysis requires all three evidence types, uses Gemini only, considers session history, stores a result, and cannot execute BUY/WAIT/SKIP itself.
Old Workflow Dependencies to Avoid: `WATCHING_UPDATE`, `OPEN_POSITION_UPDATE`, `PARTIAL_EXIT_REVIEW`, `CLOSING_ANALYSIS`, provider fallback, generic validation registry.
Evidence: `GeminiProvider` defaults to `gemini-3.1-flash-lite`; `ProviderRouter` iterates `provider_order`; prompt catalog registers five legacy/current types.

### 4.4 BUY Decision

PRD Requirement: After analysis, the user may choose BUY and open one position.
Approved Behavior: BUY is user-controlled and records entry price, quantity, entry timestamp, stop loss, and target; one session has one position.
Existing Implementation: Authenticated open-position action service and API, trade-state model, idempotency, and open-position UI.
Existing Locations: `backend/app/services/actions/open_position.py`, `backend/app/api/routes/trade_actions.py` (`open_position`), `backend/app/models/trade_state.py`, `frontend/src/features/trade-actions/open-position-modal.tsx`.
Reuse Decision: ADAPT
Required Replacement or New Ownership: Preserve user-confirmed fact recording and idempotency; align lifecycle/status guards to the approved states and prohibit AI/provider mutation of execution facts.
Migration Impact: Existing trade actions and state rows remain historical; no position facts are rewritten.
Frontend Impact: Keep a user-entered BUY form and display confirmed facts as authoritative; remove any interpretation that AI opened the position.
Focused Test Requirement: BUY creates exactly one owner-scoped position with user-supplied facts and cannot be executed by an analysis result.
Old Workflow Dependencies to Avoid: `INITIAL_ANALYZED`/`WATCHING` assumptions, Partial Exit state, automated action interpretation.
Evidence: `trade_actions.py` routes `open_position` through `OpenPositionService.confirm`; the response exposes trade-state facts and session status.

### 4.5 WAIT Decision

PRD Requirement: After analysis, the user may choose WAIT without opening a position.
Approved Behavior: WAIT is user-controlled, creates no position, and moves the session into the approved waiting path.
Existing Implementation: `PostInitialDecisionService.wait` records an action/event, sets `WATCHING`, and creates a `WATCHING_UPDATE` batch.
Existing Locations: `backend/app/services/actions/post_initial_decision.py`, `backend/app/api/routes/trade_actions.py` (`wait_decision`), `backend/app/services/evaluation_records.py`, frontend lifecycle/action components.
Reuse Decision: ADAPT
Required Replacement or New Ownership: Retain idempotent user-decision/event recording; replace the `WATCHING`/`WATCHING_UPDATE` transition with approved `WAITING` and `WAIT_UPDATE` ownership.
Migration Impact: Existing WAIT actions, events, watching sessions, and evaluation records remain readable.
Frontend Impact: Display WAIT as a user action and waiting state; do not expose provider or AI execution of the decision.
Focused Test Requirement: WAIT creates no position, records the user action once, and triggers no Gemini request.
Old Workflow Dependencies to Avoid: `WATCHING`, old watching batch state machine, AI-selected WAIT.
Evidence: `PostInitialDecisionService.wait` targets `TradeSessionStatus.WATCHING` and creates `AnalysisType.WATCHING_UPDATE`; `/api/actions/wait` is authenticated and idempotent.

### 4.6 SKIP Decision

PRD Requirement: After analysis, the user may choose SKIP and end the setup without a position.
Approved Behavior: SKIP is user-controlled, creates no position, and ends at `CLOSED_SKIPPED`.
Existing Implementation: Post-initial skip service/action/event and evaluation outcome completion.
Existing Locations: `backend/app/services/actions/post_initial_decision.py` (`skip`), `backend/app/api/routes/trade_actions.py` (`skip_decision`), `backend/app/models/enums.py`, `backend/app/services/evaluation_records.py`.
Reuse Decision: ADAPT
Required Replacement or New Ownership: Retain user confirmation, reason, idempotency, and `CLOSED_SKIPPED`; remove dependence on legacy source states and unrelated evaluation side effects.
Migration Impact: Existing skip actions/events/outcomes remain available; no historical session is changed.
Frontend Impact: Provide a user-confirmed SKIP action and terminal display without Partial Exit/Closing controls.
Focused Test Requirement: SKIP creates no position, records the reason, and ends as `CLOSED_SKIPPED`.
Old Workflow Dependencies to Avoid: `_DECISION_SOURCES` requiring `INITIAL_ANALYZED` or `WATCHING`; automated skip decisions.
Evidence: `PostInitialDecisionService.skip` targets `CLOSED_SKIPPED`; `skip_decision` calls it with authenticated owner and idempotency key.

### 4.7 WAIT Update

PRD Requirement: While waiting, the user may upload evidence and request repeated WAIT Updates.
Approved Behavior: Each `WAIT_UPDATE` compares current evidence with complete session history and may recommend BUY/WAIT/SKIP without executing decisions.
Existing Implementation: Watching-update prompts, transport normalizer, watching batches, analysis routes, worker processor, and frontend watching view.
Existing Locations: `backend/app/ai/providers/watching_transport.py`, `prompts/production/v1/watching_update.*`, `schemas/production/v1/watching_update.schema.json`, `frontend/src/features/analysis/watching-update-view.tsx`, `backend/app/services/evidence_batches.py`.
Reuse Decision: REPLACE
Required Replacement or New Ownership: New WAIT Update ownership must replace `WATCHING_UPDATE` naming, batch gates, transport schema, and legacy status assumptions while retaining longitudinal context requirements.
Migration Impact: Existing watching analyses/batches remain historical; new records must use only `WAIT_UPDATE`.
Frontend Impact: Replace watching-specific labels/actions with repeated WAIT Update presentation and user-controlled BUY/WAIT/SKIP controls.
Focused Test Requirement: WAIT Update requires waiting state/evidence, includes relevant history, creates no position, and does not execute a recommendation.
Old Workflow Dependencies to Avoid: `WATCHING`, generic provider fallback, generic schema registry, Closing/Partial Exit flows.
Evidence: `watching_transport.py`, watching prompt/schema files, and `AnalysisType.WATCHING_UPDATE` show the current implementation; `context_builder.py` supplies historical-context behavior.

### 4.8 Position Update

PRD Requirement: After BUY, the user may request repeated Position Updates for one open position.
Approved Behavior: Each `POSITION_UPDATE` uses current user-supplied evidence and history; Gemini may recommend but cannot change confirmed position facts or current price.
Existing Implementation: Open-position transport, evidence batches, current-price update route, open-position view, and modified P9 files.
Existing Locations: `backend/app/ai/providers/open_position_transport.py`, `backend/app/services/evidence_batches.py`, `backend/app/api/routes/trade_sessions.py`, `frontend/src/features/analysis/open-position-update-view.tsx`, `frontend/src/lib/api/trade-sessions.ts`.
Reuse Decision: REPLACE
Required Replacement or New Ownership: New Position Update ownership must replace `OPEN_POSITION_UPDATE` semantics and preserve strict separation between AI assessment and user-owned position facts.
Migration Impact: Existing open-position batches/analyses and unfinished P9 migration remain untouched and historical; no migration is applied here.
Frontend Impact: Adapt open-position evidence/current-price entry to approved Position Update and make confirmed entry, quantity, timestamp, stop, target, and current price authoritative.
Focused Test Requirement: Position Update cannot modify confirmed position facts, supports repeated updates, and cannot create a second position.
Old Workflow Dependencies to Avoid: modified P9 transport/current-price assumptions, Partial Exit, provider fallback, AI mutation of trade state.
Evidence: `update_open_position_batch_current_price` is an owner-scoped route; `open_position_transport.py` and related route/model files are existing unfinished P9 work and were not changed.

### 4.9 CLOSE

PRD Requirement: The user may close the one open position.
Approved Behavior: CLOSE is user-controlled, requires an open position, records exit facts, and ends at `CLOSED`; no Closing Analysis is required.
Existing Implementation: Full-exit action service/API and frontend full-exit modal, plus multiple close-status mappings.
Existing Locations: `backend/app/services/actions/full_exit.py`, `backend/app/api/routes/trade_actions.py`, `frontend/src/features/trade-actions/full-exit-modal.tsx`, `backend/app/models/trade_state.py`.
Reuse Decision: ADAPT
Required Replacement or New Ownership: Retain user-confirmed full-exit recording and calculations; narrow close status/guards to approved `CLOSED` and remove any required Closing Analysis trigger.
Migration Impact: Existing `CLOSED_TAKE_PROFIT`, `CLOSED_STOP_LOSS`, `CLOSED_MANUAL`, and historical exit rows remain readable.
Frontend Impact: Keep user-entered close facts/reason and terminal history; do not require AI approval or Closing Analysis.
Focused Test Requirement: CLOSE requires an open position, records user-entered exit facts, makes no Gemini request, and ends as `CLOSED`.
Old Workflow Dependencies to Avoid: Partial Exit prerequisite, multiple legacy terminal statuses, Closing Analysis requirement, automated close decisions.
Evidence: `FullExitService` is called by the trade-action route; `TradeSessionStatus` currently contains three specialized close statuses beyond `CLOSED`.

### 4.10 Complete Chronological History

PRD Requirement: One session page must show complete chronological evidence, analyses, decisions, position facts, updates, and close history.
Approved Behavior: Every new analysis considers relevant session history and every material action is traceable to its evidence/context.
Existing Implementation: Session events, evidence/analysis repositories, timeline API/UI, context summary, and history panels.
Existing Locations: `backend/app/models/session_event.py`, `backend/app/repositories/session_event.py`, `backend/app/api/routes/timeline.py`, `frontend/src/features/trade-session/trade-session-shell.tsx`, `frontend/src/features/analysis/history/analysis-history.tsx`.
Reuse Decision: ADAPT
Required Replacement or New Ownership: Preserve chronological persistence/query mechanics while filtering legacy event/type presentation and ensuring the approved flow is the authoritative history.
Migration Impact: Existing events, analyses, evidence, and historical state remain available; no event backfill is defined here.
Frontend Impact: Adapt timeline/history rendering to show the approved flow and distinguish user actions from Gemini recommendations.
Focused Test Requirement: History returns all session events in chronological order with related evidence/analysis references and owner isolation.
Old Workflow Dependencies to Avoid: Partial Exit/Closing-only event assumptions, same-ticker cross-session merging, provider routing metadata as decision authority.
Evidence: Session shell loads `getTimeline`, `listAnalyses`, and `getSession`; `SessionEventType` persists analysis, evidence, user decision, position, and exit events.

### 4.11 Gemini Integration

PRD Requirement: Use Gemini as the only AI provider with production model `gemini-3.1-flash-lite`.
Approved Behavior: Gemini analyzes supplied context and may recommend; it never executes BUY/WAIT/SKIP/CLOSE or mutates user-entered facts.
Existing Implementation: `GeminiProvider` and Google GenAI client wrapper, surrounded by generic provider routing/capability/repair layers.
Existing Locations: `backend/app/ai/providers/gemini.py`, `backend/app/ai/providers/base.py`, `backend/app/ai/providers/router.py`, `backend/app/ai/providers/selection.py`.
Reuse Decision: ADAPT
Required Replacement or New Ownership: Retain the direct Gemini SDK/error boundary; bypass provider-order/fallback and generic routing ownership.
Migration Impact: Existing provider request/response metadata remains historical; new records must identify Gemini and the approved model only.
Frontend Impact: Show analysis progress/results without exposing provider fallback or implying autonomous action.
Focused Test Requirement: Only Gemini is selectable, the production model is correct, recommendation output cannot mutate decisions/facts, and no fallback request occurs.
Old Workflow Dependencies to Avoid: `ProviderRouter`, `DeepSeekProvider`, `MOCK`/provider order, repair/fallback status semantics.
Evidence: `_GoogleGenAIModelClient` calls `google.genai`; `GeminiProvider` defaults to `gemini-3.1-flash-lite`; `ProviderRouter` supports ordered fallback.

### 4.12 Background Worker

PRD Requirement: Background processing must make AI job progress visible while preserving session history and ownership.
Approved Behavior: A worker processes approved analysis jobs durably; user decisions remain outside worker authority.
Existing Implementation: Heartbeat/polling runtime, leased PostgreSQL queue, `AnalysisJobConsumer`, and legacy `AnalysisProcessor`.
Existing Locations: `worker/app/runtime.py`, `worker/app/consumers/analysis_jobs.py`, `backend/app/jobs/queue.py`, `backend/app/jobs/processor.py`.
Reuse Decision: ADAPT
Required Replacement or New Ownership: Retain operational heartbeat/claim mechanics where suitable; replace processor/job semantics that depend on legacy types, generic validation, provider fallback, or lifecycle restoration.
Migration Impact: Existing queued/processing jobs and leases remain intact; no job migration or replay is performed here.
Frontend Impact: Preserve visible processing status while reducing it to approved job behavior and avoiding fallback/repair claims.
Focused Test Requirement: Worker claims one eligible job safely, processes approved analysis types, preserves ownership/history, and cannot execute user decisions.
Old Workflow Dependencies to Avoid: `restore_session_status`, legacy `AnalysisProcessor`, provider fallback, generic validation stages.
Evidence: `AnalysisJobConsumer.run_once` claims then processes a job; `run_worker` refreshes heartbeats and polls; `PostgreSQLJobQueue` uses leased row locking.

### 4.13 Session Page

PRD Requirement: Provide one dedicated workspace page for the complete lifecycle and current user-controlled actions.
Approved Behavior: The page presents session metadata, evidence, analysis, history, position facts, progress, and only actions valid for the approved status.
Existing Implementation: Next.js session route and large client shell importing legacy analysis, action, evidence, timeline, and evaluation components.
Existing Locations: `frontend/src/app/sessions/[sessionId]/page.tsx`, `frontend/src/features/trade-session/trade-session-shell.tsx`, `frontend/src/app/layout.tsx`.
Reuse Decision: REPLACE
Required Replacement or New Ownership: New session-page ownership must present the approved flow; only general layout/auth/presentation mechanics are candidates for reuse.
Migration Impact: Existing session URLs and historical data remain available during cutover; no route migration is defined here.
Frontend Impact: Substantial replacement: remove Partial Exit, Closing Analysis, legacy watching/open-position views, and provider fallback UI while retaining chronological workspace principles.
Focused Test Requirement: Page loads the owner’s session, renders complete history, exposes only status-valid user actions, and never presents AI as executing a decision.
Old Workflow Dependencies to Avoid: `PartialExitModal`, `ClosingAnalysisView`, legacy `WATCHING_UPDATE`/`OPEN_POSITION_UPDATE` views, generic lifecycle action lists.
Evidence: `TradeSessionShell` imports initial, watching, open-position, partial-exit, closing-analysis, timeline, evidence, and action components; the route renders that shell for `[sessionId]`.

## 5. Requirement Ownership Summary

The existing repository can supply evidence and partial mechanics for authenticated ownership, private evidence storage, user-confirmed trade facts, chronological persistence, Gemini SDK access, and durable worker operation. Approved Initial Analysis, WAIT Update, Position Update, and the session page require replacement ownership because their current implementations import legacy types, generic frameworks, or disallowed flows. No existing component is accepted as a complete rebuild implementation.

## 6. Existing Components Approved for Reuse

Only narrow infrastructure mechanics are candidates for reuse: owner-scoped repository predicates, authenticated request identity, local/private file-storage safety, user-confirmed action/idempotency patterns, chronological event persistence, the direct Google GenAI adapter boundary, and worker heartbeat/transactional claim mechanics. Each remains subject to the area-specific decisions above; this section does not authorize module design.

## 7. Existing Components Requiring Replacement or Bypass

Replace or bypass the legacy analysis-type/prompt/schema registries, provider router/fallback, generic validation framework, old lifecycle state machine, EvidenceBatch workflow as an authority, legacy watching/open-position transports, Partial Exit, Closing Analysis, and the current session shell. Preserve these components and their historical data until cutover gates are verified.

## 8. Migration Impact Summary

No migrations are designed or applied in P1.1. Existing tables, enum values, analysis/job/provider records, evidence batches, events, evaluations, and user-execution facts must remain available during transition. The main migration risks are legacy enum values, old analysis types, Partial Exit/Closing records, job leases, and references from historical payloads; later tasks must determine compatibility without rewriting history prematurely.

## 9. Frontend Impact Summary

The existing layout, authentication context, upload controls, user-confirmed BUY/WAIT/SKIP/CLOSE mechanics, polling mechanics, and timeline presentation are partial candidates. The session shell and workflow-specific analysis/action views require replacement or focused adaptation to remove Partial Exit, Closing Analysis, fallback/repair states, and legacy analysis names. The page must keep user-entered execution facts authoritative and show AI as advisory.

## 10. Focused Test Requirement Summary

- Create session: `DRAFT`, owner isolation, one ticker/session identity.
- Initial evidence: all three required evidence types gate Initial Analysis.
- Initial Analysis: longitudinal context, Gemini-only, advisory output, no decision execution.
- BUY: one user-owned position with immutable user-entered execution facts.
- WAIT: no position, user action recorded, no Gemini request for the decision.
- SKIP: no position, reason recorded, terminal `CLOSED_SKIPPED`.
- WAIT Update: repeated waiting analyses use history and cannot execute decisions.
- Position Update: repeated updates cannot alter confirmed position facts or create a second position.
- CLOSE: open position required, user facts recorded, no Closing Analysis or Gemini request required.
- History: complete chronological order, evidence/analysis/action traceability, owner isolation.
- Gemini: only `gemini-3.1-flash-lite`, no fallback, no autonomous mutations.
- Worker: durable claim/process behavior for approved analysis jobs without user-decision authority.
- Session page: complete history and only status-valid user-controlled actions.

## 11. Unresolved Mapping Questions

- Exact compatibility strategy for existing database enum values while introducing approved status/type names.
- Whether historical P9 jobs can remain claimable during cutover and how they are isolated from rebuild jobs.
- Which direct Gemini normalization and schema-validation mechanics can be retained without recreating generic registries.
- Retention and presentation requirements for historical Partial Exit, Closing Analysis, evaluation, and provider-fallback records.
- Exact frontend compatibility requirements for existing session URLs and historical sessions.
- How current-price input and other execution facts are protected from all AI processing paths.

## 12. P1.1 Conclusion

All 13 approved product areas are mapped to repository evidence, reuse decisions, replacement/new ownership needs, migration impact, frontend impact, focused tests, and legacy dependencies to avoid. The mapping confirms that only narrow infrastructure mechanics are partial reuse candidates; legacy workflow authorities must not control the rebuild. No module boundary, schema, API contract, migration, or implementation is defined here.
