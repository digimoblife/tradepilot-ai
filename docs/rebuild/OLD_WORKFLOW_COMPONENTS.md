# Old Workflow Components

## 1. Purpose

This document identifies existing components that belong to the old TradePilot AI workflow architecture. It records classification and coupling evidence only. It does not modify, remove, bypass, or redesign any component.

## 2. Scope and Constraints

Inspection was limited to lifecycle, evidence batches, analysis and transport handling, normalization, validation, evaluation, provider routing, Partial Exit, Closing Analysis, and user WAIT/SKIP flows. Existing unfinished P9 files, runtime data, old tables, and historical records remain untouched. Classifications are evaluated against the approved rebuild guardrails: Gemini-only, `gemini-3.1-flash-lite`, analysis types `INITIAL_ANALYSIS`, `WAIT_UPDATE`, `POSITION_UPDATE`, approved statuses `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, `CLOSED_SKIPPED`, and user-controlled BUY/WAIT/SKIP/CLOSE.

## 3. Classification Definitions

- `REUSE`: Directly supports the approved PRD without importing unnecessary old workflow behavior.
- `ADAPT`: Some mechanics may support the rebuild, but old assumptions must be changed later.
- `BYPASS`: May remain temporarily, but must not control or be required by the rebuild.
- `DEPRECATE`: No new rebuild flow should use it; historical or old-system behavior may still depend on it.
- `REMOVE_AFTER_CUTOVER`: Obsolete for the approved product and removable only after cutover gates pass.

## 4. Old Workflow Inventory

### 4.1 Lifecycle Enums

Component Name: Expanded `TradeSessionStatus`, `AnalysisType`, action, event, and provider enums
Location: `backend/app/models/enums.py`, `backend/migrations/versions/b7c9d1e2f3a4_p1_lifecycle_statuses.py`, `backend/migrations/versions/fc58b8bbeab7_analysis_models.py`
Current Responsibility: Defines lifecycle, analysis, action, event, provider, validation, and job-state vocabulary used throughout the existing system.
Key Entry Points: `TradeSessionStatus`, `AnalysisType`, `ActionType`, `SessionEventType`, `ProviderType`.
Primary Dependencies: SQLAlchemy enum columns, lifecycle services, routes, workers, schemas, tests, migrations.
Classification: ADAPT
Reason: The enum mechanics are central, but the values include `WATCHING`, `INITIAL_ANALYZED`, `PARTIALLY_CLOSED`, `CLOSED_*`, `WATCHING_UPDATE`, `OPEN_POSITION_UPDATE`, `PARTIAL_EXIT_REVIEW`, `CLOSING_ANALYSIS`, `DEEPSEEK`, and `MOCK`.
Approved PRD Conflict or Compatibility: Conflicts with the narrower approved status/type/provider sets; `USER_WAITED`, `SESSION_SKIPPED`, and `CLOSED_SKIPPED` show compatible user-controlled history.
Current Consumers: `backend/app/lifecycle/*`, services/actions, API routes, worker queue/processor, frontend feature components, schema and migration tests.
Cutover Dependency: Old database enum values and historical rows must remain readable until replacement behavior and cutover are verified.
Evidence: `backend/app/models/enums.py` contains the expanded values; migration `fc58b8bbeab7_analysis_models.py` persists the five legacy analysis types.

### 4.2 Lifecycle Transition Services

Component Name: Legacy transition map and `SessionLifecycleService`
Location: `backend/app/lifecycle/transitions.py`, `backend/app/lifecycle/service.py`, `backend/app/lifecycle/restoration.py`
Current Responsibility: Validates status transitions, maintains transient/stable status, locks owned sessions, and restores archived/processing state.
Key Entry Points: `_TRANSITION_MAP`, `is_transition_allowed`, `SessionLifecycleService.transition`, `restore_session_status`.
Primary Dependencies: `TradeSessionStatus`, `TradeSessionRepository`, SQLAlchemy row locks, queue processing.
Classification: ADAPT
Reason: It provides a useful transition-checking mechanism but encodes a broad lifecycle platform, transient `ARCHIVED`, multiple terminal close states, `WATCHING`, and `PARTIALLY_CLOSED`.
Approved PRD Conflict or Compatibility: The current map does not match the approved status set and permits old Partial Exit/Closing paths; user decisions are explicit service inputs.
Current Consumers: Trade-session routes, job queue/processor, action services, archive flow, lifecycle tests.
Cutover Dependency: Existing status values and `stable_status`/restoration data must remain interpretable while old jobs and records exist.
Evidence: `_TRANSITION_MAP` includes `READY_FOR_*`, `INITIAL_ANALYZED`, `WATCHING`, `PARTIALLY_CLOSED`, `CLOSED_TAKE_PROFIT`, `CLOSED_STOP_LOSS`, `CLOSED_MANUAL`, `CANCELLED`, and `ARCHIVED`.

### 4.3 EvidenceBatch State Machine

Component Name: `EvidenceBatchService` draft/ready/processing/frozen/failed workflow
Location: `backend/app/services/evidence_batches.py`, `backend/app/models/evidence_batch.py`, `backend/app/repositories/evidence_batch.py`, `backend/migrations/versions/c8d9e0f1a2b3_p2_evidence_batches.py`
Current Responsibility: Creates current drafts, assigns sequence numbers and monitoring slots, freezes immutable batches, validates batch mutations, and couples batches to analysis types.
Key Entry Points: `get_or_create_current_draft`, `update_monitoring_slot`, `update_open_position_current_price`, ready/freeze methods, `IMMUTABLE_BATCH_STATUSES`.
Primary Dependencies: `AnalysisType`, `EvidenceBatchStatus`, `TradeSessionStatus`, evidence service, route handlers.
Classification: BYPASS
Reason: The state machine is workflow-specific and includes monitoring slots, open-position current price, and legacy analysis-type requirements.
Approved PRD Conflict or Compatibility: Batch immutability and evidence grouping may be compatible, but `WATCHING_UPDATE`, `OPEN_POSITION_UPDATE`, `PARTIAL_EXIT_REVIEW`, and `CLOSING_ANALYSIS` are outside approved rebuild types.
Current Consumers: Evidence routes/service, trade-session routes, analysis job creation, frontend evidence and analysis components.
Cutover Dependency: Existing batch rows and evidence references must remain available for historical sessions until cutover.
Evidence: `EvidenceBatchService` defaults by `AnalysisType`, uses `DRAFT/READY/PROCESSING/FROZEN/FAILED`, and `c8d9e0f1a2b3_p2_evidence_batches.py` creates the legacy analysis enum values.

### 4.4 Old Analysis Types

Component Name: Legacy analysis-type model, routes, prompts, and schemas
Location: `backend/app/models/enums.py`, `backend/app/ai/prompts/catalog.py`, `schemas/production/v1/`, `backend/app/api/routes/trade_sessions.py`, `frontend/src/features/analysis/`
Current Responsibility: Represents and processes `INITIAL_ANALYSIS`, `WATCHING_UPDATE`, `OPEN_POSITION_UPDATE`, `PARTIAL_EXIT_REVIEW`, and `CLOSING_ANALYSIS`.
Key Entry Points: `AnalysisType`, `_ANALYSIS_TYPE_SCHEMA`, analysis request routes, `RequestAnalysis`, `ClosingAnalysisView`, `PartialExitReviewView`.
Primary Dependencies: Prompt files, transport schemas, validation registry, provider router, job processor, frontend views.
Classification: DEPRECATE
Reason: Four of the existing names and their views are old workflow concepts rather than the approved `WAIT_UPDATE` and `POSITION_UPDATE` names.
Approved PRD Conflict or Compatibility: `INITIAL_ANALYSIS` is compatible; `WATCHING_UPDATE`/`OPEN_POSITION_UPDATE` require semantic replacement, while Partial Exit and Closing Analysis are explicitly disallowed requirements.
Current Consumers: Backend analysis jobs/services/routes, prompt catalog, schemas, tests, frontend request/history/detail views.
Cutover Dependency: Historical analyses and database rows must remain readable; new flow must not create these legacy types after cutover.
Evidence: `backend/app/ai/prompts/catalog.py` registers all five types; `schemas/production/v1/common.schema.json` enumerates the four post-initial legacy types.

### 4.5 Transport Schema Registry

Component Name: Production schema manifest/registry and Gemini transport schemas
Location: `backend/app/schemas/manifest.py`, `backend/app/schemas/registry.py`, `schemas/production/v1/manifest.json`, `schemas/production/v1/*_gemini_transport_v1.schema.json`
Current Responsibility: Loads schema documents, maps analysis types to schemas, and supports transport-to-canonical validation.
Key Entry Points: `load_production_manifest`, `LocalSchemaRegistry`, manifest required-type mappings, transport schema files.
Primary Dependencies: JSON schema files, provider router, validation service, worker startup.
Classification: BYPASS
Reason: The registry is generic and its manifest includes old analysis types and provider transport variants.
Approved PRD Conflict or Compatibility: Conflicts with the prohibition on a generic schema registry for rebuild behavior and with the reduced analysis/provider set.
Current Consumers: `backend/app/ai/providers/selection.py`, worker startup/processor, JSON-schema validation, tests.
Cutover Dependency: Existing schemas must remain for historical response validation and old job replay decisions until cutover.
Evidence: `schemas/production/v1/manifest.json` and `backend/app/schemas/manifest.py` define production required analysis types; transport files include `watching_update_gemini_transport_v1` and `open_position_update_gemini_transport_v1`.

### 4.6 Canonical Normalizers

Component Name: Provider transport normalization and context canonicalization
Location: `backend/app/ai/providers/gemini.py`, `backend/app/ai/providers/watching_transport.py`, `backend/app/ai/providers/open_position_transport.py`, `backend/app/ai/context_builder.py`, `backend/app/ai/initial_analysis_partitioning.py`
Current Responsibility: Converts provider payloads into canonical payloads, normalizes chart/open-position fields, partitions initial-analysis responses, and rebuilds context.
Key Entry Points: `normalize_initial_analysis_transport_payload`, `normalize_watching_update_transport_payload`, `normalize_open_position_update_transport_payload`, context builder functions.
Primary Dependencies: Provider router, transport schemas, analysis types, evidence/context models, P9 open-position changes.
Classification: BYPASS
Reason: The normalization layer is tied to legacy transport shapes and analysis-specific fields; current files also overlap unfinished P9 work.
Approved PRD Conflict or Compatibility: Some data normalization may be useful, but no legacy transport or canonicalizer should control the rebuild without explicit type/status alignment.
Current Consumers: `ProviderRouter`, analysis processor, context builder, Gemini/provider tests, modified P9 files.
Cutover Dependency: Existing stored payloads and analysis records may depend on current normalization output.
Evidence: `backend/app/ai/providers/router.py` imports all three normalizers; `backend/app/ai/providers/open_position_transport.py` is an existing modified P9 file and was left untouched.

### 4.7 Domain Validation

Component Name: Unified/generic validation service and domain validators
Location: `backend/app/validation/service.py`, `backend/app/validation/registry.py`, `backend/app/validation/json_schema.py`, `backend/app/validation/{trade_state,partial_exit,closing,state_consistency}.py`
Current Responsibility: Runs parse, JSON-schema, domain, state-consistency, lifecycle, and narrative validation across analysis payloads and trade state.
Key Entry Points: `UnifiedValidationService.validate`, validation registry, `validate_partial_exit`, `validate_closing`, `JsonSchemaValidationService`.
Primary Dependencies: JSON schemas, `AnalysisType`, `TradeSessionStatus`, trade state, lifecycle rules, worker processor.
Classification: DEPRECATE
Reason: It is a generic validation framework spanning disallowed Partial Exit/Closing behavior and multiple legacy analysis types.
Approved PRD Conflict or Compatibility: Deterministic validation is useful, but the approved rebuild explicitly excludes a generic validation framework and automated AI decisions.
Current Consumers: Worker runtime, analysis processor, API/job services, validation tests, schemas.
Cutover Dependency: Keep it available for old jobs and historical records until replacement validation is proven and old processing is retired.
Evidence: `ValidationStage` includes `DOMAIN`, `STATE_CONSISTENCY`, `LIFECYCLE`, and `NARRATIVE`; `backend/app/validation/registry.py` registers legacy types and Partial Exit/Closing validators.

### 4.8 Evaluation Records and Flow

Component Name: P7 evaluation record service, backfill, API, and dashboard
Location: `backend/app/services/evaluation_records.py`, `backend/app/services/evaluation_backfill.py`, `backend/app/models/evaluation_record.py`, `backend/app/api/routes/evaluation.py`, `frontend/src/features/evaluation/`
Current Responsibility: Records predictions from accepted analyses, captures user decisions, completes outcomes on close/skip, supports backfill/export, and exposes evaluation UI.
Key Entry Points: `record_prediction_from_analysis`, `record_user_decision`, `record_outcome_on_closure`, evaluation API routes.
Primary Dependencies: Accepted `Analysis`, `TradeSessionStatus`, `TradeState`, action names, provider/model metadata, evaluation repository.
Classification: REMOVE_AFTER_CUTOVER
Reason: This is an old P7 evaluation flow, not a required rebuild workflow, but it owns historical records and outcome data.
Approved PRD Conflict or Compatibility: Capturing user-controlled BUY/WAIT/SKIP/CLOSE is compatible as historical data; prediction/evaluation dashboards and backfill are outside the rebuild scope.
Current Consumers: Post-initial decision service, analysis acceptance flow, evaluation API, frontend evaluation dashboard, backfill scripts/services.
Cutover Dependency: Evaluation tables, exports, and historical records must remain available until cutover gates and data-retention decisions are complete.
Evidence: `EvaluationRecordService` records `BUY`, `WAIT`, `SKIP`, and `SELL`, and `record_outcome_on_closure` distinguishes `CLOSED` and `CLOSED_SKIPPED`; module docstrings identify P7.

### 4.9 Provider Routing and Fallback

Component Name: Multi-provider router with repair and fallback
Location: `backend/app/ai/providers/router.py`, `backend/app/ai/providers/selection.py`, `backend/app/ai/providers/deepseek.py`, `backend/tests/ai/test_provider_fallback.py`, `worker/app/config.py`
Current Responsibility: Selects providers in configured order, performs capability checks and repair attempts, and falls back to later providers after failures.
Key Entry Points: `ProviderRouter.generate_validated`, `_validate_provider_order`, `AnalysisProviderConfig`, `provider_order`.
Primary Dependencies: `AIProvider`, Gemini/DeepSeek adapters, repair service, validation service, worker configuration.
Classification: DEPRECATE
Reason: The router directly implements multi-provider selection and fallback.
Approved PRD Conflict or Compatibility: Conflicts with Gemini-only, production `gemini-3.1-flash-lite`, and the explicit prohibition on a multi-provider router/fallback.
Current Consumers: Analysis processor, worker runtime, provider tests, provider request/response models.
Cutover Dependency: Existing provider metadata and historical provider responses must remain queryable; new jobs must not depend on fallback.
Evidence: `ProviderRouter` iterates `provider_order`; `ProviderType` includes `DEEPSEEK`; `test_provider_fallback.py` exercises `provider_order=["gemini", "deepseek"]`.

### 4.10 Partial Exit

Component Name: Partial Exit action, validation, state, and UI flow
Location: `backend/app/services/actions/partial_exit.py`, `backend/app/validation/partial_exit.py`, `backend/app/api/routes/trade_actions.py`, `frontend/src/features/trade-actions/partial-exit-modal.tsx`, `backend/migrations/versions/6730f9d6ee1d_trade_actions.py`
Current Responsibility: Validates partial quantities and realized P&L, records `PARTIAL_EXIT`, updates remaining position state, changes lifecycle to `PARTIALLY_CLOSED`, and rebuilds context.
Key Entry Points: `PartialExitActionService.confirm`, `validate_partial_exit`, `/api/actions/partial-exit`, `PartialExitModal`.
Primary Dependencies: `TradeState`, `TradeAction`, `SessionEvent`, `ContextRebuildService`, lifecycle statuses, calculations.
Classification: REMOVE_AFTER_CUTOVER
Reason: It implements a product capability explicitly excluded from the approved rebuild.
Approved PRD Conflict or Compatibility: Direct conflict: no Partial Exit and no `PARTIALLY_CLOSED` rebuild status.
Current Consumers: Trade action routes, session shell, trade-state/context calculations, tests, historical action rows.
Cutover Dependency: Existing partial-exit records and state must remain readable until all old sessions are safely cut over or retired.
Evidence: `PartialExitActionService` sets `TradeSessionStatus.PARTIALLY_CLOSED`; `partial_exit.py` defines quantity/P&L validation codes and the migration records `PARTIAL_EXIT` actions.

### 4.11 Closing Analysis

Component Name: Closing Analysis request, schema, service, and frontend view
Location: `backend/app/api/routes/trade_sessions.py`, `schemas/production/v1/closing_analysis.schema.json`, `prompts/production/v1/closing_analysis.*`, `frontend/src/features/analysis/closing-analysis-view.tsx`, `backend/tests/api/test_closing_analysis.py`
Current Responsibility: Requests and displays a post-trade Closing Analysis with final thesis, execution, risk, and AI evaluation sections.
Key Entry Points: `request_closing_analysis`, `ClosingAnalysisView`, closing prompt/schema files.
Primary Dependencies: Closed session state, analysis jobs, evaluation records, partial-exit history, provider routing.
Classification: DEPRECATE
Reason: It is an explicit old workflow requirement and not required by the approved rebuild.
Approved PRD Conflict or Compatibility: Direct conflict with “No Closing Analysis requirement”; it also references legacy event and analysis types.
Current Consumers: Trade-session API, analysis history, same-ticker history, frontend session shell, closing tests and schemas.
Cutover Dependency: Historical closing payloads and records must remain viewable until cutover confirms their replacement/retention path.
Evidence: The API exposes `POST /{session_id}/closing-analysis`; the production schema has `const: CLOSING_ANALYSIS` and final evaluation sections.

### 4.12 Old WAIT Implementation

Component Name: Post-initial WAIT decision and watching loop
Location: `backend/app/services/actions/post_initial_decision.py`, `backend/app/api/routes/trade_actions.py`, `frontend/src/features/analysis/helpers.ts`, `backend/app/services/evaluation_records.py`
Current Responsibility: Accepts a user WAIT decision, records `USER_WAITED`, changes the session to `WATCHING`, creates a `WATCHING_UPDATE` batch, and records the decision.
Key Entry Points: `PostInitialDecisionService.wait`, `/api/actions/wait`, `ActionType.USER_WAITED`, `SessionEventType.USER_WAITED`.
Primary Dependencies: `TradeSessionStatus.WATCHING`, `EvidenceBatchService`, evaluation records, idempotent trade actions.
Classification: ADAPT
Reason: User control and event recording are compatible, but the current loop uses legacy `WATCHING` status and `WATCHING_UPDATE` analysis/batch semantics.
Approved PRD Conflict or Compatibility: WAIT is approved and user-controlled; `WATCHING` and `WATCHING_UPDATE` are not approved rebuild names.
Current Consumers: Trade-action API, trade-session routes/UI, evidence batches, evaluation service, tests.
Cutover Dependency: Existing WAIT actions and watching sessions must remain readable; new WAIT behavior must not require the old watching state machine.
Evidence: `PostInitialDecisionService.wait` targets `TradeSessionStatus.WATCHING` and creates `AnalysisType.WATCHING_UPDATE`; its route is `/api/actions/wait`.

### 4.13 Old SKIP Implementation

Component Name: Post-initial SKIP decision and closure path
Location: `backend/app/services/actions/post_initial_decision.py`, `backend/app/api/routes/trade_actions.py`, `backend/app/models/enums.py`, `backend/app/services/evaluation_records.py`
Current Responsibility: Accepts a user SKIP decision, records `SESSION_SKIPPED`, sets `CLOSED_SKIPPED`, records a reason/event, and completes the evaluation outcome.
Key Entry Points: `PostInitialDecisionService.skip`, `/api/actions/skip`, `ActionType.SESSION_SKIPPED`, `record_outcome_on_closure`.
Primary Dependencies: `TradeSessionStatus.CLOSED_SKIPPED`, `TradeAction`, `SessionEvent`, evaluation records, idempotency.
Classification: ADAPT
Reason: User-controlled SKIP and `CLOSED_SKIPPED` are compatible, but this service also depends on legacy source states and evaluation side effects.
Approved PRD Conflict or Compatibility: The decision itself and target status are approved; `_DECISION_SOURCES` includes legacy `INITIAL_ANALYZED` and `WATCHING`.
Current Consumers: Trade-action API, session shell, evaluation service, same-ticker history, action/event repositories.
Cutover Dependency: Preserve historical skip actions/outcomes while replacing legacy source-state assumptions.
Evidence: `skip` targets `TradeSessionStatus.CLOSED_SKIPPED`; `_DECISION_SOURCES` is `{INITIAL_ANALYZED, WATCHING}` and `record_outcome_on_closure` marks skipped sessions complete.

## 5. Cross-Component Dependency Summary

The old workflow forms a connected chain: expanded enums feed lifecycle transitions; lifecycle and EvidenceBatch services gate evidence and analysis jobs; the prompt/schema registry and transport normalizers feed generic validation; the provider router adds repair/fallback; the worker executes the resulting job; frontend views expose legacy types and actions; evaluation records observe WAIT/SKIP/close outcomes. Partial Exit and Closing Analysis add additional state, schema, prompt, UI, and historical-record dependencies.

## 6. Components That Must Not Control the Rebuild

The multi-provider router/fallback, generic schema registry, generic validation framework, legacy analysis-type registry, legacy transport normalizers, Partial Exit flow, Closing Analysis flow, and the existing full lifecycle transition map must not control rebuild behavior. The old session shell and old worker processor are also workflow consumers, not rebuild authorities.

## 7. Components That Must Remain Until Cutover

Keep old lifecycle/status enums, EvidenceBatch tables, analysis/job/provider records, evaluation records, Partial Exit and Closing Analysis historical rows, and existing WAIT/SKIP action/event records available until the new workflow passes its cutover gates. This is a retention requirement for compatibility and history, not a recommendation to use these components in new rebuild flows.

## 8. Unknowns Requiring Later Inspection

- Exact database rows and foreign-key dependencies that must be retained during cutover.
- Whether legacy jobs can still be safely claimed while the rebuild is introduced.
- Complete provider-selection call graph and environment combinations beyond the inspected configuration.
- Exact payload compatibility requirements for historical analyses and transport-normalized records.
- Evaluation/export retention requirements and any external consumers of evaluation APIs.
- Whether old frontend routes must remain available for historical session viewing after cutover.

## 9. P0.3 Conclusion

The old workflow components have been identified and classified without changing or deleting them. The largest conflicts are the expanded lifecycle, legacy analysis types, generic validation/schema/provider layers, Partial Exit, and Closing Analysis. WAIT and SKIP remain user-controlled concepts, but their current implementations depend on legacy state and batch behavior. No rebuild architecture or Phase 1 implementation is defined here.
