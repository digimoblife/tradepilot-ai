# File: `.agent-skills/tradepilot-ai-provider-specialist/SKILL.md`

# TradePilot AI Provider Specialist

## Purpose

Protect the correctness, safety, diagnosability, and contract integrity of TradePilot AI’s Gemini provider integration.

This skill ensures that provider configuration, multimodal requests, production prompts, structured responses, errors, retries, and verification behavior remain aligned with TradePilot AI requirements.

It must prevent:

* silent model changes;
* missing evidence in multimodal requests;
* hidden provider errors;
* unvalidated analysis persistence;
* secret leakage;
* incorrect retry behavior;
* false claims that Gemini was called;
* schema weakening to accommodate inconsistent output.

---

## When to Use

Use this skill for tasks involving:

* Gemini model configuration;
* Gemini SDK integration;
* provider adapters;
* provider routing;
* multimodal evidence submission;
* production prompts;
* request construction;
* structured-output generation;
* response extraction;
* JSON parsing;
* schema validation;
* domain validation;
* token usage;
* provider timeouts;
* retries;
* invalid API keys;
* invalid model names;
* provider failure classification;
* SDK migration;
* production-like smoke testing;
* provider observability.

---

## Required Context

Before implementation or investigation, read:

* `.agent-skills/shared/PROJECT_INVARIANTS.md`;
* `.agent-skills/tradepilot-product-guardian/SKILL.md`;
* `.agent-skills/tradepilot-repository-navigator/SKILL.md`;
* `.agent-skills/tradepilot-test-engineer/SKILL.md`;
* `.agent-skills/shared/EXIT_REPORT_TEMPLATE.md`;
* approved AI provider specifications;
* canonical analysis schemas;
* domain validation rules;
* production prompt files;
* provider adapter code;
* provider routing code;
* worker retry and terminalization logic;
* active environment configuration;
* relevant provider tests.

For provider failures, also read:

* `.agent-skills/tradepilot-debugging-investigator/SKILL.md`;
* `.agent-skills/shared/DEBUGGING_PROTOCOL.md`.

For production-like browser verification, also read:

* `.agent-skills/tradepilot-production-smoke-test-engineer/SKILL.md`;
* `.agent-skills/tradepilot-devops-safety/SKILL.md`.

---

## Core Invariants

The provider integration must preserve:

* approved Gemini-only production behavior;
* configured model selection;
* production prompt usage;
* required multimodal evidence;
* current evidence authority over historical context;
* canonical schema validation;
* domain validation;
* application-owned deterministic calculations;
* sanitized provider diagnostics;
* bounded retry behavior;
* terminal job consistency;
* no secret leakage;
* no false success;
* no silent contract weakening.

AI output is untrusted until validated.

The AI must not become the source of truth for deterministic facts such as:

* lifecycle state;
* entry price calculations;
* average exit price;
* realized return;
* holding duration;
* position quantity;
* persisted timestamps.

---

## Source of Truth

Before editing, identify the authoritative source for:

* provider selection;
* model name;
* API key variable;
* SDK client construction;
* request timeout;
* retry policy;
* generation configuration;
* prompt version;
* context-package structure;
* image-evidence representation;
* response extraction;
* schema validation;
* domain validation;
* error mapping;
* usage metadata;
* provider diagnostics;
* job terminalization.

Do not assume the provider model from comments, examples, or historical configuration.

Do not introduce a second model configuration source.

---

## Mandatory Workflow

### 1. Verify the Active Provider Configuration

Determine:

* active provider;
* active model;
* configuration source;
* environment override behavior;
* provider-order behavior;
* fallback behavior;
* mock-provider behavior;
* deprecated provider paths;
* deprecated SDK usage.

Report sanitized configuration only.

Example:

```text id="pf18yu"
Provider: Gemini
Model: <configured model name>
Configuration source: environment
Fallback provider: disabled
Mock provider: disabled
SDK adapter: backend/app/ai/providers/gemini.py
```

Never print:

* API keys;
* authorization headers;
* complete secret-bearing environment files;
* raw credential objects;
* secret values embedded in exceptions.

---

### 2. Confirm Model Selection Integrity

