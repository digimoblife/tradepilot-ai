# TradePilot Focused Testing and Evaluation

## Purpose

Use this skill for testing, reviewing, and evaluating TradePilot AI implementation tasks.

Its purpose is to verify the official task efficiently without running unnecessary broad tests, making real Gemini requests, or accepting results based only on an agent summary.

Use it together with:

* `tradepilot-source-lock`;
* the technical skill relevant to the task.

## Core Testing Rule

Run the smallest test set that can prove the official acceptance criteria and detect likely regressions in the affected area.

Do not run the entire repository test suite unless:

* the official task is a phase gate;
* the task explicitly requires broad regression;
* focused tests cannot establish safety;
* the change affects shared infrastructure with broad impact.

More tests are not automatically better. Tests must be relevant, reproducible, and tied to the task.

## Test Selection Workflow

### 1. Read the Official Task

Identify directly from the authoritative task plan:

* objective;
* changed product behavior;
* acceptance criteria;
* in-scope files or layers;
* out-of-scope behavior;
* required verification;
* dependencies and gate requirements.

Do not derive the test plan from memory or from the implementation prompt alone.

### 2. Inspect the Change

Review:

* changed files;
* affected symbols;
* migrations;
* routes;
* schemas;
* service behavior;
* component state ownership;
* existing tests near the affected code;
* possible regression boundaries.

Do not accept a claimed implementation result without inspecting the actual diff or repository state.

### 3. Build a Focused Test Matrix

The matrix must cover:

* direct acceptance criteria;
* primary success path;
* important validation or failure path;
* authorization or ownership where applicable;
* lifecycle eligibility where applicable;
* duplicate-submission or idempotency risk;
* one adjacent regression boundary.

Do not add unrelated test categories merely because they exist elsewhere in the repository.

## Test Levels

Use only the levels needed for the task.

### Unit Tests

Use for:

* pure mapping;
* validation;
* status eligibility;
* state reducers;
* formatting;
* utility behavior.

### Service or Repository Tests

Use for:

* ownership;
* persistence;
* status preservation;
* filtering;
* idempotency;
* transaction behavior;
* data integrity.

### API Tests

Use for:

* endpoint contract;
* authentication;
* authorization;
* validation;
* response shape;
* error behavior;
* lifecycle enforcement.

### Component Tests

Use for:

* action visibility;
* form validation;
* loading and error states;
* responsive composition;
* copy and interaction behavior.

### Focused Integration Tests

Use for:

* route-to-data behavior;
* create-to-detail navigation;
* submission-to-processing recovery;
* archive-to-list movement;
* lifecycle surface transitions.

### Phase-Gate Regression

Use only when the official gate requires multiple tasks or a complete flow to be verified together.

## Gemini and External-Service Rules

Do not make real Gemini requests unless the official task explicitly requires an end-to-end Gemini test.

Prefer:

* mocks;
* fixtures;
* fake providers;
* stored canonical responses;
* existing request records;
* controlled local test data.

Do not change production prompts or provider configuration merely to make a test easier.

No Archive, routing, visual, responsive, accessibility, or ordinary frontend task requires a real Gemini call by default.

## Database Testing Rules

When a task changes persistence:

* test migrations on an empty database;
* test against representative existing data;
* verify defaults;
* verify constraints;
* verify related data remains intact;
* verify rollback only when repository conventions support it;
* never reset or mutate production data.

Migration success alone does not prove domain behavior.

## Frontend Testing Rules

Verify only applicable states:

* loading;
* empty;
* success;
* validation error;
* server error;
* unauthorized;
* not found;
* processing;
* direct URL;
* refresh;
* duplicate submit;
* mobile narrow;
* desktop.

Do not require every frontend task to test every state. Select states according to the official acceptance criteria and risk.

For polling or asynchronous requests, verify:

* only one client owner polls;
* leaving the screen stops unnecessary polling;
* returning recovers backend state;
* refresh does not resubmit;
* completed and failed requests render correctly.

## Regression Boundaries

Always identify the nearest behavior that must remain unchanged.

Examples:

* Archive changes must not alter lifecycle status.
* Route changes must not alter authentication.
* UI refactors must not change API payloads.
* Form movement must not change validation.
* Session-list changes must not expose another owner’s data.
* Responsive fixes must not change action eligibility.
* Restore must not reopen a terminal session.

Test the boundary directly where practical.

## Test Failure Handling

When a focused test fails:

1. determine whether the failure is caused by the current task;
2. compare expected behavior with the authoritative documents;
3. inspect whether the test itself is outdated;
4. fix only within the official task scope;
5. rerun the smallest relevant test set.

Do not rewrite tests to accept incorrect behavior.

Do not fix unrelated failures unless they block task verification. Report unrelated failures separately.

Return `BLOCKED` when resolving a failure requires a product decision or out-of-scope change.

## Evaluation Outcomes

Use exactly these outcomes:

### PASS

Use when:

* all official acceptance criteria are satisfied;
* focused tests pass;
* no material deviation exists;
* no unapproved behavior is introduced.

### PASS WITH LIMITATIONS

Use when:

* acceptance criteria are satisfied;
* focused tests pass or sufficient evidence exists;
* a non-blocking limitation remains;
* the limitation is explicit and does not invalidate the next task.

### FAIL

Use when:

* implementation was attempted;
* one or more acceptance criteria are not satisfied;
* a defect is within scope and should be corrected.

### BLOCKED

Use when:

* authoritative sources conflict;
* required dependency is incomplete;
* repository behavior requires an unapproved product change;
* verification cannot be completed safely;
* resolving the issue exceeds task scope.

Do not label incomplete evidence as PASS.

## Acceptance-Criteria Evaluation

Evaluate every official acceptance criterion separately.

For each criterion, record:

* `PASS`;
* `FAIL`;
* `NOT VERIFIED`;
* `NOT APPLICABLE`, only when justified.

A task cannot receive overall PASS when a required criterion is `FAIL` or `NOT VERIFIED`.

Do not evaluate against acceptance criteria invented in the implementation prompt.

## Result Evidence

Record:

* exact test commands;
* test files;
* pass, fail, skip, and error counts;
* relevant runtime or browser evidence;
* migrations executed;
* fixtures or mocks used;
* whether any real external request occurred;
* limitations in the environment.

Avoid pasting excessive raw logs. Include the lines needed to establish the result.

## Required Review Checks

Before final status, verify:

* changed files match scope;
* no unrelated dependency was added;
* no lifecycle, endpoint, schema, provider, or evidence deviation occurred;
* no hidden fallback masks failure;
* no hardcoded test-only behavior entered production code;
* no skipped test covers a required acceptance criterion;
* next task is not selected from memory.

## BLOCKED Conditions

Return `BLOCKED` when:

* authoritative acceptance criteria cannot be located;
* required test infrastructure is missing and creating it exceeds scope;
* a real Gemini call would be required but is not authorized;
* production data or infrastructure would need to be mutated;
* repository and authoritative behavior conflict;
* a failing test requires an out-of-scope fix;
* an upstream task or phase gate has not passed.

## Required Result Report

Report:

* official task ID and title;
* authoritative sources used;
* changed files reviewed;
* focused test matrix;
* exact commands executed;
* results;
* acceptance-criteria evaluation;
* adjacent regression checks;
* external services used or explicitly not used;
* limitations and deviations;
* final status;
* next official task identified from the authoritative task plan.
