# **SCHEMA\_VALIDATION\_SPEC.md**

## **TradePilot AI Schema Validation Specification**

**Document Version:** 1.0  
**Status:** Draft for Implementation  
**Applies To:** Production schema package v1.0.0  
**Primary Runtime:** Python backend  
**Schema Standard:** JSON Schema Draft 2020-12

---

## **1\. Purpose**

This document defines how TradePilot AI validates structured data generated or consumed by the application.

The validation system must ensure that:

* AI output follows the correct JSON contract;  
* payloads match the active schema version;  
* schema references resolve correctly;  
* business rules remain consistent with canonical Trade State;  
* invalid provider output is repaired or rejected safely;  
* AI recommendations never overwrite confirmed trade facts;  
* historical payloads remain readable after future schema changes.

Validation is performed in multiple layers because JSON Schema alone cannot enforce all trading, lifecycle, and calculation rules.

---

## **2\. Validation Principles**

### **2.1 Canonical Trade State is authoritative**

`trade_state.schema.json` represents the current confirmed business state.

When AI output conflicts with Trade State:

* Trade State wins;  
* the AI output is rejected or corrected;  
* no automatic state mutation is allowed.

### **2.2 AI output is untrusted until validated**

Output from Gemini or DeepSeek must be treated as untrusted external input.

It must not be:

* stored as an accepted analysis;  
* rendered as final user-facing analysis;  
* used to update context memory;  
* used to propose lifecycle transitions;

until validation succeeds.

### **2.3 Validation is layered**

The validation pipeline consists of:

1. transport validation;  
2. JSON parsing;  
3. schema registry validation;  
4. JSON Schema validation;  
5. domain validation;  
6. canonical-state consistency validation;  
7. lifecycle validation;  
8. narrative and safety validation;  
9. persistence validation.

### **2.4 Unknown values use `null`**

Unknown numeric values must never be represented as zero.

Example:

{  
  "average": null  
}

Not:

{  
  "average": 0  
}

### **2.5 Recommendations are not executions**

AI-generated changes to entry, stop loss, target, quantity, partial exit, or full exit remain proposals until explicitly confirmed by the user.

---

## **3\. Validation Architecture**

Recommended components:

SchemaRegistry  
    |  
    v  
JsonSchemaValidator  
    |  
    v  
DomainValidatorRegistry  
    |  
    v  
TradeStateConsistencyValidator  
    |  
    v  
LifecycleValidator  
    |  
    v  
ValidatedAnalysisService

### **3.1 Schema Registry**

Responsible for:

* loading `manifest.json`;  
* registering active schemas;  
* resolving schema IDs;  
* resolving local `$ref` dependencies;  
* exposing schema by name and version;  
* rejecting unknown or inactive schemas;  
* caching compiled validators.

### **3.2 JSON Schema Validator**

Responsible for:

* structural validation;  
* required fields;  
* field types;  
* enum values;  
* nullability;  
* conditional schema rules;  
* additional property rejection;  
* format validation.

### **3.3 Domain Validator Registry**

Responsible for business rules that are not practical or reliable to express in JSON Schema.

Examples:

* `high >= low`;  
* target above entry for a long position;  
* remaining quantity consistency;  
* weighted average exit;  
* percentage calculations;  
* timeline ordering.

### **3.4 Trade State Consistency Validator**

Compares AI output against canonical Trade State.

Examples:

* entry price must match confirmed entry;  
* remaining quantity must match current state;  
* active stop must match confirmed stop;  
* proposed stop must not be treated as active;  
* session ticker must match analysis ticker.

### **3.5 Lifecycle Validator**

Ensures the requested analysis type is valid for the current session status.

---

## **4\. Schema Registry Startup**

At application startup, the backend must load:

schemas/production/v1/manifest.json

The loader must then:

1. validate the manifest structure;  
2. confirm manifest status is `ACTIVE`;  
3. register every active schema;  
4. load schema files from the declared paths;  
5. confirm each file `$id` matches `schema_id`;  
6. confirm schema version matches manifest version;  
7. resolve all `$ref` dependencies;  
8. compile each schema validator;  
9. fail startup if a required production schema cannot load.

Production must not start with a partially loaded schema registry.

---

