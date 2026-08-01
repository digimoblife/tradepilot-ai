# P12-B — Dependency and Runtime Impact Verification

## Executive Summary

All 36 P12-A records were verified without changing classifications. Active V2 closure is `/trade-workspace` → `/api/v2/trade-sessions` → `backend/app/trade_workspace` → `analysis_requests_v2` → `RebuildAnalysisRequestConsumer`. A material coupling remains: the active worker's startup validation uses the legacy production prompt/provider stack before constructing the V2 consumer.

## Product-Owner Cleanup Strategy

This verification follows the locked P12-A → P12-F evidence sequence. It is not a KEEP, REMOVE, or REFACTOR decision. Phase 11 remains deferred.

## P12-A Baseline

Baseline inventory commit: `2532d78d97f02b175155bb8bf1794c2ad63e692a`; 36 stable IDs, paths, and P12-A classifications were validated unchanged.

## Audit Method

Static import/route searches, safe FastAPI application construction, worker/Dockerfile inspection, SQLAlchemy metadata inspection, Alembic revision inspection, prompt/schema consumer search, and frontend app-route/import inspection. No database mutation, API mutation, deployment, or Gemini request occurred.

## Starting Commit and Repository State

Starting commit `2532d78d97f02b175155bb8bf1794c2ad63e692a` on `main`. The pre-existing 14 tracked backend/frontend source/test edits and untracked local paths remained untouched and unstaged. Git emitted the pre-existing non-fatal fsmonitor IPC warning while returning status/diff results.

## Active Runtime Entrypoints

- Frontend: `/` and authenticated navigation lead to `/trade-workspace`; its V2 client calls `/v2/trade-sessions`.
- Backend: `uvicorn app.main:app` constructs the FastAPI application and includes the V2 router.
- Worker: `python -m app.main` calls `run_worker`; `_create_consumer` lazily constructs `RebuildAnalysisRequestConsumer` and `RebuildAnalysisProcessor`.
- Gateway: Nginx proxies `/api/` to backend and all other frontend routes to Next.js.

## Frontend Route and Bundle Reachability

`/sessions`, `/sessions/new`, and `/sessions/[sessionId]` are app-router inputs and redirect to `/trade-workspace`; middleware protects both route families. No active header navigation link to `/sessions` was found, but bookmarks remain a repository-unobservable compatibility concern. `/evaluations` is a built, directly imported legacy page with no navigation link found. No active V2 workspace import of `features/trade-session` or `features/analysis` was found; those remain packaged source with test/local legacy imports.

## Backend Route Registration and Consumers

The FastAPI probe enumerated registered legacy `/api/analysis-jobs`, `/api/evaluation-records`, `/api/actions`, and `/api/trade-sessions` endpoints as well as V2 endpoints. Legacy frontend API modules call the corresponding paths; evaluation has a reachable page. V2 routes are in `app.trade_workspace.api.routes.trade_sessions` and no V2 route imports the legacy services/actions/lifecycle roots.

## Worker Entrypoint and Consumer Reachability

The production worker branch uses the V2 consumer. `AnalysisJobConsumer` is copied/symlinked into the image and test-imported, but no default or alternate production command selects it. The worker image build imports legacy `app.lifecycle` and `app.jobs.processor`, and runtime startup validates legacy prompt/provider infrastructure; those are deployment/startup facts, not proof the legacy consumer is selected.

## Provider and AI Runtime Dependencies

V2 processing directly uses `backend/app/trade_workspace/ai/gemini_adapter.py`, `RebuildPromptLoader`, and the rebuild response validator. It does not import `backend/app/ai/providers/gemini.py`. However, active `validate_worker_startup` imports `PromptRegistry` and `validate_analysis_provider_startup`, which reads the legacy provider layer/configuration. `AI-002` remains unresolved because its committed caller is legacy `jobs/processor.py`, while the file has unrelated working-tree modifications.

## Prompt and Schema Filesystem Dependencies

`prompts/rebuild` is directly read by the V2 processor. `prompts/production/v1` is read by worker startup validation through `PromptRegistry`. `schemas/rebuild/v1` is used by V2 response validation. `schemas/production/v1` is loaded at backend application startup and by legacy-provider startup validation. Mounting alone was not used as per-file proof.

## Database Metadata Dependencies

The metadata probe lists old and V2 tables, including all six V2 tables and `analysis_jobs`, `evidence_batches`, `trade_sessions`, and related old tables. Registered legacy routes directly import legacy models. Metadata registration must not be mistaken for V2 business coupling.

## Alembic Migration Graph

`alembic heads` reports two heads: `a1b2c3d4e5f6` (legacy open-position branch) and `d0e1f2a3b4c5` (rebuild). The V2 sequence p31–p36 descends from a legacy branchpoint after evaluation records. Historical migrations, downgrade logic, FKs, and the two-head topology are deployment/migration dependencies; no migration is assessed for removal.

## Docker and Deployment Dependencies

Production Compose starts PostgreSQL, backend, worker, frontend, and gateway. Backend command is Uvicorn; worker command is `python -m app.main`; frontend builds/runs Next.js; Nginx proxies API/frontend. The worker mounts prompts and schemas, backend mounts schemas, and backend/worker share evidence storage. The worker Dockerfile copies and imports legacy modules during image build.

## Environment Variable Consumers

