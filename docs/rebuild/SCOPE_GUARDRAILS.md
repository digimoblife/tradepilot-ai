# Rebuild Scope Guardrails

## 1. Purpose

These guardrails define what rebuild work is allowed. They are enforceable task limits, not architecture or implementation instructions.

## 2. Product Authority

The PRD and the TradePilot AI Rebuild Detailed Task Plan are the only product and implementation authorities. Existing code does not define the product. Existing components may be reused only when they directly support the approved PRD. If an authority conflict or scope expansion appears, RETURN `BLOCKED`.

## 3. Approved Product Scope

The rebuild covers one user-owned Trade Session, one position at most, complete chronological history, manual evidence, longitudinal AI analysis, and user-controlled BUY, WAIT, SKIP, and CLOSE. No feature may be added without explicit product approval.

## 4. AI Provider and Model Rules

- Gemini is the only AI provider.
- The production model MUST be `gemini-3.1-flash-lite`.
- Provider routing and fallback are prohibited.
- Gemini MAY recommend an action but MUST NOT persist BUY, WAIT, SKIP, or CLOSE; create/change/close a position; or alter user-entered current price, entry price, quantity, entry timestamp, stop loss, target price, or position status.
- No real Gemini request is allowed unless an explicit end-to-end task requires and authorizes it.
- One prompt performs only one small task.

## 5. Approved Session Statuses

Only these business statuses are allowed:

`DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, `CLOSED_SKIPPED`.

No additional lifecycle status is allowed. `ANALYSIS_FAILED` MUST NOT become a permanent business status; an analysis failure may be stored on the request while the previous valid business status remains recoverable.

## 6. Approved Analysis Types

Only these analysis types are allowed:

`INITIAL_ANALYSIS`, `WAIT_UPDATE`, `POSITION_UPDATE`.

No other analysis type may be introduced, created, or used as new rebuild business behavior.

## 7. User Decision Authority

Only the user may persist:

`BUY`, `WAIT`, `SKIP`, `CLOSE`.

Execution facts entered or confirmed by the user remain authoritative. AI output is advisory and MUST NOT execute decisions or mutate position facts.

## 8. Prohibited Product Features

The rebuild MUST NOT include:

- Partial Exit;
- a Closing Analysis requirement;
- automated BUY, WAIT, SKIP, or CLOSE;
- automated trading or broker execution;
- more than one position per session;
- a feature without explicit product approval.

## 9. Prohibited Technical Abstractions

The rebuild MUST NOT depend on:

- a generic workflow engine;
- a generic lifecycle platform;
- a generic schema registry as rebuild business authority;
- a generic validation framework as rebuild business authority;
- provider routing or fallback;
- any new framework or abstraction not explicitly approved.

## 10. Existing Code Reuse Rules

Existing code is evidence, not product authority. Reuse is allowed ONLY when the component directly supports the approved PRD and does not import old workflow behavior. Old workflow components MUST NOT control the rebuild.

Authentication, ownership checks, private storage mechanics, PostgreSQL connection setup, direct Gemini SDK mechanics, worker/queue operations, migration tooling, gateway topology, and generic frontend shell mechanics may be considered only as narrowly scoped infrastructure. Old lifecycle decisions, legacy statuses/types, EvidenceBatch behavior, provider fallback, Partial Exit, Closing Analysis, generic validation, and evaluation flow MUST NOT be imported as rebuild authority.

Evidence: `docs/rebuild/OLD_WORKFLOW_COMPONENTS.md`, `docs/rebuild/PRD_CODE_MAPPING.md`, and `docs/rebuild/REBUILD_MODULE_BOUNDARY.md`.

## 11. Historical Data and Cutover Rules

Old tables and historical records MUST remain available until cutover is verified. Old APIs and old frontend surfaces may remain temporarily for historical access. Rebuild data and old-workflow data MUST NOT be mixed in new behavior. No old component, table, record, or runtime artifact may be removed or cleaned up under these guardrails.

## 12. Task Execution Rules

- One task MUST implement only one small approved task.
- The requested behavior MUST be explicitly approved by the PRD and task plan.
- Work MUST stay within the current task’s output and verification scope.
- Do not continue the old P9 workflow.
- Do not begin a later task automatically.
- Do not add implementation architecture, APIs, schemas, migrations, or product features unless the active task explicitly authorizes them.
- Do not make real Gemini requests unless explicitly authorized by an end-to-end task.

## 13. BLOCKED Conditions

RETURN `BLOCKED` immediately when:

- scope expansion is required;
- approved behavior must change;
- a new status, analysis type, provider, feature, framework, or abstraction is required;
- old workflow authority must control new behavior;
- preservation of old tables or historical records is not possible;
- the task requires a real Gemini request without explicit authorization;
- the task cannot be completed without leaving its approved documentation or implementation scope.

Do not silently resolve a BLOCKED condition by widening scope.

## 14. Guardrail Checklist

- [ ] Does this task implement only one small approved task?
- [ ] Is the requested behavior explicitly approved by the PRD?
- [ ] Does it use Gemini only?
- [ ] Does it avoid unapproved statuses and analysis types?
- [ ] Does it keep user decisions and execution facts user-owned?
- [ ] Does it avoid old lifecycle authority?
- [ ] Does it avoid new frameworks or abstractions?
- [ ] Does it preserve old data until cutover?
- [ ] Does it avoid real Gemini requests unless explicitly authorized?
- [ ] Must the task return `BLOCKED` instead of expanding scope?

## 15. P1.3 Conclusion

The rebuild is limited to the approved Gemini-only, user-controlled, one-position session flow and the seven approved statuses and three approved analysis types. Existing code may provide narrowly scoped infrastructure only. Scope expansion, behavior changes, old-workflow control, or unauthorized Gemini activity requires RETURN `BLOCKED`.
