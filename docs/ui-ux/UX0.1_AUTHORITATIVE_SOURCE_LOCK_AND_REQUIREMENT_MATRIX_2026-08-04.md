# UX0.1 — Authoritative Source Lock and Requirement Matrix

**Date:** 4 August 2026
**Official task:** `UX0.1 — Authoritative Source Lock and Requirement Matrix`
**Status:** PASS
**Scope Diff:** Documentation and mapping only. No repository behavior, product contract, route, schema, API, migration, test, or configuration changes.

## 1. Source Lock and Document Metadata

### Documents reviewed directly

1. `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md` — authoritative product definition.
2. `docs/TradePilot AI PRD Amendment.md` — authoritative BUY/WAIT/SKIP amendment.
3. `docs/TradePilot AI Rebuild — Detailed Task Plan.md` — authoritative existing implementation sequence.
4. `docs/redesign/TradePilot_AI_UI_UX_PRD_Guided_Session_Experience_and_Archive_FINAL.docx` — authoritative redesign product definition.
5. `docs/redesign/TradePilot_AI_UI_UX_Detailed_Task_Plan_FINAL.docx` — authoritative redesign implementation sequence.

The two DOCX sources were read from their actual document content.

### Skills reviewed directly

- `.agent-skills/tradepilot-source-lock/SKILL.md`
- `.agent-skills/tradepilot-focused-testing/SKILL.md`

### Repository baseline

- Branch inspected: `main`.
- Inspection was limited to confirming the branch, authoritative paths, and broad V2 implementation targets.
- Repository behavior is implementation evidence only. It is not product authority and cannot override the sources above.
- The redesign target is the V2 session entity/table `trade_sessions_v2` under `backend/app/trade_workspace/`.
- Legacy `trade_sessions`, legacy models/services/routes, and legacy `TradeSessionStatus.ARCHIVED` behavior are non-authoritative and outside redesign implementation scope unless an official future task explicitly requires compatibility or cutover work.

## 2. Authoritative Source Hierarchy

| Precedence | Source | Role | Conflict rule |
|---|---|---|---|
| 1 | TradePilot AI PRD v2 | Product definition, lifecycle, AI, evidence, and ownership authority | Overrides repository behavior and lower-priority sources. |
| 2 | TradePilot AI PRD Amendment | Explicit BUY/WAIT/SKIP amendment | Overrides the base PRD only where it explicitly amends it. |
| 3 | Existing TradePilot AI Detailed Task Plan | Existing implementation sequence and task boundaries | Preserves established task order and scope. |
| 4 | UI/UX PRD — Guided Session Experience and Archive | Approved redesign product behavior | Supplements, but does not replace, unrelated product contracts. |
| 5 | UI/UX Detailed Task Plan — Guided Session Experience and Archive | Approved redesign tasks, dependencies, gates, and verification | Defines redesign execution order; one prompt executes one official task. |
| 6 | Current repository | Implementation evidence and broad target confirmation | Never defines product behavior. Conflicts are recorded, not silently worked around. |

An implementation-affecting conflict that cannot be resolved by this precedence is `BLOCKED`. A repository conflict resolved by the explicit V2/legacy boundary is recorded as `RESOLVED_BY_AUTHORITY`.

## 3. Product Invariants

- Gemini is the only AI provider; production model remains `gemini-3.1-flash-lite`.
- Gemini is advisory only. User decisions and execution facts remain user-owned.
- Canonical V2 persisted statuses are `DRAFT`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, and `CLOSED_SKIPPED`. `ANALYZING` is only the authoritative transient/internal processing state.
- Approved transitions remain exactly those defined by PRD v2; no new session status or transition may be introduced.
- User decisions remain `BUY`, `WAIT`, and `SKIP`.
- Analysis types remain `INITIAL_ANALYSIS`, `WAIT_UPDATE`, and `POSITION_UPDATE`.
- Initial evidence remains exactly one `ORDERBOOK`, one `CHART_3_MONTH`, and one `CHART_6_MONTH` set.
- Request processing, durable queue behavior, retry behavior, ownership, and authorization remain unchanged.
- The experience is guided, multi-page, mobile-first, user-friendly, and progressive-disclosure based.
- Each screen has one primary purpose and one dominant primary action.
- Archive is organizational metadata, not a session status.
- Only terminal `CLOSED` and `CLOSED_SKIPPED` V2 sessions may be archived.
- Archive uses nullable metadata such as `archived_at`, preserves terminal status and all related records, and does not delete or reopen anything.
- Restore clears archive metadata only, returns the session to the Completed list, and leaves it terminal and read-only.
- Archived sessions remain readable/read-only and are excluded from the default non-archived Sessions list.
- Canonical implementation target: `trade_sessions_v2` and `backend/app/trade_workspace/`.

## 4. Requirement Traceability Matrix

Status values in this document are matrix labels only: `MAPPED`, `RESOLVED_BY_AUTHORITY`, or `NON_BLOCKING_AMBIGUITY`. They are not product statuses.

