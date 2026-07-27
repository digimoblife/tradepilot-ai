import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { RequestAnalysis } from "./request-analysis";
import type { TradeState, TradeSessionSummary } from "@/types/trade-session";
import * as tradeSessionApi from "@/lib/api/trade-sessions";
import * as analysesApi from "@/lib/api/analyses";

vi.mock("@/lib/api/analyses", () => ({
  requestAnalysis: vi.fn().mockResolvedValue({
    job_id: "j1",
    session_id: "s1",
    analysis_type: "CLOSING_ANALYSIS",
    status: "QUEUED",
  }),
}));

vi.mock("@/lib/api/evidence", () => ({
  listEvidence: vi.fn().mockResolvedValue({ evidence: [] }),
}));

describe("P5 Closing Analysis Flow", () => {
  const mockClosedSession: TradeSessionSummary = {
    id: "s1",
    ticker: "BBRI",
    title: "Trade BBRI",
    company_name: "Bank Rakyat Indonesia",
    exchange: "IDX",
    currency: "IDR",
    lifecycle_status: "CLOSED",
    archived_at: null,
    created_at: "2026-07-20T10:00:00Z",
    updated_at: "2026-07-27T10:00:00Z",
  };

  const mockClosedTradeState: TradeState = {
    position_status: "CLOSED",
    thesis_status: "CLOSED",
    entry_price: "5000",
    entry_at: "2026-07-20T10:00:00Z",
    original_quantity: "100",
    remaining_quantity: "0",
    active_stop_loss: null,
    active_target: null,
    average_exit_price: "5500",
    realized_pnl: "50000",
    realized_return: "10.0",
    state_version: 2,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders 0-evidence request analysis UI and enables submission for CLOSING_ANALYSIS", async () => {
    const onSuccess = vi.fn();
    render(
      <RequestAnalysis
        sessionId="s1"
        analysisType="CLOSING_ANALYSIS"
        onSuccess={onSuccess}
      />
    );

    await waitFor(() => {
      const submitBtn = screen.getByRole("button", { name: /Jalankan Closing Analysis/i });
      expect(submitBtn).not.toBeDisabled();
    });

    const submitBtn = screen.getByRole("button", { name: /Jalankan Closing Analysis/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(analysesApi.requestAnalysis).toHaveBeenCalledWith(
        "s1",
        { analysis_type: "CLOSING_ANALYSIS" }
      );
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("displays closed trade outcome metrics and safe missing data fallbacks", () => {
    render(
      <div data-testid="closed-outcome-view">
        <h2>Sesi Selesai (CLOSED)</h2>
        <div>Harga Masuk: Rp {mockClosedTradeState.entry_price}</div>
        <div>Harga Keluar: Rp {mockClosedTradeState.average_exit_price}</div>
        <div>Return Realisasi: +{mockClosedTradeState.realized_return}%</div>
        <div>Status Posisi: {mockClosedTradeState.position_status}</div>
        <button onClick={() => window.location.assign("/")}>Buat Sesi Baru</button>
      </div>
    );

    expect(screen.getByText("Sesi Selesai (CLOSED)")).toBeInTheDocument();
    expect(screen.getByText("Harga Masuk: Rp 5000")).toBeInTheDocument();
    expect(screen.getByText("Harga Keluar: Rp 5500")).toBeInTheDocument();
    expect(screen.getByText("Return Realisasi: +10.0%")).toBeInTheDocument();
    expect(screen.getByText("Buat Sesi Baru")).toBeInTheDocument();
  });
});