## **5\. Schema Registry Data Model**

Recommended Python models:

from dataclasses import dataclass  
from pathlib import Path  
from typing import Any

@dataclass(frozen=True)  
class RegisteredSchema:  
    name: str  
    version: str  
    schema\_id: str  
    file\_path: Path  
    category: str  
    root\_schema: bool  
    active: bool  
    raw\_schema: dict\[str, Any\]  
    compiled\_validator: Any

Recommended registry interface:

class SchemaRegistry:  
    def get(self, name: str, version: str) \-\> RegisteredSchema:  
        ...

    def get\_by\_analysis\_type(  
        self,  
        analysis\_type: str,  
    ) \-\> RegisteredSchema:  
        ...

    def resolve\_schema\_id(self, schema\_id: str) \-\> RegisteredSchema:  
        ...

    def is\_active(self, name: str, version: str) \-\> bool:  
        ...

---

## **6\. Reference Resolution**

All production schemas use absolute schema IDs such as:

https://schemas.tradepilot.local/production/v1/common.schema.json

These are logical identifiers and do not require an HTTP server.

The application must map schema IDs to local files through the registry.

Example mapping:

schema\_store \= {  
    registered.schema\_id: registered.raw\_schema  
    for registered in registry.schemas  
}

Remote network resolution must be disabled.

The validator must never fetch schema references from the public internet.

---

## **7\. Supported Validation Library**

Recommended Python libraries:

* `jsonschema`  
* `referencing`

The implementation should use Draft 2020-12 validation.

Example:

from jsonschema import Draft202012Validator  
from referencing import Registry, Resource

The backend must enable format checking for:

* UUID;  
* date;  
* date-time.

---

## **8\. AI Output Validation Pipeline**

The AI analysis worker must use the following sequence.

Provider Response  
      |  
      v  
Transport Check  
      |  
      v  
Extract JSON  
      |  
      v  
Parse JSON  
      |  
      v  
Resolve Expected Schema  
      |  
      v  
JSON Schema Validation  
      |  
      v  
Domain Validation  
      |  
      v  
Canonical Trade State Validation  
      |  
      v  
Lifecycle Validation  
      |  
      v  
Narrative Validation  
      |  
      v  
Accepted Analysis

---

## **9\. Step 1 — Transport Validation**

The provider adapter must confirm:

* request completed successfully;  
* response is not empty;  
* provider did not return a refusal;  
* response size is within configured limits;  
* provider metadata is available;  
* only one final structured payload is selected.

Transport failure examples:

* timeout;  
* connection error;  
* rate limit;  
* invalid API response;  
* empty content;  
* truncated response.

Transport failures are provider errors, not schema errors.

---

## **10\. Step 2 — JSON Extraction**

Structured output mode should be used whenever supported.

The provider adapter should ideally return the JSON object directly.

If provider output contains a text wrapper, the extraction layer may remove:

* Markdown code fences;  
* leading explanatory text;  
* trailing explanatory text.

The extraction layer must not invent missing fields or alter business values.

Allowed normalization:

\`\`\`json  
{ ... }

to:

\`\`\`json  
{ ... }

Disallowed normalization:

* adding a missing stop loss;  
* changing a probability;  
* replacing invalid enum values;  
* changing active target to a proposed target.

---

## **11\. Step 3 — JSON Parsing**

The response must parse into exactly one JSON object.

Reject:

* malformed JSON;  
* multiple top-level objects;  
* arrays when an object is expected;  
* duplicate critical keys;  
* non-finite numbers;  
* comments inside JSON;  
* trailing invalid content.

Non-finite values include:

* `NaN`;  
* `Infinity`;  
* `-Infinity`.

---

## **12\. Step 4 — Expected Schema Resolution**

The expected schema must come from trusted application context, not from the provider output alone.

Example:

expected\_schema \= registry.get\_by\_analysis\_type(  
    requested\_analysis\_type  
)

Provider output metadata must then match:

* expected analysis type;  
* expected schema name;  
* expected schema version.

For example, an Open Position request must produce:

{  
  "metadata": {  
    "analysis\_type": "OPEN\_POSITION\_UPDATE",  
    "schema": {  
      "schema\_name": "open\_position\_update",  
      "schema\_version": "1.0.0"  
    }  
  }  
}

A provider may not choose a different schema.

---

## **13\. Step 5 — JSON Schema Validation**

The compiled Draft 2020-12 validator must validate the complete payload.

Validation must include:

* required properties;  
* property types;  
* enum constraints;  
* `allOf`;  
* `if` / `then`;  
* `oneOf`;  
* `additionalProperties: false`;  
* numeric ranges;  
* string length;  
* formats.

All errors should be collected in one pass where possible.

Recommended normalized error structure:

{  
  "code": "SCHEMA\_VALIDATION\_ERROR",  
  "path": "/target\_assessment/target\_probability",  
  "schema\_path": "/properties/target\_assessment/...",  
  "message": "120 is greater than the maximum of 100",  
  "validator": "maximum",  
  "invalid\_value": 120  
}

---

## **14\. Error Path Format**

Application error paths should use JSON Pointer.

Examples:

/metadata/analysis\_type  
/market\_snapshot/high  
/position\_assessment/remaining\_quantity  
/trading\_plan/current\_action

Root errors use:

/

This format is used for:

* logs;  
* retry prompts;  
* debugging UI;  
* test assertions.

---

## **15\. Domain Validation Registry**

Each root schema should map to one or more domain validators.

Recommended mapping:

DOMAIN\_VALIDATORS \= {  
    "market\_snapshot": \[  
        validate\_market\_snapshot,  
    \],  
    "trade\_state": \[  
        validate\_trade\_state,  
        validate\_position\_calculations,  
    \],  
    "initial\_analysis": \[  
        validate\_market\_snapshot,  
        validate\_entry\_plan,  
        validate\_stop\_loss\_plan,  
        validate\_target\_plan,  
        validate\_price\_level\_relationships,  
    \],  
    "watching\_update": \[  
        validate\_market\_snapshot,  
        validate\_watching\_entry\_assessment,  
        validate\_price\_level\_relationships,  
    \],  
    "open\_position\_update": \[  
        validate\_market\_snapshot,  
        validate\_position\_assessment,  
        validate\_target\_assessment,  
        validate\_stop\_loss\_assessment,  
        validate\_price\_level\_relationships,  
    \],  
    "partial\_exit\_review": \[  
        validate\_market\_snapshot,  
        validate\_partial\_exit,  
        validate\_remaining\_position,  
        validate\_price\_level\_relationships,  
    \],  
    "closing\_analysis": \[  
        validate\_closing\_result,  
        validate\_trade\_timeline,  
    \],  
    "context\_summary": \[  
        validate\_context\_summary,  
        validate\_context\_cutoff,  
    \],  
}

---

## **16\. Market Snapshot Domain Rules**

`validate_market_snapshot()` must verify:

* high is greater than or equal to low;  
* high is greater than or equal to open when both exist;  
* high is greater than or equal to last when both exist;  
* low is less than or equal to open when both exist;  
* low is less than or equal to last when both exist;  
* best offer is greater than or equal to best bid;  
* spread equals best offer minus best bid;  
* change equals last or close minus previous close;  
* change percentage matches the same reference;  
* spread percentage is calculated consistently;  
* average is within a plausible range;  
* timestamp and trading date are consistent;  
* market-close updates should prefer `close`;  
* intraday updates should prefer `last`.

A configurable numeric tolerance should be used for percentages.

Example:

PERCENT\_TOLERANCE \= 0.02

---

## **17\. Trade State Domain Rules**

`validate_trade_state()` must verify:

* ticker is consistent across the session;  
* status and position state match;  
* original quantity is positive when position exists;  
* remaining quantity is not greater than original quantity;  
* open positions have remaining quantity above zero;  
* closed positions have remaining quantity equal to zero;  
* average exit exists for partially or fully closed positions;  
* active stop and target are null after full close;  
* timestamps are chronological;  
* confirmed actions are ordered;  
* confirmed actions do not contradict current state.

---

## **18\. Position Calculation Rules**

For a simple long position:

unrealized\_profit\_loss \=  
(current\_price \- entry\_price) × remaining\_quantity

unrealized\_return\_percentage \=  
((current\_price \- entry\_price) / entry\_price) × 100

distance\_to\_stop\_percentage \=  
((current\_price \- stop\_loss) / current\_price) × 100

distance\_to\_target\_percentage \=  
((target \- current\_price) / current\_price) × 100

The backend calculation is authoritative.

AI-calculated values must be compared against backend values.

If outside tolerance:

* validation fails;  
* corrected values must come from backend;  
* the AI should not be retried merely to recalculate deterministic fields unless the payload contract requires provider-generated values.

Preferred implementation:

* backend computes deterministic financial values before prompt construction;  
* provider repeats or explains them;  
* validator compares them to backend values.

---

## **19\. Entry Plan Domain Rules**

`validate_entry_plan()` must verify:

* exact entry uses `entry_price`;  
* price-zone entry uses both zone bounds;  
* zone low is not above zone high;  
* maximum acceptable entry is not below the proposed entry;  
* no-entry plans do not contain active entry prices;  
* confirmation-required plans include confirmation conditions;  
* cancellation condition is always present;  
* chase-risk logic is consistent with current price;  
* reference entry is compatible with proposed stop and target.

---

## **20\. Stop-Loss Domain Rules**

For a long position:

* stop loss should generally be below entry;  
* proposed protective stop may be above entry after profit develops;  
* stop must be below current price unless already triggered;  
* stop-triggered state requires current price at or below stop, subject to execution rules;  
* risk percentage must match entry and stop;  
* active stop must match canonical Trade State;  
* proposed stop must not replace active stop without user confirmation.

If a proposed stop is above the active target or logically invalid, reject it.

---

## **21\. Target Domain Rules**

For a long position:

* target should be above entry;  
* target distance must match current price;  
* proposed target must be distinguishable from active target;  
* target probability must correspond to the active or clearly identified proposed target;  
* a reached target must be consistent with market high or confirmed execution;  
* target revision does not change canonical state automatically.

---

## **22\. Risk-Reward Validation**

For the reference entry:

risk \=  
entry\_price \- stop\_loss

reward \=  
target\_price \- entry\_price

risk\_reward\_ratio \=  
reward / risk

Validation must reject:

* zero or negative risk denominator;  
* negative reward for a long setup;  
* inconsistent AI-provided ratio;  
* ratio based on a different entry than the one declared.

The backend-calculated value is authoritative.

---

## **23\. Open Position Consistency Rules**

`validate_analysis_trade_state_consistency()` for `open_position_update` must verify:

* session ID matches;  
* ticker matches;  
* entry price matches canonical state;  
* remaining quantity matches;  
* active stop matches;  
* active target matches;  
* current position status is `OPEN`;  
* analysis timestamp is not before entry;  
* proposed stop or target is not presented as confirmed;  
* current price matches the latest accepted market source within tolerance.

If the AI claims a stop was triggered but canonical state is still open, the analysis may still be valid as a warning, but the system must not close the position automatically.

---

## **24\. Watching Update Consistency Rules**

A Watching Update must verify:

* canonical position does not exist;  
* session status is `WATCHING`;  
* no realized or unrealized P/L is present;  
* entry remains a proposal;  
* stop and target remain proposals;  
* entry confirmation does not imply execution;  
* current action is compatible with setup status.

---

## **25\. Partial Exit Validation**

`validate_partial_exit()` must verify:

* partial exit was explicitly confirmed;  
* previous remaining quantity is known;  
* exited quantity is above zero;  
* new remaining quantity is above zero;  
* exited quantity plus new remaining quantity equals previous remaining quantity;  
* exit price is positive;  
* exit timestamp is after entry;  
* realized P/L calculation is correct;  
* partial exit action exists in canonical action history;  
* session status is `PARTIALLY_CLOSED`.

For repeated partial exits, calculations must use the relevant quantities and weighted average exit logic.

---

## **26\. Closing Result Validation**

`validate_closing_result()` must verify:

* full exit was explicitly confirmed;  
* remaining quantity becomes zero;  
* final exit quantity equals the previous remaining quantity;  
* average exit is weighted correctly across all exits;  
* gross P/L is correct;  
* gross return is correct;  
* fee and tax handling is consistent;  
* net P/L exists only when required inputs exist;  
* closing timestamp is after entry;  
* closing reason matches final session status;  
* closed state has no active stop or target.

---

## **27\. Trade Timeline Validation**

`validate_trade_timeline()` must verify:

* events are chronological;  
* position opening follows initial or watching analysis;  
* partial exits occur after entry;  
* final exit occurs last;  
* timeline quantities match confirmed actions;  
* referenced analysis IDs exist;  
* analysis count is consistent with stored accepted analyses;  
* no event occurs after closing unless explicitly classified as post-close journaling.

---

## **28\. Context Summary Validation**

`validate_context_summary()` must verify:

* canonical facts match Trade State;  
* latest accepted analysis is represented;  
* latest orderbook conclusion matches latest accepted orderbook analysis;  
* chart timestamp is preserved;  
* historical chart use is clearly marked;  
* pending user confirmations are preserved;  
* proposals are not copied into active levels;  
* closed sessions contain closing context;  
* open sessions do not contain closing results;  
* important history remains chronologically ordered.

---

## **29\. Context Cutoff Validation**

`validate_context_cutoff()` must verify:

* no source event is later than `source_cutoff_timestamp`;  
* `generated_at` is equal to or later than cutoff;  
* latest included analysis is not newer than cutoff;  
* latest included user action is not newer than cutoff;  
* evidence timestamps are not incorrectly treated as upload timestamps;  
* stale context is flagged when newer accepted data exists outside the summary.

---

## **30\. Session Lifecycle Validation**

The lifecycle validator uses `session_status_schema_mapping` from `manifest.json`.

Examples:

* `INITIAL_ANALYSIS` is allowed from `READY_FOR_ANALYSIS`;  
* `WATCHING_UPDATE` is allowed from `WATCHING`;  
* `OPEN_POSITION_UPDATE` is allowed from `OPEN_POSITION`;  
* `PARTIAL_EXIT_REVIEW` is allowed from `PARTIALLY_CLOSED`;  
* `CLOSING_ANALYSIS` is allowed from a closed state.

During temporary worker execution, the session may use `ANALYZING`, but the validator must also know the status that existed before analysis started.

Recommended job context:

{  
  "session\_status\_before\_job": "OPEN\_POSITION",  
  "session\_status\_during\_job": "ANALYZING",  
  "requested\_analysis\_type": "OPEN\_POSITION\_UPDATE"  
}

---

## **31\. Narrative Validation**

Narrative validation is lightweight and must not attempt to judge investment correctness.

It should verify:

* user-facing narratives are in Indonesian;  
* technical keys remain English;  
* required summaries are not empty;  
* no raw chain-of-thought is present;  
* no unsupported claim of guaranteed profit appears;  
* probabilities are described as estimates;  
* recommendations do not claim execution;  
* missing evidence is acknowledged where required.

Disallowed phrases should include explicit guarantees such as:

pasti profit  
dijamin mencapai target  
tidak mungkin turun  
100% aman

A rule-based scanner may flag these phrases for retry or manual review.

---

## **32\. Schema Error Classification**

Validation errors should be classified as:

### **32.1 `PARSE_ERROR`**

The response is not valid JSON.

### **32.2 `SCHEMA_ERROR`**

The JSON object violates JSON Schema.

### **32.3 `DOMAIN_ERROR`**

The structure is valid, but financial or business rules are inconsistent.

### **32.4 `STATE_CONFLICT`**

The AI output conflicts with canonical Trade State.

### **32.5 `LIFECYCLE_ERROR`**

The analysis type is not allowed for the current session status.

### **32.6 `NARRATIVE_ERROR`**

The output violates narrative or recommendation rules.

### **32.7 `REGISTRY_ERROR`**

The schema name, version, ID, or manifest registration is invalid.

### **32.8 `PROVIDER_ERROR`**

The provider request or response transport failed.

---

## **33\. Validation Result Contract**

Recommended result model:

from dataclasses import dataclass, field  
from typing import Any

@dataclass  
class ValidationIssue:  
    code: str  
    path: str  
    message: str  
    severity: str  
    expected: Any | None \= None  
    actual: Any | None \= None

@dataclass  
class ValidationResult:  
    valid: bool  
    schema\_name: str  
    schema\_version: str  
    issues: list\[ValidationIssue\] \= field(default\_factory=list)  
    validated\_payload: dict\[str, Any\] | None \= None

Severity values:

* `ERROR`  
* `WARNING`

Warnings do not block acceptance unless configured as strict.

---

## **34\. Retry Strategy**

Invalid AI output may be retried with a structured repair request.

Recommended maximum:

Initial provider attempt: 1  
Same-provider repair attempt: 1  
Fallback-provider attempt: 1  
Maximum total provider calls: 3

Suggested sequence:

1. primary provider generates output;  
2. validation fails;  
3. primary provider receives repair prompt;  
4. validation fails again;  
5. fallback provider receives original context plus validation errors;  
6. if still invalid, analysis job fails.

The system must not retry indefinitely.

---

## **35\. Repair Prompt Rules**

The repair prompt must include:

* expected schema name;  
* expected schema version;  
* invalid payload;  
* normalized validation errors;  
* instruction to return only corrected JSON;  
* instruction not to alter valid canonical facts;  
* instruction not to add commentary.

Example:

Return a corrected JSON object that validates against  
open\_position\_update schema version 1.0.0.

Do not change these canonical facts:  
\- entry\_price: 2800  
\- remaining\_quantity: 100  
\- active\_stop\_loss: 2840  
\- active\_target: 2920

Validation errors:  
1\. /ai\_assessment/target\_probability must be \<= 100\.  
2\. /position\_assessment/remaining\_quantity must equal 100\.  
3\. /trading\_plan/requires\_user\_confirmation must be true when action is EXIT.

Return JSON only.

---

## **36\. Repair Restrictions**

The repair process may correct:

* malformed JSON;  
* missing required fields;  
* invalid enum values;  
* inconsistent null usage;  
* formatting issues;  
* values that conflict with explicitly supplied canonical facts.

The repair process must not invent:

* missing user-confirmed entry;  
* missing quantity;  
* an execution that did not happen;  
* exit details;  
* a new stop or target as if confirmed;  
* unavailable market facts.

When required canonical facts are missing from the application context, the job must fail or request user input rather than ask the model to guess.

---

## **37\. Deterministic Corrections**

Some errors should be corrected by backend code instead of retrying the provider.

Examples:

* computed P/L;  
* computed percentages;  
* distance to stop;  
* distance to target;  
* risk-reward ratio;  
* weighted average exit;  
* holding duration;  
* analysis timestamp generated by the system;  
* schema metadata inserted by the application.

Preferred design:

1. provider generates interpretive fields;  
2. backend injects or overwrites deterministic fields;  
3. final payload is validated;  
4. canonical values are stored.

The application should explicitly document which fields are provider-generated and which are backend-generated.

---

## **38\. Provider Output Ownership**

Recommended ownership:

### **Backend-owned fields**

* IDs;  
* schema name and version;  
* session ID;  
* ticker;  
* timestamps;  
* provider metadata;  
* canonical position facts;  
* deterministic calculations;  
* confirmed user actions.

### **AI-owned fields**

* summaries;  
* observations;  
* interpretation;  
* thesis assessment;  
* target realism;  
* recommended action;  
* probability estimates;  
* confidence;  
* warnings based on analytical limitations.

### **Mixed fields**

Mixed fields are created by AI but checked or enriched by backend:

* price levels;  
* support and resistance;  
* target probability;  
* risk level;  
* setup status;  
* position health.

---

## **39\. Persistence Rules**

Only validated payloads may be stored as accepted analyses.

Recommended database fields:

analysis\_id  
session\_id  
analysis\_type  
schema\_name  
schema\_version  
prompt\_version  
provider  
model  
status  
raw\_provider\_response  
parsed\_payload  
validated\_payload  
validation\_errors  
created\_at  
validated\_at

Possible statuses:

* `PENDING`  
* `PROVIDER_COMPLETED`  
* `VALIDATION_FAILED`  
* `REPAIRING`  
* `VALIDATED`  
* `ACCEPTED`  
* `FAILED`

Raw provider responses should be retained for debugging and audit.

They must not be treated as accepted analysis data.

---

## **40\. Atomic Acceptance**

The following operations should occur in one database transaction:

1. store validated analysis;  
2. mark analysis as accepted;  
3. update latest accepted analysis pointer;  
4. rebuild context summary;  
5. create non-canonical proposals;  
6. complete the analysis job.

If any step fails, the transaction should roll back.

Canonical Trade State changes remain separate and require user confirmation.

---

## **41\. Validation Logging**

Each validation attempt should log:

* analysis job ID;  
* session ID;  
* analysis type;  
* provider;  
* model;  
* schema name;  
* schema version;  
* attempt number;  
* error category;  
* error count;  
* validation duration;  
* repair attempted;  
* final result.

Logs must not expose provider API keys or sensitive system prompts.

---

## **42\. Metrics**

Recommended metrics:

tradepilot\_schema\_validation\_total  
tradepilot\_schema\_validation\_failures\_total  
tradepilot\_domain\_validation\_failures\_total  
tradepilot\_state\_conflicts\_total  
tradepilot\_provider\_repair\_attempts\_total  
tradepilot\_provider\_fallback\_total  
tradepilot\_analysis\_validation\_duration\_seconds  
tradepilot\_analysis\_acceptance\_total

Useful labels:

* schema name;  
* provider;  
* model;  
* analysis type;  
* result.

---

## **43\. API Error Response**

Recommended internal API response:

{  
  "error": {  
    "code": "ANALYSIS\_VALIDATION\_FAILED",  
    "message": "The AI output could not be validated.",  
    "analysis\_job\_id": "7bc1c727-4dd8-43a6-850e-42bf2325c02c",  
    "retryable": false,  
    "issues": \[  
      {  
        "code": "STATE\_CONFLICT",  
        "path": "/position\_assessment/entry\_price",  
        "message": "Entry price does not match confirmed Trade State."  
      }  
    \]  
  }  
}

User-facing UI should show a simpler Indonesian message:

Analisa belum dapat diproses karena hasil AI tidak konsisten dengan data posisi yang sudah dikonfirmasi. Silakan coba analisa ulang.

Detailed errors remain available in logs or developer mode.

---

## **44\. Schema Version Handling**

When validating historical data:

* use the schema version stored with that payload;  
* do not automatically validate old payloads against the newest schema;  
* retain all schema versions referenced by stored data;  
* use explicit migration for major schema upgrades.

Example registry lookup:

registry.get(  
    name=analysis.schema\_name,  
    version=analysis.schema\_version,  
)

---

## **45\. Schema Migration Validation**

A migration must define:

* source schema;  
* target schema;  
* field transformations;  
* default values;  
* removed fields;  
* enum mappings;  
* recalculated deterministic values;  
* rollback behavior.

Migration flow:

Load historical payload  
        |  
        v  
Validate against old schema  
        |  
        v  
Run migration  
        |  
        v  
Validate against new schema  
        |  
        v  
Run domain validation  
        |  
        v  
Persist migrated copy

Original historical payloads should remain available.

---

## **46\. Strict and Development Modes**

### **46.1 Production strict mode**

* reject unknown properties;  
* validate formats;  
* reject inactive schemas;  
* reject warnings configured as blocking;  
* no automatic permissive coercion;  
* limited retries.

### **46.2 Development mode**

May additionally expose:

* complete schema error tree;  
* payload diff;  
* resolved schema;  
* validation timing;  
* domain calculation traces.

Development mode must still reject invalid payloads.

---

## **47\. Test Strategy**

The schema validation system requires:

* unit tests;  
* valid fixture tests;  
* invalid fixture tests;  
* provider-output contract tests;  
* domain validator tests;  
* lifecycle tests;  
* context-summary tests;  
* migration tests;  
* fallback-provider tests.

---

## **48\. Valid Fixture Tests**

Each schema must have at least one valid fixture:

fixtures/valid/  
├── market\_snapshot.valid.json  
├── trade\_state.valid.json  
├── evidence.valid.json  
├── initial\_analysis.valid.json  
├── watching\_update.valid.json  
├── open\_position\_update.valid.json  
├── partial\_exit\_review.valid.json  
├── closing\_analysis.valid.json  
└── context\_summary.valid.json

All fixtures must validate during CI.

---

## **49\. Invalid Fixture Tests**

Invalid fixtures should be organized by rule:

fixtures/invalid/  
├── market\_snapshot/  
│   ├── high\_below\_low.json  
│   └── offer\_below\_bid.json  
├── trade\_state/  
│   ├── remaining\_exceeds\_original.json  
│   └── closed\_with\_remaining\_quantity.json  
├── open\_position\_update/  
│   ├── wrong\_entry\_price.json  
│   ├── invalid\_probability.json  
│   ├── exit\_without\_confirmation.json  
│   └── active\_target\_mismatch.json  
└── closing\_analysis/  
    ├── wrong\_average\_exit.json  
    └── timeline\_out\_of\_order.json

Each test should assert the expected error code and JSON Pointer path.

---

## **50\. Provider Contract Tests**

For both Gemini and DeepSeek, tests should cover:

* valid initial output;  
* missing required section;  
* invalid enum;  
* extra property;  
* malformed JSON;  
* canonical-state conflict;  
* invalid calculation;  
* repair success;  
* repair failure;  
* fallback success;  
* fallback failure.

Provider contract tests may use recorded responses or mocked adapters.

---

## **51\. CI Validation Command**

Recommended command:

python \-m app.schema\_validation.validate\_all

It should:

1. load manifest;  
2. resolve all schemas;  
3. compile validators;  
4. validate all valid fixtures;  
5. ensure invalid fixtures fail;  
6. run domain validation tests;  
7. output a concise report;  
8. exit non-zero on failure.

Example output:

Manifest: OK  
Schemas loaded: 10  
References resolved: OK  
Valid fixtures passed: 9  
Invalid fixtures passed: 24  
Domain validators passed: 41  
Result: PASS

---

## **52\. Recommended Module Structure**

backend/  
└── app/  
    ├── schemas/  
    │   ├── registry.py  
    │   ├── loader.py  
    │   ├── resolver.py  
    │   └── errors.py  
    │  
    ├── validation/  
    │   ├── json\_schema\_validator.py  
    │   ├── domain\_registry.py  
    │   ├── market\_snapshot.py  
    │   ├── trade\_state.py  
    │   ├── position.py  
    │   ├── entry\_plan.py  
    │   ├── price\_levels.py  
    │   ├── partial\_exit.py  
    │   ├── closing.py  
    │   ├── lifecycle.py  
    │   ├── context\_summary.py  
    │   └── narrative.py  
    │  
    ├── ai/  
    │   ├── validation\_pipeline.py  
    │   ├── repair\_service.py  
    │   └── provider\_adapters/  
    │  
    └── tests/  
        ├── fixtures/  
        ├── test\_schema\_registry.py  
        ├── test\_json\_schema\_validation.py  
        ├── test\_domain\_validation.py  
        ├── test\_provider\_repair.py  
        └── test\_schema\_migrations.py

---

## **53\. Suggested Validation Service Interface**

class AnalysisValidationService:  
    def validate(  
        self,  
        \*,  
        payload: dict,  
        expected\_analysis\_type: str,  
        trade\_state: dict,  
        session\_status\_before\_job: str,  
        context\_summary: dict | None,  
    ) \-\> ValidationResult:  
        ...

The service should not mutate Trade State.

---

## **54\. Acceptance Criteria**

The schema validation implementation is complete when:

1. `manifest.json` loads successfully.  
2. All active schemas compile.  
3. All local `$ref` values resolve without network access.  
4. Valid fixtures pass.  
5. Invalid fixtures fail for expected reasons.  
6. Domain calculations are checked against backend results.  
7. AI output cannot override confirmed Trade State.  
8. Invalid provider output triggers bounded repair attempts.  
9. Fallback provider uses the same schema contract.  
10. Failed validation never produces accepted analysis.  
11. Accepted analysis rebuilds context summary atomically.  
12. Historical payloads validate against their stored schema versions.  
13. CI fails when any production schema or validator becomes inconsistent.

---

## **55\. Immediate Next Implementation Step**

The next technical artifact should be:

DOMAIN\_VALIDATION\_RULES.md

It should define the exact formulas, tolerances, validation codes, and rules for:

* market snapshot;  
* position calculations;  
* entry, stop loss, and target relationships;  
* partial exit calculations;  
* weighted average exit;  
* closing result;  
* lifecycle consistency;  
* context-summary consistency.

