# P12-A — Repository Legacy Inventory

## Executive Summary

This is a shallow, mapping-first inventory of repository areas that are active V2, shared, legacy-looking, mixed, test-only, historical, or uncertain. It is not a dependency proof and does not state that anything is safe to remove.

## Product-Owner Cleanup Decision

The product owner replaced the transitional Phase 12 execution assumption with the evidence-first cleanup sequence recorded in `PHASE_12_CLEANUP_EXECUTION_LOCK.md`. Phase 11 remains deferred and is not marked completed.

## Locked P12-A → P12-F Sequence

P12-A inventory → P12-B dependency/runtime verification → P12-C V2 coupling classification → P12-D incremental safe removal → P12-E V2 decoupling/replacement → P12-F final verification. No removal is permitted before P12-B and P12-C evidence exists.

## Audit Scope

Structure-level review covered 795 tracked files; 693 tracked source, test, prompt, schema, configuration, deployment, script, and documentation files were enumerated after excluding tracked caches and generated artifacts. Directory areas mapped: frontend, backend, worker, prompts, schemas, migrations, tests, fixtures, scripts, Docker/deployment, documentation, and root configuration.

## Starting Commit and Repository State

- Starting commit: `906d3d89bbbd1025487ae3fe3fce7b58f1f0b580`
- Branch: `main`
- Existing unrelated tracked changes: 14 modified backend/frontend source and test files, recorded before inspection.
- Existing unrelated untracked paths: `.agent-skills/`, an open-position migration, PRD amendment/archive/P11 evidence documents, `scripts/e2e_p9_smoke.py`, and `storage/local/`.

Those paths are preserved and unstaged. The starting Git commands emitted a non-fatal `.git/fsmonitor--daemon.ipc` query error; Git still returned the listed status/diff information.

## Authoritative V2 Boundary

