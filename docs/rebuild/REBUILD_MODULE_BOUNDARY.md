# Rebuild Module Boundary

## 1. Purpose

Define the backend and frontend ownership boundaries for the approved TradePilot AI rebuild so new business behavior does not depend on the old lifecycle engine. This is a documentation boundary only; no implementation directories, APIs, models, schemas, migrations, or components are created here.

## 2. Scope and Authorities

The product authority is `docs/PRD.md`; the implementation sequence is the supplied TradePilot AI Rebuild Detailed Task Plan. Supporting repository evidence is `docs/rebuild/EXISTING_ASSET_INVENTORY.md`, `docs/rebuild/OLD_WORKFLOW_COMPONENTS.md`, and `docs/rebuild/PRD_CODE_MAPPING.md`. The boundary is limited to the approved flow, statuses, analysis types, user-controlled decisions, one position per session, and Gemini-only processing.

## 3. Boundary Principles

- New rebuild business behavior is owned by the rebuild boundary, not by the existing lifecycle engine.
- The approved vocabulary is limited to `INITIAL_ANALYSIS`, `WAIT_UPDATE`, `POSITION_UPDATE` and `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, `CLOSED_SKIPPED`.
- BUY, WAIT, SKIP, and CLOSE remain user-controlled; Gemini is advisory only.
- One session owns one position. Partial Exit, Closing Analysis, provider routing/fallback, generic workflow engines, generic schema registries, generic validation frameworks, and new abstractions are outside the boundary.
- Shared infrastructure may be reused only when its old business behavior is not imported with it.
- Old records and old runtime surfaces remain available for historical compatibility until cutover is verified.

## 4. Backend Package Boundary

Exact proposed backend package path: `backend/app/trade_workspace/`.

This package owns only approved rebuild business responsibilities: session creation, initial evidence handling, Initial Analysis request ownership, user BUY/WAIT/SKIP, position creation, WAIT Update, Position Update, user CLOSE, and session-history aggregation. It is the business owner for the approved statuses and analysis types, without defining internal classes, layers, or implementation structure in this task.

The package may import approved shared infrastructure listed in Section 8. It must not import or delegate new behavior to `backend/app/lifecycle/`, `backend/app/services/evidence_batches.py` as a workflow authority, `backend/app/ai/providers/router.py`, legacy analysis/prompt/schema registries, Partial Exit/Closing services, or the generic validation framework. Existing authentication, storage, database, queue, and worker mechanics may be called only through their general infrastructure responsibilities.

Responsibilities remaining outside this package include authentication primitives, database connection setup, file-storage mechanics, worker runtime/heartbeat, queue mechanics, gateway/Docker topology, and historical old-workflow compatibility. Those areas do not become rebuild business authorities merely because they are shared.

Evidence: P0.2 identifies authentication, storage, PostgreSQL, worker, queue, and gateway as infrastructure candidates; P0.3 classifies lifecycle, EvidenceBatch, provider routing, validation, Partial Exit, and Closing Analysis as old workflow components; P1.1 maps approved behavior to replacement/adaptation ownership.

## 5. Frontend Feature Boundary

Exact proposed frontend feature path: `frontend/src/features/trade-workspace/`.

This feature owns only the approved screens/actions: session creation, initial evidence upload, Initial Analysis display, BUY/WAIT/SKIP actions, WAIT Update form/history, position summary, Position Update form/history, CLOSE action, complete session timeline, and status-based action display. It owns presentation of user-controlled decisions and must present Gemini output as advisory.

Generic frontend infrastructure may be reused, including the existing root layout, authentication context, API client mechanics, generic loading/error handling, and presentational primitives. Existing workflow UI must not control the rebuild: `frontend/src/features/trade-session/trade-session-shell.tsx`, legacy watching/open-position/Partial Exit/Closing Analysis views, fallback/repair job states, and action lists based on old lifecycle enums remain outside the rebuild feature boundary.

No detailed layout, component tree, or UI contract is defined here. The existing `frontend/src/app/sessions/[sessionId]/page.tsx` may later be integrated with the boundary, but this task does not modify or prescribe that route.

Evidence: P0.2 identifies the current session shell as highly workflow-coupled; P1.1 identifies the session page as requiring replacement while general layout/auth mechanics are partial reuse candidates.

## 6. Database Table Ownership

Rebuild-owned tables will be owned by the new rebuild module and its approved behavior. Exact table names, columns, constraints, indexes, and migration design belong to Phase 3 and are not defined here.

Old business tables remain available until cutover is verified. New rebuild business behavior must not depend on old lifecycle tables or old status decisions. Old tables may be read only when explicitly required for historical compatibility or a later migration task. No existing table is removed, altered, or migrated during P1.2.

Evidence: P0.3 records old lifecycle, analysis, EvidenceBatch, evaluation, and action tables as historical dependencies; P1.1 records enum, job, evidence, and historical-payload migration impact without designing migrations.

## 7. API Boundary

The rebuild API prefix is:

`/api/v2/trade-sessions`

All new rebuild business endpoints live under this prefix. Old APIs remain separate during verification, including the existing `/api/trade-sessions` and `/api/actions` surfaces. Rebuild and old-workflow data must not be mixed through shared endpoint behavior or implicit fallback. Endpoint names, payloads, response contracts, authentication details, and error formats belong to later tasks and are not defined here.

Evidence: Existing routes are under `/api/trade-sessions`, `/api/actions`, `/api/analysis-jobs`, and `/api/evidence`; P1.1 maps those routes as old or partial implementations rather than the new API boundary.

## 8. Allowed Shared Infrastructure

The following existing general infrastructure may be reused, subject to the restriction that old business behavior must not be imported with it:

- Authentication and user identity: `backend/app/auth/`, `backend/app/api/dependencies.py`. Reuse identity resolution and cookie/session mechanics, not old lifecycle decisions.
- Ownership checks: owner-scoped repository predicates such as `get_by_id_for_user`. Reuse authorization mechanics, not old route behavior.
- PostgreSQL connection setup: `backend/app/database/session.py`. Reuse engine/session mechanics, not old models as rebuild ownership.
- File storage adapter: `backend/app/storage/base.py` and `backend/app/storage/local.py`. Reuse safe private file persistence, not EvidenceBatch workflow rules.
- Direct Gemini SDK mechanics: `backend/app/ai/providers/gemini.py`. Reuse the Google GenAI boundary and approved model configuration, not provider routing/fallback or old transport authority.
- Worker runtime mechanics: `worker/app/runtime.py`, heartbeat, and shutdown behavior. Reuse operations, not the legacy processor’s business decisions.
- Queue mechanics: `backend/app/jobs/queue.py` and worker consumer lease handling. Reuse transactional claim/lease mechanics, not old lifecycle restoration or legacy job semantics.
- Migration tooling: `backend/alembic.ini` and `backend/migrations/env.py`. Reuse the runner only; exact rebuild schema ownership belongs to Phase 3.
- Docker Compose topology: `docker-compose.production.yml` and `infra/docker/compose.yml`. Reuse service topology without changing it in P1.2.
- Gateway and generic frontend shell: `infra/nginx/tradepilot.conf`, `frontend/src/app/layout.tsx`, and generic client/auth infrastructure. Reuse routing/layout mechanics, not old workflow UI.

## 9. Old-Code Access Restrictions

The following restrictions apply to new rebuild business code:

- `backend/app/lifecycle/`, old transition services, and restoration logic: `PROHIBITED` for new business behavior.
- EvidenceBatch state machine and legacy batch service: `PROHIBITED` as rebuild business authority; `HISTORICAL_READ_ONLY` only for explicit compatibility work.
- Legacy analysis types, prompt/schema registries, transport normalizers, and provider router: `PROHIBITED` as rebuild authorities; `READ_ONLY_REFERENCE` for mapping/history.
- Partial Exit and Closing Analysis services, routes, prompts, schemas, and UI: `HISTORICAL_READ_ONLY`; they must not control new flow.
- Existing WAIT/SKIP action services: `READ_ONLY_REFERENCE` for behavior evidence; new rebuild decisions must be owned by the rebuild boundary.
- Authentication, identity, ownership, storage, database, queue, worker operations, gateway, and generic layout: `SHARED_INFRASTRUCTURE_ONLY`.
- Existing P9-modified files and local runtime artifacts: `READ_ONLY_REFERENCE`; they are not rebuild dependencies and remain untouched.

New rebuild business code must not call old lifecycle transition services or use old workflow status decisions.

## 10. Prohibited Dependencies

The rebuild boundary must not depend on:

- the old lifecycle transition engine;
- the EvidenceBatch state machine as a business authority;
- unapproved lifecycle statuses;
- unapproved analysis types;
- provider routing or fallback;
- Partial Exit;
- Closing Analysis;
- the generic schema registry as rebuild business authority;
- canonical-versus-transport dual pipelines;
- the generic domain validation framework as rebuild business authority;
- evaluation flow as a rebuild runtime requirement;
- automated BUY, WAIT, SKIP, or CLOSE decisions.

These prohibitions are evidenced by the P0.3 old-workflow inventory and P1.1 mapping. No additional prohibited systems are introduced here.

## 11. Cross-Boundary Interaction Rules

The minimum allowed interaction is:

`frontend/src/features/trade-workspace/`
→ `/api/v2/trade-sessions`
→ `backend/app/trade_workspace/`
→ approved shared infrastructure

The frontend rebuild feature must not call old workflow APIs as a fallback. The rebuild backend may read historical records only when explicitly required for compatibility or a later migration task. It must not delegate new business behavior to the old workflow. Shared infrastructure may provide identity, storage, persistence, queueing, or operations, but not old status/type decisions.

## 12. Historical Compatibility Boundary

Old records remain readable until cutover is verified. Old APIs and frontend surfaces may remain temporarily for historical access and verification. Rebuild and old-workflow data must not be mixed in new business behavior, status transitions, analysis requests, or user decisions.

Deletion and cleanup are deferred to Phase 12. P1.2 does not define migration behavior, data conversion, route retirement, table removal, or historical backfill. Existing unfinished P9 files and local runtime data remain outside the boundary and are preserved.

## 13. Unresolved Boundary Questions

- Exact rebuild-owned table names and migration strategy, deferred to Phase 3.
- Whether a compatibility read adapter is required for historical records, without allowing old tables to control new behavior.
- Exact worker/queue isolation needed while old jobs remain present.
- Exact authentication and gateway wiring for the `/api/v2/trade-sessions` prefix.
- How historical session URLs will expose old records after the rebuild page is introduced.
- Which direct Gemini normalization mechanics can be retained without importing a generic transport/schema pipeline.

## 14. P1.2 Conclusion

The approved rebuild boundary is documented as backend `backend/app/trade_workspace/`, frontend `frontend/src/features/trade-workspace/`, and API prefix `/api/v2/trade-sessions`. The boundary owns only the approved session flow and user-controlled decisions, may use narrowly scoped shared infrastructure, and prohibits old workflow authorities from controlling new behavior. No directories, implementation files, APIs, schemas, migrations, or product code were created or modified.
