# Existing Runtime Asset Inventory

## 1. Purpose

This inventory records existing technical runtime assets that may potentially support the approved TradePilot AI rebuild. It is an evidence-based inventory only; it does not define the rebuild architecture or decide how any asset will be implemented.

## 2. Scope and Constraints

Inspection was limited to authentication, ownership, evidence upload/storage, Gemini and prompts, workers and job handling, the relevant frontend session surface, and shared runtime infrastructure. Existing unfinished P9 files and runtime data were left untouched. Classifications are against the approved rebuild guardrails: Gemini-only, analysis types `INITIAL_ANALYSIS`, `WAIT_UPDATE`, and `POSITION_UPDATE`, statuses `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, and `CLOSED_SKIPPED`, and user-controlled decisions.

## 3. Executive Summary

The repository contains reusable authentication primitives, owner-scoped repository queries, local evidence storage, PostgreSQL connection setup, Alembic migration tooling, Docker Compose services, and an Nginx gateway. These are general infrastructure candidates, subject to later security and deployment review.

The AI, prompt, queue, worker, and session-page assets are not clean rebuild primitives. They encode legacy analysis names, lifecycle statuses, provider routing, validation stages, partial-exit/closing behavior, or broad UI workflow assumptions. They may be useful as references or partial building blocks, but reuse would require explicit coupling removal in a later task. This inventory does not perform that removal.

## 4. Asset Inventory

### 4.1 Authentication

Component Name: Cookie-backed password authentication and session service
Location: `backend/app/auth/service.py`, `backend/app/auth/sessions.py`, `backend/app/auth/passwords.py`, `backend/app/api/auth.py`, `backend/app/api/dependencies.py`
Current Responsibility: Authenticates active users, creates and revokes database-backed sessions, resolves session cookies, and exposes `/api/auth/login`, `/api/auth/logout`, and `/api/auth/me`.
Key Entry Points: `AuthenticationService.authenticate`, `AuthenticationService.resolve_session`, `AuthenticationService.revoke_session`, `get_current_user`, `set_session_cookie`.
Primary Dependencies: FastAPI, SQLAlchemy `AsyncSession`, `UserRepository`, `AuthSessionRepository`, `AppConfig`, password hashing.
Old Workflow Coupling: Low; it supplies identity rather than trade lifecycle behavior.
Reuse Candidate: YES
Dependency Risk: MEDIUM
Recommendation: Retain as an infrastructure candidate; later verify cookie configuration, secret handling, expiry, and rebuild route coverage.
Evidence: `AuthenticatedUser` contains only `id` and `email`; route dependencies resolve the configured cookie and every inspected protected route depends on `get_current_user`.

### 4.2 User Isolation and Ownership

Component Name: Owner-scoped repository and route access checks
Location: `backend/app/repositories/trade_session.py`, `backend/app/repositories/evidence.py`, `backend/app/repositories/analysis_job.py`, `backend/app/api/routes/trade_sessions.py`, `backend/app/api/routes/evidence.py`
Current Responsibility: Filters sessions, evidence, and jobs by authenticated user ID, including update and row-lock queries.
Key Entry Points: `TradeSessionRepository.get_by_id_for_user`, `list_for_user`, `get_by_id_for_user_for_update`; corresponding evidence/job repository methods; route calls passing `current_user.id`.
Primary Dependencies: SQLAlchemy models, `AuthenticatedUser`, FastAPI dependencies.
Old Workflow Coupling: Low at the query boundary; some routes also embed old lifecycle rules.
Reuse Candidate: YES
Dependency Risk: MEDIUM
Recommendation: Retain the owner-scoping pattern, with later endpoint-by-endpoint authorization review.
Evidence: `TradeSessionRepository` adds `TradeSession.owner_id == user_id`; trade-session routes call `_load_session(..., current_user.id)` and evidence file reads call `get_by_id_for_user`.

### 4.3 File Upload Handling

Component Name: Multipart evidence upload and validation
Location: `backend/app/api/routes/evidence.py`, `backend/app/evidence/validation.py`, `backend/app/services/evidence.py`, `frontend/src/features/evidence/evidence-upload-form.tsx`
Current Responsibility: Reads `UploadFile`, validates type, MIME, dimensions and size, then delegates creation/replacement to `EvidenceService`.
Key Entry Points: `upload_evidence`, `replace_evidence`, `EvidenceUploadValidator`, `EvidenceService.create`, `EvidenceService.replace`.
Primary Dependencies: FastAPI multipart handling, `AppConfig.max_upload_size_bytes`, evidence enums/models, local storage.
Old Workflow Coupling: HIGH; required-evidence mappings and permitted mutations depend on legacy analysis types and statuses.
Reuse Candidate: PARTIAL
Dependency Risk: HIGH
Recommendation: Reuse only generic byte/file validation after later mapping its evidence and session rules to approved rebuild behavior.
Evidence: `EvidenceService` maps `INITIAL_ANALYSIS`, `WATCHING_UPDATE`, `OPEN_POSITION_UPDATE`, `PARTIAL_EXIT_REVIEW`, and `CLOSING_ANALYSIS`; route handlers accept multipart uploads and call the service.

### 4.4 Evidence Storage

Component Name: Local filesystem storage adapter
Location: `backend/app/storage/base.py`, `backend/app/storage/local.py`, `backend/app/storage/__init__.py`, `backend/app/models/evidence.py`
Current Responsibility: Stores evidence below a configurable root using `<user_id>/<session_id>/<generated_filename>`, records SHA-256 and size, reads/deletes by safe relative reference, and blocks path traversal.
Key Entry Points: `FileStorage` protocol, `LocalFileStorage.store`, `read`, `delete`, `create_file_storage`.
Primary Dependencies: `Path`, UUID filenames, SHA-256, `AppConfig.storage_root`, evidence persistence.
Old Workflow Coupling: Low in the adapter; service-level batch/status rules are separate.
Reuse Candidate: YES
Dependency Risk: MEDIUM
Recommendation: Retain as a candidate for generic private evidence persistence; later review permissions, retention, backup, and production object-storage needs.
Evidence: `LocalFileStorage._resolve_safe` rejects absolute paths and root escapes; `store` creates a user/session hierarchy and returns `StoredFile` metadata.

### 4.5 Gemini Client or SDK Adapter

Component Name: Gemini provider adapter with provider abstraction
Location: `backend/app/ai/providers/gemini.py`, `backend/app/ai/providers/base.py`, `backend/app/ai/providers/__init__.py`, `backend/app/ai/providers/capabilities.py`
Current Responsibility: Wraps Google GenAI async `generate_content`, loads images, maps provider errors, normalizes responses, and exposes a generic `AIProvider` capability contract.
Key Entry Points: `_GoogleGenAIModelClient`, `GeminiProvider`, `GeminiProvider.generate`, `build_analysis_provider_config`.
Primary Dependencies: `google.genai`, model configuration, response schemas, provider capability/normalization layers.
Old Workflow Coupling: HIGH; the provider is inside a multi-provider abstraction and the surrounding configuration supports provider order/fallback.
Reuse Candidate: PARTIAL
Dependency Risk: HIGH
Recommendation: Treat the Gemini SDK wrapper and error mapping as references/candidates only; later isolate Gemini-only behavior and verify the production model `gemini-3.1-flash-lite`.
Evidence: `_GoogleGenAIModelClient` calls `genai.Client(...).aio.models.generate_content`; `GeminiProvider` defaults to `gemini-3.1-flash-lite`, while provider configuration and UI status include provider/fallback concepts.

### 4.6 Prompt Loading

Component Name: Versioned prompt registry and catalog loader
Location: `backend/app/ai/prompts/registry.py`, `backend/app/ai/prompts/catalog.py`, `backend/app/ai/prompts/models.py`, `prompts/production/v1/`
Current Responsibility: Loads version-controlled system/user prompt files, maps analysis types to schema names and versions, validates registrations, and renders templates.
Key Entry Points: `PromptRegistry.__init__`, `PromptRegistry.get`, `PromptRegistry.render`, `load_catalog`.
Primary Dependencies: Prompt Markdown files, production schema names, analysis-type mappings.
Old Workflow Coupling: HIGH; catalog entries include `WATCHING_UPDATE`, `OPEN_POSITION_UPDATE`, `CLOSING_ANALYSIS`, and legacy evidence requirements.
Reuse Candidate: PARTIAL
Dependency Risk: HIGH
Recommendation: Reuse only the deterministic file-loading/versioning mechanics after later narrowing the catalog to approved rebuild types.
Evidence: `_ANALYSIS_TYPE_SCHEMA` explicitly registers four legacy/current types; `_REQUIRED_EVIDENCE` and `_REQUIRES_IMAGES` encode workflow-specific assumptions.

### 4.7 Background Worker

Component Name: Polling analysis worker with heartbeat
Location: `worker/app/runtime.py`, `worker/app/main.py`, `worker/app/heartbeat.py`, `worker/app/consumers/analysis_jobs.py`
Current Responsibility: Starts a worker, initializes/refreshes a heartbeat, polls for work, claims one job, processes it, records errors, and shuts down cleanly.
Key Entry Points: `run_worker`, `_create_consumer`, `AnalysisJobConsumer.run_once`.
Primary Dependencies: SQLAlchemy async sessions, `PostgreSQLJobQueue`, `AnalysisProcessor`, provider configuration, validation service, worker config.
Old Workflow Coupling: HIGH; it constructs the legacy analysis processor and validation/provider pipeline.
Reuse Candidate: PARTIAL
Dependency Risk: HIGH
Recommendation: Retain the operational loop/heartbeat as a candidate only; later inspect job payload and processor boundaries before any reuse.
Evidence: `_create_consumer` imports `AnalysisProcessor`, `PostgreSQLJobQueue`, `build_analysis_provider_config`, and `UnifiedValidationService`; `run_worker` loops on `consumer.run_once()`.

### 4.8 Analysis Queue and Job Claiming

Component Name: PostgreSQL-backed leased analysis queue
Location: `backend/app/jobs/queue.py`, `backend/app/models/analysis_job.py`, `backend/app/repositories/analysis_job.py`, `worker/app/consumers/analysis_jobs.py`
Current Responsibility: Claims queued/retrying jobs with `FOR UPDATE`/expired leases, renews and releases leases, retries or terminalizes failures, and records worker ownership.
Key Entry Points: `PostgreSQLJobQueue.claim_next`, `renew_lease`, `release`, `record_processing_error`, `AnalysisJobConsumer.run_once`.
Primary Dependencies: PostgreSQL, `AnalysisJobStatus`, `AnalysisType`, `TradeSession`, lifecycle restoration, evidence batches.
Old Workflow Coupling: HIGH; queue state transitions restore session lifecycle state and use broad legacy analysis/job enums.
Reuse Candidate: PARTIAL
Dependency Risk: HIGH
Recommendation: Consider only the transactional claim/lease technique later; do not assume the existing job model or restoration behavior matches the rebuild.
Evidence: `PostgreSQLJobQueue` documents `FOR UPDATE SKIP LOCKED`; `_claim` writes lease fields and `restore_session_status` is imported for session recovery.

### 4.9 Frontend Job Polling

Component Name: Analysis job status polling UI
Location: `frontend/src/features/jobs/job-status.tsx`, `frontend/src/lib/api/analyses.ts`, `frontend/src/features/trade-session/trade-session-shell.tsx`
Current Responsibility: Requests `/api/analysis-jobs/{jobId}`, polls every three seconds until terminal status, persists an active job in `sessionStorage`, and renders progress/retry/failure states.
Key Entry Points: `JobStatus.poll`, `isTerminal`, `getJobStatus`, `TradeSessionShell` active-job restoration.
Primary Dependencies: Next/React hooks, analysis-job API types, legacy status labels, `AnalysisFailure`.
Old Workflow Coupling: HIGH; status labels include `FALLBACK`, `BUILDING_CONTEXT`, `CALLING_PROVIDER`, `VALIDATING`, and `REPAIRING`.
Reuse Candidate: PARTIAL
Dependency Risk: HIGH
Recommendation: Retain polling mechanics as a candidate, but later reduce statuses and callbacks to approved rebuild job behavior.
Evidence: `POLL_INTERVAL_MS = 3000`; `JobStatus` stops only at `COMPLETED`, `FAILED`, or `CANCELLED` and displays provider fallback/repair stages.

### 4.10 Frontend Layout and Session Page Structure

Component Name: Next.js root layout and client session shell
Location: `frontend/src/app/layout.tsx`, `frontend/src/app/sessions/[sessionId]/page.tsx`, `frontend/src/features/trade-session/trade-session-shell.tsx`
Current Responsibility: Provides global `AuthProvider`, header, page content area, and a session detail shell that loads a session, analyses, timeline, evidence, actions, and analysis views.
Key Entry Points: `RootLayout`, `SessionDetailPage`, `TradeSessionShell`.
Primary Dependencies: Next.js App Router, React state/effects, authentication context, session/analysis/timeline/evidence APIs, many feature panels and modals.
Old Workflow Coupling: HIGH; the shell imports initial, watching, open-position, partial-exit, closing-analysis, and multiple trade-action components.
Reuse Candidate: PARTIAL
Dependency Risk: HIGH
Recommendation: Retain only global layout conventions and reusable presentation primitives as candidates; treat the session shell as workflow-coupled.
Evidence: `RootLayout` composes `AuthProvider` and `Header`; `SessionDetailPage` renders `TradeSessionShell`; the shell imports `PartialExitModal`, `ClosingAnalysisView`, and legacy analysis views.

### 4.11 Docker Compose

Component Name: Multi-service production Compose definition
Location: `docker-compose.production.yml`, `infra/docker/compose.yml`, `infra/docker/*.Dockerfile`
Current Responsibility: Defines PostgreSQL, backend, worker, frontend, and Nginx services, health checks, dependencies, environment wiring, and the `pgdata` volume.
Key Entry Points: Compose services `postgres`, `backend`, `worker`, `frontend`, `nginx`; `pgdata` volume; backend/worker `DATABASE_URL` and `DATABASE_SYNC_URL`.
Primary Dependencies: Docker images/build contexts, PostgreSQL 17, Nginx, environment variables, named volume.
Old Workflow Coupling: MEDIUM; service topology is general, but backend/worker commands run the existing application.
Reuse Candidate: YES
Dependency Risk: MEDIUM
Recommendation: Retain topology as an infrastructure candidate, with later environment, health, secret, and volume review.
Evidence: `docker-compose.production.yml` defines five services and mounts `pgdata`; Nginx is configured from `infra/nginx/tradepilot.conf` read-only.

### 4.12 Gateway or Reverse Proxy

Component Name: Nginx frontend/API gateway
Location: `infra/nginx/tradepilot.conf`
Current Responsibility: Routes `/` to frontend, `/api/` and `/health` to backend, forwards proxy headers, and denies direct `/data/evidence` and `/storage/` access.
Key Entry Points: `frontend_upstream`, `backend_upstream`, location blocks for `/`, `/api/`, `/health`, `/data/evidence`, and `/storage/`.
Primary Dependencies: Docker service DNS names `frontend` and `backend`, TLS/server configuration.
Old Workflow Coupling: Low.
Reuse Candidate: YES
Dependency Risk: MEDIUM
Recommendation: Retain as a candidate after later checking TLS, forwarding, upload limits, and deployment-specific routing.
Evidence: `proxy_pass` targets the two service upstreams; storage paths are explicitly denied and evidence is expected through authenticated backend routes.

### 4.13 PostgreSQL Integration

Component Name: Shared async SQLAlchemy database integration
Location: `backend/app/database/session.py`, `backend/app/database/base.py`, `backend/app/config.py`, `docker-compose.production.yml`
Current Responsibility: Creates a shared async engine/session factory, yields transactional FastAPI sessions, and connects backend/worker to PostgreSQL.
Key Entry Points: `_get_engine`, `get_engine`, `get_db_session`, Compose `DATABASE_URL`/`DATABASE_SYNC_URL`.
Primary Dependencies: SQLAlchemy async engine, psycopg/asyncpg URLs, `AppConfig`, PostgreSQL service.
Old Workflow Coupling: Low in connection management; models and repositories are workflow-specific.
Reuse Candidate: YES
Dependency Risk: MEDIUM
Recommendation: Retain connection/session mechanics as infrastructure; later verify pool sizing, transaction boundaries, and schema scope.
Evidence: `get_db_session` commits on success, rolls back on exception, and closes sessions; Compose wires backend and worker to the `postgres` service.

### 4.14 Migration Tooling

Component Name: Alembic migration runner and version history
Location: `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/versions/`
Current Responsibility: Loads `DATABASE_SYNC_URL`, binds SQLAlchemy metadata, and runs online/offline Alembic migrations.
Key Entry Points: `run_migrations_offline`, `run_migrations_online`, `target_metadata`, `alembic.ini` configuration.
Primary Dependencies: Alembic, SQLAlchemy metadata, PostgreSQL sync URL, model imports.
Old Workflow Coupling: MEDIUM; runner mechanics are general, but metadata/version history includes old analysis, lifecycle, partial-exit, and P9 migration concepts.
Reuse Candidate: PARTIAL
Dependency Risk: HIGH
Recommendation: Retain the runner mechanics as a candidate; treat existing revisions as historical context, not an automatic rebuild schema.
Evidence: `env.py` imports `Analysis`, `AnalysisJob`, `EvidenceBatch`, `TradeSession`, and other domain models; version files include `p1_lifecycle_statuses`, `p2_evidence_batches`, and an untracked P96 migration.

### 4.15 Existing Session Detail Page

Component Name: Existing Trade Session detail route and workflow shell
Location: `frontend/src/app/sessions/[sessionId]/page.tsx`, `frontend/src/features/trade-session/trade-session-shell.tsx`, `backend/app/api/routes/trade_sessions.py`
Current Responsibility: Loads an owned session and presents status, evidence, analyses, timeline, same-ticker history, lifecycle decisions, position actions, and archive/closing flows.
Key Entry Points: `SessionDetailPage`, `TradeSessionShell`, backend `get_trade_session`, `list_trade_sessions`, action and analysis routes.
Primary Dependencies: Trade-session repositories/services, evidence batches, analysis APIs, timeline, lifecycle action APIs, legacy status/type enums.
Old Workflow Coupling: HIGH.
Reuse Candidate: NO
Dependency Risk: HIGH
Recommendation: Use only as a reference for current runtime behavior; do not treat the page or route composition as the approved rebuild surface.
Evidence: The shell imports `InitialAnalysisView`, `WatchingUpdateView`, `OpenPositionUpdateView`, `PartialExitReviewView`, `ClosingAnalysisView`, `PartialExitModal`, and `FullExitModal`; backend routes include `/closing-analysis` and open-position batch routes.

## 5. Shared Infrastructure Candidates

The strongest general candidates are cookie/session authentication, owner-scoped query patterns, local storage path-safety primitives, PostgreSQL connection/session setup, Docker service topology, and the Nginx routing configuration. The generic parts of multipart validation, leased queue mechanics, worker heartbeat/lifecycle, prompt file loading, and job polling are potential partial candidates only. None of these classifications authorizes reuse without later implementation review.

## 6. High-Risk Coupling Summary

The highest-risk coupling is concentrated in the AI and workflow path. Existing enums include `WATCHING_UPDATE`, `OPEN_POSITION_UPDATE`, `PARTIAL_EXIT_REVIEW`, and `CLOSING_ANALYSIS`, as well as lifecycle values outside the approved status set. Prompt loading, evidence requirements, queue claiming, worker processing, validation, and frontend polling all reference those concepts. Provider configuration also exposes abstraction/fallback behavior that conflicts with a Gemini-only rebuild. The existing session page imports partial-exit and closing components that are explicitly outside the approved rebuild constraints.

## 7. Unknowns Requiring Later Inspection

- Whether authentication cookie/session configuration is suitable for the final deployment and threat model.
- Whether local evidence storage is acceptable for the rebuild deployment or must be replaced by an object-storage implementation.
- Exact provider configuration and all call sites that can select providers or fallback behavior.
- Exact job payload, processor, transaction, retry, and session-status semantics required by the approved rebuild.
- Database schema/data-retention implications of preserving or replacing existing runtime tables.
- Nginx TLS, upload-size, timeout, and production secret configuration.
- Which visual components are genuinely presentational after workflow-coupled imports are removed.

## 8. P0.2 Conclusion

The existing runtime assets have been inventoried without modifying application behavior or runtime state. Shared infrastructure is potentially reusable; AI, workflow, queue, and session-page assets require later review because of substantial old-workflow coupling. No architecture, module boundary, PRD mapping, or implementation decision is defined here.
