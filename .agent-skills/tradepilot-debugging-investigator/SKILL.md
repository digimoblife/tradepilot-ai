TradePilot Debugging Investigator
Purpose

Investigate TradePilot AI failures systematically and correct root causes with minimal, tested changes.

This skill prioritizes evidence and boundary tracing over speculative editing.

When to Use

Use for:

production or local failures;
schema mismatches;
provider failures;
stale context;
retry loops;
duplicate frontend requests;
incorrect lifecycle state;
database inconsistency;
worker terminalization problems;
failed health checks;
unexplained user-interface states;
regressions after a previous fix.
Required Context

Read:

.agent-skills/shared/PROJECT_INVARIANTS.md
.agent-skills/shared/DEBUGGING_PROTOCOL.md
relevant logs;
affected tests;
active source code;
the expected contract;
prior fix attempts for the same issue.
Mandatory Workflow
Phase 1: Define

State:

expected behavior;
actual behavior;
reproduction;
affected environment;
first known divergence.
Phase 2: Inspect

Trace the entire affected path and identify the earliest failing boundary.

Phase 3: Hypothesize

Form one primary falsifiable hypothesis.

Phase 4: Verify the Hypothesis

Use logs, tests, database state, request payloads, or controlled reproduction.

Do not edit code merely to see what happens.

Phase 5: Correct

Apply the smallest change that corrects the identified cause.

Phase 6: Protect

Add a regression test that demonstrates the original failure.

Phase 7: Verify

Run focused and neighboring tests, then verify the user-relevant path.

Phase 8: Report

Use .agent-skills/shared/EXIT_REPORT_TEMPLATE.md.

Boundary Checklist

For AI analysis failures, inspect:

user action;
frontend request;
gateway;
backend route;
authorization;
context freshness;
job creation;
worker claim;
provider request;
provider response;
parser;
schema validation;
persistence;
job terminalization;
frontend polling;
rendering.

For lifecycle failures, inspect:

current state;
requested transition;
authorization;
domain validation;
database lock;
transaction;
deterministic calculations;
persistence;
rollback;
resulting analysis job.
Hypothesis Quality Standard

A hypothesis must include:

exact failing boundary;
suspected mechanism;
evidence expected if true;
minimal correction;
test that would prove the correction.

Example:

The worker catches the provider exception but loses its structured message field, so the job is terminalized with only PROVIDER_ROUTING_FAILED. Preserve sanitized provider details in the adapter and assert them in the worker failure test.

Minimal-Fix Standard

A valid minimal fix:

addresses the root cause;
avoids unrelated refactoring;
preserves contracts where possible;
does not hide failure;
does not weaken validation silently;
does not introduce a retry loop;
includes a regression test.
Two-Fix Escalation Rule

Maintain an attempt log for the same underlying issue.

After two unsuccessful or circular code changes, stop.

Report:

Attempt 1:
Hypothesis:
Change:
Result:

Attempt 2:
Hypothesis:
Change:
Result:

Recurring mismatch:
Decision required:

Present practical product options:

relax validation;
change the expected contract;
accept model output as-is;
continue enforcing the original requirement.

Do not apply a third speculative fix without direction.

Prohibited Actions

Do not:

change code before reproduction or evidence;
apply broad “cleanup” during debugging;
add retries to deterministic failures;
suppress stack traces required for diagnosis;
expose secrets in logs;
weaken schema requirements silently;
mutate production data directly;
mark the issue fixed because one unit test passes;
delete or weaken failing tests;
continue circular fixes beyond the escalation threshold.
Validation Requirements

A debugging task requires:

confirmed root cause or explicit uncertainty;
regression test;
focused test pass;
neighboring behavior verification;
failure-path verification where relevant;
declared remaining risk;
accurate status.

Use IMPLEMENTED_NOT_FULLY_VERIFIED when the real affected flow could not be exercised.

Expected Output

During investigation, produce:

Expected:
Actual:
First failing boundary:
Evidence:
Primary hypothesis:
Minimal fix:
Regression test:

At completion, provide the shared exit report.

Exit Criteria

The task is complete only when:

the root cause is identified;
the correction targets that cause;
regression protection exists;
the affected flow is verified;
no hidden contract weakening occurred;
unresolved risks are documented.