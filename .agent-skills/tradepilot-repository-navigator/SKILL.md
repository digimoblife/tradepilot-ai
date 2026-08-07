TradePilot Repository Navigator
Purpose

Understand the TradePilot AI repository before editing it.

This skill prevents local patches that ignore system flow, duplicate an existing source of truth, or cause unexpected changes in neighboring layers.

When to Use

Use before:

implementing a feature;
fixing a bug;
changing a schema;
modifying a lifecycle transition;
changing provider integration;
changing frontend polling;
adding a migration;
editing worker behavior;
modifying deployment configuration;
reviewing a proposed implementation.
Required Context

Read:

.agent-skills/shared/PROJECT_INVARIANTS.md
the task request;
repository root documentation;
relevant architecture and domain documents;
relevant tests;
current code paths.
Mandatory Workflow
1. Establish Repository Shape

Identify the locations of:

backend application;
worker;
frontend;
gateway;
database migrations;
schemas;
prompts;
shared types;
tests;
Docker and deployment configuration;
evidence storage;
environment examples.

Do not assume conventional paths.

2. Locate the Source of Truth

For the requested behavior, identify the authoritative layer.

Examples:

schema shape;
domain transition;
database state;
provider model;
frontend job state;
context construction;
analysis rendering.

Record any duplicated representations that must stay synchronized.

3. Trace the Call Chain

Trace from the user or system trigger to the final effect.

For analysis generation, inspect:

Frontend
→ Gateway
→ Backend API
→ Domain or application service
→ Context builder
→ Database
→ Job queue
→ Worker
→ AI provider
→ Parser and validator
→ Persistence
→ Frontend polling
→ Rendering

For lifecycle writes, inspect:

API
→ Authorization
→ Domain validation
→ Transaction boundary
→ State mutation
→ Derived calculation
→ Analysis job creation
→ Response
4. Find Related Tests

Before changing code, locate:

tests for the target behavior;
tests for neighboring behavior;
schema fixtures;
failure-path tests;
integration tests;
end-to-end tests.

Determine whether current tests express the intended product behavior or only the current implementation.

5. Assess Blast Radius

Classify affected areas:

direct;
synchronized contract dependency;
potential regression area;
not affected.

Check for:

shared enums;
generated types;
repeated field definitions;
frontend assumptions;
worker assumptions;
migration implications;
compatibility concerns.
6. Detect Legacy or Duplicate Paths

Search for:

deprecated schemas;
old prompt versions;
multiple provider adapters;
unused endpoints;
duplicated calculations;
legacy polling logic;
old environment variables;
shadowed type definitions.

Do not edit the first matching file without confirming it is active.

7. Produce a Change Map

Before implementation, summarize:

active entry point;
source of truth;
primary files;
synchronized files;
tests to update;
files intentionally not changed;
expected blast radius.
Navigation Rules

Use targeted search before broad reading.

Prefer:

symbol search;
enum or schema field search;
call-site search;
route search;
test-name search;
configuration key search.

Read enough surrounding context to understand ownership and transaction boundaries.

Do not base a change on an isolated snippet.

Prohibited Actions

Do not:

edit before locating the active source of truth;
create a second implementation of existing behavior;
change generated files without changing their source;
assume a file is active because its name looks correct;
refactor unrelated modules;
replace architecture merely because another pattern is preferred;
ignore tests that cover neighboring lifecycle states;
modify environment or Docker files without checking project isolation;
change both old and new paths unless both are confirmed active.
Validation Requirements

Before implementation:

active code path identified;
source of truth identified;
call chain traced;
related tests identified;
blast radius documented;
legacy paths distinguished from active paths.

After implementation:

no duplicate source of truth introduced;
synchronized layers remain aligned;
tests cover the active path;
unrelated paths remain unchanged.
Expected Output

Produce a concise repository map:

Trigger:
Source of truth:
Primary path:
Dependent contracts:
Relevant tests:
Blast radius:
Files likely to change:
Files intentionally excluded:

Do not produce a generic repository summary unrelated to the task.

Exit Criteria

Navigation is complete when the agent can explain:

where the behavior begins;
where it is validated;
where state is mutated;
where the final result is consumed;
which file owns the behavior;
which tests prove it;
which neighboring areas may regress.