| ID | Category | Approved requirement | Authoritative source / section | Canonical rule | Intended implementation area | Official task / title | Gate | Focused verification | Dependency | Status / notes |
|---|---|---|---|---|---|---|---|---|---|---|
| AUTH-001 | Authority | Product authority is PRD v2, then Amendment, existing task plan, redesign PRD, redesign task plan, then repository evidence. | UX0.1 source lock; redesign PRD §4.3 | Repository cannot override product documents. | `docs/ui-ux/` governance | `UX0.1 — Authoritative Source Lock and Requirement Matrix` | `UX0-G — Phase Gate — Authority and Repository Alignment` | Source-to-row review | None | MAPPED |
| AUTH-002 | Authority | Every implementation prompt rereads sources, preserves exact official task data, and contains Source Lock and Scope Diff. | Source Lock skill; redesign task plan §1 | One prompt executes one official task only. | Task prompts and task records | `UX0.1 — Authoritative Source Lock and Requirement Matrix`; subsequent official tasks | All gates | Prompt-structure audit | UX0-G | MAPPED |
| AUTH-003 | Authority | Repository behavior is evidence only; conflicts are recorded and unresolved implementation conflicts are BLOCKED. | PRD v2 §1; Source Lock skill | Do not infer product requirements from existing code. | All redesign work | `UX0.1 — Authoritative Source Lock and Requirement Matrix`; `UX0.2 — Current Main-Branch UI/UX Impact Audit` | UX0-G | Conflict-register review | None | MAPPED |
| AUTH-004 | Authority | Official task IDs, titles, order, boundaries, acceptance criteria, dependencies, and gates remain unchanged. | Existing task plan; redesign task plan Appendix A/C | No rename, reorder, merge, split, or reinterpretation. | Documentation and task governance | `UX0.1 — Authoritative Source Lock and Requirement Matrix`; `UX8.5 — Documentation and Traceability Finalization` | UX8-G | Task-index comparison | None | MAPPED |
| GLOBAL-001 | Global experience | The product uses a guided multi-page journey from Login through Sessions, creation, evidence, analysis, decisions, updates, Close, Archive, and Archived Sessions. | Redesign PRD §§7–8 | Do not place the full workflow on one default page. | Frontend route architecture | `UX2.1 — New Route Skeletons`; `UX8.3 — Focused Full-Flow Regression` | UX8-G | Fixture-backed journey traversal | UX2-G, UX5-G, UX6-G | MAPPED |
| GLOBAL-002 | Global experience | Successful login lands on `/sessions`. | Redesign PRD §10.1; AC-01 | Authentication behavior otherwise remains unchanged. | Login navigation | `UX2.2 — Post-Login Sessions Redirect` | UX2-G | Fresh login and protected-route checks | UX2.1 | MAPPED |
| GLOBAL-003 | Global experience | Each screen has one clear purpose and one dominant primary action. | Redesign PRD §§5, 11, 14 | Progressive disclosure; no unrelated forms by default. | Shared screen composition | `UX2.3 — Global Navigation Shell`; `UX4.3 — Session Summary Content`; UX5 tasks | UX5-G | Screen-state and action-visibility review | UX2-G, UX4-G | MAPPED |
| GLOBAL-004 | Global experience | One session is opened at a time; Summary, Analysis, History, forms, and Archive are separated. | Redesign PRD §§7, 11; AC-06 | Session context is stable and route recoverable. | Session shell and nested routes | `UX4.4 — In-Session Navigation`; `UX5.11 — Complete Session History View` | UX5-G | Direct navigation and layout review | UX4-G | MAPPED |
| GLOBAL-005 | Global experience | The experience is mobile-first, user-friendly, touch-safe, readable, and free of required horizontal scrolling. | Redesign PRD §§3, 13, 16; AC-17/18 | Mobile layout first; desktop may enhance without changing workflow. | Global styling and screen layouts | `UX7.1 — Mobile Responsive Foundation`; `UX7.2 — Mobile Forms and Upload Refinement` | UX7-G | Mobile narrow/standard and desktop viewport matrix | Screen completion | MAPPED |
| GLOBAL-006 | Global experience | Accessibility includes keyboard operation, logical focus, semantic headings/labels, safe dialogs, and non-color status meaning. | Redesign PRD §16; AC-18/20 | Accessibility cannot change business behavior. | Components, forms, dialogs, navigation | `UX7.3 — Accessibility Semantics and Keyboard Flow` | UX7-G | Keyboard, focus, labels, error, contrast checks | UX5 completion | MAPPED |
| GLOBAL-007 | Global experience | User-facing UI and analysis display are Indonesian; canonical internal/API/schema/task terminology remains unchanged. | Redesign PRD §14.1; AC-21 | Translation is presentation-only. | UI copy and labels | `UX7.4 — Indonesian UI Copy Consistency` | UX7-G | Copy inventory and canonical-value audit | UX5 completion | MAPPED |
| GLOBAL-008 | Global experience | Loading, empty, submitting, processing, success, validation, server failure, unauthorized, not-found, retry, and interrupted states are understandable. | Redesign PRD §15; AC-20 | Never fabricate success or show unrelated forms while unresolved. | Shared state presentation | `UX7.5 — System-State Visual Consistency` | UX7-G | State fixture matrix | Screen completion | MAPPED |
| ROUTE-001 | Routes | `/login` is authentication. | Redesign PRD §7.2 | Protected access remains enforced. | `frontend/src/app/login/` | `UX2.1 — New Route Skeletons` | UX2-G | Authenticated/unauthenticated route checks | UX0-G | MAPPED |
| ROUTE-002 | Routes | `/sessions` is the default non-archived Sessions list. | Redesign PRD §7.2, §11.2; AC-01/02 | Only owned, non-archived sessions appear. | Sessions route and V2 list API | `UX3.1 — Sessions List Data Integration` | UX3-G | List filtering and ownership fixtures | UX1-G, UX2-G | MAPPED |
| ROUTE-003 | Routes | `/sessions/new` is a dedicated creation screen. | Redesign PRD §7.2, §11.4; AC-03 | Creation is not embedded in the list. | New-session route/form | `UX3.4 — Dedicated Create Session Form` | UX3-G | Required fields, validation, cancel/back | UX2-G | MAPPED |
| ROUTE-004 | Routes | `/sessions/{session_id}` is Session Summary and current next action. | Redesign PRD §7.2, §11.5 | Load from URL, auth context, and backend state. | Session Detail route | `UX4.1 — Session Header and Identity Context`; `UX4.2 — Backend-Authoritative Current-Step Model` | UX4-G | Direct URL, refresh, not-found, unauthorized | UX3-G | MAPPED |
| ROUTE-005 | Routes | `/sessions/{session_id}/analysis` is analysis history/detail. | Redesign PRD §7.2, §11.7 | Preserve canonical analysis payload and chronology. | Analysis route/view | `UX5.3 — Analysis Reading Experience` | UX5-G | Latest-first and historical analysis fixtures | UX4-G | MAPPED |
| ROUTE-006 | Routes | `/sessions/{session_id}/history` is complete chronological history. | Redesign PRD §7.2, §11.14; AC-06/15 | History remains separate from Archive metadata by default. | History route/view | `UX5.11 — Complete Session History View` | UX5-G | Chronology, long content, mobile layout | UX4-G | MAPPED |
| ROUTE-007 | Routes | `/sessions/archived` lists archived terminal sessions. | Redesign PRD §7.2, §12.5; AC-14 | Only owned archived sessions appear. | Archived route and V2 list API | `UX6.2 — Archived Sessions List` | UX6-G | Empty/populated/ownership/list separation | UX1-G, UX4-G | MAPPED |
| ROUTE-008 | Routes | Direct URL and refresh recover the correct session without duplicate submissions; legacy `/trade-workspace` redirect waits for parity. | Redesign PRD §10.4, §20; AC-19 | Backend state, not temporary selected-session state, is authoritative. | Route loaders and cutover | `UX2.4 — Route-Level State Recovery Foundation`; `UX8.1 — Legacy Workspace Dependency Audit`; `UX8.2 — Legacy Entry-Point Redirect` | UX8-G | Direct URL, refresh, back, legacy redirect checks | UX2-G, UX5-G | MAPPED |
| SESSION-001 | Sessions list | Sessions list shows only non-archived sessions owned by the authenticated user. | Redesign PRD §11.2; AC-02 | Archived metadata excludes a session from default list. | V2 repository/API and Sessions UI | `UX1.3 — Session List Archive Filtering`; `UX3.1 — Sessions List Data Integration` | UX3-G | Non-archived/archived and cross-owner fixtures | UX1-G | MAPPED |
| SESSION-002 | Sessions list | List items show ticker, company name, user-facing status, next stage/action, and last-updated time. | Redesign PRD §11.2 | Status display must not invent lifecycle values. | Session card/list | `UX3.2 — Sessions List Card and Status Presentation` | UX3-G | All canonical statuses, long names, narrow viewport | UX2-G | MAPPED |
| SESSION-003 | Sessions list | UI groupings are Needs Attention, In Progress, and Completed only as visual groupings. | Redesign PRD §11.2, Appendix B | Groupings are not persisted statuses. | Sessions grouping mapper | `UX3.3 — Sessions UI Grouping` | UX3-G | Every canonical status mapped once | UX3.1 | MAPPED |
| SESSION-004 | Sessions list | Empty, loading, error, retry, unauthorized, and no-session states are clear; list does not load guided session forms/full analysis. | Redesign PRD §§11.2–11.3, §15 | Empty state presents Create New Session; no dashboard expansion. | Sessions page/state components | `UX3.1 — Sessions List Data Integration`; `UX7.5 — System-State Visual Consistency` | UX7-G | State fixtures and list payload inspection | UX2-G | MAPPED |
| SESSION-005 | Sessions list | Each item has one clear Open Session action. | Redesign PRD §11.2 | Action navigates without changing session state. | Session card/navigation | `UX3.2 — Sessions List Card and Status Presentation` | UX3-G | Open action and back navigation | UX3.1 | MAPPED |
| CREATE-001 | Creation | Dedicated Create Session form contains required ticker/Stock Code and company name, plus optional initial note. | PRD v2 §9; Redesign PRD §11.4; AC-03 | Preserve canonical validation/normalization and fields only. | V2 creation route/service | `UX3.4 — Dedicated Create Session Form` | UX3-G | Required/optional field and validation checks | UX2-G | MAPPED |
| CREATE-002 | Creation | Successful creation navigates directly to the new Session Detail. | Redesign PRD §11.4; AC-04 | Use returned canonical session identifier. | Create mutation/navigation | `UX3.5 — Create Success Navigation` | UX3-G | Create-to-detail and refresh checks | UX3.4 | MAPPED |
| CREATE-003 | Creation | Duplicate submission is prevented and valid values survive recoverable validation errors. | Redesign PRD §11.4, §15; AC-20 | No duplicate session or invented defaults. | Form state/mutation handling | `UX3.4 — Dedicated Create Session Form` | UX3-G | Validation preservation and duplicate-submit check | UX2-G | MAPPED |
| DETAIL-001 | Session Detail | Detail shows ticker, company name, canonical display status, timestamps, and initial note when present. | Redesign PRD §11.5 | Canonical internal values remain available to implementation; display may be Indonesian. | Session header/summary | `UX4.1 — Session Header and Identity Context` | UX4-G | All statuses, long company names, archived context | UX3-G | MAPPED |
| DETAIL-002 | Session Detail | Current Step/Next Action derives from backend-authoritative status and action availability. | Redesign PRD §§5, 11.5, 17; AC-05 | Frontend cannot invent eligibility or session state. | V2 detail aggregate/current-step mapper | `UX4.2 — Backend-Authoritative Current-Step Model` | UX4-G | Status/action matrix, missing/failed state fixtures | UX3-G | MAPPED |
| DETAIL-003 | Session Detail | Summary shows latest relevant result, key position data only when present, compact recent activity, and History link. | Redesign PRD §11.5 | No unsupported calculations or analysis reinterpretation. | Summary composition | `UX4.3 — Session Summary Content` | UX4-G | Optional data and long-content checks | UX4.2 | MAPPED |
| DETAIL-004 | Session Detail | In-session navigation exposes Ringkasan, Analisis, and Riwayat without losing session context. | Redesign PRD §22.2 | Navigation does not submit or mutate lifecycle. | Nested session navigation | `UX4.4 — In-Session Navigation` | UX4-G | Direct tabs/routes, back, mobile navigation | UX4.1 | MAPPED |
| DETAIL-005 | Session Detail | Default Summary does not render every guided session form and complete timeline simultaneously. | Redesign PRD §11.5, §11.14; AC-06 | One relevant active task at a time. | Session Detail composition | `UX4.3 — Session Summary Content`; `UX4-G — Phase Gate — Session Detail Foundation` | UX4-G | Default-screen composition review | UX4.2 | MAPPED |
| LIFE-001 | Initial Evidence | DRAFT exposes only the approved Initial Evidence step when eligible. | PRD v2 §§5, 10; Redesign PRD §9, §11.6 | Exactly one ORDERBOOK, CHART_3_MONTH, CHART_6_MONTH set. | V2 evidence route/service and focused UI | `UX5.1 — Initial Evidence Focused Surface` | UX5-G | Required set, missing set, duplicate-set fixtures | UX4-G | MAPPED |
| LIFE-002 | Initial Evidence | Analysis submission stays disabled until required evidence exists; selection and analysis submission are distinct. | PRD v2 §10; Redesign PRD §11.6; AC-07 | No second initial set or replacement unless separately approved. | Evidence form/action | `UX5.1 — Initial Evidence Focused Surface` | UX5-G | Validation and duplicate-initial-set checks | UX4-G | MAPPED |
| LIFE-003 | Initial Evidence | Filenames, upload progress, validation errors, processing, completion, and failure are safe and readable on mobile. | Redesign PRD §11.6, §§13–15 | No horizontal overflow or fabricated success. | Evidence UI/state handling | `UX5.1 — Initial Evidence Focused Surface`; `UX7.2 — Mobile Forms and Upload Refinement` | UX7-G | Long filenames, mobile upload, failure/retry | UX4-G | MAPPED |
| LIFE-004 | Initial Analysis | Initial Analysis displays the canonical Indonesian sections and never creates a position. | PRD v2 §11; Redesign PRD §11.7 | Preserve canonical payload and advisory meaning. | Analysis view and V2 read path | `UX5.2 — Initial Analysis Processing Recovery`; `UX5.3 — Analysis Reading Experience` | UX5-G | Canonical fixture rendering and no-position boundary | UX5.1 | MAPPED |
| LIFE-005 | Processing | Analysis processing is recoverable by durable request state, with one polling owner and no duplicate request after refresh. | PRD v2 §11.3; Redesign PRD §15.1; AC-19 | Failure remains request-level; no new permanent business status. | Request recovery/polling owner | `UX5.2 — Initial Analysis Processing Recovery` | UX5-G | Refresh during processing, completed/failed/retry fixtures | UX4-G | MAPPED |
| LIFE-006 | Analysis | Analysis view shows latest analysis by default and prior Initial/WAIT/Position analyses chronologically. | Redesign PRD §11.7; AC-06/15 | Do not generate conclusions or unsupported scores in frontend. | Analysis route/view | `UX5.3 — Analysis Reading Experience` | UX5-G | Latest/history fixtures, missing fields, mobile wrapping | UX4.4 | MAPPED |
| LIFE-007 | Decisions | After Initial Analysis and after successful WAIT analysis, BUY, WAIT, and SKIP remain legitimate explicit user choices. | PRD v2 §12; Amendment §§1–2, 4.5; AC-08 | Gemini may recommend but cannot persist/execute a decision. | Decision surface and V2 decision services | `UX5.4 — Decision Surface — BUY, WAIT, SKIP` | UX5-G | All decision branches, disabled/ineligible actions | UX5.3 | MAPPED |
| LIFE-008 | BUY | BUY collects only approved entry price, quantity, entry time, stop loss, target price, and optional note; creates exactly one user-owned position and transitions to OPEN_POSITION. | PRD v2 §13; Amendment §3 | BUY does not trigger Gemini automatically. | BUY form/action | `UX5.4 — Decision Surface — BUY, WAIT, SKIP`; `UX5.7 — Open Position Summary and Actions` | UX5-G | Valid/invalid fields, duplicate submit, position boundary | UX5.3 | MAPPED |
| LIFE-009 | WAIT | WAIT creates no position, transitions to WAITING, and exposes approved WAIT Update behavior. | PRD v2 §14; Amendment §4; AC-08/09 | Repeated WAIT remains auditable. | WAIT decision and WAITING summary | `UX5.4 — Decision Surface — BUY, WAIT, SKIP`; `UX5.5 — WAITING Summary and WAIT Update Entry` | UX5-G | WAIT branch and no-position assertion | UX5.3 | MAPPED |
| LIFE-010 | WAIT Update | WAIT Update is available only in WAITING with no position and uses approved observation period, current price, timestamp, orderbook, and optional note. | PRD v2 §15; Amendment §§4.2–4.4; AC-09 | User-entered current price is authoritative; recommendation remains advisory. | WAIT Update form/service | `UX5.5 — WAITING Summary and WAIT Update Entry`; `UX5.6 — WAIT Update Focused Surface` | UX5-G | Eligibility, input validation, request recovery, repeated updates | UX5.4 | MAPPED |
| LIFE-011 | Open Position | OPEN_POSITION shows confirmed position facts, latest Position Update, Update Position primary action, and Close secondary action. | PRD v2 §13; Redesign PRD §11.10 | No BUY/WAIT/SKIP after position opens. | Open-position summary/actions | `UX5.7 — Open Position Summary and Actions` | UX5-G | Position fact preservation and action visibility | UX5.4 | MAPPED |
| LIFE-012 | Position Update | Position Update is available only for OPEN_POSITION with exactly one open position and preserves approved evidence/input/context contracts. | PRD v2 §17; Redesign PRD §11.11; AC-10 | User-owned position facts cannot be replaced by Gemini. | Position Update form/service | `UX5.8 — Position Update Focused Surface` | UX5-G | Eligibility, request processing, failure/retry, refresh | UX5.7 | MAPPED |
| LIFE-013 | Close and terminal | Close uses approved closing fields/confirmation, creates CLOSED only after an open position, and does not automatically archive. | PRD v2 §18; Redesign PRD §11.12; AC-10 | Close is not Delete; terminal session becomes read-only. | Close form/action and terminal detail | `UX5.9 — Close Session Focused Surface`; `UX5.10 — Terminal Session Read-Only Mode` | UX5-G | Close eligibility, confirmation, success, terminal read-only | UX5.8 | MAPPED |
| LIFE-014 | SKIP and terminal | SKIP stores approved reason/note, creates no position, becomes CLOSED_SKIPPED, disables further analysis/evidence, and remains distinguishable from CLOSE. | PRD v2 §16; Amendment §5; AC-08/11 | No close price or realized P/L for skipped session. | SKIP form/action and terminal detail | `UX5.4 — Decision Surface — BUY, WAIT, SKIP`; `UX5.10 — Terminal Session Read-Only Mode` | UX5-G | Skip reason, no-position, terminal read-only checks | UX5.3 | MAPPED |
| LIFE-015 | History | Complete chronological events preserve evidence, requests, analyses, decisions, updates, position, closure, and history. | PRD v2 §4; Redesign PRD §11.14; AC-15 | Archive metadata remains separate from trading timeline by default. | History route/timeline | `UX5.11 — Complete Session History View` | UX5-G | Chronology, long content, mobile vertical stream | UX4.4 | MAPPED |
| ARCH-001 | Archive | Archive is V2 organizational metadata, never a V2 session status; legacy `ARCHIVED` behavior is non-authoritative. | Redesign PRD §12.3; Archive skill; approved decision 3 | Do not introduce or reuse `ARCHIVED` in V2. | V2 session model/service | `UX1.1 — Archive Persistence Model and Migration`; `UX1.2 — Archive Domain Eligibility Service` | UX1-G | Schema/domain review and status-preservation fixtures | UX0-G | MAPPED |
| ARCH-002 | Archive | Only CLOSED and CLOSED_SKIPPED are archivable; DRAFT, ANALYZING, ANALYZED, WAITING, and OPEN_POSITION are not. | Redesign PRD §12.2; AC-12 | Backend enforces eligibility; frontend visibility is not security. | V2 eligibility service/API | `UX1.2 — Archive Domain Eligibility Service`; `UX1.4 — Archive and Restore API Contract` | UX1-G | Every eligible/ineligible status and owner boundary | UX1.1 | MAPPED |
| ARCH-003 | Archive | Archive persists nullable metadata such as `archived_at`, defaults existing/new sessions to non-archived, and preserves terminal status. | Redesign PRD §12.3; AC-13 | Backward-compatible, non-destructive persistence. | `trade_sessions_v2` migration/model | `UX1.1 — Archive Persistence Model and Migration` | UX1-G | Empty/representative migration and default-null checks | UX0-G | MAPPED |
| ARCH-004 | Archive | Archive preserves evidence, analyses, decisions, positions, closure data, requests, and history. | Redesign PRD §12.3; AC-15 | No delete, detach, regenerate, or lifecycle rewrite. | V2 service/repository/API | `UX1.2 — Archive Domain Eligibility Service`; `UX1.5 — Archive Backend Regression Verification` | UX1-G | Related-record integrity and lifecycle regression | UX1.1 | MAPPED |
| ARCH-005 | Archive | Archive confirmation states which session is affected, removes it from the main list, preserves data/history, and can be reversed. | Redesign PRD §12.4 | Archive is not destructive deletion. | Archive action/confirmation UI | `UX6.1 — Archive Confirmation and Action` | UX6-G | Confirmation copy and success navigation | UX1-G, UX4-G | MAPPED |
| ARCH-006 | Archive | Default Sessions query excludes archived sessions; Archived Sessions query includes only archived owned sessions. | Redesign PRD §§11.2, 12.5; AC-02/14 | Preserve owner isolation and ordering. | V2 repository/query/API | `UX1.3 — Session List Archive Filtering` | UX1-G | List separation, owner isolation, direct archived read | UX1.1 | MAPPED |
| ARCH-007 | Archive | Archived Sessions shows terminal status, identity, close/archive times, View Session, and Return to List. | Redesign PRD §12.5 | Archived detail is read-only. | Archived list/detail routes | `UX6.2 — Archived Sessions List`; `UX6.3 — Archived Session Read-Only Detail` | UX6-G | Empty/populated/long-content/mobile checks | UX1-G, UX4-G | MAPPED |
| ARCH-008 | Archive | Archived detail remains directly readable and exposes no analysis, decision, update, or close actions. | Redesign PRD §12.5; AC-15 | Read access remains owner-scoped. | Archived detail route/aggregate | `UX6.3 — Archived Session Read-Only Detail` | UX6-G | Direct URL, refresh, unauthorized, action absence | UX6.2 | MAPPED |
| ARCH-009 | Archive | Restore clears archive metadata only, returns the session to Completed, preserves terminal status, and never re-enables trading. | Redesign PRD §12.6; AC-16 | No reopen, new analysis, or trading history event by default. | V2 restore API/service and UI | `UX1.2 — Archive Domain Eligibility Service`; `UX1.4 — Archive and Restore API Contract`; `UX6.4 — Restore to Completed List` | UX6-G | Restore success/failure, status/action preservation | UX1-G, UX6.3 | MAPPED |
| ARCH-010 | Archive | Archive and Restore follow repository idempotency/error conventions without creating duplicate records. | Archive skill; redesign task plan UX1.2/UX1.4 | No invented silent-success convention. | V2 service/API | `UX1.2 — Archive Domain Eligibility Service`; `UX1.4 — Archive and Restore API Contract` | UX1-G | Repeated Archive/Restore and controlled errors | UX1.1 | MAPPED |
| MOBILE-001 | Mobile | Mobile narrow/standard screens use single-column layouts, safe gutters, readable widths, and no horizontal scrolling. | Redesign PRD §13; AC-17 | Desktop enhancement cannot change workflow order. | Global layout/styles | `UX7.1 — Mobile Responsive Foundation` | UX7-G | 320–375px, 390–430px, desktop | Screen completion | MAPPED |
| MOBILE-002 | Mobile | Primary actions are touch-safe, reachable, and understandable without hover. | Redesign PRD §§13.2, 14.2; AC-18 | Status/action meaning is not hover- or color-dependent. | Buttons/action layout | `UX7.1 — Mobile Responsive Foundation` | UX7-G | Touch-target and hover-independent checks | Screen completion | MAPPED |
| MOBILE-003 | Mobile | Long tickers, company names, notes, filenames, statuses, analysis, numbers, and errors wrap safely. | Redesign PRD §§11.6, 13.2–13.3 | No clipped content or overflow. | Cards, forms, analysis/timeline | `UX7.2 — Mobile Forms and Upload Refinement`; `UX7.5 — System-State Visual Consistency` | UX7-G | Long-content fixtures | UX7.1 | MAPPED |
| MOBILE-004 | Mobile | Forms use visible labels above inputs, suitable mobile input hints, preserved values, safe uploads, and usable keyboard-open dialogs/drawers. | Redesign PRD §§13.2–13.3, 16 | Do not add fields or alter canonical values. | Forms/upload/dialog components | `UX7.2 — Mobile Forms and Upload Refinement` | UX7-G | Mobile keyboard, upload, validation, dialog checks | UX5 completion | MAPPED |
| MOBILE-005 | Accessibility | Keyboard flow, visible focus, semantic headings/landmarks, focus containment/return, and programmatic errors are required. | Redesign PRD §16 | Accessibility fixes cannot change lifecycle or API behavior. | All approved screens/forms | `UX7.3 — Accessibility Semantics and Keyboard Flow` | UX7-G | Keyboard-only and semantic review | UX5 completion | MAPPED |
| MOBILE-006 | Accessibility | Status, error, loading, processing, success, selected, and disabled meaning cannot rely on color alone. | Redesign PRD §§14–16 | Use text/semantics in addition to visual treatment. | Status/action components | `UX7.3 — Accessibility Semantics and Keyboard Flow`; `UX7.5 — System-State Visual Consistency` | UX7-G | Contrast, non-color, live-state checks | UX5 completion | MAPPED |
| COPY-001 | Content | User-facing copy and analysis are Indonesian; technical/API/schema/task terminology stays canonical English where required. | Redesign PRD §14.1; AC-21 | Translate presentation, not persisted values. | UI copy inventory | `UX7.4 — Indonesian UI Copy Consistency` | UX7-G | Copy inventory and canonical terminology audit | UX5 completion | MAPPED |
| COPY-002 | Content | Approved status display mapping is `DRAFT → Sesi Baru`, `ANALYZED → Menunggu Keputusan`, `WAITING → Menunggu`, `OPEN_POSITION → Posisi Terbuka`, `CLOSED → Selesai`, `CLOSED_SKIPPED → Dilewati`. | Approved decision 2; redesign PRD §9 | Indonesian labels are not backend statuses. | Status-label mapping | `UX7.4 — Indonesian UI Copy Consistency` | UX7-G | Label/value separation check | UX4-G | MAPPED |
| COPY-003 | Content | Archive, Restore, Close, and decision confirmations describe outcomes clearly and do not imply deletion or reopening. | Redesign PRD §§11.12, 12.4, 14.3 | Archive/Close are not Delete; Restore is not Reopen. | Confirmation dialogs/copy | `UX6.1 — Archive Confirmation and Action`; `UX6.4 — Restore to Completed List`; `UX7.4 — Indonesian UI Copy Consistency` | UX7-G | Confirmation copy and action semantics | UX6-G | MAPPED |

