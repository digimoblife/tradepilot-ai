TradePilot AI Project Invariants
Purpose

This document defines the product and engineering rules that must remain true throughout TradePilot AI development.

These invariants apply to all coding agents, including Codex, Antigravity, OpenCode, and human contributors.

They are not implementation suggestions. They are project constraints.

1. Product Identity

TradePilot AI is an AI Trading Workspace that assists users in evaluating and managing a trade thesis.

It is not:

an autonomous trading bot;
a broker;
an automatic order execution system;
a guaranteed signal provider;
a substitute for user judgment.

The AI acts as a trading analyst. The user remains responsible for all trade decisions.

2. One Trade One Story

Each trading session represents one trade lifecycle for one ticker.

A session must preserve:

the original thesis;
uploaded market evidence;
analysis history;
trade state changes;
entry facts;
partial exits;
final exit;
thesis changes over time;
closing evaluation.

Information from different trade sessions must not be mixed.

Each session page must remain a coherent chronological story of one trade.

3. Language Policy

All engineering-facing materials must use English, including:

source code;
code comments;
schemas;
prompts;
specifications;
API documentation;
architecture documents;
implementation instructions;
test descriptions;
agent skills.

All user-facing AI analysis displayed in the product must use Indonesian.

Technical identifiers, enum values, field names, and API payload keys remain in English.

4. AI Responsibility Boundary

AI may:

interpret evidence;
compare current evidence with historical evidence;
explain market conditions;
assess thesis strength;
estimate scenarios and probabilities;
propose a trading plan;
describe uncertainty.

AI must not be the source of truth for deterministic application facts.

The application must calculate or validate deterministic values such as:

average entry price;
average exit price;
realized return;
remaining position quantity;
holding duration;
lifecycle state;
timestamps;
transaction totals;
required state transitions.

AI output must be treated as untrusted structured input until validated.

5. Evidence Integrity

AI analysis must use evidence actually associated with the current session.

The system must not invent:

prices;
orderbook values;
chart patterns;
volume facts;
support or resistance levels;
transaction facts;
session history.

When evidence is missing, unreadable, ambiguous, or inconsistent, the output must state the limitation rather than fabricate certainty.

New evidence supplements historical evidence. It must not silently erase the previous trade thesis or prior analysis.

6. Lifecycle Integrity

Trade state transitions must follow the approved lifecycle.

Expected conceptual states include:

WATCHING
OPEN_POSITION
PARTIAL_EXIT
CLOSED

A transition must:

be explicitly valid;
preserve historical facts;
be transactional when multiple records are affected;
reject illegal transitions;
avoid duplicate effects on retry;
produce a consistent resulting state.

Closing a trade must not leave the database partially updated.

7. Contract Integrity

The following layers must remain synchronized:

JSON Schema;
backend validation models;
domain validation rules;
database storage;
AI prompts;
AI response parsing;
TypeScript types;
frontend rendering;
test fixtures.

A contract change must be identified explicitly as one of:

backward compatible;
breaking;
storage-only;
presentation-only;
internal implementation change.

Do not solve contract mismatches by silently weakening validation.

8. Compact Analysis Principle

User-facing analysis must be:

concise;
actionable;
structured;
readable;
prioritized by decision relevance.

Avoid manual-like, repetitive, or excessively verbose output.

Important conclusions should appear before secondary explanation.

Do not repeat the same market fact across several sections unless necessary for clarity.

9. Context Integrity

Longitudinal analysis must preserve chronology.

Current analysis should distinguish:

what was previously believed;
what new evidence shows;
what changed;
whether the thesis strengthened or weakened;
what action is appropriate next.

Context must be fresh before analysis is queued when freshness is required.

Stale context must not produce rapid retry loops.

Context summaries must remain derived from session evidence and validated historical state.

10. Provider Configuration

Production analysis uses the approved Gemini configuration.

Provider and model names must come from configuration rather than being duplicated as hardcoded values throughout the codebase.

Provider errors must preserve useful sanitized diagnostics.

Do not collapse all provider failures into a generic error that hides the original cause.

Secrets, API keys, authentication headers, and sensitive provider payloads must never be logged.

11. Job Integrity

Background jobs must be:

claim-safe;
retry-aware;
idempotent where required;
terminalized correctly;
observable;
protected against rapid failure loops.

The system must distinguish:

transient provider errors;
permanent provider errors;
invalid configuration;
schema validation failures;
context freshness failures;
internal application failures;
user-correctable evidence problems.

A terminal job must not be automatically restored into an infinite frontend retry cycle.

12. Frontend State Integrity

The backend remains the authoritative source for persistent job and session state.

The frontend must avoid:

duplicate requests;
duplicate polling ownership;
remount loops;
restored failed jobs triggering repeated retries;
stale “processing” states after terminal completion;
unnecessary full-page or full-shell reloads.

Shared resources should have one clear fetch owner or a deduplicated query mechanism.

13. Transaction Safety

Critical multi-record operations must be atomic.

Required patterns include:

explicit transaction boundaries;
row or session locking when concurrent writes are possible;
rollback on failure;
idempotency protection;
consistency verification after commit.

Critical write paths must include rollback tests.

Direct production database mutation is prohibited unless explicitly authorized through an approved operational procedure.

14. Deployment Safety

TradePilot AI may share infrastructure with other projects.

Agents must:

check port usage before binding;
preserve Docker project isolation;
use isolated volumes for local testing;
avoid destructive global Docker commands;
avoid deleting shared networks or volumes;
restart only necessary services;
avoid production databases and production evidence in smoke tests;
review environment changes before deployment.

Commands such as docker system prune, indiscriminate volume deletion, and broad container removal are prohibited.

15. Scope Control

Agents must implement only the requested task.

They must not:

introduce unrelated refactors;
redesign the product without approval;
replace established architecture casually;
add speculative features;
upgrade unrelated dependencies;
change public contracts without declaring it;
modify production infrastructure during local testing.

Small necessary supporting changes are allowed only when clearly connected to the task and reported in the exit summary.

16. Two-Fix Escalation Rule

When two consecutive fix attempts result in any of the following:

a new schema mismatch;
circular behavior;
a new failure in a neighboring layer;
repeated disagreement between expected and actual model output;
repeated changes that only move the error elsewhere;

the agent must stop automatic iteration.

The agent must explain the recurring mismatch and request a product decision among practical options such as:

relax validation;
change the expected contract;
accept the model output as-is;
continue enforcing the original requirement.

The agent must not continue producing speculative fixes without that decision.

17. Verification Standard

A task is not complete merely because code compiles.

Completion requires appropriate evidence such as:

focused tests;
regression tests;
integration tests;
schema validation;
rollback verification;
API verification;
worker verification;
frontend behavior verification;
end-to-end smoke testing when required.

The final report must distinguish:

implemented;
tested;
verified;
not tested;
remaining risk.