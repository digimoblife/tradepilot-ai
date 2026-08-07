TradePilot AI Exit Report Template

Use this template at the end of every implementation, investigation, or verification task.

Do not claim VERIFIED unless the required behavior was actually exercised.

Status

Choose one:

VERIFIED
IMPLEMENTED_NOT_FULLY_VERIFIED
BLOCKED
NO_CHANGE_REQUIRED
Objective

Briefly state the requested outcome.

Root Cause

For bug fixes, explain the first failing boundary and mechanism.

For feature work, write Not applicable.

Changes

List the meaningful changes by responsibility.

Example:

Backend:
Worker:
Database:
Schema:
Frontend:
Tests:
Documentation:

Do not list unrelated file-level noise.

Contract Impact

Choose and explain:

no contract change;
backward-compatible change;
breaking change;
storage-only change;
presentation-only change.

Mention affected schemas, APIs, or types.

Validation Performed

List exact commands and checks.

Example:

pytest backend/tests/api/test_closing_analysis.py -v
npm test -- restored-job-state.test.tsx
docker compose -p tradepilot-local ps
Results

Report each acceptance criterion as:

PASS
FAIL
NOT TESTED
NOT APPLICABLE
Failure-Path Verification

Describe tested failure behavior, including rollback, invalid state, provider error, or terminal job handling where relevant.

Remaining Risks

State any uncertainty, untested behavior, environment limitation, or follow-up requirement.

Write None identified only when justified.

Files Changed

Provide a concise file list.

Git Status

Include when requested:

branch;
commit hash;
commit message;
push status;
working tree status.
Final Outcome

State what is now true from the user or system perspective.

Avoid vague statements such as “everything works.”