import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { WaitUpdatePanel } from "./wait-update";
import { readWaitUpdateAnalysis } from "./api";

vi.mock("./api", () => ({
  readWaitUpdateAnalysis: vi.fn(),
  retryWaitUpdateAnalysis: vi.fn(),
  submitWaitUpdateAnalysis: vi.fn(),
  uploadWaitUpdateInput: vi.fn(),
}));

describe("Gate F WAIT Update frontend boundary", () => {
  it("keeps the result session-scoped and exposes only the approved completed sections", async () => {
    vi.mocked(readWaitUpdateAnalysis).mockResolvedValue({
      analysis_request_id: "request-b",
      session_id: "session-b",
      analysis_type: "WAIT_UPDATE",
      request_status: "COMPLETED",
      session_status: "WAITING",
      processed_response: {
        update_summary: "Update",
        current_price: 1234,
        orderbook_assessment: "Seimbang",
        change_from_previous_analysis: "Tetap",
        current_entry_condition: "Belum siap",
        key_risks: ["Volatilitas"],
        upside_probability: 55,
        downside_probability: 45,
        recommended_action: "WAIT",
        next_plan: "Pantau",
        conclusion: "Tunggu",
      },
      error_code: null,
      error_message: null,
      observation_period: "MIDDAY",
      created_at: "2026-07-30T00:00:00Z",
      started_at: "2026-07-30T00:01:00Z",
      completed_at: "2026-07-30T00:02:00Z",
    });
    render(
      <WaitUpdatePanel
        sessionId="session-b"
        sessionStatus="WAITING"
        onProcessing={vi.fn()}
        onFinished={vi.fn()}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Hasil WAIT Update" })).toBeTruthy();
    expect(readWaitUpdateAnalysis).toHaveBeenCalledWith("session-b");
    expect(screen.getByRole("heading", { name: "Kesimpulan AI" })).toBeTruthy();
    expect(screen.queryByText(/raw_response|input_snapshot/i)).toBeNull();
  });
});
