# VD-1 — Current UI Visual Audit

## 1. Audit Metadata

| Field | Value |
| --- | --- |
| Task | VD-1 — Current UI Visual Audit |
| Audit date | 2026-08-01 |
| Branch | `main` |
| Commit | `aa06998391d85165b76a851c0b3e0316c4373506` |
| Working-tree state | Pre-existing changes were present before this audit; see below. |
| Inspection method | Direct repository inspection of frontend source, tests, package/configuration files, and authoritative documents. Runtime probes were read-only. |
| Runtime inspection status | NOT AVAILABLE: ports 3000, 3001, and backend health at localhost:8000 were not listening. |
| Authoritative sources read | `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`; `docs/TradePilot AI Rebuild — Detailed Task Plan.md`; `docs/rebuild/AUTHORITATIVE_TASK_LEDGER.md`. |

Pre-existing working-tree state included modified backend files, modified frontend files (`frontend/src/features/analysis/request-analysis.tsx`, `frontend/src/lib/api/trade-sessions.ts`, `frontend/src/types/trade-session.ts`), untracked documentation, migration, script, skill, and local-storage paths. These changes were not modified or cleaned.

## 2. Executive Summary

The frontend is a Next.js 16.2.10 / React 19.2.4 application using the App Router, Tailwind CSS v4 utility classes, a small global stylesheet, and no visible component library or design-token layer. The V2 Trade Workspace is implemented as a single `/trade-workspace` surface with a session list and create form on the left and a selected session workspace on the right. Legacy `/sessions` routes redirect to that workspace.

The current workspace has broad lifecycle coverage in code: session creation, three-file initial evidence upload, initial analysis processing/completion/failure/retry, explicit BUY/WAIT/SKIP decisions, WAIT Updates, Position Updates, CLOSE, and a chronological timeline. The strongest current state is functional separation of user actions and AI result presentation; the main visual weakness is the amount of information rendered as successive generic bordered cards with limited visual differentiation between facts, advisory output, actions, and history.

Verified code findings include dense one-line JSX in major workspace files, repeated ad-hoc utility classes, inconsistent container/card conventions across current feature families, and a decision panel where BUY and WAIT are not rendered symmetrically in the visible action row. Mobile behavior is not runtime-verified. Potential mobile risks include long forms, repeated analysis cards, timeline density, long filenames/text, and header navigation wrapping.

The audit is limited to repository evidence. It does not claim runtime appearance, authenticated content behavior, or pixel-level viewport behavior.

## 3. Frontend Architecture and Styling Inventory

