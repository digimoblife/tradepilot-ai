import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { partialExit } from "@/lib/api/trade-actions";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

vi.mock("@/lib/api/trade-actions", () => ({
  partialExit: vi.fn(),
}));

import { PartialExitModal } from "./partial-exit-modal";

function resetMock() {
  vi.mocked(partialExit).mockReset();
}

beforeEach(() => {
  vi.clearAllMocks();
  resetMock();
});

const defaultProps = {
  sessionId: "sess-a",
  isOpen: true,
  onClose: vi.fn(),
  onSuccess: vi.fn(),
  remainingQuantity: "100",
};

// -------------------------------------------------------------------
// Modal rendering
// -------------------------------------------------------------------
describe("modal rendering", () => {
  it("does not render when isOpen is false", () => {
    const { container } = render(<PartialExitModal {...defaultProps} isOpen={false} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders title and form fields", () => {
    render(<PartialExitModal {...defaultProps} />);
    expect(screen.getByText("Partial Exit")).toBeTruthy();
    expect(screen.getByText("Harga Exit")).toBeTruthy();
    expect(screen.getByText("Quantity Dijual")).toBeTruthy();
    expect(screen.getByText("Waktu Eksekusi")).toBeTruthy();
    expect(screen.getByText("Alasan")).toBeTruthy();
    expect(screen.getByText("Catatan")).toBeTruthy();
  });

  it("shows remaining quantity", () => {
    render(<PartialExitModal {...defaultProps} />);
    expect(screen.getByText("100")).toBeTruthy();
  });

  it("shows buttons", () => {
    render(<PartialExitModal {...defaultProps} />);
    expect(screen.getByText("Batal")).toBeTruthy();
    expect(screen.getByText("Konfirmasi Partial Exit")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Remaining quantity preview
// -------------------------------------------------------------------
describe("remaining quantity preview", () => {
  it("shows remaining after exit calculation", async () => {
    render(<PartialExitModal {...defaultProps} />);
    const input = screen.getByPlaceholderText("30");
    await userEvent.type(input, "30");
    expect(await screen.findByText(/Sisa setelah exit/)).toBeTruthy();
    expect(await screen.findByText(/70/)).toBeTruthy();
  });

  it("does not show preview when quantity is empty", () => {
    render(<PartialExitModal {...defaultProps} />);
    expect(screen.queryByText(/Sisa setelah exit/)).toBeNull();
  });
});

// -------------------------------------------------------------------
// Validation
// -------------------------------------------------------------------
describe("validation", () => {
  it("shows errors when submitting empty form", async () => {
    render(<PartialExitModal {...defaultProps} />);
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Partial Exit" }));
    expect(await screen.findByText(/Harga exit harus lebih besar dari 0/)).toBeTruthy();
    expect(await screen.findByText(/Quantity harus lebih besar dari 0/)).toBeTruthy();
    expect(await screen.findByText(/Alasan partial exit wajib diisi/)).toBeTruthy();
  });

  it("rejects full remaining quantity as partial exit", async () => {
    render(<PartialExitModal {...defaultProps} />);
    const input = screen.getByPlaceholderText("30");
    await userEvent.type(input, "100");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Partial Exit" }));
    expect(await screen.findByText(/Gunakan Tutup Posisi untuk keluar penuh/)).toBeTruthy();
  });

  it("rejects quantity exceeding remaining", async () => {
    render(<PartialExitModal {...defaultProps} />);
    const input = screen.getByPlaceholderText("30");
    await userEvent.type(input, "150");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Partial Exit" }));
    expect(await screen.findByText(/Gunakan Tutup Posisi untuk keluar penuh/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Submission
// -------------------------------------------------------------------
describe("submission", () => {
  it("calls partialExit with user values", async () => {
    vi.mocked(partialExit).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "PARTIAL_EXIT", confirmed_at: "", price: "2900", quantity: "30" },
      session_status: "PARTIALLY_CLOSED",
      trade_state: { position_status: "PARTIALLY_CLOSED", entry_price: "2800", original_quantity: "100", remaining_quantity: "70", active_stop_loss: null, active_target: null, average_exit_price: "2900", realized_pnl: "3000", state_version: 2 },
    });
    render(<PartialExitModal {...defaultProps} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.type(screen.getByPlaceholderText("30"), "30");
    await userEvent.selectOptions(screen.getByRole("combobox"), "PARTIAL_TAKE_PROFIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Partial Exit" }));
    await waitFor(() => { expect(partialExit).toHaveBeenCalled(); });
    const call = vi.mocked(partialExit).mock.calls[0][0];
    expect(call.exit_price).toBe("2900");
    expect(call.exit_quantity).toBe("30");
    expect(call.reason).toBe("PARTIAL_TAKE_PROFIT");
    expect(call.session_id).toBe("sess-a");
  });

  it("prevents duplicate pending submission", async () => {
    vi.mocked(partialExit).mockImplementation(() => new Promise(() => {}));
    render(<PartialExitModal {...defaultProps} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.type(screen.getByPlaceholderText("30"), "30");
    await userEvent.selectOptions(screen.getByRole("combobox"), "PARTIAL_TAKE_PROFIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Partial Exit" }));
    expect(await screen.findByText("Memproses…")).toBeTruthy();
  });

  it("calls onSuccess and onClose after success", async () => {
    vi.mocked(partialExit).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "PARTIAL_EXIT", confirmed_at: "", price: "2900", quantity: "30" },
      session_status: "PARTIALLY_CLOSED",
      trade_state: { position_status: "PARTIALLY_CLOSED", entry_price: "2800", original_quantity: "100", remaining_quantity: "70", active_stop_loss: null, active_target: null, average_exit_price: "2900", realized_pnl: "3000", state_version: 2 },
    });
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    render(<PartialExitModal {...defaultProps} onSuccess={onSuccess} onClose={onClose} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.type(screen.getByPlaceholderText("30"), "30");
    await userEvent.selectOptions(screen.getByRole("combobox"), "PARTIAL_TAKE_PROFIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Partial Exit" }));
    await waitFor(() => { expect(onSuccess).toHaveBeenCalled(); });
    expect(onClose).toHaveBeenCalled();
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows API error", async () => {
    vi.mocked(partialExit).mockRejectedValue(new ApiError(400, "ERROR", "Quantity tidak valid."));
    render(<PartialExitModal {...defaultProps} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.type(screen.getByPlaceholderText("30"), "30");
    await userEvent.selectOptions(screen.getByRole("combobox"), "PARTIAL_TAKE_PROFIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Partial Exit" }));
    expect(await screen.findByText("Quantity tidak valid.")).toBeTruthy();
  });

  it("shows auth error", async () => {
    vi.mocked(partialExit).mockRejectedValue(new AuthenticationError(401, "AUTH", "Auth"));
    render(<PartialExitModal {...defaultProps} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.type(screen.getByPlaceholderText("30"), "30");
    await userEvent.selectOptions(screen.getByRole("combobox"), "PARTIAL_TAKE_PROFIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Partial Exit" }));
    expect(await screen.findByText("Silakan masuk terlebih dahulu.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Safety
// -------------------------------------------------------------------
describe("safety", () => {
  it("does not use direct fetch", () => {
    const src = PartialExitModal.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
  });
});
