# TradePilot Database Migration Safety

## Purpose

Use this skill for every TradePilot AI task that changes database models, constraints, indexes, enums, defaults, or migration files.

Its purpose is to protect production data, preserve compatibility, and prevent migrations from silently changing approved product behavior.

Use it together with:

- `tradepilot-source-lock`;
- the relevant domain skill;
- `tradepilot-focused-testing`.

## Core Safety Rule

A migration must make the smallest database change required by the official task.

Do not use a migration to introduce unapproved:

- lifecycle statuses;
- analysis types;
- evidence types;
- providers;
- abstractions;
- tables;
- data rewrites;
- cleanup.

Existing repository structure does not justify changing the authoritative product contract.

## Pre-Migration Inspection

Before editing, inspect:

- canonical model and table;
- current migration head;
- naming conventions;
- foreign keys;
- constraints;
- indexes;
- defaults;
- nullability;
- timestamp and timezone conventions;
- related repository queries;
- representative existing data assumptions.

Confirm there is only one canonical target entity.

Return `BLOCKED` if multiple competing models or tables make the authoritative target unclear.

## Migration Design Rules

Prefer additive and backward-compatible changes.

Safe examples include:

- nullable column addition;
- non-destructive index addition;
- constraint addition only after existing data compatibility is proven;
- staged population followed by staged constraint enforcement when required.

Avoid:

- dropping columns or tables;
- renaming without compatibility planning;
- destructive type conversion;
- full-table rewrite without necessity;
- adding a non-null column without a safe default or staged migration;
- changing enum values outside the official task;
- replacing canonical identifiers;
- resetting migration history.

Do not edit an already-applied migration unless repository policy explicitly permits it and deployment history proves it is safe. Prefer a new migration.

## Existing Data Preservation

The migration must preserve:

- session records;
- ownership;
- evidence;
- analyses;
- decisions;
- positions;
- closure data;
- requests;
- timestamps;
- foreign-key relationships.

Do not delete, recreate, detach, or silently normalize production records unless the authoritative task explicitly requires a reviewed data transformation.

For Archive, existing sessions must remain non-archived through a nullable archive field or equivalent approved default.

## Defaults and Nullability

Every new field must have an explicit reason for:

- nullable or non-null;
- server default;
- application default;
- backfill behavior.

Avoid permanent server defaults when they are needed only for migration compatibility.

A model default and database default must not conflict.

Do not use placeholder values to satisfy non-null constraints when the product has no valid value.

## Enum and Constraint Rules

Treat lifecycle, request status, analysis type, evidence type, provider, and decision enums as product contracts.

Do not add, remove, or rename enum values unless explicitly required by the authoritative task.

For new constraints:

1. inspect existing data;
2. prove current rows comply;
3. add focused tests;
4. ensure application validation and database validation agree.

Do not weaken a constraint merely to make existing incorrect code pass.

## Index Rules

Add an index only when justified by an approved query pattern or demonstrated repository need.

Verify:

- indexed columns match actual filters and ordering;
- owner isolation remains efficient;
- duplicate indexes are not created;
- index naming follows repository conventions;
- write overhead is proportionate.

Do not add speculative indexes.

## Transaction and Lock Awareness

Assess whether the migration may:

- lock a large table;
- rewrite all rows;
- block active reads or writes;
- exceed normal deployment tolerance.

Prefer metadata-only or staged operations where supported.

If production table size or lock risk cannot be determined and the operation may be disruptive, return `BLOCKED` or document a required deployment decision.

## Upgrade and Downgrade

Upgrade must always be implemented and tested.

Implement downgrade only when repository conventions require it.

A downgrade must not pretend to be safe when it would destroy data. Where rollback is inherently destructive, document that limitation clearly.

Do not test migrations against production infrastructure.

## Migration Verification

Minimum applicable checks:

- migration applies to an empty test database;
- migration applies to a database at the previous revision;
- representative existing rows remain intact;
- defaults and nullability behave as intended;
- constraints accept valid rows and reject invalid rows;
- indexes and foreign keys exist as expected;
- application model matches the migrated schema;
- relevant repository/service tests pass.

Where practical, verify the schema directly rather than relying only on migration command success.

## Data Backfill Rules

A backfill must be:

- explicitly required;
- deterministic;
- scoped;
- restart-safe where appropriate;
- tested against representative rows;
- separated from unrelated cleanup.

Do not infer missing business data.

If correct backfill values cannot be determined from authoritative records, return `BLOCKED`.

## Deployment Compatibility

Plan for the actual deployment sequence.

When backend and database may be deployed separately:

- the old application should tolerate the new schema where practical;
- the new application should tolerate the migration state expected at startup;
- newly added nullable fields should not break old reads;
- removing compatibility must occur only in a later approved task.

Do not assume an atomic deployment unless the deployment system guarantees it.

## Failure Handling

If migration testing fails:

1. stop further implementation;
2. inspect the exact schema state;
3. determine whether partial changes were applied;
4. repair only within the official task;
5. recreate the test environment if needed;
6. rerun from the previous clean revision.

Never continue from an uncertain schema state.

Never use manual production SQL as an undocumented substitute for a migration.

## BLOCKED Conditions

Return `BLOCKED` when:

- the canonical table or model is unclear;
- authoritative documents and schema requirements conflict;
- existing data violates a required new constraint and remediation is not approved;
- safe backfill values cannot be determined;
- the migration requires destructive production changes;
- migration ordering conflicts with existing heads;
- deployment compatibility cannot be maintained;
- table-lock or data-volume risk is material and unknown;
- the task requires resetting or recreating production data.

## Required Result Report

Report:

- official task ID and title;
- authoritative sources reread;
- previous and new migration revision;
- tables, columns, constraints, and indexes changed;
- nullability, defaults, and backfill behavior;
- compatibility assessment;
- exact migration test commands;
- representative data verification;
- focused application tests;
- downgrade behavior or limitation;
- detected risks;
- deviations;
- final status.