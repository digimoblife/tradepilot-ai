# TradePilot AI — Session Lifecycle Specification (System-Acquired Evidence)

## 1. Lifecycle Overview

A Trade Session represents one structured trade story. Under the **System-Acquired Evidence** architecture, the lifecycle transitions through:

```
[DRAFT] 
   │ (User enters Ticker -> clicks "Ambil Data & Analisa")
   ▼
[EVIDENCE_COLLECTING]
   │
   ├─► (Validation Success) ──► [EVIDENCE_VALIDATED] ──► [ANALYZING] ──► [INITIAL_ANALYZED]
   │                                                                           │
   └─► (Validation Failure) ──► [EVIDENCE_INCOMPLETE] (Retryable)              ├──► [WATCHING]
                                                                               ├──► [OPEN_POSITION]
                                                                               └──► [CLOSED_SKIPPED]
```

## 2. State Definitions

| State | Type | Description |
| :--- | :--- | :--- |
| `DRAFT` | Initial | Session initialized with symbol and trading style. |
| `EVIDENCE_COLLECTING` | Transient | System asynchronously queries Pluang, IDX, and Stockbit APIs. |
| `EVIDENCE_VALIDATED` | Transient | Snapshot passed all completeness and sanity checks; snapshot persisted. |
| `EVIDENCE_INCOMPLETE` | Error/Transient | Critical market data unavailable; user presented with diagnostic & retry. |
| `ANALYZING` | Transient | AI reasoning engine is processing the structured snapshot context. |
| `INITIAL_ANALYZED` | Stable | First analysis completed. Decision, trade plan, and key levels are ready. |
| `WATCHING` | Stable | Trade setup is intact; user is waiting for optimal entry trigger. |
| `OPEN_POSITION` | Stable | User confirmed position entry. Active position tracking engaged. |
| `PARTIALLY_CLOSED` | Stable | User realized partial profit; remaining position monitored. |
| `CLOSED` | Terminal | Full exit confirmed. Session finalized. |
| `CANCELLED` | Terminal | Session discarded before execution. |
| `ARCHIVED` | Terminal | Session archived for historical performance review. |

## 3. Re-evaluation & Refresh Transitions

During `WATCHING` or `OPEN_POSITION`:
1. User clicks **"Refresh Analysis"**.
2. System enters transient state `EVIDENCE_COLLECTING`.
3. System fetches fresh quote/orderbook and broker summary -> generates `EvidenceSnapshot #N` and `EvidenceDelta`.
4. State transitions to `ANALYZING` -> returns to `WATCHING` or `OPEN_POSITION` with updated thesis, recommendations, and adjusted levels.
