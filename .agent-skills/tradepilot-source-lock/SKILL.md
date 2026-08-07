# TradePilot Source-Lock Workflow

## Purpose

Use this skill for every TradePilot AI planning, implementation, review, debugging, and evaluation task.

Its purpose is to prevent product drift by ensuring that authoritative documents, not memory or existing repository behavior, define the work.

## Authoritative Sources

Before determining, implementing, or evaluating any task, directly reread the applicable authoritative documents:

1. TradePilot AI PRD v2.
2. TradePilot AI PRD Amendment.
3. The current authoritative Detailed Task Plan.
4. Any approved initiative-specific PRD or task plan explicitly referenced by the official task.

Do not rely on prior chat summaries, remembered task numbers, previous prompts, or patterns from earlier tasks.

## Required Workflow

### 1. Read the Official Task

Locate the task directly in the authoritative task plan.

Preserve exactly:

* task ID;
* task title;
* official sequence;
* objective;
* lifecycle rules;
* endpoint or schema requirements;
* in-scope work;
* out-of-scope work;
* acceptance criteria;
* gate dependencies;
* BLOCKED conditions.

Do not rename, merge, reorder, expand, or reinterpret the official task.

Internal subtasks may use suffixes such as `UX1.2a`, but they must remain under the official task and must not become new official tasks.

### 2. Inspect the Repository

Inspect the current branch and identify:

* relevant files and symbols;
* existing behavior;
* reusable components;
* tests covering the affected area;
* repository behavior that conflicts with the authoritative sources.

Existing code describes the current implementation, not the approved product.

Do not treat existing routes, schemas, statuses, abstractions, providers, or components as authoritative unless they match the approved documents.

### 3. Produce Source Lock

Every implementation prompt or evaluation must include a `Source Lock` section stating:

* the authoritative documents reread;
* the exact official task ID and title;
* the current repository baseline inspected;
* the rule that authoritative documents override repository behavior.

### 4. Produce Scope Diff

Every implementation prompt must include a `Scope Diff` section describing:

* current repository behavior;
* required behavior from the official task;
* the smallest change needed to close that gap;
* behaviors that must remain unchanged.

If no repository difference exists, do not invent work. Report that the task may already be satisfied and verify it against the acceptance criteria.

### 5. Enforce Scope

Only perform work required by the official task.

Do not add:

* new features;
* new lifecycle statuses;
* new analysis types;
* new AI providers;
* new evidence rules;
* speculative abstractions;
* unrelated refactors;
* visual or copy changes outside the task;
* cleanup not required for acceptance.

One prompt must execute one official task only.

### 6. Handle Conflicts

Return `BLOCKED` when:

* repository behavior conflicts with an authoritative requirement and resolving it requires a product decision;
* authoritative documents conflict with each other;
* required upstream work is incomplete;
* the requested change exceeds the official task;
* an endpoint, schema, lifecycle rule, or acceptance criterion would need to be changed;
* required source documents cannot be found or read.

A BLOCKED result must state:

1. the exact conflict;
2. the authoritative requirement;
3. the repository evidence;
4. why proceeding would create product drift;
5. the product decision required.

Do not silently choose a workaround.

## Evaluation Rules

Evaluate implementation results against the original official task, not against the generated prompt or the agent’s summary.

Verify:

* changed files match the permitted scope;
* official acceptance criteria are satisfied;
* out-of-scope behavior was not introduced;
* required focused tests passed;
* lifecycle, data, endpoint, and provider contracts remain unchanged unless explicitly required;
* limitations and deviations are clearly reported.

Use only these outcomes:

* `PASS`: all acceptance criteria are satisfied with no material deviation.
* `PASS WITH LIMITATIONS`: acceptance criteria are satisfied, but a documented non-blocking limitation remains.
* `BLOCKED`: implementation cannot safely proceed or acceptance cannot be established.
* `FAIL`: implementation was attempted but does not satisfy the official task.

## Next-Task Rule

Never determine the next task from memory.

After completing or evaluating a task:

1. reread the authoritative task plan;
2. confirm the current task status;
3. verify its phase gate or dependency;
4. identify the next official task directly from the document.

Do not skip a phase gate or begin a dependent task early.

## Required Result Report

Every result report must include:

* official task ID and title;
* authoritative sources used;
* repository baseline;
* files changed;
* implementation summary;
* tests executed and results;
* acceptance-criteria evaluation;
* scope deviations;
* limitations;
* final status;
* next task identified from the authoritative task plan.
