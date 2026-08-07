# TradePilot Archive Backend

## Purpose

Use this skill for TradePilot AI database, domain, repository, service, API, and test tasks related to session archiving.

This skill must always be used together with:

* `tradepilot-source-lock`;
* `tradepilot-focused-testing` when implementation or evaluation is performed.

Its purpose is to add Archive safely without changing the approved trading lifecycle.

## Core Product Rule

Archive is an organizational state, not a trading lifecycle status.

Never add:

* `ARCHIVED` to the session status enum;
* an Archive lifecycle transition;
* an Archive analysis type;
* a separate archived-session business entity;
* behavior that treats Archive as deletion.

The canonical terminal status must remain:

* `CLOSED`; or
* `CLOSED_SKIPPED`.

Archive metadata may be represented by a nullable field such as:

```text
archived_at: timestamp | null
```

Use the repository’s established timestamp, timezone, naming, and migration conventions.

## Archive Eligibility

A session may be archived only when its canonical status is:

* `CLOSED`; or
* `CLOSED_SKIPPED`.

Archive must be rejected for every non-terminal state, including:

* `NEW`;
* `ANALYZING` where represented;
* `INITIAL_ANALYZED`;
* `WAITING`;
* `OPEN_POSITION`.

The backend must enforce this rule even when the frontend hides the action.

Never rely on frontend visibility as the eligibility control.

## Archive Behavior

A successful Archive action must:

1. verify authentication and session ownership;
2. verify terminal status;
3. set the approved archive metadata;
4. preserve the terminal lifecycle status;
5. preserve all related records;
6. remove the session from the default non-archived list;
7. make the session available in the archived list;
8. keep direct read access available to the owner.

Archive must not:

* delete the session;
* delete or move evidence;
* delete or regenerate analyses;
* alter decisions;
* alter position data;
* alter closure data;
* cancel or create analysis requests;
* change chronological trading history;
* reopen or close a session;
* call Gemini.

## Restore Behavior

Restore is an organizational action that returns an archived session to the completed-session list.

A successful Restore action must:

1. verify authentication and ownership;
2. verify that the session is archived;
3. clear the archive metadata;
4. preserve `CLOSED` or `CLOSED_SKIPPED`;
5. keep the session read-only;
6. return the session only to the completed grouping.

Restore must not:

* change the session to an active status;
* enable BUY, WAIT, SKIP, Position Update, or Close;
* recreate evidence or analysis requests;
* reopen a position;
* create a new trading lifecycle event unless explicitly approved.

User-facing wording may use “Return to List,” but the backend contract must remain unambiguous.

## Persistence Rules

Prefer extending the canonical session record with minimal nullable archive metadata.

Do not create a separate archive table unless an authoritative task explicitly requires it.

Migration requirements:

* backward-compatible;
* no database reset;
* no destructive data migration;
* existing sessions default to non-archived;
* new sessions default to non-archived;
* canonical terminal statuses remain unchanged;
* indexes must be justified by actual query patterns.

Do not add `archived_by` unless required by the authoritative task or existing multi-user audit convention.

## Repository and Query Rules

The default Sessions query must exclude archived sessions.

The Archived Sessions query must include only archived sessions.

Both queries must:

* enforce owner isolation;
* preserve approved ordering;
* avoid leaking another user’s sessions;
* return only the fields required by the API contract.

Direct detail retrieval must continue to support archived sessions for their owner.

Do not duplicate repository logic when an existing scoped query can be safely extended.

## API Rules

Use endpoint names and HTTP conventions established by the repository and official task.

The API must support:

* listing non-archived sessions;
* listing archived sessions;
* archiving an eligible session;
* restoring an archived session;
* reading archived-session detail.

Responses must provide enough canonical data for the frontend to determine:

* terminal status;
* whether the session is archived;
* archive timestamp where approved;
* whether Archive or Restore is currently available.

Controlled errors must distinguish applicable cases such as:

* unauthenticated;
* unauthorized;
* not found;
* ineligible lifecycle state;
* already archived;
* not archived;
* validation or persistence failure.

Do not expose another user’s session existence through differing unauthorized responses if repository security conventions prevent it.

## Idempotency

Follow existing repository conventions.

Where the official task does not specify behavior:

* repeated Archive must not mutate lifecycle data;
* repeated Restore must not reopen or alter the session;
* duplicate requests must not create additional records.

Do not invent silent-success behavior if the existing API convention uses explicit conflict or validation errors. Document the chosen existing convention in Scope Diff.

## History and Audit

Archive metadata is separate from the trading-analysis timeline by default.

Do not add “session archived” or “session restored” as a trading history event unless explicitly approved.

Existing `updated_at` behavior must follow repository conventions. Do not change it solely to make Archive appear in the trading timeline.

## Focused Verification

Minimum applicable tests:

* archive `CLOSED`;
* archive `CLOSED_SKIPPED`;
* reject every non-terminal status;
* owner can archive own session;
* user cannot archive another user’s session;
* status remains terminal after Archive;
* all related records remain intact;
* default list excludes archived session;
* archived list includes archived session;
* archived detail remains readable;
* Restore clears archive metadata;
* Restore preserves terminal status;
* Restore does not re-enable lifecycle actions;
* migration preserves existing data;
* repeated Archive and Restore follow repository idempotency conventions.

No real Gemini request is permitted for Archive tests.

## BLOCKED Conditions

Return `BLOCKED` when:

* implementation requires an `ARCHIVED` lifecycle status;
* the canonical session entity cannot be identified;
* terminal status rules conflict across authoritative documents;
* ownership enforcement is unclear or absent;
* archive requires deleting, moving, or rewriting related records;
* Restore would require reopening the lifecycle;
* repository and authoritative API requirements conflict;
* migration cannot be made backward-compatible;
* the requested task includes bulk archive, deletion, search, tags, or other unapproved features.

## Required Result Report

Report:

* official task ID and title;
* authoritative sources reread;
* persistence and migration changes;
* service and API behavior;
* ownership and eligibility enforcement;
* query filtering behavior;
* files changed;
* focused tests and results;
* proof that terminal status and related records remain unchanged;
* deviations or limitations;
* final status.