## 5. Acceptance-Criteria Coverage Matrix

All 22 UI/UX PRD acceptance criteria have planned official task coverage. Gate references below use exact official gate IDs and titles.

| AC | Requirement summary | Official task coverage | Responsible gate | Required evidence | Dependency | Coverage |
|---|---|---|---|---|---|---|
| AC-01 | Login lands on `/sessions`. | `UX2.2 — Post-Login Sessions Redirect` | `UX2-G — Phase Gate — Application Shell and Routing` | Fresh login, authenticated redirect, no auth regression | UX2.1 | COVERED |
| AC-02 | `/sessions` shows only owned, non-archived sessions. | `UX1.3 — Session List Archive Filtering`; `UX3.1 — Sessions List Data Integration` | `UX3-G — Phase Gate — Sessions and Create Session` | Main/archived list separation and cross-owner fixtures | UX1-G, UX2-G | COVERED |
| AC-03 | Dedicated creation screen with Stock Code, Company Name, Note. | `UX3.4 — Dedicated Create Session Form` | UX3-G | Required/optional fields and focused form | UX2-G | COVERED |
| AC-04 | Creation navigates directly to Session Detail. | `UX3.5 — Create Success Navigation` | UX3-G | Returned ID, direct navigation, refresh | UX3.4 | COVERED |
| AC-05 | Detail shows only actions valid for authoritative state. | `UX4.2 — Backend-Authoritative Current-Step Model` | `UX4-G — Phase Gate — Session Detail Foundation` | Canonical status/action fixture matrix | UX3-G | COVERED |
| AC-06 | Default Detail does not show every form and full timeline together. | `UX4.3 — Session Summary Content`; `UX5.11 — Complete Session History View` | `UX5-G — Phase Gate — Guided Session Flow` | Default composition and separated History route | UX4-G | COVERED |
| AC-07 | Initial Evidence set remains exact and non-repeatable. | `UX5.1 — Initial Evidence Focused Surface` | UX5-G | Three-file requirement, duplicate rejection | UX4-G | COVERED |
| AC-08 | BUY/WAIT/SKIP behavior remains unchanged. | `UX5.4 — Decision Surface — BUY, WAIT, SKIP`; `UX5.5 — WAITING Summary and WAIT Update Entry`; `UX5.7 — Open Position Summary and Actions`; `UX5.10 — Terminal Session Read-Only Mode` | UX5-G | Branch behavior, position/no-position, terminal fixtures | UX5.3 | COVERED |
| AC-09 | WAIT Update only in WAITING. | `UX5.5 — WAITING Summary and WAIT Update Entry`; `UX5.6 — WAIT Update Focused Surface` | UX5-G | Eligibility and action visibility | UX5.4 | COVERED |
| AC-10 | Position Update and Close only when allowed for OPEN_POSITION. | `UX5.7 — Open Position Summary and Actions`; `UX5.8 — Position Update Focused Surface`; `UX5.9 — Close Session Focused Surface` | UX5-G | Eligibility, action visibility, close boundary | UX5.7 | COVERED |
| AC-11 | CLOSED/CLOSED_SKIPPED are read-only and expose Archive. | `UX5.10 — Terminal Session Read-Only Mode`; `UX6.1 — Archive Confirmation and Action` | `UX6-G — Phase Gate — Archive Experience` | Both terminal statuses and action matrix | UX1-G, UX5-G | COVERED |
| AC-12 | No non-terminal session can be archived. | `UX1.2 — Archive Domain Eligibility Service`; `UX1.4 — Archive and Restore API Contract` | UX1-G | Every ineligible status rejected backend-side | UX1.1 | COVERED |
| AC-13 | Archive preserves CLOSED/CLOSED_SKIPPED status. | `UX1.1 — Archive Persistence Model and Migration`; `UX1.2 — Archive Domain Eligibility Service`; `UX1.5 — Archive Backend Regression Verification` | UX1-G | Status-before/after and related-record checks | UX0-G | COVERED |
| AC-14 | Archive moves the session from `/sessions` to `/sessions/archived`. | `UX1.3 — Session List Archive Filtering`; `UX1.4 — Archive and Restore API Contract`; `UX6.2 — Archived Sessions List` | UX6-G | Archive-to-list movement and query separation | UX1-G, UX5-G | COVERED |
| AC-15 | Archived sessions remain readable with records intact. | `UX1.5 — Archive Backend Regression Verification`; `UX6.3 — Archived Session Read-Only Detail` | UX6-G | Direct archived read, evidence/analysis/history integrity | UX1-G, UX4-G | COVERED |
| AC-16 | Restore returns session to Completed without reopening. | `UX1.2 — Archive Domain Eligibility Service`; `UX1.4 — Archive and Restore API Contract`; `UX6.4 — Restore to Completed List` | UX6-G | Metadata clearing, terminal status/action preservation | UX6.3 | COVERED |
| AC-17 | Supported mobile layouts do not horizontally scroll. | `UX7.1 — Mobile Responsive Foundation`; `UX7.2 — Mobile Forms and Upload Refinement` | `UX7-G — Phase Gate — Mobile, Accessibility, and Content` | Mobile narrow/standard viewport evidence | Screen completion | COVERED |
| AC-18 | Primary actions are touch-friendly and hover-independent. | `UX7.1 — Mobile Responsive Foundation`; `UX7.3 — Accessibility Semantics and Keyboard Flow` | UX7-G | Touch and keyboard interaction evidence | Screen completion | COVERED |
| AC-19 | Direct URL/refresh recover backend state without duplicate submission. | `UX2.4 — Route-Level State Recovery Foundation`; `UX5.2 — Initial Analysis Processing Recovery`; `UX8.3 — Focused Full-Flow Regression` | `UX8-G — Final Gate — Guided Session Experience and Archive` | Refresh during processing, direct URLs, duplicate-submit checks | UX2-G, UX5-G | COVERED |
| AC-20 | Required loading/validation/processing/success/empty/auth/not-found/failure states exist. | `UX7.5 — System-State Visual Consistency` plus applicable lifecycle tasks | UX7-G | State matrix and retry evidence | Screen completion | COVERED |
| AC-21 | Labels are Indonesian; canonical API values unchanged. | `UX7.4 — Indonesian UI Copy Consistency` | UX7-G | Copy inventory and API-value audit | UX4-G | COVERED |
| AC-22 | No new session status, analysis type, provider, or evidence rule. | `UX0.1 — Authoritative Source Lock and Requirement Matrix`; `UX1.1 — Archive Persistence Model and Migration`; `UX5.4 — Decision Surface — BUY, WAIT, SKIP`; `UX8.5 — Documentation and Traceability Finalization` | `UX8-G — Final Gate — Guided Session Experience and Archive` | Source-lock matrix, contract regression, final traceability | UX0-G | COVERED |

