# UX6.1 Implementation Report — Archive Confirmation and Action

**Date**: 2026-08-07
**Official Task Title**: UX6.1 — Archive Confirmation and Action
**Internal Subtask**: UX6.1a — Add Archive Reversibility Confirmation Copy
**Official Task Status**: PASS
**Branch**: main
**Commit Baseline**: d20ca8e5ee283b55c8e8572f77984539c448c06c

---

## 1. Executive Summary

This report documents the implementation and verification for official task **UX6.1 — Archive Confirmation and Action** and internal correction **UX6.1a — Add Archive Reversibility Confirmation Copy**:

1. **Official Decision**: **PASS**.
2. **Implementation Summary**:
   - Discovered and connected the canonical V2 Archive endpoint (`POST /api/v2/trade-sessions/{id}/archive`) via `archiveSessionV2` in `api.ts`.
   - Created the interactive two-step `ArchiveActionButton` component embedded within `SessionTerminalSummary` in `session-terminal-summary.tsx`.
   - Implemented eligibility-driven visibility (`status` in `CLOSED` | `CLOSED_SKIPPED` AND `archived_at === null`).
   - Updated confirmation body copy (UX6.1a) to explicitly communicate reversibility alongside data/history preservation and removal from main Sessions list without deletion implications:
     `Sesi {ticker} akan dipindahkan dari daftar Sessions ke Archived Sessions. Data, analisis, dan riwayat sesi tetap tersimpan, dan sesi dapat dikembalikan ke daftar selesai nanti.`
   - Implemented single-flight submission ref locking (`submitInFlightRef`) preventing duplicate API calls.
   - Implemented safe navigation after success to `/sessions/archived` (existing route placeholder).
   - Implemented Indonesian error state handling preserving unarchived session UI state.
3. **Acceptance Criteria**:
   - Archive is never shown for non-terminal sessions — **PASS**
   - Confirmation explains data remains stored and is reversible — **PASS**
   - Successful archive removes session from main list — **PASS**
4. **Next Task Eligibility**: **UX6.2 is eligible to be considered next, but it must be reread directly from the authoritative task plan before execution.**

---

## 2. Source Lock

Authoritative and current files reread and inspected:
1. `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
2. `docs/TradePilot AI PRD Amendment.md`
3. `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
4. [TradePilot_AI_UI_UX_PRD_Guided_Session_Experience_and_Archive_FINAL.docx](file:///Users/cahyo/Developer/Web/tradepilot-ai/docs/redesign/TradePilot_AI_UI_UX_PRD_Guided_Session_Experience_and_Archive_FINAL.docx)
5. [TradePilot_AI_UI_UX_Detailed_Task_Plan_FINAL.docx](file:///Users/cahyo/Developer/Web/tradepilot-ai/docs/redesign/TradePilot_AI_UI_UX_Detailed_Task_Plan_FINAL.docx)
6. [UX0.1_AUTHORITATIVE_SOURCE_LOCK_AND_REQUIREMENT_MATRIX_2026-08-04.md](file:///Users/cahyo/Developer/Web/tradepilot-ai/docs/ui-ux/UX0.1_AUTHORITATIVE_SOURCE_LOCK_AND_REQUIREMENT_MATRIX_2026-08-04.md)
7. [UX0.2_CURRENT_MAIN_BRANCH_UI_UX_IMPACT_AUDIT_2026-08-04.md](file:///Users/cahyo/Developer/Web/tradepilot-ai/docs/ui-ux/UX0.2_CURRENT_MAIN_BRANCH_UI_UX_IMPACT_AUDIT_2026-08-04.md)
8. [UX5-G_GUIDED_SESSION_FLOW_GATE_2026-08-07.md](file:///Users/cahyo/Developer/Web/tradepilot-ai/docs/ui-ux/UX5-G_GUIDED_SESSION_FLOW_GATE_2026-08-07.md)

---

## 3. Component Placement & Eligibility Matrix

Placement: `ArchiveActionButton` is placed inside `SessionTerminalSummary` (`session-terminal-summary.tsx`), making it an organizational action on eligible terminal Session Detail surfaces.

| Session Status | archived_at | Archive Visible? | Rationale | Result |
|---|---|---|---|---|
| `DRAFT` | `null` | NO | Non-terminal state | PASS |
| `ANALYZED` | `null` | NO | Non-terminal state | PASS |
| `WAITING` | `null` | NO | Non-terminal state | PASS |
| `OPEN_POSITION` | `null` | NO | Non-terminal state | PASS |
| `CLOSED` | `null` | YES | Terminal unarchived state | PASS |
| `CLOSED_SKIPPED` | `null` | YES | Terminal unarchived state | PASS |
| `CLOSED` | `2026-08-07T...` | NO | Already archived session | PASS |
| `CLOSED_SKIPPED` | `2026-08-07T...` | NO | Already archived session | PASS |

---

## 4. Confirmation Copy & User Experience

- **Action Button Label**: `Arsipkan Sesi`
- **Confirmation Title**: `Arsipkan Sesi {ticker}?`
- **Confirmation Body Copy**: `Sesi {ticker} akan dipindahkan dari daftar Sessions ke Archived Sessions. Data, analisis, dan riwayat sesi tetap tersimpan, dan sesi dapat dikembalikan ke daftar selesai nanti.`
- **Confirm Button Label**: `Arsipkan Sesi`
- **Cancel Button Label**: `Batal`
- **Submitting Label**: `Mengarsipkan…`

---

## 5. Verification Summary

- **Vitest**: `session-terminal-summary.test.tsx` (8 passed tests, 164ms duration).
- **TypeScript Typecheck**: `tsc --noEmit` (0 errors).
- **ESLint**: 0 errors across all modified files.
- **Git Check**: `git diff --check` clean (0 errors).
