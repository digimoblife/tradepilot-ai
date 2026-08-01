# P12-C — V2 Coupling Classification

## Executive Summary

All 36 inventory IDs are classified for a later action, with no action executed. The V2 core, shared infrastructure, migration history, and documentation history are preserved. Seven reachable legacy runtime groups require route disablement first; five legacy-origin groups must be decoupled from active V2 startup before any cleanup. Four records remain unresolved rather than being admitted to removal planning.

## Product-Owner Cleanup Strategy

The locked sequence remains inventory, verification, classification, incremental removal, decoupling/replacement, then final verification. Phase 11 remains deferred; official task statuses are unchanged.

## P12-A and P12-B Baselines

P12-A: `2532d78d97f02b175155bb8bf1794c2ad63e692a`. P12-B: `95fc28dcb3ed212879f917d5352852adcb7ecb58`. Both JSON files contain exactly 36 matching stable IDs; P12-A classifications and P12-B impacts are preserved verbatim in the classification JSON.

## Classification Method

Each decision applies the P12-B verified impact: V2/shared dependency stays protected; registered legacy reachability requires entry-surface disablement; active startup coupling requires P12-E decoupling; migration and documentation history are preserved; insufficient bundle/operational or unstable-source proof remains unresolved.

## V2 Protected Boundary

`FE-001`, `FE-002`, `BE-001`, `AI-003`, `SC-001`, and `WK-001` are `KEEP_V2`: active workspace, V2 backend package, rebuild prompts/schemas, and the default V2 queue consumer.

## Shared Infrastructure Boundary

`INFRA-001` through `INFRA-003` are `KEEP_SHARED`: authentication/ownership, database mechanics, and evidence storage. `BE-002` is `SPLIT_SHARED_AND_LEGACY`: preserve the FastAPI host/V2 registration while removing legacy router registrations only after their routes are retired.

## Migration and Historical Preservation Rules

`DB-001` through `DB-003` are `PRESERVE_MIGRATION_HISTORY`. The two-head graph and legacy ancestry/FK/downgrade history make all migration records protected. `DOC-001` and `DOC-002` are `PRESERVE_DOCUMENTATION_HISTORY`.

## Compatibility Decisions

`FE-003` is `KEEP_COMPATIBILITY_TEMPORARILY`. It preserves `/sessions`, `/sessions/new`, and `/sessions/[sessionId]` redirects plus middleware behavior. Later removal requires product-owner approval to retire bookmarked URLs and a route-traffic/compatibility decision.

## Direct Safe-Removal Candidates

None. `FE-004`, `FE-005`, and `WK-002` lack the required production bundle or operational-command proof, so each remains `UNRESOLVED` rather than becoming a direct-removal candidate.

## Route-Dependent Removal Candidates

`FE-006`, `FE-007`, `BE-003`, `BE-004`, `BE-005`, `BE-007`, `BE-008`, and `TEST-002` are `REMOVE_AFTER_LEGACY_ROUTE_DISABLE`. Required preconditions and focused tests are in the JSON: disable `/evaluations`, legacy `/api` families, and action/analysis-job producers before deleting their components/tests; leave deployment and migrations untouched.

## V2 Decoupling Candidates

`AI-001`, `AI-004`, `SC-002`, `WK-003`, and `INFRA-004` are `DECOUPLE_FROM_V2_FIRST`. Exact dependency: the active worker startup invokes legacy provider validation and `PromptRegistry`; backend startup loads the production schema manifest; runtime retains old validation helpers; Compose supplies legacy provider configuration. P12-E must give V2 direct Gemini-only startup ownership, prove zero callers, and run focused startup tests before legacy provider/prompt/schema/config cleanup.

## Mixed Shared/Legacy Items

`BE-002`: retain FastAPI host, V2/auth/health routing; later remove legacy registrations. `BE-006`: retain V2/shared metadata and preserve migrations while isolating old runtime models. `TEST-001` and `TEST-003`: preserve V2 coverage/fixtures and split legacy subsets only after their production owners are removed. `FE-007` has an E6 module-split precondition if its common client mechanics are proven needed.

## Unresolved Items

`FE-004` and `FE-005` require a production build-manifest/import-closure check. `WK-002` requires confirmation that no alternate worker command or operator invocation exists. `AI-002` remains unresolved because unrelated working-tree changes prevent stable committed-source closure. None may enter P12-D/P12-E first.

## Per-ID Classification Table