Relevant existing-product acceptance obligations are preserved through AC-07/08/09/10/13/15/16/22 and the focused regression gates; no redesign row authorizes changing them.

## 6. Canonical Terminology vs Indonesian UI Labels

| Concept | Canonical internal term | Canonical value/enum | Approved Indonesian label | Preserve canonical terminology in | Translated UI allowed in | Authority / restrictions |
|---|---|---|---|---|---|---|
| Draft session | Session status | `DRAFT` | `Sesi Baru` | Database, API, schema, task docs, tests | Status badges and explanatory UI | Never persist the Indonesian label. |
| Analysis complete / decision required | Session status | `ANALYZED` | `Menunggu Keputusan` | Database, API, schema, task docs, tests | Status badges and current-step copy | Never use legacy `INITIAL_ANALYZED` for V2. |
| Waiting | Session status | `WAITING` | `Menunggu` | Database, API, schema, task docs, tests | Status badges and action copy | No position exists. |
| Open position | Session status | `OPEN_POSITION` | `Posisi Terbuka` | Database, API, schema, task docs, tests | Status badges and summary copy | Exactly one position. |
| Closed trade | Session status | `CLOSED` | `Selesai` | Database, API, schema, task docs, tests | Terminal summary/status | Remains terminal after Archive/Restore. |
| Closed without trade | Session status | `CLOSED_SKIPPED` | `Dilewati` | Database, API, schema, task docs, tests | Terminal summary/status | Distinct from CLOSE. |
| Processing | Transient/internal state | `ANALYZING` | Approved Indonesian processing copy | Request/API/internal state where authoritative | Processing message | Not added to the six-status canonical persisted redesign list. |
| User decision | Decision | `BUY`, `WAIT`, `SKIP` | BUY, WAIT, SKIP with Indonesian explanation where needed | API, schema, task docs, tests | Buttons may retain approved decision tokens | Gemini cannot persist or execute it. |
| Analysis type | Analysis type | `INITIAL_ANALYSIS`, `WAIT_UPDATE`, `POSITION_UPDATE` | Approved Indonesian headings | API, schema, task docs, tests | Headings and navigation | Observation periods are metadata, not types. |
| Evidence type | Evidence type | `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH` | Indonesian upload labels | API, schema, task docs, tests | Upload labels | No new evidence type or second initial set. |
| Archive | Organizational metadata | `archived_at` or approved equivalent | `Arsipkan Sesi` | Persistence/API/task docs | Action labels and confirmation | Never a session status; no V2 `ARCHIVED`. |
| Restore | Organizational metadata mutation | Clear archive metadata | `Kembalikan ke Daftar` | API/service/task docs | Action labels and confirmation | Never Reopen; remains terminal/read-only. |
| UI grouping | Frontend-derived grouping | None | Needs Attention / In Progress / Completed, with approved Indonesian UI copy as applicable | Documentation of grouping rule | Sessions list section labels | Never persisted as statuses. |
| User-facing analysis | Canonical analysis payload | Approved analysis response fields | Indonesian display content | API/schema and canonical payload | Rendered analysis sections | Frontend must not invent conclusions, scores, or color meaning. |

