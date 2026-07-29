# Analysis Types and Input Contracts

## 1. Purpose

Define only the approved AI analysis types and their required input contracts. This document defines input eligibility and authority boundaries; it does not define output fields, schemas, prompts, models, validators, APIs, queue behavior, or frontend forms.

## 2. Scope and Authorities

The PRD and the TradePilot AI Rebuild Detailed Task Plan are the authorities. Supporting evidence is `docs/rebuild/SCOPE_GUARDRAILS.md`, `docs/rebuild/SESSION_STATUS_RULES.md`, and `docs/rebuild/SIMPLE_ARCHITECTURE.md`. Existing code is reference evidence only. The only approved analysis types are `INITIAL_ANALYSIS`, `WAIT_UPDATE`, and `POSITION_UPDATE`.

## 3. Input Contract Principles

- Inputs MUST match one of the three approved analysis types.
- User-owned fields and uploaded evidence are authoritative.
- Existing Gemini analyses are context only and cannot override newer user-owned facts.
- Observation period is metadata, not an analysis type or session status.
- Invalid input creates no Gemini request; user input and uploaded evidence remain preserved.
- No contract includes Partial Exit, Closing Analysis, provider selection, fallback configuration, old lifecycle state, or evaluation records as required input.
- No output contract is defined in P2.3.

## 4. Approved Analysis Types

Only these analysis types exist:

`INITIAL_ANALYSIS`

`WAIT_UPDATE`

`POSITION_UPDATE`

Morning, Midday, and Afternoon are observation-period metadata values only. No additional analysis type may be added.

## 5. INITIAL_ANALYSIS Input Contract

Analysis Type: `INITIAL_ANALYSIS`
Purpose: Produce the first analysis for one session from its initial user-provided context and required evidence.
Allowed Session Status: `DRAFT` for submission; request processing uses `ANALYZING`.
Required Inputs: Ticker; company name; initial note; orderbook image; three-month chart image; six-month chart image.
Optional Inputs: No additional analysis input is defined here.
Required Evidence: All three images are required: orderbook, three-month chart, and six-month chart.
Required Historical Context: No previous analysis is required; use only session facts, initial note, and the three required images.
Position Requirement: No position exists.
User-Owned Authoritative Fields: Ticker, company name, initial note, and uploaded images.
Gemini Context Fields: None before this first analysis; the resulting Initial Analysis becomes context for later requests.
Prohibited Inputs: Current price, position facts, previous analysis, Partial Exit, Closing Analysis, provider selection, or fallback configuration.
Submission Eligibility: Valid only when the session is `DRAFT` and all required inputs/evidence are present; invalid input creates no Gemini request.

Ticker and company name belong to the session. The initial note is user-entered context. Current price is not required, and no position exists under this contract.

## 6. WAIT_UPDATE Input Contract

Analysis Type: `WAIT_UPDATE`
Purpose: Analyze new waiting-state evidence against the Initial Analysis and prior waiting updates.
Allowed Session Status: `WAITING`.
Required Inputs: Observation period; user-entered current price; observation timestamp; orderbook image; Initial Analysis; prior WAIT Updates when available.
Optional Inputs: User note.
Required Evidence: One orderbook image.
Required Historical Context: Initial Analysis and previous WAIT Updates in chronological order when available.
Position Requirement: No position may exist.
User-Owned Authoritative Fields: Observation period, current price, timestamp, orderbook image, and user note.
Gemini Context Fields: Initial Analysis and prior WAIT Updates; these are context only and cannot override newer user-owned facts.
Prohibited Inputs: Position facts, fabricated position data, Partial Exit, Closing Analysis, provider selection, fallback configuration, or an old lifecycle state as required input.
Submission Eligibility: Valid only when session status is `WAITING`, no position exists, current price/period/timestamp/orderbook are present, and required context is available; invalid input creates no Gemini request.

Current price is entered by the user and is authoritative. Gemini MUST NOT replace it with a value inferred from the image. A WAIT Update must not create a position.

## 7. POSITION_UPDATE Input Contract