The active model must come from the approved configuration path.

Verify:

* the model is not hardcoded in multiple files;
* frontend code does not determine the provider model;
* tests do not accidentally override production model selection;
* worker and backend use consistent configuration;
* invalid model tests do not mutate committed production defaults;
* fallback logic does not silently switch models.

If model selection differs from the approved product decision, stop and report it.

---

### 3. Trace the Provider Call Chain

Trace the complete active path:

```text id="p4adlt"
Analysis request
→ Job creation
→ Worker claim
→ Provider router
→ Gemini adapter
→ Prompt assembly
→ Evidence assembly
→ SDK request
→ Provider response
→ Response extraction
→ JSON parsing
→ Schema validation
→ Domain validation
→ Persistence
→ Job terminalization
```

Identify the first provider-specific boundary.

Do not edit the provider adapter before confirming the active call path.

---

### 4. Verify Prompt Selection

Confirm:

* the correct analysis type selects the correct prompt;
* the production prompt version is used;
* system and user prompts are both included where required;
* all required placeholders are resolved;
* no unresolved template token reaches Gemini;
* historical context is included only when approved;
* historical context remains secondary;
* current evidence retains higher authority;
* prompt language requirements are correct;
* user-facing output remains Indonesian;
* engineering instructions remain English.

Do not duplicate large context sections unnecessarily.

---

### 5. Verify Context-Package Construction

Inspect the context package for:

* current session facts;
* current trade state;
* current evidence;
* prior accepted analyses;
* same-ticker history where approved;
* context summary;
* user-confirmed execution facts;
* metadata;
* analysis type;
* authority ordering.

Confirm:

* only the current user’s data is included;
* only the current session’s primary evidence is included;
* historical information is bounded;
* raw provider payloads are excluded unless explicitly required;
* evidence images are not duplicated;
* stale context is refreshed before job execution when required;
* no production or unrelated session data leaks into the request.

---

### 6. Verify Multimodal Evidence

For every required image evidence item, verify:

* evidence record exists;
* file belongs to the current user;
* file belongs to the current session;
* file exists in storage;
* file is readable;
* MIME type is permitted;
* file size is acceptable;
* SDK representation is correct;
* image order is deterministic where required;
* image label or role is preserved;
* missing evidence is handled before provider invocation when required.

Examples of expected evidence roles may include:

* orderbook;
* three-month chart;
* six-month chart.

Do not silently omit an unreadable image and continue as though the request were complete.

---

### 7. Verify Request Construction

Confirm that the provider request contains the approved:

* model;
* system prompt;
* user prompt;
* context package;
* evidence parts;
* generation configuration;
* response-format expectation;
* timeout;
* safety or content settings when applicable.

Check for:

* accidental prompt duplication;
* missing image parts;
* incorrectly serialized JSON;
* incorrect MIME types;
* unsupported SDK argument names;
* hidden fallback values;
* excessive token growth.

Do not log the full request payload in production.

---

### 8. Prove Real Provider Invocation

When a task requires real Gemini verification, prove that:

* the active Gemini adapter was invoked;
* the configured model was used;
* no fake provider was active;
* the SDK request was attempted;
* a provider response or provider-classified failure was received;
* the request is correlated to the correct job and session.

Configuration inspection alone is not proof.

Acceptable evidence may include:

* sanitized provider-request event;
* provider-response event;
* job metadata;
* model metadata;
* provider request identifier where available;
* real terminal provider error.

Do not expose secrets to prove invocation.

---

### 9. Verify Response Extraction

The adapter must safely handle provider responses that may contain:

* valid generated text;
* multiple content parts;
* empty content;
* blocked content;
* partial output;
* finish reasons;
* safety metadata;
* usage metadata;
* SDK warnings;
* provider request identifiers;
* unexpected object shapes.

The extraction layer must not assume:

* response text always exists;
* the first part is always text;
* JSON is always complete;
* provider success means schema success.

Preserve useful sanitized metadata.

---

### 10. Verify JSON Parsing

Provider text must be parsed through the approved parser.

Confirm behavior for:

* valid JSON;
* JSON wrapped in markdown fences;
* leading or trailing explanatory text;
* incomplete JSON;
* duplicate fields;
* invalid number formats;
* null values;
* unexpected arrays;
* unexpected objects;
* unsupported additional fields.

Do not write ad hoc parsing logic in multiple locations.

Do not use permissive extraction that hides malformed provider output.

---

### 11. Verify Canonical Schema Validation

After parsing, validate against the approved canonical schema.

Verify:

* required fields;
* field types;
* enum values;
* numeric bounds;
* nested structures;
* nullability;
* additional-property rules;
* analysis-type-specific requirements;
* schema version.

A JSON object is not accepted merely because it parses.

Do not silently drop invalid fields and mark the analysis accepted unless the approved contract explicitly permits normalization.

---

### 12. Verify Domain Validation

After schema validation, apply approved domain rules.

Examples may include:

* probability ranges;
* probability relationships;
* target and stop consistency;
* lifecycle compatibility;
* evidence-source requirements;
* current-state compatibility;
* scenario consistency;
* execution-fact preservation.

Schema-valid output may still be domain-invalid.

Do not move domain logic into prompts as a substitute for application validation.

---

### 13. Preserve Application-Owned Facts

Where required, enrich or override output with deterministic application values.

Examples:

* session identifiers;
* job identifiers;
* timestamps;
* lifecycle state;
* entry calculations;
* exit calculations;
* holding duration;
* accepted evidence metadata.

The provider must not overwrite canonical execution facts.

Historical provider output must not override current user-confirmed facts.

---

### 14. Persist Only Accepted Output

Persistence must occur only after:

1. response extraction;
2. JSON parsing;
3. canonical schema validation;
4. domain validation;
5. deterministic application enrichment where required.

Rejected output may be retained only in an approved protected diagnostic location.

Do not:

* store malformed output as an accepted analysis;
* mark the job successful before commit;
* expose rejected raw output to the user;
* create duplicate accepted analyses during retry.

---

### 15. Preserve Provider Failure Diagnostics

Provider failures should retain sanitized:

* provider;
* model;
* error category;
* provider error code where available;
* provider message;
* relevant details;
* timeout classification;
* retryability;
* root-cause message;
* attempt number;
* job ID;
* session ID.

Do not collapse all failures into:

```text id="nsrc8e"
PROVIDER_ROUTING_FAILED
```

without preserving the original sanitized cause.

User-facing messages may be simpler, but internal diagnostics must remain actionable.

---

### 16. Classify Failure Types

Classify provider-related failures into stable categories.

Recommended categories:

* provider authentication failure;
* invalid model;
* invalid request;
* provider rate limit;
* provider unavailable;
* network failure;
* timeout;
* blocked response;
* empty response;
* malformed response;
* JSON parse failure;
* schema validation failure;
* domain validation failure;
* adapter internal failure;
* unknown provider failure.

Do not treat validation failures as network failures.

Do not retry permanent configuration errors as though they were transient.

---

### 17. Verify Retry Behavior

For every failure class, determine:

* retryable or non-retryable;
* maximum attempts;
* backoff policy;
* terminal status;
* user-facing behavior;
* diagnostic behavior.

Permanent failures usually include:

* invalid API key;
* invalid model;
* invalid request;
* deterministic schema mismatch;
* deterministic domain validation failure.

Potentially transient failures may include:

* network interruption;
* provider service unavailable;
* rate limit;
* timeout.

Retries must be bounded.

Do not allow rapid retry loops.

---

### 18. Protect Secrets

Sanitize all provider-related output.

Never log:

* API keys;
* authorization headers;
* complete provider requests;
* raw evidence bytes;
* secret-bearing environment dumps;
* full prompts containing sensitive session data;
* unrestricted raw provider output.

Tests should verify that known secret strings do not appear in:

* logs;
* job failure messages;
* API responses;
* frontend messages;
* test artifacts.

---

### 19. Verify Usage and Payload Discipline

Where the SDK provides usage metadata, inspect:

* prompt tokens;
* output tokens;
* total tokens;
* cached tokens where applicable;
* image count;
* request duration;
* output length.

Also assess:

* historical context size;
* repeated context sections;
* duplicated evidence;
* prompt verbosity;
* output verbosity.

