# TradePilot Evidence Expansion — Source Lock

## Purpose

Protect every Evidence Expansion implementation task from scope drift and memory-based assumptions. Force direct reading of authoritative repository documents before any work begins.

## When to Use

Use this skill for every task that touches the Foreign Flow / Broker Flow Evidence Expansion feature. Load it before any specialist skill. Use it together with `tradepilot-source-lock`.

---

## Authoritative Sources

Read these documents directly before every task. Do not rely on memory, chat summaries, or patterns from earlier tasks.

### Authority Boundaries

| Document | Location | Governs |
|---|---|---|
| Evidence Expansion PRD | `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md` | Approved Evidence Expansion delta only |
| Authoritative Rebuild PRD | `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md` | Unchanged product contracts |
| Authoritative Rebuild Detailed Task Plan | `docs/TradePilot AI Rebuild — Detailed Task Plan.md` | Unchanged implementation sequence and task discipline |
| Scope Guardrails | `docs/rebuild/SCOPE_GUARDRAILS.md` | Approved statuses, types, providers, task discipline |
| Session Status Rules | `docs/rebuild/SESSION_STATUS_RULES.md` | Lifecycle, transitions, terminal states |
| Analysis Input Contracts | `docs/rebuild/ANALYSIS_INPUT_CONTRACTS.md` | Approved evidence and input eligibility |
| Simple Architecture | `docs/rebuild/SIMPLE_ARCHITECTURE.md` | Component responsibilities, prohibited patterns |
| Project Invariants | `.agent-skills/shared/PROJECT_INVARIANTS.md` | Cross-cutting product and engineering constraints |

The Evidence Expansion PRD governs only its approved delta. Authoritative rebuild documents remain authoritative for unchanged lifecycle, analysis types, monitoring slots, decisions, queue, and provider contracts. Explicit Product Owner decisions resolve conflicts. Current implementation is reference evidence only, never product authority. If a conflict is not explicitly resolved, **return BLOCKED**.

---

## No-Memory Rule

Do not:
- rely on prior chat context;
- assume task patterns from earlier completed tasks;
- infer requirements from code that already exists;
- treat existing repository behavior as the approved product.

Read the source documents. Use what they say. Nothing else.

---

## Evidence Expansion Scope Boundaries

### What this feature IS

- Add `FOREIGN_FLOW_1W` as a **required** evidence item for `INITIAL_ANALYSIS`.
- Add `BROKER_FLOW_1D` as an **optional** evidence item for `WAIT_UPDATE` and `POSITION_UPDATE`.
- Update Gemini prompts for the three affected analysis types.
- Add `Analisa Foreign Flow` section to Initial Analysis output.
- Add `Analisa Broker Flow` section to WAIT Update and Position Update output when Broker Flow evidence is supplied.
- Extend evidence-type definitions to include the two new types.
- Add upload controls to the three affected forms.

### What this feature IS NOT

This feature must not:
- introduce a new session lifecycle status;
- introduce a new analysis type;
- introduce a new BUY / WAIT / SKIP / CLOSE action;
- change the Gemini provider or model;
- introduce a second AI provider;
- introduce provider routing or fallback;
- create a new queue architecture;
- redesign the dashboard;
- add new navigation items or routes;
- add automatic broker identification outside Gemini;
- calculate foreign flow or broker flow numerically from raw data;
- require OCR or image-content validation beyond existing upload validation;
- modify historical session records.

---

## Flow Assignment Rules

These rules are non-negotiable. Memorize them before writing a single prompt.

### FOREIGN_FLOW_1W
- Belongs exclusively to **Initial Analysis** (`INITIAL_ANALYSIS`).
- Is part of the immutable **Initial Evidence set** — submitted exactly once per session.
- Is **required**. Initial Analysis cannot proceed without it.
- Cannot be overwritten, appended, versioned, or replaced after submission.
- Must not appear in WAIT Update or Position Update forms.

### BROKER_FLOW_1D
- Belongs to **WAIT Update** (`WAIT_UPDATE`) and **Position Update** (`POSITION_UPDATE`) only.
- Is **optional** in both contexts.
- Must never be part of the Initial Evidence set.
- Must belong to the exact update/observation containing the corresponding Orderbook, never generic session-level evidence.

---

## Lifecycle Invariants

These must remain unchanged after implementation:

| Invariant | Required State |
|---|---|
| Approved session statuses | `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, `CLOSED_SKIPPED` — no additions |
| Approved analysis types | `INITIAL_ANALYSIS`, `WAIT_UPDATE`, `POSITION_UPDATE` — no additions |
| Position Update monitoring slots | `MORNING`, `MIDDAY`, `AFTERNOON` — unchanged |
| User decisions | BUY, WAIT, SKIP, CLOSE — unchanged |
| Gemini provider | Gemini only, production default `gemini-3.1-flash-lite` — no change |
| No provider routing or fallback | Prohibited — unchanged |

---

## Backward Compatibility Requirement

- Existing sessions created before the feature must remain fully readable.
- Historical Initial Analyses that contain only Orderbook + Chart 3M + Chart 6M remain valid.
- Historical WAIT Updates and Position Updates without Broker Flow remain valid.
- The four-image requirement applies only to new Initial Analysis submissions after the feature is active.

---

## BLOCKED Conditions

Return **BLOCKED** immediately when:

- the task requires a new lifecycle status, analysis type, or trading action;
- the task requires changing the AI provider or adding a second provider;
- a required authoritative document cannot be found or read;
- authoritative documents conflict and no explicit Product Owner decision resolves it;
- the change would redesign existing dashboard navigation or routes;
- the change would break historical session readability;
- the change would require OCR or automatic image-content validation beyond existing upload mechanics;
- the task scope exceeds what the Evidence Expansion PRD explicitly approves.

---

## Required Task Discipline

Every implementation task for this feature must include:

1. **Source Lock section**: list which authoritative documents were reread for this specific task.
2. **Scope Diff section**: state current behavior, required behavior, smallest change needed, and behaviors that must remain unchanged.
3. **Flow Assignment check**: confirm that FOREIGN_FLOW_1W is handled only in Initial Analysis and BROKER_FLOW_1D only in WAIT/Position Updates.
4. **Unchanged-contract check**: confirm lifecycle, analysis types, monitoring slots, decisions, queue, and provider architecture remain unchanged.
5. **Backward compatibility check**: confirm historical sessions and analyses remain unaffected.

---

## Required Sources Summary

> Before any Evidence Expansion task: read the PRD at `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md` and the governance documents listed above. Do not proceed from memory.
