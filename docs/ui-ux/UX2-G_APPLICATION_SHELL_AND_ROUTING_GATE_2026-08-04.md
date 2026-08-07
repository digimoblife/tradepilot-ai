# UX2-G — Phase Gate — Application Shell and Routing

## 1. Metadata and Repository Baseline

- Date: 4 August 2026
- Official task: `UX2-G — Phase Gate — Application Shell and Routing`
- Branch inspected: `main`
- Starting commit: `d20ca8e5ee283b55c8e8572f77984539c448c06c`
- Final gate status: **PASS**
- Canonical redesign target: TradePilot AI V2 guided-session frontend backed by `trade_sessions_v2` and `backend/app/trade_workspace/`.
- Working-tree condition: mixed pre-existing modified and untracked application, test, migration, skill, documentation, diagnostic, and local-storage paths. Accepted UX2 changes remain identifiable from unrelated work.
- Prerequisites: UX0-G **PASS**, UX1-G **PASS**, and the accepted UX2.1–UX2.4 task results are **PASS**.
- Sequencing: UX2-G was the next official task. UX3.1 or later implementation had not started when this gate was evaluated.

## 2. Sources Reviewed

Authoritative product and task sources:

1. `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
2. `docs/TradePilot AI PRD Amendment.md`
3. `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
4. `docs/redesign/TradePilot_AI_UI_UX_PRD_Guided_Session_Experience_and_Archive_FINAL.docx` — read from actual document contents
5. `docs/redesign/TradePilot_AI_UI_UX_Detailed_Task_Plan_FINAL.docx` — read from actual document contents

Authority, audit, and prior-gate records:

6. `docs/ui-ux/UX0.1_AUTHORITATIVE_SOURCE_LOCK_AND_REQUIREMENT_MATRIX_2026-08-04.md`
7. `docs/ui-ux/UX0.2_CURRENT_MAIN_BRANCH_UI_UX_IMPACT_AUDIT_2026-08-04.md`
8. `docs/ui-ux/UX0-G_AUTHORITY_AND_REPOSITORY_ALIGNMENT_GATE_2026-08-04.md`
9. `docs/ui-ux/UX1-G_ARCHIVE_BACKEND_FOUNDATION_GATE_2026-08-04.md`

Required repository procedures:

10. `.agent-skills/tradepilot-source-lock/SKILL.md`
11. `.agent-skills/tradepilot-focused-testing/SKILL.md`

Accepted UX2 implementation and configuration:

12. `frontend/src/app/layout.tsx`
13. `frontend/src/app/page.tsx`
14. `frontend/src/app/login/page.tsx`
15. `frontend/src/app/trade-workspace/page.tsx`
16. `frontend/src/app/sessions/page.tsx`
17. `frontend/src/app/sessions/new/page.tsx`
18. `frontend/src/app/sessions/archived/page.tsx`
19. `frontend/src/app/sessions/[sessionId]/page.tsx`
20. `frontend/src/app/sessions/[sessionId]/analysis/page.tsx`
21. `frontend/src/app/sessions/[sessionId]/history/page.tsx`
22. `frontend/src/app/sessions/_components/route-placeholder.tsx`
23. `frontend/src/app/sessions/_components/route-session-placeholder.tsx`
24. `frontend/src/middleware.ts`
25. `frontend/src/lib/auth-context.tsx`
26. `frontend/src/components/header.tsx`
27. `frontend/src/features/sessions/use-route-session.ts`
28. `frontend/src/features/trade-workspace/api.ts`
29. `frontend/src/lib/api/client.ts`
30. `frontend/src/lib/api/errors.ts`
31. `frontend/src/types/api.ts`
32. `frontend/package.json`
33. `frontend/package-lock.json`
34. `frontend/next.config.ts`
35. `frontend/tsconfig.json`
36. `frontend/vitest.config.ts`
37. Refreshed `frontend/.next/routes-manifest.json` build evidence

Focused tests:

38. `frontend/src/__tests__/route-skeletons.test.tsx`
39. `frontend/src/__tests__/route-session-recovery.test.tsx`
40. `frontend/src/__tests__/login.test.tsx`
41. `frontend/src/__tests__/cutover.test.tsx`
42. `frontend/src/components/header.test.tsx`
43. `frontend/src/features/sessions/use-route-session.test.tsx`
44. `frontend/src/features/trade-workspace/api-url.test.ts`
45. `frontend/src/lib/api/client.test.ts`
46. `frontend/src/features/trade-workspace/trade-workspace.test.tsx`

Backend contract reference only:

47. `backend/app/trade_workspace/api/routes/trade_sessions.py`
48. `backend/app/trade_workspace/api/schemas.py`

## 3. Scope Diff Confirmation

UX2-G performed source comparison, accepted-diff inspection, route-manifest review, backend-contract reference inspection, focused frontend tests, targeted lint, TypeScript checking, scoped diff checking, and one production build because the prior route manifest predated the final UX2.4 route integration.

Only this gate record was added by UX2-G. No application, test, API, schema, migration, dependency, configuration, lifecycle, provider, evidence, refactor, cleanup, or UX3.1 work was performed. No backend test, broad frontend suite, commit, or real Gemini request was performed.

## 4. UX2.1 Verification

**PASS.**

- Real page shells exist for `/sessions`, `/sessions/new`, `/sessions/archived`, `/sessions/{session_id}`, `/sessions/{session_id}/analysis`, and `/sessions/{session_id}/history`.
- Static paths `new` and `archived` remain distinct from the dynamic session path.
- Approved routes no longer blindly redirect to `/trade-workspace`.
- Session shells provide safe parent navigation and receive the route session identifier.
- The refreshed production build lists all approved routes and the framework not-found route.
- No lifecycle component, workflow action, or list-data integration was moved into the new shells.
- `/trade-workspace` remains mounted and functional as a separate page during transition.

## 5. UX2.2 Verification

**PASS.**

- Authenticated `/` replaces to `/sessions`.
- Normal successful login pushes `/sessions`.
- Middleware protects `/sessions` and every nested Sessions path using the existing session-cookie/backend-verification behavior.
- Middleware preserves the requested pathname in `next` for unauthenticated or invalid-session redirects.
- Login accepts only the approved protected same-origin path forms, preserves safe query strings, and rejects external, protocol-relative, malformed, public, fragment-bearing, looping, and unsupported destinations.
- `/trade-workspace` remains an allowed intended destination during transition.
- Login payload, authentication API behavior, logout behavior, and auth context were not changed by UX2.

## 6. UX2.3 Verification

**PASS.**

- `RootLayout` remains the single global owner of `Header`.
- Authenticated primary navigation contains only Sessions and Archive.
- Sessions links to `/sessions`; Archive links to `/sessions/archived`.
- `usePathname()` drives active state, with `aria-current="page"` on the active destination.
- Archive does not activate Sessions; nested non-Archive session routes activate Sessions; legacy `/trade-workspace` activates neither.
- Account identity and logout remain accessible, and unauthenticated navigation remains reduced to brand plus login.
- The mobile grid uses min-width-safe tracks, truncates long identity text on larger layouts, hides it visually on small layouts, and keeps 44px-equivalent minimum interactive heights.
- Tests verify DOM/keyboard order from brand through Sessions, Archive, and logout, plus unchanged logout navigation.

## 7. UX2.4 Verification

**PASS.**

- Session Detail, Analysis, and History obtain `sessionId` from route params and share `useRouteSession(sessionId)`.
- The loader calls canonical `GET /api/v2/trade-sessions/{session_id}` through the shared API client.
- Backend inspection confirms the route is authenticated, owner-scoped through `get_owned`, and returns the canonical `TradeSessionResponse` including `archived_at`.
- A previous list selection is not required; direct mount and remount/refresh issue route-owned backend loads.
- Malformed UUIDs resolve to a controlled not-found state without an API request.
- Loading, success, not-found, authentication-required, and generic failure states are explicit and do not fabricate protected data.
- `AbortController`, propagated `AbortSignal`, and request-generation checks cancel or ignore stale work during navigation and unmount.
- The hook clears previously successful session data synchronously when navigation begins, preventing session A from flashing during session B loading.

## 8. Approved Route Matrix

| Route | UX2 responsibility | Auth | Recovery source | Gate result |
|---|---|---|---|---|
| `/login` | Focused authentication entry | Public | Login/auth context | PASS |
| `/sessions` | Default post-login shell | Protected | Route itself; list data deferred to UX3.1 | PASS |
| `/sessions/new` | Dedicated creation shell | Protected | Route itself; form deferred to UX3.4 | PASS |
| `/sessions/archived` | Archived-list shell | Protected | Route itself; archive list deferred to UX6.2 | PASS |
| `/sessions/{session_id}` | Session Summary shell | Protected | URL ID plus canonical V2 GET | PASS |
| `/sessions/{session_id}/analysis` | Analysis shell | Protected | URL ID plus canonical V2 GET | PASS |
| `/sessions/{session_id}/history` | History shell | Protected | URL ID plus canonical V2 GET | PASS |
| `/trade-workspace` | Preserved legacy transition entry | Protected | Existing legacy/V2 workspace state | PASS |

