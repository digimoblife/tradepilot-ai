# P10.5 Failure and Retry UI Reconciliation

- Official task: P10.5 — Build Failure and Retry UI
- Parent task: P10.5
- Starting commit: `790e537196c10e23e3f818cf5383cee6b87e0d60`
- Previous blocker: failure views rendered raw `error_message` values.
- Root cause: three feature components treated backend error text as safe UI text, and the timeline had no shared failure-message mapping.

## Correction

Added the frontend-only `safeErrorMessage` helper at `frontend/src/features/trade-workspace/safe-error.ts`. It returns fixed Indonesian messages by feature context for Initial Analysis, WAIT Update, and Position Update; it never returns or concatenates the input error. The same helper is used by all three failure views and timeline failed events.

Provider, database, filesystem, endpoint, worker, stack-trace, and unknown synthetic error text is hidden. Manual retry controls, preserved evidence/input/history, request lifecycle, polling, and session status behavior remain unchanged.

## Verification

- Initial Analysis: safe failure message, evidence preserved, retry remains manual, no decision controls before success.
- WAIT Update: safe failure message, WAITING lifecycle and retry behavior preserved.
- Position Update: safe failure message, OPEN_POSITION and confirmed position facts preserved; CLOSE remains available.
- Timeline: failed events remain chronological and use the shared safe messages without raw details.
- Duplicate-request and controlled-polling behavior remain covered by existing tests.
- P7.2a `WAITING → WAITING` and P8.2a `OPEN_POSITION → OPEN_POSITION` are unchanged.

Focused command from `frontend/`:

```text
npm test -- --run src/features/trade-workspace/safe-error.test.ts src/features/trade-workspace/evidence-hydration.test.tsx src/features/trade-workspace/wait-update.test.tsx src/features/trade-workspace/position-update.test.tsx src/features/trade-workspace/timeline.test.tsx src/features/trade-workspace/polling-loop.test.tsx src/features/trade-workspace/decision-ui.test.tsx src/features/trade-workspace/close.test.tsx src/features/trade-workspace/workspace-header.test.tsx
Test Files  9 passed (9)
Tests       53 passed (53)

npm run typecheck
tsc --noEmit: passed
```

`git diff --check` passed. No backend production code changed, no retry endpoint or lifecycle changed, and no real Gemini request occurred.

## Ledger and result

P10.5 remains `COMPLETED`; its authoritative commit field appends the regression fix `cb0bb56` and reconciliation commit `DOCS_COMMIT`. The execution pointer advances from P10.5 to P11.1.
