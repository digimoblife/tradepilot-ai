import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { confirmTarget, changeTarget } from "@/lib/api/trade-actions";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { openPositionUpdateFixture } from "@/test/fixtures";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

vi.mock("@/lib/api/trade-actions", () => ({
  confirmTarget: vi.fn(),
  changeTarget: vi.fn(),
}));

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { TargetModal } from "./target-modal";

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
  vi.mocked(confirmTarget).mockReset();
  vi.mocked(changeTarget).mockReset();
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
  activeTarget: "3000",
};

// -------------------------------------------------------------------
// Modal rendering
// -------------------------------------------------------------------
describe("modal rendering", () => {
  it("does not render when isOpen is false", () => {
    const { container } = render(<TargetModal {...defaultProps} isOpen={false} action="CONFIRM_TARGET" />);
    expect(container.innerHTML).toBe("");
  });

  it("shows title for CONFIRM_TARGET", () => {
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    expect(screen.getByRole("heading", { level: 2, name: "Konfirmasi Target" })).toBeTruthy();
  });

  it("shows title for CHANGE_TARGET", () => {
    render(<TargetModal {...defaultProps} action="CHANGE_TARGET" />);
    expect(screen.getByRole("heading", { level: 2, name: "Ubah Target" })).toBeTruthy();
  });

  it("shows active target value", async () => {
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    expect(await screen.findByText(/3.000/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// AI proposal
// -------------------------------------------------------------------
describe("AI proposal", () => {
  it("loads proposal from latest OPU", async () => {
    mockProposalAvailable();
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", { analysis_type: "OPEN_POSITION_UPDATE" });
    });
  });

  it("prefills input from active target when no proposal", async () => {
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    const input = await screen.findByDisplayValue("3000");
    expect(input).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Editing
// -------------------------------------------------------------------
describe("editing", () => {
  it("allows changing the value", async () => {
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    const input = await screen.findByPlaceholderText("3000");
    await userEvent.clear(input);
    await userEvent.type(input, "3100");
    expect(await screen.findByDisplayValue("3100")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Validation
// -------------------------------------------------------------------
describe("validation", () => {
  it("shows error for empty value", async () => {
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    const input = await screen.findByPlaceholderText("3000");
    await userEvent.clear(input);
    const btn = screen.getByRole("button", { name: "Konfirmasi Target" });
    await userEvent.click(btn);
    expect(await screen.findByText(/Nilai target wajib diisi/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Submission
// -------------------------------------------------------------------
describe("submission", () => {
  it("calls confirmTarget for CONFIRM_TARGET action", async () => {
    vi.mocked(confirmTarget).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "TARGET_CONFIRMED", confirmed_at: "", price: "3100", quantity: null },
      session_status: "OPEN_POSITION",
      trade_state: { position_status: "OPEN", entry_price: "2800", original_quantity: "100", remaining_quantity: "100", active_stop_loss: null, active_target: "3100", average_exit_price: null, realized_pnl: null, state_version: 2 },
    });
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    const input = await screen.findByPlaceholderText("3000");
    await userEvent.clear(input);
    await userEvent.type(input, "3100");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Target" }));
    await waitFor(() => { expect(confirmTarget).toHaveBeenCalled(); });
    const call = vi.mocked(confirmTarget).mock.calls[0][0];
    expect(call.target).toBe("3100");
    expect(call.session_id).toBe("sess-a");
  });

  it("calls changeTarget for CHANGE_TARGET action", async () => {
    vi.mocked(changeTarget).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "TARGET_CHANGED", confirmed_at: "", price: "3100", quantity: null },
      session_status: "OPEN_POSITION",
      trade_state: { position_status: "OPEN", entry_price: "2800", original_quantity: "100", remaining_quantity: "100", active_stop_loss: null, active_target: "3100", average_exit_price: null, realized_pnl: null, state_version: 2 },
    });
    render(<TargetModal {...defaultProps} action="CHANGE_TARGET" />);
    const input = await screen.findByPlaceholderText("3000");
    await userEvent.clear(input);
    await userEvent.type(input, "3100");
    await userEvent.click(screen.getByRole("button", { name: "Ubah Target" }));
    await waitFor(() => { expect(changeTarget).toHaveBeenCalled(); });
    const call = vi.mocked(changeTarget).mock.calls[0][0];
    expect(call.target).toBe("3100");
  });

  it("prevents duplicate pending submission", async () => {
    vi.mocked(confirmTarget).mockImplementation(() => new Promise(() => {}));
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    const input = await screen.findByPlaceholderText("3000");
    await userEvent.clear(input);
    await userEvent.type(input, "3100");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Target" }));
    expect(await screen.findByText("Memproses…")).toBeTruthy();
  });

  it("calls onSuccess and onClose after success", async () => {
    vi.mocked(confirmTarget).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "TARGET_CONFIRMED", confirmed_at: "", price: "3100", quantity: null },
      session_status: "OPEN_POSITION",
      trade_state: { position_status: "OPEN", entry_price: "2800", original_quantity: "100", remaining_quantity: "100", active_stop_loss: null, active_target: "3100", average_exit_price: null, realized_pnl: null, state_version: 2 },
    });
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" onSuccess={onSuccess} onClose={onClose} />);
    const input = await screen.findByPlaceholderText("3000");
    await userEvent.clear(input);
    await userEvent.type(input, "3100");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Target" }));
    await waitFor(() => { expect(onSuccess).toHaveBeenCalled(); });
    expect(onClose).toHaveBeenCalled();
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows API error", async () => {
    vi.mocked(confirmTarget).mockRejectedValue(new ApiError(400, "ERROR", "Nilai terlalu tinggi."));
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    const input = await screen.findByPlaceholderText("3000");
    await userEvent.clear(input);
    await userEvent.type(input, "3100");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Target" }));
    expect(await screen.findByText("Nilai terlalu tinggi.")).toBeTruthy();
  });

  it("shows auth error", async () => {
    vi.mocked(confirmTarget).mockRejectedValue(new AuthenticationError(401, "AUTH", "Auth"));
    render(<TargetModal {...defaultProps} action="CONFIRM_TARGET" />);
    const input = await screen.findByPlaceholderText("3000");
    await userEvent.clear(input);
    await userEvent.type(input, "3100");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Target" }));
    expect(await screen.findByText("Silakan masuk terlebih dahulu.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Safety
// -------------------------------------------------------------------
describe("safety", () => {
  it("does not use direct fetch", () => {
    const src = TargetModal.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
  });
});