## 7. Explicit Non-Goals Register

| ID | Non-goal | Authority / boundary |
|---|---|---|
| NONGOAL-001 | New AI providers or provider routing/fallback | PRD v2 §§1–2; AC-22 |
| NONGOAL-002 | New AI models or model selection | Redesign PRD §4.2; production remains Gemini `gemini-3.1-flash-lite` |
| NONGOAL-003 | New analysis types | PRD v2 §7; AC-22 |
| NONGOAL-004 | New session statuses, transitions, or business abstractions | PRD v2 §§5–6; AC-22 |
| NONGOAL-005 | `ARCHIVED` as a V2 session status or reuse of legacy Archive lifecycle behavior | Redesign PRD §12.3; approved decision 3 |
| NONGOAL-006 | Changes to evidence requirements or evidence replacement behavior | PRD v2 §10; redesign PRD §11.6 |
| NONGOAL-007 | Changes to BUY, WAIT, SKIP meaning or user decision authority | PRD v2 §§12–16; Amendment §§1–5 |
| NONGOAL-008 | Changes to request statuses, durable queue, retry, polling, or Gemini request semantics | PRD v2 §11.3; redesign PRD §15.1 |
| NONGOAL-009 | Session deletion, evidence deletion, Archive deletion, or destructive migration | Redesign PRD §§4.2, 12.3 |
| NONGOAL-010 | Session reopening, Restore-to-active behavior, or new trading history for Restore | Redesign PRD §12.6 |
| NONGOAL-011 | Bulk Archive/Restore | Redesign PRD §4.2; UX6 task boundaries |
| NONGOAL-012 | Search, tags, folders, portfolio analytics, dashboards, or dashboard expansion | Redesign PRD §4.2; UX3.3 boundaries |
| NONGOAL-013 | Unapproved endpoint renaming or exact migration/class/function prescriptions | Redesign task plan UX1.4 and UX1.1 boundaries |
| NONGOAL-014 | Legacy compatibility, cleanup, removal, or behavior changes outside explicit UX8 cutover tasks | Approved V2/legacy boundary; UX8 scope |
| NONGOAL-015 | Repository-derived product overrides | PRD v2 §1; Source Lock skill |
| NONGOAL-016 | General cleanup, refactoring, architecture replacement, or speculative abstractions | Source Lock skill; redesign task plan governance |
| NONGOAL-017 | Real Gemini calls for ordinary UI, responsive, archive, routing, or documentation verification | Focused Testing skill |
| NONGOAL-018 | Product analytics, third-party tracking, sensitive evidence collection, or privacy expansion without separate approval | Redesign PRD §18 |

