TradePilot Product Guardian
Purpose

Protect TradePilot AI product intent, domain boundaries, language policy, scope, and non-negotiable invariants during implementation and review.

This skill acts as the product constitution for technical agents.

When to Use

Use this skill for every TradePilot AI task involving:

product behavior;
API behavior;
AI analysis;
schemas;
lifecycle state;
frontend presentation;
prompts;
database changes;
worker behavior;
deployment;
testing;
documentation.

This skill should be loaded before specialist skills.

Required Context

Read:

.agent-skills/shared/PROJECT_INVARIANTS.md
relevant product and engineering specifications;
canonical schemas related to the task;
current implementation before proposing changes.

Do not rely solely on task wording when repository source-of-truth documents are available.

Source of Truth Priority

When sources disagree, use this order:

explicit current product decision;
canonical schema or approved specification;
domain validation rules;
current tests expressing approved behavior;
current implementation;
historical documentation or comments.

Do not treat outdated comments as authoritative.

Report contradictions instead of choosing silently.

Mandatory Workflow
1. Classify the Task

Identify whether the task changes:

product behavior;
domain behavior;
contract;
storage;
presentation;
infrastructure;
internal implementation only.
2. Identify Relevant Invariants

List the invariants affected by the task.

Examples:

One Trade One Story;
lifecycle validity;
deterministic calculations;
Indonesian user-facing output;
compact analysis;
provider diagnostics;
transaction atomicity.
3. Check for Product Decisions

Determine whether implementation requires an unresolved decision.

Examples:

changing required schema fields;
accepting different model output;
altering lifecycle semantics;
weakening evidence requirements;
changing probability interpretation;
changing session ownership.

Do not make such decisions implicitly.

4. Guard Scope

Ensure the planned change is limited to the requested result.

Reject unrelated cleanup, speculative features, or architectural replacement.

5. Verify User-Facing Consequences

Confirm that the resulting behavior remains understandable and aligned with TradePilot AI’s analyst role.

6. Report Contract Impact

Every final report must state whether there was a contract or product behavior change.

Product Invariants

The agent must preserve:

AI analyst role, not autonomous trader;
one trade lifecycle per session;
chronological evidence history;
Indonesian user-facing analysis;
English engineering artifacts;
application-owned deterministic calculations;
validated AI output;
compact and actionable analysis;
explicit uncertainty;
legal lifecycle transitions;
atomic critical writes;
safe provider diagnostics;
safe deployment practices.
Prohibited Actions

Do not:

add automatic trade execution;
produce guaranteed trading outcomes;
mix evidence between sessions;
allow AI to define deterministic trade facts;
silently change schema expectations;
silently relax validation;
remove historical thesis context;
expose raw provider secrets;
add features outside the current scope;
redesign the session lifecycle without approval;
convert concise analysis back into long manual-style output;
continue after the two-fix escalation threshold without a product decision.
Validation Requirements

Before completion, confirm:

the task preserves relevant project invariants;
user-facing language remains correct;
source-of-truth ownership remains clear;
contract impact is declared;
lifecycle behavior is valid;
critical deterministic values are application-calculated;
tests cover the intended behavior;
no unrelated product behavior changed.
Escalation Rules

Escalate when:

specifications conflict;
a schema and approved model behavior cannot both be satisfied;
a requested change alters core lifecycle semantics;
evidence requirements need to be relaxed;
two fix attempts produce repeated or circular mismatches;
the correct behavior depends on a product preference rather than an engineering fact.

Present concrete options and consequences.

Expected Output

Before implementation, provide a concise task interpretation containing:

goal;
affected product behavior;
relevant invariants;
expected contract impact;
scope boundaries.

At completion, use the shared exit report template.

Exit Criteria

This skill’s responsibilities are complete when:

product intent is preserved;
unresolved product decisions are surfaced;
scope remains controlled;
contract impact is explicit;
user-facing consequences are verified;
the implementation does not violate project invariants.