| Area | Repository path | Current responsibility | Styling method | Responsive mechanism | Notes |
| --- | --- | --- | --- | --- | --- |
| Framework/application | `frontend/package.json`, `frontend/src/app/` | Next.js App Router pages and layouts | Tailwind CSS v4 imported in `globals.css` | Tailwind responsive variants | Next 16.2.10, React 19.2.4. |
| Root shell | `frontend/src/app/layout.tsx` | HTML language, metadata, auth provider, global header, main wrapper | Tailwind classes plus `globals.css` | `flex`, `min-h-full`, responsive descendants | Root sets `lang="id"`; no theme/provider is present. |
| Global CSS | `frontend/src/app/globals.css` | Tailwind import and system sans font stack | Plain CSS | None beyond descendant utility classes | No CSS variables, tokens, custom breakpoints, or component primitives observed. |
| Authentication | `frontend/src/lib/auth-context.tsx`, `frontend/src/middleware.ts`, `frontend/src/app/login/page.tsx` | Auth state, login, protected navigation behavior | Tailwind utilities | Login form has `w-full max-w-sm`; no viewport-specific runtime evidence | Login copy and labels are Indonesian. |
| Global navigation | `frontend/src/components/header.tsx` | Brand link, session link, email, logout/login | Tailwind utilities | Fixed `h-14`, `flex`, `gap-4`, `px-4`; no explicit breakpoint | Email plus links may compete for width on narrow screens; potential risk only. |
| Workspace shell | `frontend/src/features/trade-workspace/trade-workspace.tsx` | Loads sessions, selection, create/list/detail composition | Tailwind utilities | `max-w-6xl`, `grid`, `lg:grid-cols-[260px_1fr]`, `gap-6` | Below `lg`, list/create and detail stack. Runtime not verified. |
| Workspace session list | `frontend/src/features/trade-workspace/session-list.tsx` | Selects session and displays ticker/company/status | Tailwind utilities | Full-width buttons; no explicit breakpoint | Status uses raw status text rather than shared visual status component. |
| Create-session form | `frontend/src/features/trade-workspace/create-session.tsx` | Ticker, company, note, create action | Tailwind utilities | `sm:grid-cols-2` for two inputs | Inline JSX and generic border/input styling. |
| Session workspace | `frontend/src/features/trade-workspace/workspace.tsx` | Header, decisions, evidence, analysis, updates, timeline | Tailwind utilities | `sm:grid-cols-2` for facts/BUY fields; flex-wrap action/header areas | Major surface contains many conditional lifecycle branches. |
| Session header | `frontend/src/features/trade-workspace/workspace.tsx` and `frontend/src/features/trade-session/session-header.tsx` | Ticker/company/status/facts in current and alternate feature paths | Tailwind utilities | `flex-wrap`, `sm:grid-cols-2` in current workspace | Two session-header implementations exist in the repository. |
| Evidence | `frontend/src/features/trade-workspace/workspace.tsx`; `frontend/src/features/evidence/*` | Initial three-file upload and separate evidence list/upload cards | Tailwind utilities | Mostly single-column; `EvidenceCard` image uses `w-full` and `max-h-40` | Two evidence implementations are present: V2 workspace-local and shared/legacy evidence feature. |
| Initial analysis | `frontend/src/features/trade-workspace/result.tsx`, `frontend/src/features/analysis/initial-analysis-view.tsx` | Displays structured analysis sections | Tailwind utilities | Section cards stack vertically | Two result/view families exist. |
| WAIT Update | `frontend/src/features/trade-workspace/wait-update.tsx`, `frontend/src/features/analysis/watching-update-view.tsx` | Input, processing, result, retry | Tailwind utilities | Forms use grid/flex utilities; no explicit viewport test | V2 workspace component is the relevant current flow. |
| Position Update/CLOSE | `frontend/src/features/trade-workspace/position-update.tsx`, `frontend/src/features/trade-actions/*` | Position facts, updates, close form/result | Tailwind utilities | `sm:grid-cols-2` for data; `flex-wrap` in summary | Current V2 flow has direct close handling; other action-modal components remain. |
| Timeline | `frontend/src/features/trade-workspace/timeline.tsx` | Builds and renders chronological event cards | Tailwind utilities | Event detail grids switch at `sm`; text uses `break-words` | Left border plus stacked cards; runtime readability not verified. |
| API/types | `frontend/src/features/trade-workspace/api.ts`, `frontend/src/features/trade-workspace/types.ts`, `frontend/src/lib/api/*`, `frontend/src/types/*` | Fetches data and defines UI state contracts | Not applicable | Not applicable | Both V2 and older API/type families are present. |
| Icons | `frontend/src/` | No icon package or icon component was found in the inspected frontend inventory | Text labels and Unicode check mark in evidence status | Not applicable | Icon approach is effectively text/Unicode, not a shared icon system. |
| Typography | `frontend/src/app/globals.css`, utility classes | System sans stack; Tailwind font-size/weight utilities | Plain CSS plus Tailwind | No typography scale/token file observed | No externally loaded font source observed. |

## 4. Route and Screen Inventory

