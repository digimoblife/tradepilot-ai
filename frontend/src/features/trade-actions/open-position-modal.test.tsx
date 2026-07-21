import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { openPosition } from "@/lib/api/trade-actions";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { watchingUpdateFixture } from "@/test/fixtures";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

vi.mock("@/lib/api/trade-actions", () => ({
  openPosition: vi.fn(),
}));

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { OpenPositionModal } from "./open-position-modal";

function makeWUSummary(overrides: Partial<AnalysisSummary> = {}): AnalysisSummary {
  const base: AnalysisSummary = {
    id: "wu-proposal",
    session_id: "sess-a",
    analysis_type: "WATCHING_UPDATE",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-20T10:00:00+07:00",
    created_at: "2026-07-20T09:55:00+07:00",
    prompt_version: "1.0.0",
    schema_name: "watching_update",
    schema_version: "1.0.0",
    supersedes_analysis_id: null,
  };
  return { ...base, ...overrides };
}

function makeWUDetail(overrides: Partial<AnalysisDetail> = {}): AnalysisDetail {
  return {
    id: "wu-proposal",
    session_id: "sess-a",
    analysis_type: "WATCHING_UPDATE",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-20T10:00:00+07:00",
    created_at: "2026-07-20T09:55:00+07:00",
    prompt_name: "watching_update",
    prompt_version: "1.0.0",
    schema_name: "watching_update",
    schema_version: "1.0.0",
    payload: JSON.parse(JSON.stringify(watchingUpdateFixture)) as Record<string, unknown>,
    supersedes_analysis_id: null,
    ...overrides,
  };
}

function mockProposalAvailable() {
  vi.mocked(listAnalyses).mockResolvedValue({
    analyses: [makeWUSummary()],
    total: 1,
  });
  vi.mocked(getAnalysis).mockResolvedValue(makeWUDetail());
}

function resetMocks() {
  vi.mocked(openPosition).mockReset();
  vi.mocked(listAnalyses).mockReset();
  vi.mocked(getAnalysis).mockReset();
  vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
}

beforeEach(() => {
  vi.clearAllMocks();
  resetMocks();
});