Report significant growth.

Do not reduce required safety or contract instructions merely to save tokens.

---

## Required Failure Tests

Provider-sensitive changes should include the relevant scenarios below.

### A. Invalid API Key

Verify:

* provider authentication failure is classified;
* the key is never printed;
* no unintended fallback occurs;
* retries follow policy;
* job reaches terminal failure;
* frontend exits processing;
* no successful analysis is persisted;
* internal diagnostic cause remains available.

---

### B. Invalid Model

Verify:

* invalid-model or configuration failure is classified;
* sanitized model name is preserved;
* no silent fallback to another model occurs;
* retries follow policy;
* job terminalizes;
* frontend exits processing;
* no false successful analysis is created.

---

### C. Timeout

Verify:

* timeout is bounded;
* timeout category is preserved;
* retryability is correct;
* attempt count is visible;
* retries stop at the approved limit;
* terminal state is reached.

---

### D. Rate Limit

Verify:

* rate-limit failure is distinguished from authentication failure;
* retry behavior follows approved backoff;
* retry count is bounded;
* provider details are sanitized;
* user-facing behavior is appropriate.

---

### E. Malformed JSON

Verify:

* parsing fails safely;
* no accepted analysis is created;
* job failure classification is correct;
* parse error does not expose sensitive raw output;
* regression fixture reproduces the malformed shape.

---

### F. Schema-Invalid JSON

Verify:

* JSON parsing succeeds;
* schema validation fails;
* field path is preserved;
* no silent field dropping occurs;
* no accepted analysis is persisted;
* retry policy is correct.

---

### G. Domain-Invalid Output

Verify:

* schema validation succeeds;
* domain validation fails;
* domain rule is identified;
* no accepted analysis is persisted;
* application facts remain unchanged.

---

### H. Empty Response

Verify:

* empty content is detected;
* no null-reference exception occurs;
* provider-response failure is classified;
* job terminalizes correctly.

---

### I. Blocked Response

Verify:

* blocked or safety-limited response is detected;
* blocking metadata is preserved where safe;
* no false successful analysis is created;
* frontend receives a safe failure state.

---

### J. Missing Required Evidence

Verify:

* validation fails before provider invocation when required;
* Gemini is not called;
* user receives corrective guidance;
* no unnecessary provider cost is incurred;
* job behavior matches approved architecture.

---

## Real Versus Mocked Verification

Every provider-related test must identify the provider boundary as:

* real;
* mocked;
* simulated;
* not applicable.

Examples:

```text id="5k5u2q"
Success flow: real Gemini
Invalid API key: real Gemini authentication failure
Malformed output: mocked provider fixture
Schema validation: real application validator
```

Do not combine results without distinguishing them.

A mocked provider test does not prove real Gemini compatibility.

A real Gemini call does not replace deterministic malformed-response fixtures.

---

## SDK Migration Rules

When migrating Gemini SDKs:

1. identify deprecated SDK behavior;
2. map old request construction to new SDK behavior;
3. preserve model configuration;
4. preserve system and user prompts;
5. preserve image evidence;
6. preserve timeout behavior;
7. preserve retry classification;
8. preserve error diagnostics;
9. preserve response extraction;
10. preserve schema validation;
11. add adapter regression tests;
12. run isolated real-provider verification when required.

Do not combine SDK migration with:

* schema redesign;
* prompt redesign;
* lifecycle refactor;
* broad provider-routing rewrite;
* unrelated dependency upgrades.

Unless explicitly required, keep the migration narrowly scoped.

---

## Two-Fix Escalation Rule

Track provider or contract fix attempts for the same issue.

Stop after two consecutive attempts when:

* model output still violates the same contract in a different shape;
* schema changes create new mismatches;
* prompt changes move the failure to another field;
* parser changes hide one error but expose another;
* the system alternates between two failure modes;
* validation and model behavior remain irreconcilable.

Report:

```text id="30bk1f"
Attempt 1:
Hypothesis:
Change:
Result:

Attempt 2:
Hypothesis:
Change:
Result:

Recurring mismatch:
Provider behavior:
Application contract:
Decision required:
```

