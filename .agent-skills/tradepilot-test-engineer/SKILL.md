TradePilot Test Engineer
Purpose

Design and execute reliable tests that prove TradePilot AI behavior across schemas, domain logic, database transactions, APIs, workers, frontend state, and complete user flows.

Testing must verify product behavior, not merely increase coverage.

When to Use

Use for every implementation or bug fix that affects:

schemas;
lifecycle state;
deterministic calculations;
database writes;
API behavior;
job processing;
provider handling;
context freshness;
frontend polling;
frontend rendering;
deployment or smoke-test behavior.
Required Context

Read:

.agent-skills/shared/PROJECT_INVARIANTS.md
acceptance criteria;
canonical contract;
current tests;
affected implementation;
known failure path.
Test Strategy

Choose the lowest test level that proves the behavior, then add higher-level verification when system boundaries are involved.

Recommended order:

schema and domain validation;
pure service logic;
database integration;
API integration;
worker integration;
frontend state behavior;
visible end-to-end smoke test.

Do not replace integration testing with mocks when the failure depends on database, queue, provider adapter, or browser behavior.

Mandatory Test Categories

For each task, determine which categories apply.

1. Happy Path

Prove the requested behavior succeeds.

2. Invalid Input

Prove malformed or incomplete input is rejected safely.

3. Invalid State

Prove illegal lifecycle transitions are rejected.

4. Duplicate or Retry Behavior

Prove repeated requests do not create duplicate effects when idempotency is required.

5. Failure Path

Prove provider, validation, database, or worker failure results in a correct terminal state.

6. Rollback

For critical multi-record writes, force a failure after an intermediate mutation and verify that no partial state remains.

7. Regression

Reproduce the exact previously observed bug.

8. Neighboring Behavior

Prove nearby approved flows still work.

Schema Testing

Schema changes should include:

valid fixture;
minimal valid fixture;
invalid missing-field fixture;
invalid enum fixture;
invalid type fixture;
boundary-value fixture;
additional-property behavior where relevant;
cross-field domain validation.

Schema tests must align with:

backend models;
parser behavior;
frontend types;
prompt output expectations.
Database and Transaction Testing

Use a real test database when verifying:

transactions;
locks;
rollback;
constraints;
concurrency;
persistence;
calculations based on stored records.

Critical trade lifecycle operations must verify:

state before operation;
committed state after success;
unchanged state after forced failure;
derived values;
related history records;
idempotent retry behavior if applicable.

Do not use mocks to claim transaction safety.

Worker Testing

Worker tests should cover:

job claim;
correct analysis type;
provider invocation;
successful persistence;
schema failure;
provider failure;
terminal status;
retry classification;
stale context handling;
sanitized failure diagnostics;
duplicate claim protection where relevant.
Frontend Testing

Frontend state tests should cover:

one fetch owner or deduplicated fetching;
polling start and stop;
successful terminal job;
failed terminal job;
restored job from storage;
no infinite retry;
no unnecessary shell remount;
stale processing-state recovery;
rendering fallback for missing optional fields;
Indonesian user-facing analysis.

Prefer testing observable requests and UI states over private implementation details.

End-to-End Testing

Use visible Playwright testing for critical production-like flows when requested.

A full initial-analysis smoke test may verify:

login;
create session;
upload evidence;
mark evidence ready;
request analysis;
job creation;
worker processing;
real Gemini call when explicitly required;
validated persistence;
completed frontend analysis;
correct terminal job and session states.

Failure smoke tests may include:

invalid model;
invalid API key;
provider error;
malformed model response;
missing evidence.

Local smoke tests must use isolated databases, volumes, ports, and evidence.

Test Quality Rules

Tests must:

be deterministic where possible;
use descriptive names;
assert business outcomes;
avoid hidden dependence on test order;
clean up isolated state;
distinguish test setup failure from product failure;
avoid real provider calls unless explicitly part of smoke testing;
preserve useful failure output.

Do not:

loosen assertions merely to pass;
remove failure-path tests;
overmock the behavior under investigation;
claim a flow works based only on a mocked unit test;
reuse production data;
depend on uncontrolled external state.
Verification Levels

Use these terms accurately.

IMPLEMENTED

Code was changed, but verification may be incomplete.

TESTED

Relevant automated tests passed.

VERIFIED

The required acceptance behavior was exercised at the appropriate system level.

For example, a browser-based production-like requirement is not VERIFIED by backend unit tests alone.

Required Test Plan Output

Before implementation, provide:

Behavior to prove:
Primary test level:
Happy path:
Failure path:
Regression case:
Neighboring checks:
Environment requirements:
Required Completion Output

Report:

exact commands;
number and type of tests;
pass/fail result;
skipped tests;
untested acceptance criteria;
environment limitations;
remaining risk.

Use .agent-skills/shared/EXIT_REPORT_TEMPLATE.md.

Exit Criteria

Testing is complete when:

the requested behavior is proven;
the known failure is protected by regression testing;
critical failure paths are covered;
rollback is tested where applicable;
neighboring behavior is checked;
status claims match actual verification depth.