import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PositionUpdatePanel, PositionSummaryView, PositionUpdateResultView } from "./position-update";
import {
  readPositionUpdates,
  submitPositionUpdateAnalysis,
  uploadPositionUpdateInput,
} from "./api";
import type { PositionDetail, PositionUpdatesRead } from "./types";

vi.mock("./api", () => ({
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
        update_summary: "Posisi bergerak naik.",
        current_price: "1250.00",
        position_condition: "Baik",
        orderbook_assessment: "Orderbook kuat",
        change_from_previous_analysis: "Meningkat",
        target_realism: "Tinggi",
        downside_risk: "Rendah",
        target_probability: "75%",
        trading_plan: "Hold posisi",
        monitoring_points: "Pantau resisten 1300",
        warnings: "Tetap ikuti SL",
        conclusion: "Pertahankan posisi",
      },
      error_code: null,
      error_message: null,
      created_at: "2026-07-30T09:00:00Z",
      started_at: "2026-07-30T09:00:01Z",
      completed_at: "2026-07-30T09:00:05Z",
    },
    {
      analysis_request_id: "req-2",
      session_id: "session-a",
      analysis_type: "POSITION_UPDATE",
      request_status: "FAILED",
      current_price: "1270.00",
      observation_period: "MIDDAY",
      observation_timestamp: "2026-07-30T12:00:00Z",
      processed_response: null,
      error_code: "GEMINI_ERROR",
      error_message: "Gagal terhubung ke Gemini",
      created_at: "2026-07-30T12:00:00Z",
      started_at: "2026-07-30T12:00:01Z",
      completed_at: "2026-07-30T12:00:03Z",
    },
  ],
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(readPositionUpdates).mockResolvedValue({ position: mockPosition, updates: [] });
});

describe("Position Update Frontend", () => {
  it("renders position summary with confirmed stored facts and CLOSE button", () => {
    render(<PositionSummaryView position={mockPosition} />);

    expect(screen.getByText("Posisi OPEN")).toBeTruthy();
    expect(screen.getByText("1200.00")).toBeTruthy();
    expect(screen.getByText("10.00")).toBeTruthy();
    expect(screen.getByText("1100.00")).toBeTruthy();
    expect(screen.getByText("1400.00")).toBeTruthy();
    expect(screen.getByText("2026-07-29T10:00:00Z")).toBeTruthy();
    expect(screen.getByText("Catatan: Entry note")).toBeTruthy();

    const closeBtn = screen.getByRole("button", { name: "Tutup Posisi (CLOSE)" });
    expect(closeBtn).toBeTruthy();
  });

  it("does not render BUY, WAIT, or SKIP decision controls", async () => {
    render(<PositionUpdatePanel sessionId="session-a" sessionStatus="OPEN_POSITION" initialPosition={mockPosition} />);

    await screen.findByRole("heading", { name: "Position Update" });
    expect(screen.queryByRole("button", { name: "BUY" })).toBeNull();
    expect(screen.queryByRole("button", { name: "WAIT" })).toBeNull();
    expect(screen.queryByRole("button", { name: "SKIP" })).toBeNull();
  });

  it("renders Position Update form for OPEN_POSITION sessions", async () => {
    render(<PositionUpdatePanel sessionId="session-a" sessionStatus="OPEN_POSITION" initialPosition={mockPosition} />);

    expect(await screen.findByRole("heading", { name: "Position Update" })).toBeTruthy();
    expect(screen.getByLabelText(/orderbook/i)).toBeTruthy();
    expect(screen.getByLabelText(/harga saat ini/i)).toBeTruthy();
    expect(screen.getByLabelText(/periode observasi/i)).toBeTruthy();
    expect(screen.getByLabelText(/waktu observasi/i)).toBeTruthy();
    expect(screen.getByLabelText(/catatan opsional/i)).toBeTruthy();
  });

  it("does not render active Position Update form for non-OPEN_POSITION sessions", () => {
    render(<PositionUpdatePanel sessionId="session-a" sessionStatus="WAITING" initialPosition={null} />);

    expect(screen.queryByRole("heading", { name: "Position Update" })).toBeNull();
    expect(screen.queryByLabelText(/harga saat ini/i)).toBeNull();
  });

  it("submits position update input and analysis request to official endpoint", async () => {
    const user = userEvent.setup();
    const file = new File(["image"], "orderbook.png", { type: "image/png" });

    vi.mocked(uploadPositionUpdateInput).mockResolvedValue({
      evidence_id: "ev-1",
      session_id: "session-a",
      position_id: "pos-1",
      evidence_type: "ORDERBOOK",
      original_filename: "orderbook.png",
      mime_type: "image/png",
      size_bytes: 5,
      current_price: "1250.00",
      observation_period: "MIDDAY",
      observation_timestamp: "2026-07-30T12:00:00Z",
      uploaded_at: "2026-07-30T12:01:00Z",
      session_status: "OPEN_POSITION",
      position_status: "OPEN",
    });

    vi.mocked(submitPositionUpdateAnalysis).mockResolvedValue({
      analysis_request_id: "req-3",
      session_id: "session-a",
      position_id: "pos-1",
      analysis_type: "POSITION_UPDATE",
      request_status: "PENDING",
      evidence_id: "ev-1",
      observation_period: "MIDDAY",
      session_status: "OPEN_POSITION",
      position_status: "OPEN",
      created_at: "2026-07-30T12:01:00Z",
    });

    render(<PositionUpdatePanel sessionId="session-a" sessionStatus="OPEN_POSITION" initialPosition={mockPosition} />);

    await screen.findByRole("heading", { name: "Position Update" });

    await user.upload(screen.getByLabelText(/orderbook/i), file);
    await user.type(screen.getByLabelText(/harga saat ini/i), "1250.00");
    fireEvent.change(screen.getByLabelText(/periode observasi/i), { target: { value: "MIDDAY" } });
    fireEvent.change(screen.getByLabelText(/waktu observasi/i), { target: { value: "2026-07-30T12:00" } });

    const submitBtn = screen.getByRole("button", { name: "Kirim Position Update" });
    fireEvent.submit(submitBtn.closest("form")!);

    await waitFor(() => {
      expect(uploadPositionUpdateInput).toHaveBeenCalledWith("session-a", {
        orderbook: file,
        current_price: "1250.00",
        observation_period: "MIDDAY",
        observation_timestamp: expect.any(String),
      });
      expect(submitPositionUpdateAnalysis).toHaveBeenCalledWith("session-a");
    });
  });

  it("displays chronological Position Updates and completed analysis sections", async () => {
    vi.mocked(readPositionUpdates).mockResolvedValue(mockReadData);

    render(<PositionUpdatePanel sessionId="session-a" sessionStatus="OPEN_POSITION" initialPosition={mockPosition} />);

    expect(await screen.findByText("Riwayat Position Update")).toBeTruthy();
    expect(screen.getByText("Posisi bergerak naik.")).toBeTruthy();
    expect(screen.getByText("Hold posisi")).toBeTruthy();
    expect(screen.getByText("Analisis Position Update gagal diproses.")).toBeTruthy();
    expect(screen.getByText("Permintaan Position Update tidak dapat diproses. Silakan coba lagi.")).toBeTruthy();
    expect(screen.queryByText("Gagal terhubung ke Gemini")).toBeNull();
  });
});