Read directly before inspection: the authoritative PRD, Detailed Task Plan, task ledger, all three commit-to-task mappings, rebuild module boundary, simple architecture, and scope guardrails. V2 is Gemini-only (`gemini-3.1-flash-lite`); its only business statuses are `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, and `CLOSED_SKIPPED`; its analysis types are `INITIAL_ANALYSIS`, `WAIT_UPDATE`, and `POSITION_UPDATE`; and its persistence boundary is the six `_v2` tables. V2 does not use legacy `analysis_jobs` as its queue authority.

## Repository Structure Overview

Tracked relevant-file counts: backend application 204, backend migrations 23, backend tests 201, frontend source 127, worker application 10, worker tests 8, production/rebuild prompts 11, schemas 30, scripts 5, rebuild documentation 38, plus root and infrastructure configuration. Counts are structural, not an assertion that every file was semantically read.

## Active V2 Anchors

- `FE-001`/`FE-002`: `/trade-workspace` imports the V2 workspace, which calls `/v2/trade-sessions` for the approved flow.
- `BE-001`: `backend/app/trade_workspace` owns the V2 route, services, models, queue, processor, Gemini adapter, and schemas.
- `AI-003` and `SC-001`: the three rebuild prompts and three rebuild schemas match the approved analysis types.
- `DB-001`/`DB-002`: V2 session and durable queue migrations create `trade_sessions_v2` and `analysis_requests_v2`.
- `WK-001`: the default worker runtime constructs `RebuildAnalysisRequestConsumer` for `analysis_requests_v2`.

## Shared Infrastructure

- `BE-002`: FastAPI host and route-registration container.
- `INFRA-001`: authentication and ownership primitives used by the V2 route.
- `INFRA-002`: SQLAlchemy connection/base/types used by V2 persistence.
- `INFRA-003`: storage mechanics and shared evidence volume.

## Frontend Legacy Candidates

- `FE-004`: old `features/trade-session` shell/panels. Concrete indicator: it is named in the module-boundary document as outside V2 and no direct V2 workspace import was found.
- `FE-005`: old analysis views. Concrete indicators: Closing Analysis, Partial Exit Review, and Watching Update are unapproved concepts.
- `FE-006`: evaluation dashboard. Concrete indicator: it implements the unapproved evaluation workflow and has its own `/evaluations` page.

`FE-003` is not a candidate for removal: it is legacy-origin routing apparently referenced by V2 because `/sessions` redirects to `/trade-workspace`. `FE-007` is mixed API client code and is likewise not a deletion finding.

## Backend Legacy Candidates

- `BE-004`: old lifecycle service/transitions/restoration; explicitly prohibited as V2 business authority.
- `BE-005`: legacy `analysis_jobs` queue/processor control path; explicitly excluded by the V2 queue requirement.
- `BE-007`: legacy analysis-job, EvidenceBatch, evaluation, history, and trade-session services.
- `BE-008`: legacy action services. Concrete indicator: includes `partial_exit.py` and is reached through registered `/api/actions`.

`BE-003` is a registered mixed legacy route surface and `BE-006` a mixed old-model area. Both require P12-B; their presence/registration is not proof of removal safety.

## Worker and Queue Legacy Candidates

`WK-002`, the `AnalysisJobConsumer`, is a legacy candidate: the inspected default runtime selects `RebuildAnalysisRequestConsumer`, not this consumer. P12-B must still inspect alternate commands and dynamic imports. `WK-003` is legacy-origin code apparently referenced by V2 because its default `_create_consumer` creates the rebuild consumer, while retained old validation helpers need reachability proof.

## Provider and AI Asset Candidates

`AI-001` is mixed: `gemini.py` provides direct Gemini mechanics while `deepseek.py`, `router.py`, `selection.py`, and old transport modules expose forbidden provider routing/fallback or obsolete transport behavior. `AI-002` is isolated as `NEEDS_VERIFICATION`: it imports `EvidenceBatch` and handles `CLOSING_ANALYSIS`, and is currently modified by unrelated work. `AI-004` is the old prompt collection; its Closing Analysis/Watching/Open Position prompt names are concrete legacy indicators, but the worker mounts the prompt tree, so P12-B must map actual file reads.

## Schema and Prompt Candidates

`SC-001` is active rebuild schema. `SC-002` is mixed production schema/manifest material: it includes obsolete Closing Analysis, Partial Exit, Watching, and transport schemas, yet backend startup explicitly loads the production manifest. This is a direct apparent V2-adjacent reference and requires per-file dependency verification.

## Database and Migration Candidates

`DB-003` is intentionally `NEEDS_VERIFICATION`. The Alembic directory includes both V2 revisions and legacy lifecycle, EvidenceBatch, evaluation, and old-state revisions. No migration is called removable: revision-chain, deployed-database, and historical-data proof belongs to P12-B/P12-C.

## Test and Fixture Candidates

`TEST-001` is focused V2 test coverage, while `TEST-002` covers old/P9 lifecycle scenarios including Partial Exit and open-position monitoring. `TEST-003` is a mixed fixture tree containing legacy Closing Analysis, Partial Exit, and Watching fixtures alongside an initial-analysis-v2 fixture. All three are test/fixture-only inventory items, not deletion determinations.

## Deployment and Configuration Candidates

`INFRA-004` is `NEEDS_VERIFICATION`: production Compose starts the V2-capable backend, worker, frontend, PostgreSQL, and gateway with Gemini as default, but retains `PROVIDER_ORDER`. P12-B must establish each variable's live consumer. No Docker, gateway, environment, or deployment file was altered.

## Documentation and Historical Candidates

`DOC-001` contains rebuild authorities and historical verification/mapping evidence; it is protected documentation/history. `DOC-002` is a pre-rebuild provider specification, preserved as history pending any P12-B runtime-reference check. Neither classification recommends deletion.

## Legacy-Origin Items Apparently Referenced by V2

| ID | Exact apparent reference |
| --- | --- |
| FE-003 | `frontend/src/app/sessions/page.tsx` redirects to `/trade-workspace`. |
| FE-007 | `frontend/src/lib/api/trade-sessions.ts` contains concurrent V2 client additions in a mixed API directory. |
| BE-003 | `backend/app/application.py` registers legacy route families alongside the V2 router. |
| BE-006 | shared SQLAlchemy metadata/base may connect old models to the active persistence host. |
| AI-001 | Gemini/provider configuration is adjacent to active Gemini runtime while the directory remains mixed. |
| SC-002 | `backend/app/application.py` loads the production manifest at backend startup. |
| WK-003 | `worker/app/runtime.py::_create_consumer` directly creates `RebuildAnalysisRequestConsumer`. |

## Uncertain Items

`AI-002`, `DB-003`, and `INFRA-004` are `NEEDS_VERIFICATION` because evidence is respectively affected by unrelated in-progress work, migration-chain/data dependencies, and mixed production configuration. Each JSON record gives a specific P12-B check.

## Preliminary Risk Summary

Highest-risk groups are registered legacy backend routes/action services, legacy `analysis_jobs` plus its worker consumer, mixed provider/manifest assets, the mixed migration chain, and production Compose. Their risk is high because an active registration, storage/migration relationship, or deployment mount remains visible.

## Candidate Counts by Classification

| Classification | Count |
| --- | ---: |
| ACTIVE_V2 | 8 |
| SHARED_INFRASTRUCTURE | 4 |
| LEGACY_CANDIDATE | 9 |
| LEGACY_REFERENCED_BY_V2 | 7 |
| TEST_OR_FIXTURE_ONLY | 3 |
| DOCUMENTATION_OR_HISTORY | 2 |
| NEEDS_VERIFICATION | 3 |
| **Total** | **36** |

## Required P12-B Checks

P12-B must trace direct/transitive imports, registered-route reachability, worker entrypoints and dynamic imports, Compose environment and mounted-file consumers, production manifest/schema access, Alembic revision/data dependencies, and test/fixture consumers. It must preserve historical data and migrations and must not elevate a shallow "no direct reference found" result to runtime proof.

## Explicit Non-Deletion Statement

No item in this inventory is declared safe to delete. No deletion plan was created or executed. P12-A performed no P12-B runtime verification and no P12-C coupling decision.

## Final Result

COMPLETED — P12-A produced a preliminary repository inventory only. The machine-readable records are in `LEGACY_CODE_INVENTORY.json`.

## Evidence Quality Rules

Classifications rely only on inspected route/startup references, direct imports/search hits, tests, deployment mounts/configuration, and authoritative-boundary comparison. “No direct reference found” means only that shallow inspection found none; it does not rule out transitive, dynamic, migration, deployment, or historical-data dependencies.