| Classification | IDs |
| --- | --- |
| KEEP_V2 | FE-001, FE-002, BE-001, AI-003, SC-001, WK-001 |
| KEEP_SHARED | INFRA-001, INFRA-002, INFRA-003 |
| PRESERVE_MIGRATION_HISTORY | DB-001, DB-002, DB-003 |
| PRESERVE_DOCUMENTATION_HISTORY | DOC-001, DOC-002 |
| REMOVE_AFTER_LEGACY_ROUTE_DISABLE | FE-006, FE-007, BE-003, BE-004, BE-005, BE-007, BE-008, TEST-002 |
| DECOUPLE_FROM_V2_FIRST | AI-001, AI-004, SC-002, WK-003, INFRA-004 |
| SPLIT_SHARED_AND_LEGACY | BE-002, BE-006, TEST-001, TEST-003 |
| KEEP_COMPATIBILITY_TEMPORARILY | FE-003 |
| UNRESOLVED | FE-004, FE-005, AI-002, WK-002 |

| Classification | Count |
| --- | ---: |
| KEEP_V2 | 6 |
| KEEP_SHARED | 3 |
| PRESERVE_MIGRATION_HISTORY | 3 |
| PRESERVE_DOCUMENTATION_HISTORY | 2 |
| SAFE_REMOVAL_CANDIDATE | 0 |
| REMOVE_AFTER_LEGACY_ROUTE_DISABLE | 8 |
| DECOUPLE_FROM_V2_FIRST | 5 |
| SPLIT_SHARED_AND_LEGACY | 4 |
| KEEP_COMPATIBILITY_TEMPORARILY | 1 |
| UNRESOLVED | 4 |
| **Total** | **36** |

## P12-D Preliminary Removal Groups

- D1: FE-004/FE-005 only after their unresolved bundle proof closes.
- D2: FE-006 plus evaluation subset of FE-007, after `/evaluations` is disabled.
- D3: BE-003 legacy API route disablement, then its frontend consumers.
- D4: BE-008 Partial Exit/old actions, after `/api/actions` disablement; remove related tests later.
- D5: BE-005 legacy analysis-job producer; WK-002 only after its unresolved operational check closes.
- D6: BE-004/BE-007 after their route callers reach zero.
- D7: evaluation backend subset under BE-003/BE-007 after its route disablement.
- D8: TEST-002 and legacy fixture subsets only after production owners are removed.

## P12-E Preliminary Decoupling Groups

- E1: replace active worker legacy provider/prompt/schema startup validation with direct V2 Gemini-only ownership (`AI-001`, `AI-004`, `SC-002`).
- E2: remove V2 reliance on `PROVIDER_ORDER`, fallback/DeepSeek selection once E1 passes (`AI-001`, `INFRA-004`).
- E3: retain `prompts/rebuild` and `schemas/rebuild/v1`; prove no startup reliance on production assets.
- E4: split `WK-003` to preserve only V2 loop/consumer/processor and shared database/storage startup.
- E5: split `BE-002` after legacy route groups finish.
- E6: split `FE-007` only if common HTTP mechanics are retained after legacy consumers reach zero.

## Required Execution Order

1. Preserve V2/shared/migration/history records and compatibility redirects.
2. Resolve FE-004, FE-005, WK-002, and AI-002 evidence gaps.
3. Disable legacy frontend/API entry surfaces, then remove their route-dependent components, services, and tests in bounded D groups.
4. Execute E1–E4 to eliminate V2 startup coupling to legacy provider/prompt/schema/runtime configuration.
5. Split mixed host/model/client/test records after callers reach zero.
6. Run focused V2 startup/flow checks, then P12-F.

## Risk and Blocker Summary

Critical classifications are the active V2 core, migrations, shared infrastructure, registered legacy routes/actions/jobs, and active worker startup coupling. The blockers are missing frontend bundle/operational proof and the unrelated `AI-002` edit. No removal is authorized for unresolved items.

## Focused Verification Requirements

P12-D requires route enumeration, import closure, affected legacy test removal, and V2 flow smoke tests per group. P12-E requires worker/backend startup tests, provider/prompt/schema import closure, redacted Compose validation, and final zero-caller evidence before cleanup. Migrations remain untouched in every group.

## Explicit No-Code-Change Statement

No production source, test, prompt, schema, migration, Docker, environment, deployment, package file, route, startup behavior, provider configuration, or P12-A/P12-B artifact changed. No item was deleted, moved, renamed, disabled, deprecated, or refactored; no Gemini request occurred.

## Final Result

COMPLETED — P12-C supplies an evidence-bound action map only. P12-D remains the next authorized execution task.