The refreshed Next.js route output includes `/`, `/_not-found`, `/login`, all six approved Sessions routes, `/trade-workspace`, and the pre-existing `/evaluations` route.

## 9. Authentication and Intended-Route Handling

**PASS.** Protected Sessions paths cannot obtain session data without backend-authenticated, owner-scoped API access. Middleware retains the existing server verification path and sends unauthenticated/invalid sessions to login with the intended pathname. Safe login recovery returns users only to approved protected application destinations; fallback is always `/sessions`.

The inherited middleware behavior allows a page shell to render when the authentication backend is unreachable, deferring the failure to client/API handling. This does not expose session data: canonical data requests still require backend authentication and UX2.4 renders a controlled authentication/failure state. It is unchanged behavior, not an UX2 regression or a blocker for UX3.

## 10. Global Navigation and Active-State Behavior

**PASS.** Sessions and Archive are globally reachable for authenticated users, no Dashboard/Trade Workspace primary concept was added, and active state is semantic as well as visual. The brand returns authenticated users to `/sessions`; account and logout remain available. There is one global shell owner and no duplicated route-level header.

## 11. Mobile and Keyboard Behavior

**PASS.** The shared shell uses a compact two-row small-screen grid with min-width-safe content, no fixed shell width, and minimum-height touch targets. Primary navigation remains visible without depending on hover. Focus-visible styles are present on brand, navigation, login, logout, and route back links. Focused tests verify logical source/keyboard order and logout operability. Final cross-screen viewport and accessibility hardening remains correctly assigned to UX7, but no UX2 shell blocker is present.

## 12. Route Recovery and Stale-Request Protection

**PASS.** Route IDs are authoritative. Direct mount and refresh remount load canonical backend state. Invalid IDs avoid unnecessary requests. A 401 maps to authentication-required, a 404 maps to not-found, and other failures map to safe generic failure copy. Rapid A-to-B navigation aborts A, immediately hides A, accepts only the current request generation, and ignores late A success or failure. Unmount abort is also covered.

## 13. Legacy Workflow Preservation

**PASS.** `frontend/src/app/trade-workspace/page.tsx` still renders the existing `TradeWorkspace`; no redirect was added. Existing create-session, session-selection, analysis-result, touch-target, and logout checks remain green. The UX2 route shells do not import or move lifecycle components. Legacy entry-point redirect and old-workflow removal remain deferred to UX8 after parity is proven.

## 14. Business-Behavior Preservation

**PASS.** The UX2 diff is limited to route shells, login destination/safe intended routes, global navigation, route-level canonical GET loading, cancellation plumbing, and focused tests. It adds no session status, transition, action eligibility, analysis type, evidence rule, Archive mutation, provider behavior, queue behavior, persistence behavior, or Gemini call. The V2 backend detail contract was inspected read-only and not changed by UX2-G.

## 15. Focused Test Evidence

Current gate reruns on 4 August 2026:

