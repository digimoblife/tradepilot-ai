import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fullExit } from "@/lib/api/trade-actions";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

vi.mock("@/lib/api/trade-actions", () => ({
  fullExit: vi.fn(),
}));

import { FullExitModal } from "./full-exit-modal";

function resetMock() {
  vi.mocked(fullExit).mockReset();
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
  entryPrice: "2800",
  activeStopLoss: "2840",
  activeTarget: "3000",
};

// -------------------------------------------------------------------
// Modal rendering
// -------------------------------------------------------------------
describe("modal rendering", () => {
  it("does not render when isOpen is false", () => {
    const { container } = render(<FullExitModal {...defaultProps} isOpen={false} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders title and form fields", () => {
    render(<FullExitModal {...defaultProps} />);
    expect(screen.getByText("Tutup Posisi")).toBeTruthy();
    expect(screen.getByText("Harga Exit")).toBeTruthy();
    expect(screen.getByText("Waktu Eksekusi")).toBeTruthy();
    expect(screen.getByText("Alasan Penutupan")).toBeTruthy();
    expect(screen.getByText("Biaya (opsional)")).toBeTruthy();
    expect(screen.getByText("Catatan")).toBeTruthy();
  });

  it("shows confirmation banner", () => {
    render(<FullExitModal {...defaultProps} />);
    expect(screen.getByText(/Seluruh posisi/)).toBeTruthy();
    expect(screen.getByText(/100/)).toBeTruthy();
    expect(screen.getByText(/tidak dapat dibatalkan/)).toBeTruthy();
  });

  it("shows active stop and target", () => {
    render(<FullExitModal {...defaultProps} />);
    expect(screen.getByText(/2.840/)).toBeTruthy();
    expect(screen.getByText(/3.000/)).toBeTruthy();
  });

  it("shows buttons", () => {
    render(<FullExitModal {...defaultProps} />);
    expect(screen.getByText("Batal")).toBeTruthy();
    expect(screen.getByText("Konfirmasi Tutup Posisi")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Validation
// -------------------------------------------------------------------
describe("validation", () => {
  it("shows errors when submitting empty form", async () => {
    render(<FullExitModal {...defaultProps} />);
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));
    expect(await screen.findByText(/Harga exit harus lebih besar dari 0/)).toBeTruthy();
    expect(await screen.findByText(/Alasan penutupan wajib diisi/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Submission
// -------------------------------------------------------------------
describe("submission", () => {
  it("calls fullExit with user values and remaining quantity", async () => {
    vi.mocked(fullExit).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "FULL_EXIT", confirmed_at: "", price: "2900", quantity: "100" },
      session_status: "CLOSED_MANUAL",
      trade_state: { position_status: "CLOSED", entry_price: "2800", original_quantity: "100", remaining_quantity: "0", active_stop_loss: null, active_target: null, average_exit_price: "2900", realized_pnl: "10000", state_version: 3 },
    });
    render(<FullExitModal {...defaultProps} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.selectOptions(screen.getByRole("combobox"), "MANUAL_EXIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));
    await waitFor(() => { expect(fullExit).toHaveBeenCalled(); });
    const call = vi.mocked(fullExit).mock.calls[0][0];
    expect(call.exit_price).toBe("2900");
    expect(call.exit_quantity).toBe("100");
    expect(call.closing_reason).toBe("MANUAL_EXIT");
    expect(call.session_id).toBe("sess-a");
  });

  it("prevents duplicate pending submission", async () => {
    vi.mocked(fullExit).mockImplementation(() => new Promise(() => {}));
    render(<FullExitModal {...defaultProps} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.selectOptions(screen.getByRole("combobox"), "MANUAL_EXIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));
    expect(await screen.findByText("Memproses…")).toBeTruthy();
  });

  it("calls onSuccess and onClose after success", async () => {
    vi.mocked(fullExit).mockResolvedValue({
      action: { id: "a", session_id: "sess-a", action_type: "FULL_EXIT", confirmed_at: "", price: "2900", quantity: "100" },
      session_status: "CLOSED_MANUAL",
      trade_state: { position_status: "CLOSED", entry_price: "2800", original_quantity: "100", remaining_quantity: "0", active_stop_loss: null, active_target: null, average_exit_price: "2900", realized_pnl: "10000", state_version: 3 },
    });
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    render(<FullExitModal {...defaultProps} onSuccess={onSuccess} onClose={onClose} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.selectOptions(screen.getByRole("combobox"), "MANUAL_EXIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));
    await waitFor(() => { expect(onSuccess).toHaveBeenCalled(); });
    expect(onClose).toHaveBeenCalled();
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows API error", async () => {
    vi.mocked(fullExit).mockRejectedValue(new ApiError(400, "ERROR", "Harga tidak valid."));
    render(<FullExitModal {...defaultProps} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.selectOptions(screen.getByRole("combobox"), "MANUAL_EXIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));
    expect(await screen.findByText("Harga tidak valid.")).toBeTruthy();
  });

  it("shows auth error", async () => {
    vi.mocked(fullExit).mockRejectedValue(new AuthenticationError(401, "AUTH", "Auth"));
    render(<FullExitModal {...defaultProps} />);
    await userEvent.type(screen.getByPlaceholderText("2900"), "2900");
    await userEvent.selectOptions(screen.getByRole("combobox"), "MANUAL_EXIT");
    await userEvent.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));
    expect(await screen.findByText("Silakan masuk terlebih dahulu.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Result preview
// -------------------------------------------------------------------
describe("result preview", () => {
  it("shows preview when exit price is entered", async () => {
    render(<FullExitModal {...defaultProps} />);
    const input = screen.getByPlaceholderText("2900");
    await userEvent.type(input, "2900");
    expect(await screen.findByText("Estimasi Hasil")).toBeTruthy();
    expect(await screen.findByText(/Perkiraan Penerimaan/)).toBeTruthy();
    expect(await screen.findByText(/Estimasi Gross P&L/)).toBeTruthy();
    expect(await screen.findByText(/Estimasi Net P&L/)).toBeTruthy();
    expect(await screen.findByText(/Estimasi Return/)).toBeTruthy();
  });

  it("recalculates when exit price changes", async () => {
    render(<FullExitModal {...defaultProps} />);
    const input = screen.getByPlaceholderText("2900");
    await userEvent.type(input, "2900");
    const els = await screen.findAllByText(/10.000/);
    expect(els.length).toBeGreaterThanOrEqual(1);
    await userEvent.clear(input);
    await userEvent.type(input, "3000");
    const els2 = await screen.findAllByText(/20.000/);
    expect(els2.length).toBeGreaterThanOrEqual(1);
  });

  it("shows estimate disclaimer", async () => {
    render(<FullExitModal {...defaultProps} />);
    const input = screen.getByPlaceholderText("2900");
    await userEvent.type(input, "2900");
    expect(await screen.findByText(/Estimasi berdasarkan data tersedia/)).toBeTruthy();
    expect(await screen.findByText(/Hasil final dari backend bersifat authoritative/)).toBeTruthy();
  });

  it("does not show preview without exit price", () => {
    render(<FullExitModal {...defaultProps} />);
    expect(screen.queryByText("Estimasi Hasil")).toBeNull();
  });
});

// -------------------------------------------------------------------
// Safety
// -------------------------------------------------------------------
describe("safety", () => {
  it("does not use direct fetch", () => {
    const src = FullExitModal.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
  });
});
