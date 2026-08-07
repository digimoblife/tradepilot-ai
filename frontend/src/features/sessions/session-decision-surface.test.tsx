import { readFileSync } from "node:fs";

import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buyDecision, skipDecision, waitDecision } from "@/features/trade-workspace/api";
import type { CurrentStep } from "@/features/trade-workspace/types";
import { SessionDecisionSurface, SKIP_REASON_OPTIONS } from "./session-decision-surface";

vi.mock("@/features/trade-workspace/api", () => ({
  buyDecision: vi.fn(),
  waitDecision: vi.fn(),
  skipDecision: vi.fn(),
}));

const sessionId = "session-test-123";

function makeStep(overrides: Partial<CurrentStep> = {}): CurrentStep {
  return {
    code: "DECISION",
    mode: "ACTIONABLE",
    workflow_actions: ["BUY", "WAIT", "SKIP"],
    active_request: null,
    failed_request: null,
    read_only: false,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("SessionDecisionSurface", () => {
  it("renders decision options when authorized by workflow actions", () => {
    const refetch = vi.fn().mockResolvedValue({});
    render(<SessionDecisionSurface sessionId={sessionId} step={makeStep()} refetch={refetch} />);

    expect(screen.getByRole("heading", { name: "Pilih Keputusan Sesi" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Beli (BUY)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tunggu (WAIT)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lewati (SKIP)" })).toBeInTheDocument();
  });

  it("does not render when workflow actions do not include decisions or mode is not actionable", () => {
    const refetch = vi.fn().mockResolvedValue({});
    const { container, rerender } = render(
      <SessionDecisionSurface
        sessionId={sessionId}
        step={makeStep({ mode: "PROCESSING", workflow_actions: [] })}
        refetch={refetch}
      />,
    );
    expect(container).toBeEmptyDOMElement();

    rerender(
      <SessionDecisionSurface
        sessionId={sessionId}
        step={makeStep({ read_only: true, workflow_actions: [] })}
        refetch={refetch}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders only authorized decision options based on workflow_actions", () => {
    const refetch = vi.fn().mockResolvedValue({});
    render(
      <SessionDecisionSurface
        sessionId={sessionId}
        step={makeStep({ code: "WAIT_UPDATE", workflow_actions: ["WAIT", "SKIP", "SUBMIT_WAIT_UPDATE"] })}
        refetch={refetch}
      />,
    );

    expect(screen.queryByRole("button", { name: "Beli (BUY)" })).toBeNull();
    expect(screen.getByRole("button", { name: "Tunggu (WAIT)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lewati (SKIP)" })).toBeInTheDocument();
  });

  it("handles BUY decision form display, validation, submit, and refetch", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn().mockResolvedValue({});
    vi.mocked(buyDecision).mockResolvedValue({
      decision_id: "dec-1",
      session_id: sessionId,
      decision_type: "BUY",
      decision_at: "2026-01-01T00:00:00Z",
      position_id: "pos-1",
      position_status: "OPEN",
      entry_price: "5000",
      entry_timestamp: "2026-01-01T08:00:00Z",
      quantity: "100",
      stop_loss: "4800",
      target_price: "5500",
      note: "Catatan test",
      session_status: "OPEN_POSITION",
    });

    render(<SessionDecisionSurface sessionId={sessionId} step={makeStep()} refetch={refetch} />);

    await user.click(screen.getByRole("button", { name: "Beli (BUY)" }));
    expect(screen.getByRole("heading", { name: "Formulir Keputusan BUY" })).toBeInTheDocument();

    expect(screen.getByLabelText(/Harga Masuk/)).toHaveAttribute("inputmode", "decimal");
    expect(screen.getByLabelText(/Jumlah Saham/)).toHaveAttribute("inputmode", "numeric");
    expect(screen.getByLabelText(/Stop Loss/)).toHaveAttribute("inputmode", "decimal");
    expect(screen.getByLabelText(/Target Profit/)).toHaveAttribute("inputmode", "decimal");

    const submitBtn = screen.getByRole("button", { name: "Kirim Keputusan BUY" });
    await user.click(submitBtn);

    expect(screen.getByRole("alert")).toHaveTextContent("Semua nilai harga dan jumlah harus berupa angka positif.");
    expect(buyDecision).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(/Harga Masuk/), "5000");
    await user.type(screen.getByLabelText(/Waktu Masuk/), "2026-01-01T08:00");
    await user.type(screen.getByLabelText(/Jumlah Saham/), "100");
    await user.type(screen.getByLabelText(/Stop Loss/), "4800");
    await user.type(screen.getByLabelText(/Target Profit/), "5500");
    await user.type(screen.getByLabelText(/Catatan/), "Catatan test");

    await user.click(submitBtn);

    await waitFor(() => {
      expect(buyDecision).toHaveBeenCalledWith(sessionId, expect.objectContaining({
        entry_price: "5000",
        quantity: "100",
        stop_loss: "4800",
        target_price: "5500",
        note: "Catatan test",
      }));
    });
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("handles WAIT decision confirmation submit and refetch without evidence forms", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn().mockResolvedValue({});
    vi.mocked(waitDecision).mockResolvedValue({
      decision_id: "dec-2",
      session_id: sessionId,
      decision_type: "WAIT",
      decision_at: "2026-01-01T00:00:00Z",
      session_status: "WAITING",
    });

    render(<SessionDecisionSurface sessionId={sessionId} step={makeStep()} refetch={refetch} />);

    await user.click(screen.getByRole("button", { name: "Tunggu (WAIT)" }));
    expect(screen.getByRole("heading", { name: "Konfirmasi Keputusan WAIT" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/Orderbook/i)).toBeNull();

    await user.click(screen.getByRole("button", { name: "Kirim Keputusan WAIT" }));

    await waitFor(() => {
      expect(waitDecision).toHaveBeenCalledWith(sessionId);
    });
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("handles SKIP decision form with explicit confirmation step before API submit", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn().mockResolvedValue({});
    vi.mocked(skipDecision).mockResolvedValue({
      decision_id: "dec-3",
      session_id: sessionId,
      decision_type: "SKIP",
      reason: "SETUP_NOT_ATTRACTIVE",
      note: "Kurang menarik",
      decision_at: "2026-01-01T00:00:00Z",
      session_status: "CLOSED_SKIPPED",
      closed_at: "2026-01-01T00:00:00Z",
    });

    render(<SessionDecisionSurface sessionId={sessionId} step={makeStep()} refetch={refetch} />);

    await user.click(screen.getByRole("button", { name: "Lewati (SKIP)" }));
    expect(screen.getByRole("heading", { name: "Formulir Keputusan SKIP" })).toBeInTheDocument();

    const select = screen.getByLabelText(/Alasan Lewati Sesi/);
    await user.selectOptions(select, "SETUP_NOT_ATTRACTIVE");
    await user.type(screen.getByLabelText(/Catatan/), "Kurang menarik");

    // First click shows confirmation alert and changes button label
    await user.click(screen.getByRole("button", { name: "Kirim Keputusan SKIP" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Konfirmasi Lewati Sesi");
    expect(skipDecision).not.toHaveBeenCalled();

    // Second click confirms and sends request
    await user.click(screen.getByRole("button", { name: "Konfirmasi Lewati Sesi" }));

    await waitFor(() => {
      expect(skipDecision).toHaveBeenCalledWith(sessionId, {
        reason: "SETUP_NOT_ATTRACTIVE",
        note: "Kurang menarik",
      });
    });
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("preserves form input values and displays sanitized error feedback on server failure", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn().mockResolvedValue({});
    vi.mocked(buyDecision).mockRejectedValueOnce(new Error("Server error 500 JSON internal exception"));

    render(<SessionDecisionSurface sessionId={sessionId} step={makeStep()} refetch={refetch} />);

    await user.click(screen.getByRole("button", { name: "Beli (BUY)" }));
    await user.type(screen.getByLabelText(/Harga Masuk/), "5000");
    await user.type(screen.getByLabelText(/Waktu Masuk/), "2026-01-01T08:00");
    await user.type(screen.getByLabelText(/Jumlah Saham/), "100");
    await user.type(screen.getByLabelText(/Stop Loss/), "4800");
    await user.type(screen.getByLabelText(/Target Profit/), "5500");

    await user.click(screen.getByRole("button", { name: "Kirim Keputusan BUY" }));

    expect(await screen.findByText("Keputusan belum dapat disimpan")).toBeInTheDocument();
    expect(screen.getByText("Keputusan belum dapat disimpan. Periksa kembali data yang dimasukkan lalu coba lagi.")).toBeInTheDocument();
    expect(screen.queryByText("Server error 500")).toBeNull();

    expect(screen.getByLabelText(/Harga Masuk/)).toHaveValue(5000);
    expect(refetch).not.toHaveBeenCalled();
  });

  it("resets form choice and values when sessionId changes to B", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn().mockResolvedValue({});

    const { rerender } = render(<SessionDecisionSurface sessionId="session-a" step={makeStep()} refetch={refetch} />);

    await user.click(screen.getByRole("button", { name: "Beli (BUY)" }));
    await user.type(screen.getByLabelText(/Harga Masuk/), "5000");
    expect(screen.getByRole("heading", { name: "Formulir Keputusan BUY" })).toBeInTheDocument();

    rerender(<SessionDecisionSurface sessionId="session-b" step={makeStep()} refetch={refetch} />);

    expect(screen.queryByRole("heading", { name: "Formulir Keputusan BUY" })).toBeNull();
    expect(screen.getByRole("button", { name: "Beli (BUY)" })).not.toHaveAttribute("aria-pressed", "true");
  });

  it("contains no polling, localStorage, sessionStorage, legacy workspace, or Gemini calls", () => {
    const source = readFileSync("src/features/sessions/session-decision-surface.tsx", "utf8");
    expect(source).not.toMatch(/setInterval|setTimeout|localStorage|sessionStorage|SessionWorkspace|JobStatus|retryInitialAnalysis/);
    expect(SKIP_REASON_OPTIONS).toHaveLength(7);
  });
});