// -------------------------------------------------------------------
// Modal rendering
// -------------------------------------------------------------------
describe("modal rendering", () => {
  it("does not render when isOpen is false", () => {
    const { container } = render(
      <OpenPositionModal sessionId="sess-a" isOpen={false} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders title and form when open", () => {
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    expect(screen.getByText("Buka Posisi")).toBeTruthy();
    expect(screen.getByText("Harga Entry")).toBeTruthy();
    expect(screen.getByText("Quantity")).toBeTruthy();
    expect(screen.getByText("Waktu Eksekusi")).toBeTruthy();
    expect(screen.getByText("Stop Loss")).toBeTruthy();
    expect(screen.getByText("Target")).toBeTruthy();
    expect(screen.getByText("Catatan")).toBeTruthy();
  });

  it("shows Batal and Konfirmasi buttons", () => {
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    expect(screen.getByText("Batal")).toBeTruthy();
    expect(screen.getByText("Konfirmasi Buka Posisi")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// AI proposal prefill
// -------------------------------------------------------------------
describe("AI proposal prefill", () => {
  it("loads proposal from latest Watching Update", async () => {
    mockProposalAvailable();
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "WATCHING_UPDATE",
      });
    });
  });

  it("prefills entry from reference_entry_price when available", async () => {
    mockProposalAvailable();
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    const entryInput = await screen.findByDisplayValue("2480");
    expect(entryInput).toBeTruthy();
  });

  it("prefills stop loss from proposed_stop_loss", async () => {
    mockProposalAvailable();
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    const slInput = await screen.findByDisplayValue("2450");
    expect(slInput).toBeTruthy();
  });

  it("prefills target from proposed_target", async () => {
    mockProposalAvailable();
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    const tgInput = await screen.findByDisplayValue("3000");
    expect(tgInput).toBeTruthy();
  });

  it("shows proposal hint when loaded", async () => {
    mockProposalAvailable();
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    expect(await screen.findByText(/Nilai di bawah diisi berdasarkan usulan AI/)).toBeTruthy();
  });

  it("shows AI proposal label next to entry", async () => {
    mockProposalAvailable();
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    expect(await screen.findByText(/Usulan AI: 2480/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// User can edit values
// -------------------------------------------------------------------
describe("user can edit values", () => {
  it("allows changing entry price", async () => {
    mockProposalAvailable();
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    const input = await screen.findByDisplayValue("2480");
    await userEvent.clear(input);
    await userEvent.type(input, "2600");
    expect(await screen.findByDisplayValue("2600")).toBeTruthy();
  });

  it("allows changing quantity", async () => {
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    const input = screen.getByPlaceholderText("100");
    await userEvent.type(input, "200");
    expect(await screen.findByDisplayValue("200")).toBeTruthy();
  });

  it("allows adding a note", async () => {
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    const textarea = screen.getByPlaceholderText("Catatan opsional");
    await userEvent.type(textarea, "Entry di support");
    expect(await screen.findByText("Entry di support")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Validation
// -------------------------------------------------------------------
describe("validation", () => {
  it("shows errors when submitting empty form", async () => {
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.queryByText("Memuat usulan AI…")).toBeNull();
    });
    const btn = screen.getByText("Konfirmasi Buka Posisi");
    await userEvent.click(btn);
    expect(await screen.findByText(/Harga entry harus lebih besar dari 0/)).toBeTruthy();
    expect(await screen.findByText(/Quantity harus lebih besar dari 0/)).toBeTruthy();
  });

  it("shows error for invalid stop loss", async () => {
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.queryByText("Memuat usulan AI…")).toBeNull();
    });
    const entryInput = screen.getByPlaceholderText("2800");
    await userEvent.type(entryInput, "2600");
    const qtyInput = screen.getByPlaceholderText("100");
    await userEvent.type(qtyInput, "100");
    const slInput = screen.getByPlaceholderText("2700");
    await userEvent.type(slInput, "-1");
    const btn = screen.getByText("Konfirmasi Buka Posisi");
    await userEvent.click(btn);
    expect(await screen.findByText(/Stop loss harus lebih besar dari 0/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Submission
// -------------------------------------------------------------------
describe("submission", () => {
  it("calls openPosition with user values", async () => {
    vi.mocked(openPosition).mockResolvedValue({
      action: { id: "act-1", session_id: "sess-a", action_type: "POSITION_OPENED", confirmed_at: "2026-07-20T10:00:00Z", price: "2600", quantity: "200" },
      session_status: "OPEN_POSITION",
      trade_state: { position_status: "OPEN", entry_price: "2600", original_quantity: "200", remaining_quantity: "200", active_stop_loss: null, active_target: null, average_exit_price: null, realized_pnl: null, state_version: 2 },
    });
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.queryByText("Memuat usulan AI…")).toBeNull();
    });
    await userEvent.type(screen.getByPlaceholderText("2800"), "2600");
    await userEvent.type(screen.getByPlaceholderText("100"), "200");
    await userEvent.click(screen.getByText("Konfirmasi Buka Posisi"));
    await waitFor(() => {
      expect(openPosition).toHaveBeenCalled();
    });
    const call = vi.mocked(openPosition).mock.calls[0][0];
    expect(call.entry_price).toBe("2600");
    expect(call.quantity).toBe("200");
    expect(call.session_id).toBe("sess-a");
  });

  it("prevents duplicate submission while pending", async () => {
    vi.mocked(openPosition).mockImplementation(() => new Promise(() => {}));
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.type(screen.getByPlaceholderText("2800"), "2600");
    await userEvent.type(screen.getByPlaceholderText("100"), "200");
    await userEvent.click(screen.getByText("Konfirmasi Buka Posisi"));
    await waitFor(() => {
      expect(screen.getByText("Memproses…")).toBeTruthy();
    });
    expect(screen.getByText("Memproses…")).toBeTruthy();
  });

  it("calls onSuccess and onClose after successful submission", async () => {
    vi.mocked(openPosition).mockResolvedValue({
      action: { id: "act-1", session_id: "sess-a", action_type: "POSITION_OPENED", confirmed_at: "2026-07-20T10:00:00Z", price: "2600", quantity: "200" },
      session_status: "OPEN_POSITION",
      trade_state: { position_status: "OPEN", entry_price: "2600", original_quantity: "200", remaining_quantity: "200", active_stop_loss: null, active_target: null, average_exit_price: null, realized_pnl: null, state_version: 2 },
    });
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={onClose} onSuccess={onSuccess} />,
    );
    await userEvent.type(screen.getByPlaceholderText("2800"), "2600");
    await userEvent.type(screen.getByPlaceholderText("100"), "200");
    await userEvent.click(screen.getByText("Konfirmasi Buka Posisi"));
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
    expect(onClose).toHaveBeenCalled();
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows API error message", async () => {
    vi.mocked(openPosition).mockRejectedValue(new ApiError(400, "VALIDATION_ERROR", "Entry price terlalu tinggi."));
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.type(screen.getByPlaceholderText("2800"), "2600");
    await userEvent.type(screen.getByPlaceholderText("100"), "200");
    await userEvent.click(screen.getByText("Konfirmasi Buka Posisi"));
    expect(await screen.findByText("Entry price terlalu tinggi.")).toBeTruthy();
  });

  it("shows auth error safely", async () => {
    vi.mocked(openPosition).mockRejectedValue(
      new AuthenticationError(401, "AUTH_REQUIRED", "Auth"),
    );
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.type(screen.getByPlaceholderText("2800"), "2600");
    await userEvent.type(screen.getByPlaceholderText("100"), "200");
    await userEvent.click(screen.getByText("Konfirmasi Buka Posisi"));
    expect(await screen.findByText("Silakan masuk terlebih dahulu.")).toBeTruthy();
  });

  it("shows unknown error safely", async () => {
    vi.mocked(openPosition).mockRejectedValue(new Error("fail"));
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    await userEvent.type(screen.getByPlaceholderText("2800"), "2600");
    await userEvent.type(screen.getByPlaceholderText("100"), "200");
    await userEvent.click(screen.getByText("Konfirmasi Buka Posisi"));
    expect(await screen.findByText("Gagal membuka posisi. Silakan coba lagi.")).toBeTruthy();
  });

  it("shows loading state while proposal loads", () => {
    vi.mocked(listAnalyses).mockImplementation(() => new Promise(() => {}));
    render(
      <OpenPositionModal sessionId="sess-a" isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />,
    );
    expect(screen.getByText("Memuat usulan AI…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Safety and boundaries
// -------------------------------------------------------------------
describe("safety and boundaries", () => {
  it("does not use direct fetch", () => {
    const src = OpenPositionModal.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });
});
