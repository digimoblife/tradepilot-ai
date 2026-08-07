# UX6.4 Implementation Report — Restore to Completed List

**Date**: 2026-08-07
**Official Task Title**: UX6.4 — Restore to Completed List
**Official Task Status**: PASS
**Branch**: main
**Commit Baseline**: d20ca8e5ee283b55c8e8572f77984539c448c06c

---

## 1. Executive Summary

This report documents the implementation and verification for official task **UX6.4 — Restore to Completed List**:

1. **Official Decision**: **PASS**.
2. **Implementation Summary**:
   - Integrated the V2 Restore endpoint (`POST /api/v2/trade-sessions/{id}/restore`) via the `restoreSessionV2` API helper in `frontend/src/features/trade-workspace/api.ts`.
   - Created the `RestoreActionButton` component in `frontend/src/features/sessions/session-terminal-summary.tsx`, exposing the approved Indonesian action label: `Kembalikan ke Daftar`.
   - Built a two-step confirmation panel with title `Kembalikan sesi ini ke daftar?` and explicit wording confirming placement in Completed, preservation of terminal status, and 0 trading reopening.
   - Protected against duplicate submissions using single-flight ref locks (`submitInFlightRef.current`).
   - Cleared `archived_at` (`archived_at` $\rightarrow$ `null`) upon API success while leaving terminal status (`CLOSED` / `CLOSED_SKIPPED`) unchanged.
   - Navigated to `/sessions` upon success, placing the restored session into the `Completed` section via standard `groupSessions` classification.
   - Handled API errors gracefully with Indonesian error feedback (`Sesi tidak dapat dikembalikan ke daftar. Coba lagi.`), keeping the session archived in UI state.
3. **Acceptance Evaluation**: All 77 PASS conditions evaluated individually — **PASS**.
4. **Next Task Eligibility**: **UX6-G is eligible to be considered next, but it must be reread directly from the authoritative task plan before execution.**

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
8. [UX6.1_ARCHIVE_CONFIRMATION_AND_ACTION_2026-08-07.md](file:///Users/cahyo/Developer/Web/tradepilot-ai/docs/ui-ux/UX6.1_ARCHIVE_CONFIRMATION_AND_ACTION_2026-08-07.md)
9. [UX6.2_ARCHIVED_SESSIONS_LIST_2026-08-07.md](file:///Users/cahyo/Developer/Web/tradepilot-ai/docs/ui-ux/UX6.2_ARCHIVED_SESSIONS_LIST_2026-08-07.md)
10. [UX6.3_ARCHIVED_SESSION_READ_ONLY_DETAIL_2026-08-07.md](file:///Users/cahyo/Developer/Web/tradepilot-ai/docs/ui-ux/UX6.3_ARCHIVED_SESSION_READ_ONLY_DETAIL_2026-08-07.md)

---

## 3. Scope Diff

- Frontend restore interaction only: **Confirmed**
- No Reopen: **Confirmed**
- No new decision availability: **Confirmed**
- No backend/schema changes: **Confirmed**
- No UX6-G: **Confirmed**
- No UX7: **Confirmed**
- No real Gemini calls: **Confirmed**

---

## 4. V2 Restore API Contract

- **Frontend Helper**: `restoreSessionV2(id: string)` added to `frontend/src/features/trade-workspace/api.ts`.
- **HTTP Method & Endpoint**: `POST /api/v2/trade-sessions/{id}/restore`
- **Response Shape**: `{ id: string, status: string, archived_at: null }`
- **Ownership Behavior**: Enforced server-side in `RebuildTradeSessionService(db_session).restore(session_id, user_id)`.
- **Eligibility**: Terminal sessions (`CLOSED`, `CLOSED_SKIPPED`) with `archived_at IS NOT NULL`.
- **Error Conventions**: Throws 404 for unauthenticated/unowned requests and 400 for non-archived sessions.

---

## 5. Restore Action Placement

- **Single Mutation Owner**: Placed inside `SessionTerminalSummary` in `frontend/src/features/sessions/session-terminal-summary.tsx` via `RestoreActionButton`.
- **Visibility**: Renders only when `isArchived = Boolean(detail.session.archived_at)` is `true`.

---

## 6. Visibility Matrix

| Status | archived_at | Restore Visible? | Result |
|---|---|---|---|
| `DRAFT` | `null` | NO (null root) | PASS |
| `ANALYZED` | `null` | NO (null root) | PASS |
| `WAITING` | `null` | NO (null root) | PASS |
| `OPEN_POSITION` | `null` | NO (null root) | PASS |
| `CLOSED` (unarchived) | `null` | NO (renders Archive button) | PASS |
| `CLOSED` (archived) | `2026-08-01T10:00:00Z` | YES | PASS |
| `CLOSED_SKIPPED` (unarchived) | `null` | NO (renders Archive button) | PASS |
| `CLOSED_SKIPPED` (archived) | `2026-08-02T14:00:00Z` | YES | PASS |

---

## 7. Approved Copy

- **Action Label**: `Kembalikan ke Daftar`
- **Confirmation Title**: `Kembalikan sesi ini ke daftar?`
- **Confirmation Body**: `Sesi {ticker} akan dikembalikan ke bagian Completed pada daftar Sessions. Status selesai, data, analisis, dan riwayat tetap sama. Trading tidak akan dibuka kembali.`
- **Confirm Button Label**: `Kembalikan ke Daftar`
- **Cancel Button Label**: `Batal`
- **Submitting Button Label**: `Mengembalikan…`
- **Error Feedback**: `Sesi tidak dapat dikembalikan ke daftar. Coba lagi.`

---

## 8. Verification Summary

- **Vitest**:
  ```bash
  cd frontend
  npx vitest run src/features/sessions/session-terminal-summary.test.tsx src/features/sessions/session-grouping.test.ts
  ```
  - Test Files: 2 passed (2)
  - Tests: 14 passed (14)
  - Failed: 0
  - Duration: 1.02s
- **TypeScript Typecheck**: `npm run typecheck` (0 errors).
- **ESLint**: 0 warnings, 0 errors across all changed files.
- **Git Check**: `git diff --check` clean (0 errors).