| Route or surface | Entry component | Supporting components | User purpose | Observed states | Inspection confidence |
| --- | --- | --- | --- | --- | --- |
| `/` | `frontend/src/app/page.tsx` | `useAuth`, `Link` | Public landing page or redirect for authenticated user | Loading/user returns null; public marketing copy; login link | High, code verified |
| `/login` | `frontend/src/app/login/page.tsx` | `AuthProvider` | Authenticate | Empty validation, submitting, invalid-credentials error, success redirect | High, code/tests |
| `/trade-workspace` | `frontend/src/app/trade-workspace/page.tsx` → `TradeWorkspace` | Session list, create form, session workspace | Main authenticated multi-session workspace | Loading/error/no selected session/session selected; lifecycle branches below | High, code/tests |
| `/sessions` | `frontend/src/app/sessions/page.tsx` | Next redirect | Legacy route compatibility | Redirects to `/trade-workspace` | High, code verified |
| `/sessions/new` | `frontend/src/app/sessions/new/page.tsx` | Next redirect | Legacy route compatibility | Redirects to `/trade-workspace` | High, code verified |
| `/sessions/[sessionId]` | `frontend/src/app/sessions/[sessionId]/page.tsx` | Next redirect | Legacy detail route compatibility | Redirects to `/trade-workspace` | High, code verified |
| `/evaluations` | `frontend/src/app/evaluations/page.tsx` | `evaluation-dashboard` | Evaluation/dashboard surface | Repository page exists; not part of current Trade Workspace path | Medium, code inventory only |
| Shared/legacy analysis surface | `frontend/src/features/analysis/*` | Initial, watching, open-position, closing and history views | Older or parallel analysis presentation | Tests cover multiple analysis views and states | Medium, relation to active route not runtime verified |

## 5. Trade Workspace Structural Map

Current top-to-bottom composition in `frontend/src/features/trade-workspace/trade-workspace.tsx` and `workspace.tsx`:

1. Root page container: centered `max-w-6xl` with horizontal padding and vertical spacing.
2. Workspace title: “Initial Analysis Workspace” and a short description.
3. Two-column area at `lg`: left rail for `TradeWorkspaceSessionList` and `CreateTradeSession`; selected session content on the right. Below `lg` the grid becomes one column.
4. Session header: ticker, company name, status pill, status/active decision/created/updated/closed facts, and optional initial note.
5. Global error and decision success/error notices.
6. Decision panel when available: WAIT button, SKIP form, and BUY form. The visible source renders WAIT in the initial flex row; the BUY and SKIP forms follow as separated sections.
7. WAIT Update panel when the session is WAITING or when WAIT processing has been activated.
8. Chronological session history/timeline.
9. Position summary/update/CLOSE panel for `OPEN_POSITION` and `CLOSED`.
10. Initial evidence upload form for a draft without known evidence, followed by “Evidence siap” and Initial Analysis submission once evidence exists.
11. Initial Analysis processing, failure/retry, and completed result presentation.

The source order places timeline before the Position Update panel and before the initial evidence/analysis result branches. This is a factual DOM/render order observation, not a recommendation.

**Session header and facts.** `workspace.tsx` shows ticker as small muted text, company name as the largest heading in the card, and status as a neutral gray pill. Facts are a five-item definition list; active decision is derived from the latest decision in the aggregate.

**Evidence.** Draft initial evidence uses three required image file inputs: orderbook, three-month chart, and six-month chart. The workspace stores evidence in parent state. The separate `features/evidence` family renders evidence cards, status, timestamps, image previews, and upload/replace behavior.

**Analysis result.** `result.tsx` maps the thirteen required result keys to individually bordered white articles, with whitespace-preserving body text. The code does not visibly distinguish user-owned facts from Gemini output within those cards.

**Decisions and actions.** Availability comes from `getAvailableActions`. BUY, WAIT, and SKIP remain explicit client actions. BUY requires five facts plus optional note; SKIP requires a reason plus optional note; WAIT is a direct action. Disabled labels indicate saving/submission.

**WAIT Updates.** `wait-update.tsx` supports observation period, current price, timestamp, orderbook file, optional note, upload, submit, polling, completed result, failed result, pending recovery, and manual retry. It preserves a separate WAIT Update surface from Position Updates.

**Position Updates.** `position-update.tsx` supports position summary, current price, period, timestamp, orderbook, optional note, polling, result cards, and close flow. The close result displays close price, timestamp, reason, realized PnL, and note.

**Close action.** CLOSE is rendered as a button on the open position summary and opens a form in the Position Update component. The code path does not require Gemini for close.

**History/timeline.** `timeline.tsx` creates events for initial evidence, initial analysis, WAIT decisions, WAIT Updates, BUY decisions, Position Updates, SKIP decisions, and CLOSE, sorts by timestamp, and renders each as a bordered card with a left rule. Session-created and position-created are not separate event types in this renderer.

