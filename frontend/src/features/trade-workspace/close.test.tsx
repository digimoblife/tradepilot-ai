import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PositionUpdatePanel, CloseResultSummaryView } from "./position-update";
import {
  closePosition,
  readPositionUpdates,
  submitPositionUpdateAnalysis,
  uploadPositionUpdateInput,
} from "./api";
import type { CloseResponse, PositionDetail, PositionUpdatesRead } from "./types";

vi.mock("./api", () => ({
  closePosition: vi.fn(),
  readPositionUpdates: vi.fn(),
  submitPositionUpdateAnalysis: vi.fn(),
  uploadPositionUpdateInput: vi.fn(),
}));

const mockPosition: PositionDetail = {
  id: "pos-1",
  session_id: "session-a",
  status: "OPEN",
  entry_price: "1200.00",
  entry_timestamp: "2026-07-29T10:00:00Z",
  quantity: "10.00",
  stop_loss: "1100.00",
  target_price: "1400.00",
  note: "Entry note",
  created_at: "2026-07-29T10:00:00Z",
};

const mockCloseResponse: CloseResponse = {
  closure_id: "close-1",
  session_id: "session-a",
  position_id: "pos-1",
  close_price: "1350.000000",
  close_timestamp: "2026-07-31T10:00:00Z",
  close_reason: "Target price reached",
  note: "Took profit",
  realized_profit_loss: "1500.000000",
  position_status: "CLOSED",
  session_status: "CLOSED",
  closed_at: "2026-07-31T10:00:00Z",
  created_at: "2026-07-31T10:00:00Z",
};

const mockReadData: PositionUpdatesRead = {
  position: mockPosition,
  updates: [
    {
      analysis_request_id: "req-1",
      session_id: "session-a",
      analysis_type: "POSITION_UPDATE",
      request_status: "COMPLETED",
      current_price: "1250.00",
      observation_period: "MORNING",
      observation_timestamp: "2026-07-30T09:00:00Z",
      processed_response: {
        update_summary: "Posisi stabil.",
      },
      error_code: null,
      error_message: null,
      created_at: "2026-07-30T09:00:00Z",
      started_at: "2026-07-30T09:00:01Z",
      completed_at: "2026-07-30T09:00:05Z",
    },
  ],
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(readPositionUpdates).mockResolvedValue(mockReadData);
});

describe("CLOSE Frontend (P9.3)", () => {
  it("renders CLOSE button in OPEN_POSITION and opens confirmation form on click", async () => {
    render(<PositionUpdatePanel sessionId="session-a" sessionStatus="OPEN_POSITION" initialPosition={mockPosition} />);

    await screen.findByRole("heading", { name: "Position Update" });
    const closeBtn = screen.getByRole("button", { name: "Tutup Posisi (CLOSE)" });
    expect(closeBtn).toBeTruthy();

    fireEvent.click(closeBtn);

    expect(screen.getByRole("heading", { name: "Konfirmasi Tutup Posisi (CLOSE)" })).toBeTruthy();
    expect(screen.getByLabelText(/harga penutupan/i)).toBeTruthy();
    expect(screen.getByLabelText(/waktu penutupan/i)).toBeTruthy();
    expect(screen.getByLabelText(/alasan penutupan/i)).toBeTruthy();
    expect(screen.getByLabelText(/catatan \(opsional\)/i)).toBeTruthy();
  });

  it("submits close confirmation to POST /close with approved fields only", async () => {
    const user = userEvent.setup();
    vi.mocked(closePosition).mockResolvedValue(mockCloseResponse);

    render(<PositionUpdatePanel sessionId="session-a" sessionStatus="OPEN_POSITION" initialPosition={mockPosition} />);

    await screen.findByRole("heading", { name: "Position Update" });
    fireEvent.click(screen.getByRole("button", { name: "Tutup Posisi (CLOSE)" }));

    await user.type(screen.getByLabelText(/harga penutupan/i), "1350.00");
    fireEvent.change(screen.getByLabelText(/waktu penutupan/i), { target: { value: "2026-07-31T10:00" } });
    await user.type(screen.getByLabelText(/alasan penutupan/i), "Target price reached");
    await user.type(screen.getByLabelText(/catatan \(opsional\)/i), "Took profit");

    const submitBtn = screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(closePosition).toHaveBeenCalledWith("session-a", {
        close_price: "1350.00",
        close_timestamp: expect.any(String),
        close_reason: "Target price reached",
        note: "Took profit",
      });
    });
  });

  it("handles successful CLOSE by showing summary, updating statuses, and disabling update forms", async () => {
    const user = userEvent.setup();
    vi.mocked(closePosition).mockResolvedValue(mockCloseResponse);

    render(<PositionUpdatePanel sessionId="session-a" sessionStatus="OPEN_POSITION" initialPosition={mockPosition} />);

    await screen.findByRole("heading", { name: "Position Update" });
    fireEvent.click(screen.getByRole("button", { name: "Tutup Posisi (CLOSE)" }));

    await user.type(screen.getByLabelText(/harga penutupan/i), "1350.00");
    fireEvent.change(screen.getByLabelText(/waktu penutupan/i), { target: { value: "2026-07-31T10:00" } });
    await user.type(screen.getByLabelText(/alasan penutupan/i), "Target price reached");

    fireEvent.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));

    expect(await screen.findByText("Posisi berhasil ditutup.")).toBeTruthy();
    expect(screen.getByText("Ringkasan Penutupan Posisi (CLOSE)")).toBeTruthy();
    expect(screen.getByText("1350.000000")).toBeTruthy();
    expect(screen.getByText("1500.000000")).toBeTruthy();
    expect(screen.getByText("Posisi CLOSED")).toBeTruthy();

    // Position Update form is hidden after CLOSE
    expect(screen.queryByRole("heading", { name: "Position Update" })).toBeNull();
    // Previously loaded timeline remains visible
    expect(screen.getByText("Posisi stabil.")).toBeTruthy();
  });

  it("handles CLOSE failure gracefully and preserves entered form inputs", async () => {
    const user = userEvent.setup();
    vi.mocked(closePosition).mockRejectedValue(new Error("Network connection error"));

    render(<PositionUpdatePanel sessionId="session-a" sessionStatus="OPEN_POSITION" initialPosition={mockPosition} />);

    await screen.findByRole("heading", { name: "Position Update" });
    fireEvent.click(screen.getByRole("button", { name: "Tutup Posisi (CLOSE)" }));

    await user.type(screen.getByLabelText(/harga penutupan/i), "1350.00");
    fireEvent.change(screen.getByLabelText(/waktu penutupan/i), { target: { value: "2026-07-31T10:00" } });
    await user.type(screen.getByLabelText(/alasan penutupan/i), "Target price reached");

    fireEvent.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));

    expect(await screen.findByText("Network connection error")).toBeTruthy();

    // Values preserved for retry
    expect((screen.getByLabelText(/harga penutupan/i) as HTMLInputElement).value).toBe("1350.00");
    expect((screen.getByLabelText(/alasan penutupan/i) as HTMLInputElement).value).toBe("Target price reached");
    expect(screen.getByText("Posisi OPEN")).toBeTruthy();
  });
});
