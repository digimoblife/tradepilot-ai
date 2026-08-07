TradePilot AI Debugging Protocol
Purpose

This protocol defines the mandatory debugging workflow for TradePilot AI.

The objective is to identify and correct the first failing system boundary rather than repeatedly patching visible symptoms.

Core Principle

Do not edit code before establishing a testable hypothesis.

Every debugging task must follow this sequence:

reproduce;
collect evidence;
locate the first failing boundary;
form one primary hypothesis;
apply the smallest viable correction;
add a regression test;
verify the full affected flow.
1. Establish the Expected Behavior

Before investigating, state:

the expected user-visible result;
the expected domain state;
the expected API or job state;
the actual result;
the first known divergence.

Do not assume the issue description identifies the actual failing component.

2. Reproduce the Failure

Use the smallest reliable reproduction.

Record:

exact command or user action;
relevant environment;
input data;
current session state;
job state;
timestamps;
logs;
error payload;
whether the issue is deterministic.

When possible, reproduce outside production using isolated data.

Do not mutate production data merely to reproduce a bug.

3. Trace the Full Path

For an analysis request, inspect the path in order:

frontend action;
gateway request;
backend route;
service validation;
context freshness;
database write;
job creation;
worker claim;
provider request;
provider response;
response parsing;
schema validation;
persistence;
terminal job update;
frontend polling;
frontend rendering.

Identify the earliest point where actual behavior differs from expected behavior.

Later failures may be consequences rather than root causes.

4. Collect Relevant Evidence

Use targeted evidence:

structured logs;
correlation IDs;
session IDs;
job IDs;
analysis type;
state transitions;
provider error details;
validation error paths;
database records;
network requests;
frontend render cycles;
test output.

Avoid broad, noisy log collection when a narrower query is possible.

Never expose secrets or raw credentials.

5. Form One Primary Hypothesis

A valid hypothesis must be falsifiable.

Good example:

The restored failed job remains in activeJob, causing the polling hook to increment retryKey and remount the analysis shell.

Weak example:

The frontend state is probably broken.

The hypothesis should identify:

failing boundary;
probable mechanism;
expected evidence;
proposed minimal correction.
6. Check Source of Truth

Before editing, determine which layer owns the behavior.

Examples:

lifecycle validity: domain service;
persistent status: backend/database;
schema shape: canonical schema;
deterministic return calculation: application service;
analysis wording: prompt or presentation layer;
polling lifecycle: frontend state owner;
provider model: environment configuration.

Do not fix a source-of-truth issue in a downstream presentation layer.

7. Apply the Minimal Fix

The correction should:

address the identified cause;
preserve existing contracts where possible;
avoid unrelated refactoring;
avoid broad exception swallowing;
avoid adding retries that hide deterministic failures;
avoid weakening validation without approval;
avoid changing several layers simultaneously unless the contract requires it.

Document any unavoidable supporting changes.

8. Add a Regression Test

Every confirmed bug fix should include a test that fails before the fix and passes afterward.

Choose the narrowest meaningful level:

unit test;
schema fixture;
service test;
database integration test;
API test;
worker test;
frontend component or hook test;
Playwright end-to-end test.

The test must assert behavior, not merely implementation details.

9. Verify Neighboring Behavior

After the focused test passes, verify the affected end-to-end path.

Examples:

API plus worker;
worker plus schema persistence;
transaction plus rollback;
frontend restore plus terminal job behavior;
provider failure plus user-facing error;
closing flow plus calculated trade metrics.

Check both success and failure paths when the change affects critical state.

10. Two-Fix Escalation Rule

Count a fix attempt when code is changed to resolve the same underlying issue.

Stop after two unsuccessful or circular attempts when:

the mismatch changes shape but remains;
a new layer starts failing;
expected output and model output repeatedly disagree;
validation changes cause additional contract inconsistencies;
retries or state changes produce loops;
the same task alternates between two failure modes.

Report:

original mismatch;
first fix and result;
second fix and result;
likely unresolved product or contract decision.

Request one of these decisions:

relax validation;
change the expected contract;
accept the model output as-is;
continue enforcing the original requirement.

Do not apply a third speculative correction without direction.

11. Prohibited Debugging Behavior

Do not:

patch several unrelated files without a traced cause;
add generic retries to deterministic errors;
suppress provider diagnostics;
weaken schemas silently;
edit production data directly;
use destructive Docker cleanup;
claim success based only on compilation;
remove tests to make a suite pass;
replace a failing test with a weaker assertion;
mark a task verified when the actual user flow was not checked.
12. Required Debugging Output

At completion, provide:

root cause;
affected boundary;
files changed;
correction applied;
regression test added;
commands executed;
verification result;
unresolved risks;
commit and push status if requested.

Use EXIT_REPORT_TEMPLATE.md.