import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { confirmStop, changeStop } from "@/lib/api/trade-actions";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { openPositionUpdateFixture } from "@/test/fixtures";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

vi.mock("@/lib/api/trade-actions", () => ({
  confirmStop: vi.fn(),
  changeStop: vi.fn(),
}));

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { StopLossModal } from "./stop-loss-modal";

function makeOPUSummary(): AnalysisSummary {
  return {
    id: "opu-proposal",
    session_id: "sess-a",
    analysis_type: "OPEN_POSITION_UPDATE",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-20T10:00:00+07:00",
    created_at: "2026-07-20T09:55:00+07:00",
    prompt_version: "1.0.0",
    schema_name: "open_position_update",
    schema_version: "1.0.0",
    supersedes_analysis_id: null,
  };
}

function makeOPUDetail(): AnalysisDetail {
  return {
    id: "opu-proposal",
    session_id: "sess-a",
    analysis_type: "OPEN_POSITION_UPDATE",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-20T10:00:00+07:00",
    created_at: "2026-07-20T09:55:00+07:00",
    prompt_name: "open_position_update",
    prompt_version: "1.0.0",
    schema_name: "open_position_update",
    schema_version: "1.0.0",
    payload: JSON.parse(JSON.stringify(openPositionUpdateFixture)) as Record<string, unknown>,
    supersedes_analysis_id: null,
  };
}

function mockProposalAvailable() {
  vi.mocked(listAnalyses).mockResolvedValue({ analyses: [makeOPUSummary()], total: 1 });
  vi.mocked(getAnalysis).mockResolvedValue(makeOPUDetail());
}

function resetMocks() {
  vi.mocked(confirmStop).mockReset();
  vi.mocked(changeStop).mockReset();
  vi.mocked(listAnalyses).mockReset();
  vi.mocked(getAnalysis).mockReset();
  vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
}

beforeEach(() => {
  vi.clearAllMocks();
  resetMocks();
});

const defaultProps = {
  sessionId: "sess-a",
  isOpen: true,
  onClose: vi.fn(),
  onSuccess: vi.fn(),
  activeStopLoss: "2840",
};

