import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SessionSummaryContent } from "./session-summary-content";
import type { SessionDetailAggregate } from "@/features/trade-workspace/types";

const sessionId = "11111111-1111-4111-8111-111111111111";

function detail(overrides: Partial<SessionDetailAggregate> = {}): SessionDetailAggregate {
  return {
    session: {
      id: sessionId, ticker: "BBRI", company_name: "Bank BRI", status: "OPEN_POSITION",
      initial_note: null, created_at: "2026-08-05T00:00:00Z",
      updated_at: "2026-08-05T00:00:00Z", closed_at: null,
    },
    initial_evidence: [], initial_analysis: null, decisions: [], wait_updates: [],
    position: {
      status: "OPEN", entry_price: 1200, entry_timestamp: "2026-08-05T00:00:00Z",
      quantity: 100, stop_loss: 1100, target_price: 1300, note: "Catatan posisi yang panjang tetap dapat dibaca.", closed_at: null,
    },
    position_updates: [], closure: null,
    latest_analysis: { analysis_type: "POSITION_UPDATE", completed_at: "2026-08-05T01:00:00Z", has_result: true },
    recent_activity: [
      { type: "POSITION_UPDATE_COMPLETED", occurred_at: "2026-08-05T01:00:00Z", analysis_type: "POSITION_UPDATE", decision: null },
      { type: "BUY_CONFIRMED", occurred_at: "2026-08-05T00:30:00Z", analysis_type: null, decision: "BUY" },
    ],
    current_step: {
      code: "POSITION_MONITORING", mode: "ACTIONABLE", workflow_actions: ["SUBMIT_POSITION_UPDATE", "CLOSE"],
      active_request: null, failed_request: null, read_only: false,
    },
    ...overrides,
  };
}

describe("SessionSummaryContent", () => {
  it("renders bounded canonical metadata, facts, activity, and progressive links", () => {
    render(<SessionSummaryContent sessionId={sessionId} detail={detail()} />);

    expect(screen.getByRole("heading", { name: "Analisis Terbaru" })).toBeInTheDocument();
    expect(screen.getByText("Analisis Pembaruan Posisi")).toBeInTheDocument();
    expect(screen.getByText("Hasil analisis terbaru tersedia untuk ditinjau.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Lihat Analisis" })).toHaveAttribute("href", `/sessions/${sessionId}/analysis`);
    expect(screen.getByRole("heading", { name: "Ringkasan Posisi" })).toBeInTheDocument();
    expect(screen.getByText("1.200")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Aktivitas Terbaru" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Lihat Riwayat" })).toHaveAttribute("href", `/sessions/${sessionId}/history`);
    expect(screen.queryByText(/gemini|prompt versi|model ai/i)).toBeNull();
  });

  it("omits unavailable optional sections and fails CLOSED_SKIPPED position data closed", () => {
    render(<SessionSummaryContent sessionId={sessionId} detail={detail({
      session: { ...detail().session, status: "CLOSED_SKIPPED" },
      latest_analysis: null,
      closure: { close_price: 900, close_timestamp: "2026-08-05T02:00:00Z", close_reason: "x", note: null },
      recent_activity: [{ type: "SKIP_CONFIRMED", occurred_at: "2026-08-05T01:00:00Z", analysis_type: null, decision: "SKIP" }],
    })} />);

    expect(screen.queryByRole("heading", { name: "Analisis Terbaru" })).toBeNull();
    expect(screen.queryByRole("heading", { name: /Posisi/ })).toBeNull();
    expect(screen.getByText("Keputusan SKIP dikonfirmasi")).toBeInTheDocument();
  });
});