Analysis Type: `POSITION_UPDATE`
Purpose: Analyze new open-position evidence against confirmed position facts, Initial Analysis, relevant waiting history, and prior Position Updates.
Allowed Session Status: `OPEN_POSITION`.
Required Inputs: Observation period; user-entered current price; observation timestamp; orderbook image; confirmed position facts; Initial Analysis; relevant WAIT history when it exists; prior Position Updates.
Optional Inputs: User note.
Required Evidence: One orderbook image.
Required Historical Context: Initial Analysis; relevant WAIT history when available; prior Position Updates chronologically.
Position Requirement: Exactly one confirmed open position exists.
User-Owned Authoritative Fields: Observation period, current price, timestamp, orderbook image, user note, and confirmed position facts.
Gemini Context Fields: Initial Analysis, relevant WAIT history, and prior Position Updates; these are context only.
Prohibited Inputs: A second position, unconfirmed position facts, Partial Exit, Closing Analysis, provider selection, fallback configuration, or an old lifecycle state as required input.
Submission Eligibility: Valid only when session status is `OPEN_POSITION`, exactly one open position exists, and current price/period/timestamp/orderbook/confirmed facts are present; invalid input creates no Gemini request.

Confirmed position facts are: entry price, entry timestamp, quantity, stop loss, target price, and position status. Current price is user-entered and authoritative. Gemini MUST NOT modify any confirmed position fact.

## 8. Observation Period Metadata

Only these observation-period values are approved:

`MORNING`

`MIDDAY`

`AFTERNOON`

Observation period is metadata. It does not create an analysis type, session status, transition, or separate workflow.

## 9. User-Owned and Gemini-Owned Data

User-Owned Inputs: Ticker; company name; initial note; observation period; current price; observation timestamp; uploaded evidence; user note; and confirmed position facts.

Existing Gemini-Owned Context: Initial Analysis; previous WAIT Updates; and previous Position Updates.

Existing Gemini output is context only. It MUST NOT override newer user-owned facts, create decisions, create or alter position facts, or replace current price.

## 10. Context History Rules

### INITIAL_ANALYSIS

- No previous analysis context.
- Uses only session facts, initial note, and the three required images.

### WAIT_UPDATE

- Includes Initial Analysis.
- Includes previous WAIT Updates chronologically when available.
- Does not include fabricated position data.
- User-entered current price remains authoritative.

### POSITION_UPDATE

- Includes confirmed position facts.
- Includes Initial Analysis.
- Includes relevant WAIT history when available.
- Includes previous Position Updates chronologically.
- User-entered current price and confirmed position facts remain authoritative.

No summarization algorithm or token limit is defined here.

## 11. Missing and Invalid Input Rules

- Initial Analysis is invalid when any required initial evidence image is missing.
- WAIT Update is invalid when current price, observation period, timestamp, or orderbook image is missing.
- Position Update is invalid when current price, observation period, timestamp, orderbook image, or an open position is missing.
- No Gemini request is created for invalid input.
- User input and uploaded evidence remain preserved when validation fails.

No detailed error codes are defined here.

## 12. Prohibited Inputs and Behaviors

The rebuild MUST prohibit:

- unapproved analysis types;
- Partial Exit input;
- Closing Analysis input;
- provider selection;
- fallback-provider configuration;
- Gemini-created user decisions;
- Gemini-created position facts;
- Gemini replacement of current price;
- Position Update without a confirmed open position;
- WAIT Update with position facts;
- treating Morning, Midday, or Afternoon as analysis types;
- old lifecycle state as required rebuild input;
- evaluation records as required analysis input;
- generic transport or canonical payload duality.

## 13. Unresolved Contract Questions

- Exact persistence representation for context history and analysis-request references, deferred to later implementation tasks.
- Exact evidence-reference format for the three initial images and later orderbook images.
- Exact compatibility handling for historical legacy analysis types without allowing them as new input types.
- Exact user-controlled retry behavior for failed analysis requests.

## 14. P2.3 Conclusion

The rebuild defines exactly three analysis types with explicit input eligibility: Initial Analysis for a draft with three required images, WAIT Update for a waiting session without a position, and Position Update for one confirmed open position. User-owned fields remain authoritative, Gemini context is non-authoritative, observation periods remain metadata, and no output contract or implementation artifact is defined.