## 6. Lifecycle UI-State Matrix

| State | Visible UI | Available actions | Primary component | Confidence | Issue or risk |
| --- | --- | --- | --- | --- | --- |
| DRAFT / new session | Session header; create form; no-selection empty state; initial upload form when no evidence | Create session; choose three files; upload | `create-session.tsx`, `workspace.tsx` | High, code/tests | Initial evidence form appears late in the render sequence after timeline and other branches; verified code observation. |
| DRAFT / initial evidence present | “Evidence siap”, file count, Initial Analysis submission | Request Initial Analysis | `workspace.tsx` | High, code/tests | Evidence summary is count-only in this path; potential clarity risk for file-level confirmation. |
| ANALYZING / processing | Processing message; polling after request; disabled submission while busy | Wait for completion | `workspace.tsx` | High, code/tests | Processing UI is a single text card; verified presentation is minimal. |
| ANALYZED / initial analyzed | Initial Analysis result cards and decision panel | BUY, WAIT, SKIP | `workspace.tsx`, `result.tsx` | High, code/PRD | BUY form and SKIP form are expanded inline rather than modal as task plan describes; verified implementation difference. |
| WAITING | Initial result/history; WAIT Update panel; decision controls from availability | WAIT Update; BUY; WAIT; SKIP where API returns them | `workspace.tsx`, `wait-update.tsx` | High, code/tests | Repeated analysis and action surfaces can create a long vertical page; potential mobile/information-density risk. |
| OPEN_POSITION | Header/history; position summary; Position Update form/results; CLOSE | Position Update; CLOSE | `workspace.tsx`, `position-update.tsx` | High, code/tests | Position summary uses green-tinted container while other lifecycle states are mostly neutral; verified style inconsistency. |
| CLOSED | Header/history; closed position summary; close result; Position Update component read path | No new business action intended; read path remains rendered | `workspace.tsx`, `position-update.tsx` | High, code/tests | `PositionUpdatePanel` is still mounted for CLOSED for read/close-summary behavior; runtime appearance not verified. |
| CLOSED_SKIPPED | Status available in labels/types and timeline SKIP event | No new action expected after status refresh | `workspace.tsx`, `timeline.tsx` | Medium, code | No explicit dedicated closed-skipped summary component was found in the active workspace; potential clarity risk. |
| Failure | Red alert card, sanitized message, retry button for initial/WAIT paths; errors for general loads/actions | Manual retry where implemented | `workspace.tsx`, `wait-update.tsx`, `safe-error.ts` | High, tests | Failure styling is repeated ad hoc red/amber utility markup rather than a shared feedback primitive. |
| Retry | Busy label such as “Mencoba…” and fresh pending/processing state | Retry explicitly | `workspace.tsx`, `wait-update.tsx` | High, tests | Retry state is code-supported; exact runtime transition was not exercised. |