- Route/auth/shell/legacy group: **5 files passed, 37 tests passed**.
- Route-loader/API/recovery group: **4 files passed, 44 tests passed**.
- Combined focused evidence: **9 files passed, 81 tests passed**.
- Targeted ESLint over the inspected UX2 production and test paths: **PASS**, no output.
- `npm run typecheck`: **PASS**.
- Scoped `git diff --check` over UX2 production and test paths: **PASS**, no output.
- Production build with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`: **PASS** on Next.js 16.2.10; all approved routes emitted.
- Build advisory: Next.js reports the existing `middleware` file convention as deprecated in favor of `proxy`; compilation and route generation still pass. This is non-blocking and does not authorize an out-of-scope migration in UX2-G.
- No backend suite, broad frontend suite, or real Gemini request was run.

The reported per-task evidence is also consistent with current files: UX2.1 24 passed, UX2.2 25 passed, UX2.3 37 passed, UX2.4 loader/API/recovery 50 passed, UX2.4 upstream-preservation 30 passed, and the final hook group 11 passed. The current gate reruns supersede stale route evidence and independently cover the load-bearing behavior.

## 16. Working-Tree and Commit Candidate

The eventual UX2 commit candidate is the following exact 24-file set:

1. `frontend/src/__tests__/cutover.test.tsx`
2. `frontend/src/__tests__/login.test.tsx`
3. `frontend/src/__tests__/route-session-recovery.test.tsx`
4. `frontend/src/__tests__/route-skeletons.test.tsx`
5. `frontend/src/app/login/page.tsx`
6. `frontend/src/app/page.tsx`
7. `frontend/src/app/sessions/[sessionId]/analysis/page.tsx`
8. `frontend/src/app/sessions/[sessionId]/history/page.tsx`
9. `frontend/src/app/sessions/[sessionId]/page.tsx`
10. `frontend/src/app/sessions/_components/route-placeholder.tsx`
11. `frontend/src/app/sessions/_components/route-session-placeholder.tsx`
12. `frontend/src/app/sessions/archived/page.tsx`
13. `frontend/src/app/sessions/new/page.tsx`
14. `frontend/src/app/sessions/page.tsx`
15. `frontend/src/components/header.test.tsx`
16. `frontend/src/components/header.tsx`
17. `frontend/src/features/sessions/use-route-session.test.tsx`
18. `frontend/src/features/sessions/use-route-session.ts`
19. `frontend/src/features/trade-workspace/api-url.test.ts`
20. `frontend/src/features/trade-workspace/api.ts`
21. `frontend/src/lib/api/client.test.ts`
22. `frontend/src/lib/api/client.ts`
23. `frontend/src/middleware.ts`
24. `frontend/src/types/api.ts`

No frontend dependency or configuration file belongs to the UX2 candidate; `package.json`, `package-lock.json`, `next.config.ts`, `tsconfig.json`, and `vitest.config.ts` are unchanged.

All other pre-existing modified/untracked backend, migration, test, AI, unrelated frontend, skill, documentation, diagnostics, script, and `storage/local/` paths are outside the UX2 commit candidate and must remain unstaged. This gate record is a separate UX2-G documentation artifact. No commit was created.

## 17. Conflict and Risk Register

| ID | Finding | Evaluation | Resolution / owner | Status |
|---|---|---|---|---|
| UX2-R1 | Legacy `/trade-workspace` remains available while the new shells are placeholders. | Required transition behavior, not drift. | Preserve until UX8 parity and cutover tasks. | NON_BLOCKING |
| UX2-R2 | Middleware fails open when the backend verifier is unreachable. | Inherited behavior; shell visibility does not grant authenticated owner-scoped session data. | Existing client/API failure handling; any policy change requires separate auth scope. | NON_BLOCKING |
| UX2-R3 | Next.js 16.2.10 deprecates the `middleware` convention. | Build warning only; current middleware compiles and protects configured paths. | Future scoped framework maintenance, not UX2-G. | NON_BLOCKING |
| UX2-R4 | Existing Sessions/create components are present elsewhere in the repository. | UX0.2 identified these as pre-existing targets; `/sessions` remains a placeholder and does not import list data. | UX3.1 begins integration after this gate only. | RESOLVED |
| UX2-R5 | Mixed dirty tree increases staging risk. | UX2 files are exactly enumerated and unrelated paths are separable. | Stage only an approved pathspec in a later authorized commit task. | NON_BLOCKING |
| UX2-R6 | Full viewport/browser and accessibility matrices are not complete. | UX2 shell has focused structural/mobile/keyboard evidence; full hardening belongs to UX7. | Retain UX7.1–UX7.5 scope. | NON_BLOCKING |

No unresolved implementation-affecting conflict prevents UX3 from beginning.

## 18. UX2-G Acceptance Criteria Evaluation

1. **New routes are stable — PASS.** All approved routes exist as real shells, remain protected, render independently, preserve static/dynamic boundaries, support direct URLs, and appear in a successful refreshed production build.
2. **Post-login Sessions route works — PASS.** Authenticated root and normal login resolve to `/sessions`; protected intended routes are safely preserved; unsafe destinations fall back to `/sessions`.
3. **No business behavior has changed — PASS.** UX2 changes presentation/routing and read-only route recovery only; focused legacy tests pass and no lifecycle, evidence, analysis, decision, Archive, provider, queue, or persistence contract changed.

## 19. Final Gate Decision

**PASS.** UX2.1–UX2.4 collectively satisfy the approved Application Shell and Routing gate. Route, authentication, post-login, navigation, direct-link, refresh, mobile-shell, keyboard, route-recovery, stale-request, legacy-preservation, and business-preservation evidence is sufficient. No blocking condition is present.

## 20. Change Confirmation

UX2-G added only:

- `docs/ui-ux/UX2-G_APPLICATION_SHELL_AND_ROUTING_GATE_2026-08-04.md`

No existing application, test, API, schema, migration, dependency, configuration, skill, or documentation file was edited by this task. Build output remained ignored. No guided session migration, broad suite, commit, UX3.1 work, or real Gemini request occurred.

## 21. Next Official Task

`UX3.1 — Sessions List Data Integration`