## 8. Conflict and Ambiguity Register

| ID | Source A | Source B / repository evidence | Description | Impact | Resolution from authority | Status | Blocking task/phase | Product decision required |
|---|---|---|---|---|---|---|---|---|
| CONFLICT-001 | Redesign approval decisions, 4 August 2026 | Previously observed draft/pending metadata in the redesign DOCX files | Approval state conflicted before document correction. | Could prevent redesign authority from becoming active. | Corrected redesign PRD and task plan now state Approved, effective 4 August 2026. | RESOLVED_BY_AUTHORITY | UX0-G | None |
| CONFLICT-002 | Approved decision 2; redesign PRD | Legacy repository uses `INITIAL_ANALYZED`; V2 uses `ANALYZED`. | Lifecycle vocabulary differed across old and V2 implementation. | Could cause wrong action mapping. | V2 canonical values are `DRAFT` and `ANALYZED`; legacy terminology is non-authoritative. | RESOLVED_BY_AUTHORITY | UX0-G, UX4-G | None |
| CONFLICT-003 | Redesign PRD §12 and Archive skill | Legacy repository defines `TradeSessionStatus.ARCHIVED` and archive behavior. | Legacy Archive lifecycle conflicts with V2 metadata-only Archive. | Reusing legacy code would mutate session state. | V2 target is `trade_sessions_v2`/`backend/app/trade_workspace/`; legacy behavior is explicitly out of scope. | RESOLVED_BY_AUTHORITY | UX1-G | None |
| CONFLICT-004 | Approved decision 4 and UX1.1 | Repository contains both legacy `trade_sessions` and V2 `trade_sessions_v2`. | Competing entities could make migration target unclear. | Wrong table/model could create product drift or data risk. | Canonical redesign entity is explicitly `trade_sessions_v2`; legacy table is non-authoritative. | RESOLVED_BY_AUTHORITY | UX1-G | None |
| AMBIGUITY-001 | Redesign PRD §7.2 | Task plan deliberately does not prescribe final endpoint names. | Exact endpoint naming remains implementation-task detail. | UX1.4/UX2 tasks must follow repository/API conventions without changing product behavior. | Leave endpoint names to the official task; do not invent them in UX0.1. | NON_BLOCKING_AMBIGUITY | UX1.4, UX2.1 | None |
| AMBIGUITY-002 | Redesign PRD §§13.2, 22.2 | Bottom navigation is permitted only if it improves reachability. | Mobile navigation mechanism is an implementation choice. | Must not hide context or alter routes. | Evaluate during UX2/UX7 against the approved route model. | NON_BLOCKING_AMBIGUITY | UX2-G, UX7-G | None |