// -------------------------------------------------------------------
// Modal rendering
// -------------------------------------------------------------------
describe("modal rendering", () => {
  it("does not render when isOpen is false", () => {
    const { container } = render(<StopLossModal {...defaultProps} isOpen={false} action="CONFIRM_STOP" />);
    expect(container.innerHTML).toBe("");
  });

  it("shows title for CONFIRM_STOP", () => {
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    expect(screen.getByRole("heading", { level: 2, name: "Konfirmasi Stop Loss" })).toBeTruthy();
  });

  it("shows title for CHANGE_STOP", () => {
    render(<StopLossModal {...defaultProps} action="CHANGE_STOP" />);
    expect(screen.getByRole("heading", { level: 2, name: "Ubah Stop Loss" })).toBeTruthy();
  });

  it("shows active stop loss value", async () => {
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    expect(await screen.findByText(/2.840/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// AI proposal
// -------------------------------------------------------------------
describe("AI proposal", () => {
  it("loads proposal from latest OPU", async () => {
    mockProposalAvailable();
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", { analysis_type: "OPEN_POSITION_UPDATE" });
    });
  });

  it("prefills input from active stop loss when no proposal", async () => {
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    const input = await screen.findByDisplayValue("2840");
    expect(input).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Editing
// -------------------------------------------------------------------
describe("editing", () => {
  it("allows changing the value", async () => {
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    const input = await screen.findByPlaceholderText("2800");
    await userEvent.clear(input);
    await userEvent.type(input, "2900");
    expect(await screen.findByDisplayValue("2900")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Validation
// -------------------------------------------------------------------
describe("validation", () => {
  it("shows error for empty value", async () => {
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    const input = await screen.findByPlaceholderText("2800");
    await userEvent.clear(input);
    const btn = screen.getByRole("button", { name: "Konfirmasi Stop Loss" });
    await userEvent.click(btn);
    expect(await screen.findByText(/Nilai stop loss wajib diisi/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Submission
// -------------------------------------------------------------------
describe("submission", () => {
  it("calls confirmStop for CONFIRM_STOP action", async () => {
    vi.mocked(confirmStop).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "STOP_LOSS_CONFIRMED", confirmed_at: "", price: "2900", quantity: null },
      session_status: "OPEN_POSITION",
      trade_state: { position_status: "OPEN", entry_price: "2800", original_quantity: "100", remaining_quantity: "100", active_stop_loss: "2900", active_target: null, average_exit_price: null, realized_pnl: null, state_version: 2 },
    });
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    const input = await screen.findByPlaceholderText("2800");
    await userEvent.clear(input);
    await userEvent.type(input, "2900");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Stop Loss" }));
    await waitFor(() => { expect(confirmStop).toHaveBeenCalled(); });
    const call = vi.mocked(confirmStop).mock.calls[0][0];
    expect(call.stop_loss).toBe("2900");
    expect(call.session_id).toBe("sess-a");
  });

  it("calls changeStop for CHANGE_STOP action", async () => {
    vi.mocked(changeStop).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "STOP_LOSS_CHANGED", confirmed_at: "", price: "2900", quantity: null },
      session_status: "OPEN_POSITION",
      trade_state: { position_status: "OPEN", entry_price: "2800", original_quantity: "100", remaining_quantity: "100", active_stop_loss: "2900", active_target: null, average_exit_price: null, realized_pnl: null, state_version: 2 },
    });
    render(<StopLossModal {...defaultProps} action="CHANGE_STOP" />);
    const input = await screen.findByPlaceholderText("2800");
    await userEvent.clear(input);
    await userEvent.type(input, "2900");
    await userEvent.click(screen.getByRole("button", { name: "Ubah Stop Loss" }));
    await waitFor(() => { expect(changeStop).toHaveBeenCalled(); });
    const call = vi.mocked(changeStop).mock.calls[0][0];
    expect(call.stop_loss).toBe("2900");
  });

  it("prevents duplicate pending submission", async () => {
    vi.mocked(confirmStop).mockImplementation(() => new Promise(() => {}));
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    const input = await screen.findByPlaceholderText("2800");
    await userEvent.clear(input);
    await userEvent.type(input, "2900");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Stop Loss" }));
    expect(await screen.findByText("Memproses…")).toBeTruthy();
  });

  it("calls onSuccess and onClose after success", async () => {
    vi.mocked(confirmStop).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "STOP_LOSS_CONFIRMED", confirmed_at: "", price: "2900", quantity: null },
      session_status: "OPEN_POSITION",
      trade_state: { position_status: "OPEN", entry_price: "2800", original_quantity: "100", remaining_quantity: "100", active_stop_loss: "2900", active_target: null, average_exit_price: null, realized_pnl: null, state_version: 2 },
    });
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" onSuccess={onSuccess} onClose={onClose} />);
    const input = await screen.findByPlaceholderText("2800");
    await userEvent.clear(input);
    await userEvent.type(input, "2900");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Stop Loss" }));
    await waitFor(() => { expect(onSuccess).toHaveBeenCalled(); });
    expect(onClose).toHaveBeenCalled();
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows API error", async () => {
    vi.mocked(confirmStop).mockRejectedValue(new ApiError(400, "ERROR", "Nilai terlalu rendah."));
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    const input = await screen.findByPlaceholderText("2800");
    await userEvent.clear(input);
    await userEvent.type(input, "2900");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Stop Loss" }));
    expect(await screen.findByText("Nilai terlalu rendah.")).toBeTruthy();
  });

  it("shows auth error", async () => {
    vi.mocked(confirmStop).mockRejectedValue(new AuthenticationError(401, "AUTH", "Auth"));
    render(<StopLossModal {...defaultProps} action="CONFIRM_STOP" />);
    const input = await screen.findByPlaceholderText("2800");
    await userEvent.clear(input);
    await userEvent.type(input, "2900");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Stop Loss" }));
    expect(await screen.findByText("Silakan masuk terlebih dahulu.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Safety
// -------------------------------------------------------------------
describe("safety", () => {
  it("does not use direct fetch", () => {
    const src = StopLossModal.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
  });
});