Request a product decision among practical options:

1. relax validation;
2. change the expected contract;
3. accept the model output as-is;
4. continue enforcing the original requirement.

Do not apply a third speculative prompt/schema/parser correction without direction.

---

## Prohibited Actions

Do not:

* hardcode API keys;
* print secrets;
* silently switch models;
* silently enable fallback providers;
* claim real Gemini use from configuration alone;
* claim real Gemini use from mocked tests;
* omit required evidence;
* accept unvalidated output;
* persist malformed output as successful analysis;
* suppress provider diagnostics;
* retry permanent failures indefinitely;
* weaken canonical schemas without approval;
* modify both prompt and schema repeatedly without escalation;
* expose raw evidence or full provider prompts in logs;
* blame the provider without tracing the adapter boundary;
* report `VERIFIED` when the real provider boundary was not exercised as required.

---

## Contract Impact Requirement

Every task must classify provider-related contract impact as one of:

* no contract change;
* internal provider implementation change;
* backward-compatible provider metadata change;
* backward-compatible prompt change;
* backward-compatible schema handling change;
* breaking analysis contract change;
* configuration-only change;
* test-only change.

Explicitly identify affected:

* prompts;
* schemas;
* API fields;
* stored metadata;
* frontend types;
* error codes;
* retry behavior.

Do not omit this section.

---

## Required Pre-Implementation Output

Before editing, report:

```text id="if87v5"
Active provider:
Active model:
Configuration source:
Provider router:
Adapter entry point:
SDK:
Prompt version:
Context-package source:
Evidence mode:
Response extractor:
JSON parser:
Schema validator:
Domain validator:
Retry policy:
Error mapping:
Real provider verification plan:
Failure tests:
Expected contract impact:
Blast radius:
```

---

## Required Completion Output

Use:

```text id="70lx7b"
.agent-skills/shared/EXIT_REPORT_TEMPLATE.md
```

Additionally report:

* active provider;
* active model;
* configuration source;
* SDK used;
* prompt version;
* evidence count and roles;
* real or mocked invocation;
* provider request result;
* response extraction result;
* JSON parsing result;
* schema validation result;
* domain validation result;
* persistence result;
* provider error classifications tested;
* retry behavior;
* secret-sanitization result;
* usage metadata where available;
* exact commands;
* acceptance evidence;
* final Git working-tree status;
* blocking risks;
* non-blocking residual risks;
* untested provider boundaries.

---

## Verification Claims

Use precise language.

### TESTED

Use when provider-related automated tests pass but the required real Gemini path was not executed.

### VERIFIED

Use only when:

* the configured Gemini adapter was invoked;
* the expected model was used;
* required evidence was included;
* a real provider response or provider-classified failure occurred;
* response handling was exercised;
* validation and persistence behavior were confirmed;
* secrets remained protected;
* acceptance evidence was recorded.

### IMPLEMENTED_NOT_FULLY_VERIFIED

Use when the implementation is complete but real-provider verification could not be completed.

Examples:

* API credentials unavailable;
* provider outage;
* rate limit;
* network restriction;
* browser smoke flow not completed.

---

## Residual Risk Requirement

Do not default to:

```text id="b7yvb0"
Risks: None
```

Consider:

* provider behavior variability;
* SDK version differences;
* token-cost growth;
* model output drift;
* provider rate limits;
* timeout sensitivity;
* incomplete malformed-output coverage;
* untested blocked responses;
* differences between local and production secrets;
* deprecated SDK paths still present;
* model configuration duplicated elsewhere;
* provider diagnostics unavailable at one boundary.

Use:

```text id="r5ump7"
No blocking risks identified.
```

only when justified, followed by realistic non-blocking risks.

---

## Exit Criteria

This skill is complete when:

* the active Gemini configuration is verified;
* the model source of truth is clear;
* prompt and context assembly are correct;
* required evidence is included;
* real invocation is proven when required;
* provider responses are extracted safely;
* JSON, schema, and domain validation run;
* only accepted output is persisted;
* provider errors preserve sanitized root cause;
* retries are bounded and correctly classified;
* secrets remain protected;
* verification claims match the actual provider boundary exercised.