No unresolved implementation-affecting conflict remains. Therefore no register entry is `BLOCKED`.

## 9. Mandatory Focused Gates

All official gates are included in official order.

| Gate | What it protects | Requirements verified | Minimum evidence | Dependency | BLOCKED when |
|---|---|---|---|---|---|
| `UX0-G — Phase Gate — Authority and Repository Alignment` | Source alignment before implementation | AUTH-001–004 and all UX0.1/UX0.2 source mappings | Trace UX1 prerequisites to sources and repository evidence | UX0 tasks complete | Any unresolved product/repository conflict, unapproved contract, missing source, or scope expansion |
| `UX1-G — Phase Gate — Archive Backend Foundation` | Metadata-only, terminal-only Archive backend | ARCH-001–010; AC-11–16 | Migration/model, domain, query, API, ownership, status-preservation, related-record tests | UX0-G | `ARCHIVED` V2 status, non-terminal archive, deletion, reopening, unsafe migration, or missing ownership |
| `UX2-G — Phase Gate — Application Shell and Routing` | Stable authenticated route foundation | ROUTE-001–008; AC-01/19 | Route/auth/refresh/direct-link/mobile shell checks | UX0-G; UX2 tasks | Redirect loop, lost session context, unsafe direct URL, duplicate request, or moved lifecycle behavior |
| `UX3-G — Phase Gate — Sessions and Create Session` | Focused post-login list/create journey | SESSION-001–005, CREATE-001–003; AC-02–04 | Login → Sessions → Create → Detail using fixtures/safe tests | UX2-G | Full workspace remains default, creation is not focused, or archive exclusion is unproven |
| `UX4-G — Phase Gate — Session Detail Foundation` | Stable backend-authoritative session context | DETAIL-001–005; AC-05/06 | Direct URL, refresh, status matrix, mobile/desktop shell | UX3-G | Frontend invents action eligibility, stale session data leaks, or all-in-one layout remains |
| `UX5-G — Phase Gate — Guided Session Flow` | complete session flow behavior through guided screens | LIFE-001–015; AC-05–10, 19–22 | Focused guided-flow integration, request recovery, lifecycle/action matrix; no real Gemini by default | UX4-G | Any lifecycle/evidence/analysis/decision/request regression, duplicate request, or legacy dependency remains |
| `UX6-G — Phase Gate — Archive Experience` | Complete Archive/read-only/Restore journey | ARCH-005–010; AC-11–16 | Both terminal statuses, direct URL/refresh, mobile, integrity and read-only evidence | UX1-G and UX4-G; final follows UX5-G | Deletion, session-state mutation, reopen, inaccessible archived detail, or invalid action visibility |
| `UX7-G — Phase Gate — Mobile, Accessibility, and Content` | Responsive, accessible, Indonesian UI quality | GLOBAL-005–008, MOBILE-001–006, COPY-001–003; AC-17/18/20/21 | Viewport matrix, keyboard flow, copy inventory, state matrix | Screen completion | MVP-blocking mobile/accessibility defect or behavior change |
| `UX8-G — Final Gate — Guided Session Experience and Archive` | Final full-flow, cutover, and traceability acceptance | All requirements and AC-01–22 | Review all mandatory evidence; rerun failed/stale focused checks only | UX5/UX6/UX7 gates | Approved journey fails, Archive is not metadata-only, UI is not guided/mobile-friendly, or any product rule changed |