Compose supplies redacted `GEMINI_API_KEY`, `GEMINI_MODEL`, `PROVIDER_ORDER`, database URLs, storage root, worker identity/interval, auth/security values, and frontend API URLs. `GEMINI_MODEL` is consumed by V2 configuration. `PROVIDER_ORDER` is consumed by the legacy provider validation layer reached during active worker startup. No secret value was displayed.

## Test-Only Dependencies

`TEST-001`, `TEST-002`, and `TEST-003` are test/fixture-only records. Legacy worker and frontend dynamic imports found were test-only. Tests importing legacy models/jobs/services do not establish production use.

## Documentation-Only Items

`DOC-001` and `DOC-002` have no runtime-code dependency identified and remain documentation/history records.

## Per-Inventory-Item Impact Table

| IDs | Verified impact | Evidence summary |
| --- | --- | --- |
| FE-001, FE-002 | V2_RUNTIME_REQUIRED | Active workspace page and feature/API flow. |
| FE-003 | V2_RUNTIME_REQUIRED | Built redirect pages and middleware target `/trade-workspace`. |
| FE-004, FE-005 | REGISTERED_BUT_NO_ACTIVE_CONSUMER_FOUND | Legacy feature source/test imports; no active V2/page import. |
| FE-006, FE-007 | LEGACY_RUNTIME_REACHABLE | `/evaluations` page and its legacy API client; legacy client endpoints. |
| BE-001 | V2_RUNTIME_REQUIRED | V2 FastAPI router, services, models, processor. |
| BE-002 | SHARED_RUNTIME_REQUIRED | Uvicorn application host registers V2 and legacy routers. |
| BE-003–BE-005, BE-007–BE-008 | LEGACY_RUNTIME_REACHABLE | Registered old routes import their old services/jobs/actions. |
| BE-006 | DEPLOYMENT_OR_MIGRATION_REQUIRED | Mixed metadata and model/FK history. |
| AI-001, AI-004 | V2_RUNTIME_REQUIRED | Active worker startup imports provider validation and PromptRegistry. |
| AI-002 | UNRESOLVED | Legacy caller found; unrelated working-tree modification conflicts with final source proof. |
| AI-003, SC-001 | V2_RUNTIME_REQUIRED | V2 processor directly loads rebuild prompt/schema assets. |
| SC-002 | V2_RUNTIME_REQUIRED | Backend startup and active worker validation load production schema stack. |
| DB-001–DB-003, INFRA-004 | DEPLOYMENT_OR_MIGRATION_REQUIRED | V2 migration ancestry/two heads and Compose startup/mounts. |
| WK-001, WK-003 | V2_RUNTIME_REQUIRED | Default worker branch constructs V2 consumer/processor. |
| WK-002 | REGISTERED_BUT_NO_ACTIVE_CONSUMER_FOUND | Packaged/test-imported legacy consumer; no production selector found. |
| INFRA-001–INFRA-003 | SHARED_RUNTIME_REQUIRED | Auth, database, and storage serve V2 and legacy paths. |
| TEST-001–TEST-003 | TEST_ONLY | Exact test/fixture directories. |
| DOC-001–DOC-002 | DOCUMENTATION_ONLY | Documentation/history only. |

## High-Risk Findings

Critical current dependencies are the V2 application/worker closure, V2 tables/migrations, shared auth/database/storage, and Compose. The main legacy-origin coupling is worker startup validation of production prompt/provider/schema assets. Registered legacy API paths remain reachable even though the default worker does not select `AnalysisJobConsumer`.

## Registered but Unconsumed Items

`FE-004`, `FE-005`, and `WK-002` are packaged or test-imported without a proven active caller. This is not an inactivity or removal conclusion; production bundle/operational traffic proof is unavailable.

## Unresolved Items

`AI-002` is `UNRESOLVED`: committed imports show legacy job-processor use, but the file is modified by unrelated work. P12-C must require a final caller/import check against the settled committed source before classifying its coupling.

## Counts by Verified Impact

| Impact | Count |
| --- | ---: |
| V2_RUNTIME_REQUIRED | 11 |
| SHARED_RUNTIME_REQUIRED | 4 |
| LEGACY_RUNTIME_REACHABLE | 7 |
| REGISTERED_BUT_NO_ACTIVE_CONSUMER_FOUND | 3 |
| TEST_ONLY | 3 |
| DEPLOYMENT_OR_MIGRATION_REQUIRED | 5 |
| DOCUMENTATION_ONLY | 2 |
| UNRESOLVED | 1 |
| **Total** | **36** |

## Required P12-C Decisions

P12-C must classify, without removing code: redirect compatibility (`FE-003`), legacy UI/package records, each registered legacy route/service/action, mixed metadata/migration preservation, active worker startup coupling to legacy provider/prompt/schema infrastructure, and `AI-002` after unrelated changes settle.

## Explicit Non-Removal Statement

No item is labeled safe to remove. No removal, deprecation, disabling, refactor, or final coupling classification occurred.

## Final Result

COMPLETED — dependency/runtime evidence is recorded for exactly the 36 P12-A IDs; the sole unresolved record has a specific P12-C follow-up.

## Required Evidence Standard

Each runtime-required record identifies a concrete V2 or shared entrypoint; legacy-reachable records identify registered old routes/pages; registered-but-unconsumed records state both package/registration evidence and the missing active caller; deployment/migration records identify the exact startup, mount, or revision evidence; and the unresolved record states its conflict and follow-up.