Only PRD-approved business statuses are used in the V2 workspace type/label map: `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, and `CLOSED_SKIPPED`. Request statuses are separately represented as `PENDING`, `PROCESSING`, `COMPLETED`, and `FAILED`.

## 7. Responsive and Mobile Audit

Runtime viewport inspection was not available. The following is a code-based assessment and is explicitly not a claim of rendered pixel behavior.

| Viewport category | Code-observed behavior | Assessment |
| --- | --- | --- |
| Narrow mobile, approximately 360–390 px | Workspace grid is one column below `lg`; create inputs remain one column below `sm`; action/header groups use `flex-wrap`; BUY/fact grids remain one column below `sm`. | POTENTIAL RISK: long card stack, repeated result sections, and form labels can produce high scroll cost. Horizontal overflow was not runtime verified. |
| Wider mobile, approximately 414–430 px | Same breakpoint behavior; full-width form controls and file inputs are used. | POTENTIAL RISK: header email/navigation and long filenames may wrap; no explicit compact navigation state exists. |
| Tablet, approximately 768 px | At 768px, `sm` two-column fact/field grids apply, while the workspace remains one column until `lg`. | POTENTIAL RISK: two-column field grids may be tight with long labels/values; workspace list and detail are still vertically ordered. |
| Desktop, approximately 1280–1440 px | `lg` two-column workspace with fixed 260px left column and flexible detail; outer max width 1152px. | ACCEPTABLE CURRENT STATE in code: a coherent desktop grid is defined. Actual visual balance not runtime verified. |

Additional responsive observations:

- Navigation has no explicit breakpoint, collapse, or overflow handling in `header.tsx`.
- Timeline cards use `break-words`; event details use one column below `sm` and two columns at `sm`.
- Analysis results are vertically stacked articles, which avoids table overflow but increases page length.
- Evidence previews use `w-full`, `object-contain`, and `max-h-40` in `EvidenceCard`; initial draft upload has no preview before submission in the active workspace-local form.
- Buttons generally use horizontal padding and do not declare minimum touch dimensions. Touch-target suitability is NOT OBSERVABLE from runtime and is a POTENTIAL RISK from the small text/button classes used in places such as header/logout and retry controls.
- No sticky/fixed action panel, modal, or mobile-specific panel behavior was found in the inspected active workspace code.

## 8. Visual Consistency Findings

| Area | Classification | Evidence | Impact | Confidence |
| --- | --- | --- | --- | --- |
| Typography | VERIFIED ISSUE | `globals.css` supplies only a system sans stack; sizes/weights are applied ad hoc across `workspace.tsx`, `result.tsx`, `timeline.tsx`, and other features. | Similar information roles do not have a documented shared type treatment. | High, code |
| Color | VERIFIED ISSUE | Neutral, blue, amber, green, and red utility classes are repeated directly in feature files; status header uses neutral gray for every business status. | Status meaning and action emphasis are not consistently differentiated in code. | High, code |
| Spacing | VERIFIED ISSUE | Cards use varying `p-3`, `p-4`, `p-5`, `p-8`; gaps vary across `space-y-3`, `space-y-4`, `gap-2`, `gap-3`, `gap-6`. | Repeated workspace sections may not share a stable rhythm. | High, code |
| Borders and radius | VERIFIED ISSUE | Active workspace commonly uses `rounded-xl`, while shared evidence uses `rounded-lg` and some loading/error sections use no explicit radius. | Container language is inconsistent across adjacent surfaces. | High, code |
| Elevation | VERIFIED ISSUE | Some cards use `shadow-sm`, adjacent cards such as evidence-ready and timeline states do not. | Elevation does not consistently communicate grouping or priority. | High, code |
| Icons | ACCEPTABLE CURRENT STATE | No icon package or icon system is used; evidence requirement uses a text/Unicode check mark. | Low visual complexity, but no scalable icon vocabulary is established. | High, code |
| Cards and containers | VERIFIED ISSUE | Initial analysis, WAIT result, Position Update result, timeline, evidence, and status panels are mostly generic bordered white cards. | High information density is presented as repeated same-weight blocks. | High, code |
| Buttons | VERIFIED ISSUE | Primary blue, neutral dark, amber outline, and gray header controls are authored locally; WAIT is an outline button while BUY is only prominent inside its later form. | Action hierarchy is not consistently visible from the initial decision row. | High, code |
| Forms | VERIFIED ISSUE | Inputs repeatedly use variants such as `rounded-lg border`, `rounded-md border`, or bare `border p-2`; labels/field spacing are locally authored. | Form controls lack a shared visual grammar. | High, code |
| Statuses | VERIFIED ISSUE | `statusLabels` maps business statuses to text, but the header pill always uses `bg-zinc-100`; session list uses raw status text. | Lifecycle distinctions are less visually legible than the product flow requires. | High, code |
| Feedback states | VERIFIED ISSUE | Loading, errors, success, pending recovery, and retry markup is repeated in `workspace.tsx`, `wait-update.tsx`, `position-update.tsx`, and analysis feature files. | Feedback semantics are similar but not visually standardized. | High, code/tests |

No runtime-only visual finding is recorded as verified.

## 9. Usability and Information-Hierarchy Findings

- **What appears first:** In the selected session, the header and facts appear before actions, evidence, and analysis result in the source order. In the overall workspace, the session list and create form share the top-level area with the selected detail.
- **Ticker and status visibility:** Ticker is muted small text, company name is the dominant heading, and status is a neutral pill. The ticker is visible but not the strongest identifier.
- **Current decision prominence:** The “Keputusan Anda” panel appears before the timeline, but only WAIT is rendered in the immediate button row; BUY and SKIP are represented by subsequent forms. This is a VERIFIED hierarchy inconsistency in code.
- **Today’s market facts:** Current price and observation period are fields inside WAIT/Position Update forms and timeline details; no separate current-facts summary is present in the active workspace source.
- **Trading plan clarity:** Trading plan is displayed as one of the repeated analysis result cards. It is not structurally separated from other Gemini output in `result.tsx`, `wait-update.tsx`, or `position-update.tsx`.
- **User-owned facts vs Gemini output:** User-owned session/position facts are shown in header/position definition lists, while Gemini output is shown in result cards. The source does not add a common “advisory” label or shared ownership treatment to the result card family. This is a VERIFIED presentation gap, not a product-logic defect.
- **Chronology:** `buildTimelineEvents` explicitly sorts events by timestamp and renders a history heading, which is an ACCEPTABLE CURRENT STATE for chronological intent. The active timeline does not separately render session-created and position-created event types.
- **Next available action:** The API controls action availability, but the visual action panel is not a shared component and action prominence differs by branch. This is a VERIFIED consistency issue.
- **Cognitive load:** Repeated analysis output sections, history cards, and forms are all vertically stacked. This is a POTENTIAL RISK for long sessions and narrow screens; actual scroll burden is not runtime verified.

## 10. Component Disposition Matrix

| Component or area | Repository path | Classification | Factual rationale | Suggested future task | Behavior-preservation warning |
| --- | --- | --- | --- | --- | --- |
| Workspace shell | `frontend/src/features/trade-workspace/trade-workspace.tsx` | RESTRUCTURE | Owns the list/detail composition and desktop breakpoint; multiple responsibilities are composed here. | VD-3, VD-6 | Preserve one selected session and session isolation. |
| Session list | `frontend/src/features/trade-workspace/session-list.tsx` | REFINE | Small focused component with selected/empty states, but raw status text and limited metadata. | VD-3, VD-6 | Do not change session selection or status data. |
| Create session form | `frontend/src/features/trade-workspace/create-session.tsx` | REFINE | Functional focused form with responsive two-field grid and local styling. | VD-3, VD-5 | Preserve ticker/company required fields and optional note. |
| Session header | `frontend/src/features/trade-workspace/workspace.tsx`; `frontend/src/features/trade-session/session-header.tsx` | RESTRUCTURE | Duplicate header implementations and dense fact display. | VD-3, VD-4 | Preserve ticker, company, status, dates, active decision, and note semantics. |
| Initial evidence upload | `frontend/src/features/trade-workspace/workspace.tsx` | REFINE | Required three-file flow is clear in code but visually minimal and count-based after upload. | VD-5 | Preserve all three evidence requirements and evidence preservation. |
| Shared evidence section/cards | `frontend/src/features/evidence/*` | NEEDS_RUNTIME_VERIFICATION | Separate feature family includes preview, upload/replace, batch, and legacy grouping behavior. | VD-5, VD-7 | Do not alter evidence ownership, immutability, or lifecycle rules. |
| Initial Analysis result | `frontend/src/features/trade-workspace/result.tsx` | RESTRUCTURE | Correct section mapping but repeated generic cards and no visible advisory grouping. | VD-5 | Preserve all thirteen Indonesian user-facing sections and Gemini advisory authority. |
| Decision panel | `frontend/src/features/trade-workspace/workspace.tsx` | RESTRUCTURE | BUY/WAIT/SKIP are conditional but not visually symmetrical; forms are inline. | VD-3, VD-5 | BUY, WAIT, and SKIP must remain explicit user decisions; no automatic action. |
| WAIT Update | `frontend/src/features/trade-workspace/wait-update.tsx` | REFINE | Lifecycle states and retry are implemented in one focused component; output is card-heavy. | VD-5, VD-7 | Keep WAIT Updates distinct from Position Updates and preserve repeated updates. |
| Position Update | `frontend/src/features/trade-workspace/position-update.tsx` | REFINE | Includes position facts, update form, results, and polling; styling is locally authored. | VD-5, VD-7 | Preserve user-owned position facts and open-position eligibility. |
| CLOSE flow | `frontend/src/features/trade-workspace/position-update.tsx` | REFINE | Close form/result exists and is user-triggered; current visual integration is nested in position flow. | VD-5 | CLOSE remains a user action and must not call Gemini automatically. |
| Timeline | `frontend/src/features/trade-workspace/timeline.tsx` | RESTRUCTURE | Chronology is explicit, but every event is a similar card and some product events are not separate types. | VD-4, VD-7 | Preserve complete chronological history and distinguish SKIP from CLOSE. |
| Feedback/error patterns | `frontend/src/features/trade-workspace/safe-error.ts`, `workspace.tsx`, `wait-update.tsx`, `position-update.tsx` | REFINE | Sanitization and retry behavior exist, but visual markup is repeated. | VD-5, VD-7 | Preserve failure recovery, manual retry, and no duplicate request behavior. |
| Legacy analysis/action families | `frontend/src/features/analysis/*`, `frontend/src/features/trade-actions/*`, `frontend/src/features/trade-session/*` | NEEDS_RUNTIME_VERIFICATION | Repository contains parallel component families whose active route ownership is not fully observable without runtime. | VD-2, VD-7 | Do not remove or change behavior during visual work without an approved scope. |

## 11. Prioritized Audit Findings

### P0 — Blocks safe visual redesign

- **VD1-F01 — Ambiguous component ownership.** Classification: `VERIFIED ISSUE`. Surface: shared/legacy versus V2 frontend feature families. Evidence: parallel `frontend/src/features/analysis/*`, `frontend/src/features/evidence/*`, `frontend/src/features/trade-actions/*`, `frontend/src/features/trade-session/*`, and active `frontend/src/features/trade-workspace/*`; legacy routes redirect but component reachability was not runtime verified. Impact: later visual work could refine an inactive or duplicate surface. Confidence: High for duplicate families, Medium for runtime ownership. Recommended future task: VD-2, then VD-3.

### P1 — High-impact visual or mobile problem

- **VD1-F02 — Decision hierarchy is asymmetric.** Classification: `VERIFIED ISSUE`. Surface: `frontend/src/features/trade-workspace/workspace.tsx`. Evidence: WAIT renders in the immediate flex action row; BUY and SKIP are later inline forms separated by borders. Impact: the three approved post-analysis decisions do not have equal initial visual treatment. Confidence: High. Recommended future task: VD-3/VD-5.
- **VD1-F03 — Long vertical information stack.** Classification: `POTENTIAL RISK`. Surface: `workspace.tsx`, `result.tsx`, `wait-update.tsx`, `position-update.tsx`, `timeline.tsx`. Evidence: repeated result articles, forms, and timeline cards are all stacked; no runtime viewport was available. Impact: mobile scroll burden and action discoverability may degrade in long sessions. Confidence: High for code shape, Low for rendered impact. Recommended future task: VD-3/VD-6.
- **VD1-F04 — Status styling is neutral and inconsistent.** Classification: `VERIFIED ISSUE`. Surface: `workspace.tsx`, `session-list.tsx`. Evidence: status header uses the same `bg-zinc-100` pill for all statuses; session list prints raw status text. Impact: lifecycle state is harder to scan visually. Confidence: High. Recommended future task: VD-2/VD-4.

### P2 — Important consistency or usability problem

- **VD1-F05 — No shared visual primitives or tokens.** Classification: `VERIFIED ISSUE`. Surface: `globals.css` and feature files. Evidence: no CSS variables/token file/component library; repeated local class combinations with varying padding/radius/shadow. Impact: visual drift across workspace sections and future maintenance cost. Confidence: High. Recommended future task: VD-2.
- **VD1-F06 — Advisory output is not visibly separated from user facts.** Classification: `VERIFIED ISSUE`. Surface: `result.tsx`, `wait-update.tsx`, `position-update.tsx`, `workspace.tsx`. Evidence: Gemini result sections are generic cards; user facts are separate lists but no common advisory/authority treatment is present. Impact: users may need more effort to distinguish recommendation from confirmed trade data. Confidence: High for implementation, product impact is visual inference. Recommended future task: VD-2/VD-5.
- **VD1-F07 — Feedback markup is duplicated.** Classification: `VERIFIED ISSUE`. Surface: workspace, WAIT, Position Update, and analysis feature files. Evidence: repeated red/amber/neutral cards and local retry/loading labels. Impact: processing, failed, pending, and completed states may not form one consistent feedback language. Confidence: High. Recommended future task: VD-5/VD-7.

### P3 — Final-polish issue

- **VD1-F08 — Icon and typography systems are absent.** Classification: `VERIFIED ISSUE`. Surface: `globals.css`, evidence status markup, all workspace feature files. Evidence: system font only, utility-level type choices, Unicode check mark, no icon package/component. Impact: later polish lacks a shared baseline. Confidence: High. Recommended future task: VD-2/VD-7.

## 12. Product and Behavior Guardrails for Future Visual Work

The following are direct preservation rules from the authoritative PRD and approved workflow:

- One session equals one trading story and one possible trade.
- BUY, WAIT, and SKIP remain explicit user decisions; Gemini recommendations remain advisory.
- WAIT Updates remain distinct from Position Updates.
- CLOSE remains a user action and does not require Gemini.
- User-owned trading facts remain authoritative: ticker, company, notes, evidence, current price, timestamps, decisions, position facts, and closure facts.
- Gemini output remains advisory and must not overwrite user-owned facts.
- Skipped sessions remain distinguishable from closed trades: `CLOSED_SKIPPED` is not `CLOSED`, and no position/close-price/PnL facts are introduced for SKIP.
- Complete chronological history remains preserved and readable; prior evidence, analysis, decisions, and updates are not overwritten.
- No automatic order execution or automatic BUY, WAIT, SKIP, or CLOSE action may be introduced.
- No additional business statuses or analysis types may be added. Approved business statuses are `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, and `CLOSED_SKIPPED`; approved analysis types are `INITIAL_ANALYSIS`, `WAIT_UPDATE`, and `POSITION_UPDATE`.
- Gemini remains the only AI provider; no provider routing or fallback may be introduced.
- User-facing Gemini analysis remains in Indonesian.

## 13. Audit Limitations and Unknowns

- Local frontend and backend services were unavailable at the time of audit; read-only probes to localhost:3000, localhost:3001, and localhost:8000/health/ready failed to connect.
- No authenticated browser session or fixture-backed runtime was available. No viewport screenshots or direct visual observations were made.
- The four requested viewport categories were assessed from breakpoint/source code only, not rendered inspection.
- Reachability of parallel legacy feature families from the current production route was not proven by runtime.
- Persistent data, authentication behavior beyond source/tests, and actual evidence image dimensions were not inspected.
- Tests were inspected but not run, in accordance with the documentation-only request and prohibition on full-suite execution.
- No real Gemini request was made, and no runtime record was created or changed.

## 14. VD-1 Acceptance Checklist

- [x] The three Source Lock documents were read directly from the repository.
- [x] Branch, commit, and pre-existing working-tree state were recorded.
- [x] The relevant frontend surface was mapped.
- [x] Styling and responsive mechanisms were identified from actual files.
- [x] Current Trade Workspace structure was documented.
- [x] Relevant lifecycle UI states were mapped without inventing business statuses.
- [x] Lack of safe runtime inspection was explicitly documented.
- [x] Findings distinguish verified issues, potential risks, acceptable states, and unknowns.
- [x] Major components received preliminary disposition classifications.
- [x] Product behavior guardrails were extracted from the authoritative PRD.
- [x] Exactly one new audit document was created by this task.
- [x] No production code, style, test, configuration, dependency, API, schema, prompt, or runtime record was changed by this task.
- [x] No real Gemini request was made.
- [x] VD-2 was not started.

## 15. Final VD-1 Result

**PASS WITH DOCUMENTED LIMITATIONS**

The repository and authoritative documents support a factual code-based audit. Runtime viewport inspection was unavailable, so runtime-only visual conclusions remain documented as limitations or potential risks.

**No redesign or implementation is authorized by this audit.**
