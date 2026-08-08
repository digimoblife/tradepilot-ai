# TradePilot Gemini Flow Analysis — Evidence Expansion

## Purpose

Define how Gemini must interpret Foreign Flow and Broker Flow evidence. Protect prompt correctness and prevent overconfidence, fabrication, or deterministic conclusions from flow screenshots.

## When to Use

Use this skill when implementing or reviewing:
- Gemini prompt changes for Initial Analysis (adding Foreign Flow interpretation);
- Gemini prompt changes for WAIT Update (adding Broker Flow interpretation);
- Gemini prompt changes for Position Update (adding Broker Flow interpretation);
- any task that touches flow-evidence analysis behavior.

Load `tradepilot-evidence-expansion-source-lock` first.

---

## Authoritative Sources

Read directly before prompt work:

- `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md` — Sections 6, 7;
- `docs/rebuild/ANALYSIS_INPUT_CONTRACTS.md` — approved analysis types and input eligibility;
- `docs/rebuild/SESSION_STATUS_RULES.md` — lifecycle preservation;
- `docs/rebuild/SCOPE_GUARDRAILS.md` — Gemini-only and task discipline.

---

## FOREIGN FLOW Interpretation (Initial Analysis)

### What Gemini must classify

Gemini must classify the recent foreign flow condition as exactly one of:

- `ACCUMULATION` — net foreign buying with consistent or growing inflow
- `NEUTRAL` — mixed or balanced foreign activity
- `DISTRIBUTION` — net foreign selling with consistent or growing outflow

### What Gemini must evaluate

The prompt must instruct Gemini to evaluate all of the following:

1. **Consistency across the week**: Is the direction consistent, or are there reversals?
2. **Magnitude**: How significant is the visible inflow or outflow?
3. **Relationship with price**: Is price moving in the same direction as foreign flow, or opposite?
4. **Confirmation or divergence**: Does foreign flow confirm the technical thesis, or conflict with it?
5. **Thesis impact**: Does foreign activity strengthen or weaken the current trading thesis?

### One-day trap prevention

The prompt must explicitly instruct Gemini:

> Do not treat a single large foreign-buying day as automatically bullish without evaluating the preceding days. A one-day spike may be noise within a distribution pattern.

### Evidence authority

- Foreign Flow 1W is supporting evidence. It is one part of the total evidence set alongside Orderbook, Chart 3M, and Chart 6M.
- Foreign flow does not independently determine the trading decision.
- Conflicting foreign flow reduces confidence; it does not get ignored.

---

## BROKER FLOW Interpretation (WAIT Update and Position Update)

### What Gemini must classify

When Broker Flow 1D is supplied, Gemini must classify visible broker activity as exactly one of:

- `ACCUMULATION` — dominant visible buying behavior suggesting accumulation
- `NEUTRAL` — mixed or unclear broker activity
- `DISTRIBUTION` — dominant visible selling behavior suggesting distribution

### What Gemini must evaluate

The prompt must instruct Gemini to evaluate all of the following:

1. **Dominant behavior**: What is the most visible buying or selling activity?
2. **Concentration**: Does activity appear concentrated among a few brokers?
3. **Orderbook comparison**: Does broker flow confirm or conflict with the current Orderbook?
4. **Prior analysis alignment**: Does broker flow confirm or weaken the previous thesis?
5. **Thesis impact**: Does broker activity support continued waiting / open-position confidence, or does it weaken it?

### For WAIT Update specifically

The prompt must also ask Gemini:
- Is the expected confirmation beginning to appear?
- Does broker activity support continued waiting?
- Does broker activity weaken the previous thesis?
- Is the flow strong enough to materially affect the current conclusion?

### For Position Update specifically

The prompt must also ask Gemini:
- Is accumulation continuing?
- Is distribution beginning to appear?
- Does broker flow confirm or conflict with Orderbook behavior?
- Has risk to the open position increased or decreased?

### One-day noise warning

The prompt must instruct Gemini:

> One-day broker flow can be noisy. A single day of concentrated buying or selling does not prove a sustained institutional position.

### Broker code interpretation

The prompt must instruct Gemini:

> Broker codes do not necessarily represent a single investor or institution. Visible broker activity may aggregate different clients and different trading behaviors. Do not describe a broker code as a specific institution unless the evidence explicitly and unambiguously proves it.

---

## General Guardrails (Both Flow Types)

These rules apply to all flow analysis. They must appear in or be enforceable by the prompts.

### Fabrication prohibited

- Gemini must never invent broker values, foreign-flow numbers, or price facts from a screenshot it cannot read.
- When evidence is unclear, Gemini must state that the flow evidence is unclear and continue with the remaining valid evidence.
- Gemini must not claim certainty from screenshots.

### Preferred language register

Instruct Gemini to use language such as:
- _supports_, _weakens_, _confirms_, _conflicts with_, _indicates_, _suggests_

Not language such as:
- _proves_, _guarantees_, _definitively shows_, _is certain to_

### Conflict handling

- When flow evidence conflicts with technical evidence, confidence must be reduced.
- Conflicting evidence must not be silently ignored.
- Conflicting evidence reduces confidence; it is never overridden by a fixed positive boost.

### No artificial confidence adjustment

- Do not hard-code a fixed confidence boost (e.g., "+10%") for the presence of flow evidence.
- Agreement may strengthen confidence when consistently supported by the broader evidence.
- Conflict must reduce confidence.
- No deterministic arithmetic weighting is required or permitted.

### Provider constraint

- Gemini is the only AI provider for all flow analysis.
- Production model: `gemini-3.1-flash-lite` (from configuration, not hardcoded).
- No fallback to another provider or model.

---

## Prohibited Prompt Changes

Do not:
- add a hardcoded confidence formula ("+10% if ACCUMULATION");
- instruct Gemini to treat a single flow day as conclusive;
- instruct Gemini to fabricate values when the image is unclear;
- add broker-identity claims without explicit evidence;
- change the Gemini provider or model in any prompt task;
- remove the existing Orderbook, Chart 3M, or Chart 6M prompt context when adding flow;
- add a new analysis type to support flow interpretation — use the existing three types only.

---

## Prompt Scope

| Analysis Type | Prompt Change |
|---|---|
| `INITIAL_ANALYSIS` | Add Foreign Flow 1W interpretation instructions |
| `WAIT_UPDATE` | Add conditional Broker Flow 1D interpretation instructions (when evidence is supplied) |
| `POSITION_UPDATE` | Add conditional Broker Flow 1D interpretation instructions (when evidence is supplied) |

## BLOCKED Conditions

Return **BLOCKED** if the feature PRD, lifecycle/input contracts, or repository implementation disagree on an analysis type, input eligibility, or prompt contract and an explicit Product Owner decision does not resolve the conflict. Do not follow repository behavior to resolve it.