## 10. Coverage and Completeness Summary

- Total mapped requirement rows: **67**.
- Requirement rows by category: Authority **4**; Global Experience **8**; Routes **8**; Sessions list **5**; Creation **3**; Session Detail **5**; Initial Evidence **3**; Initial Analysis **1**; Processing **1**; Analysis **1**; Decisions **1**; BUY **1**; WAIT **1**; WAIT Update **1**; Open Position **1**; Position Update **1**; Close and terminal **1**; SKIP and terminal **1**; History **1**; Archive **10**; Mobile **4**; Accessibility **2**; Content **3**.
- UI/UX PRD acceptance criteria: **22**.
- Acceptance criteria covered by at least one official task: **22**.
- Uncovered acceptance criteria: **0**.
- Explicit non-goals registered: **18**.
- Mandatory phase gates mapped: **9** (`UX0-G` through `UX8-G`).
- Resolved conflicts: **4**.
- Non-blocking ambiguities: **2**.
- Blocking conflicts: **0**.

### UX0.1 acceptance criteria

- **No approved requirement is missing — PASS.** Coverage matrix spans authority, global experience, routes, Sessions, creation, Detail, lifecycle surfaces, Archive, mobile/accessibility/content, all 22 ACs, and non-goals.
- **No repository behavior is treated as product authority — PASS.** The source hierarchy and repository baseline explicitly classify repository behavior as implementation evidence only.
- **All unresolved conflicts are marked BLOCKED — PASS.** No unresolved implementation-affecting conflict remains; the two remaining ambiguities are explicitly `NON_BLOCKING_AMBIGUITY`.

**Final UX0.1 result:** `PASS`.

## 11. Change Confirmation and Next Task

- Documentation and mapping only.
- No UX0.2 work performed.
- No application, test, configuration, migration, API, schema, dependency, or agent-skill files changed.
- No product decision made beyond recording the already approved decisions.
- No broad application tests run.
- No real Gemini request made.

Next official task: **`UX0.2 — Current Main-Branch UI/UX Impact Audit`**. It is not executed by this task.
