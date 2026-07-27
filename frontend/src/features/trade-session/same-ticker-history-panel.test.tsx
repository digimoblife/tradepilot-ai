import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SameTickerHistoryPanel } from "./same-ticker-history-panel";
import * as tradeSessionApi from "@/lib/api/trade-sessions";

vi.mock("@/lib/api/trade-sessions", () => ({
  getSameTickerHistory: vi.fn(),
}));

describe("SameTickerHistoryPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders history indicator badge when historical context was used", async () => {
    vi.mocked(tradeSessionApi.getSameTickerHistory).mockResolvedValueOnce({
      session_id: "s1",
      ticker: "BBRI",
      historical_context_used: true,
      historical_session_count: 2,
      completed_trade_count: 2,
      skipped_session_count: 0,
      historical_source_session_ids: ["prior1", "prior2"],
      historical_summary_generated_at: "2026-07-27T10:00:00Z",
      recent_outcomes: [
        {
          session_id: "prior1",
          lifecycle_status: "CLOSED",
          entry_price: "5000",
          average_exit_price: "5500",
          realized_return: "10.0",
          closing_summary: "Profit taken at target",
        },
      ],
      useful_lessons: ["Wait for volume confirmation at support"],
      confidence_calibration_notes: [],
      data_quality_notes: [],
    });

    render(<SameTickerHistoryPanel sessionId="s1" />);

    await waitFor(() => {
      expect(
        screen.getByText(/Riwayat ticker digunakan: 2 sesi sebelumnya/i)
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Konteks Sekunder")).toBeInTheDocument();

    const toggleBtn = screen.getByRole("button", { name: /Lihat Ringkasan Riwayat/i });
    fireEvent.click(toggleBtn);

    expect(screen.getByText("Hasil Sesi Sebelumnya")).toBeInTheDocument();
    expect(screen.getByText(/Sesi prior1/i)).toBeInTheDocument();
    expect(screen.getByText("Harga Masuk: Rp 5000")).toBeInTheDocument();
    expect(screen.getByText("Harga Keluar: Rp 5500")).toBeInTheDocument();
    expect(screen.getByText("Wait for volume confirmation at support")).toBeInTheDocument();
  });

  it("renders nothing when historical_context_used is false", async () => {
    vi.mocked(tradeSessionApi.getSameTickerHistory).mockResolvedValueOnce({
      session_id: "s2",
      ticker: "TLKM",
      historical_context_used: false,
      historical_session_count: 0,
      completed_trade_count: 0,
      skipped_session_count: 0,
      historical_source_session_ids: [],
      historical_summary_generated_at: "2026-07-27T10:00:00Z",
      recent_outcomes: [],
      useful_lessons: [],
      confidence_calibration_notes: [],
      data_quality_notes: [],
    });

    const { container } = render(<SameTickerHistoryPanel sessionId="s2" />);

    await waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });
});
