import { readFileSync } from "node:fs";

import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useRouteSession } from "@/features/sessions/use-route-session";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import { submitWaitUpdateAnalysis, uploadWaitUpdateInput } from "@/features/trade-workspace/api";
import type { CurrentStep, SessionDetailAggregate, TradeSession } from "@/features/trade-workspace/types";
import { OBSERVATION_PERIOD_OPTIONS, WaitUpdateActionRoute } from "./wait-update-action-route";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/sessions/session-wait-123/wait-update",
}));

vi.mock("@/features/sessions/use-route-session", () => ({
  useRouteSession: vi.fn(),
}));

vi.mock("@/features/sessions/use-session-current-step", () => ({
  useSessionCurrentStep: vi.fn(),
}));

vi.mock("@/features/trade-workspace/api", () => ({
  uploadWaitUpdateInput: vi.fn(),
  submitWaitUpdateAnalysis: vi.fn(),
}));

const sessionId = "session-wait-123";

function makeSession(): TradeSession {
  return {
    id: sessionId,
    ticker: "BBRI",
    company_name: "Bank Rakyat Indonesia",
    status: "WAITING",
    note: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    closed_at: null,
  };
}

function makeStep(overrides: Partial<CurrentStep> = {}): CurrentStep {
  return {
    code: "WAIT_UPDATE",
    mode: "ACTIONABLE",
    workflow_actions: ["SUBMIT_WAIT_UPDATE", "BUY", "WAIT", "SKIP"],
    active_request: null,
    failed_request: null,
    read_only: false,
    ...overrides,
  };
}

function makeDetail(overrides: Partial<SessionDetailAggregate> = {}): SessionDetailAggregate {
  return {
    session: {
      id: sessionId,
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      status: "WAITING",
      initial_note: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      closed_at: null,
    },
    initial_evidence: [],
    initial_analysis: {},
    decisions: [],
    wait_updates: [],
    position: null,
    position_updates: [],
    closure: null,
    current_step: makeStep(),
    latest_analysis: null,
    recent_activity: [],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useRouteSession).mockReturnValue({
    status: "success",
    session: makeSession(),
  });
  vi.mocked(useSessionCurrentStep).mockReturnValue({
    status: "success",
    currentStep: makeStep(),
    detail: makeDetail(),
    refetch: vi.fn().mockResolvedValue({ status: "success" }),
  });
});

describe("WaitUpdateActionRoute", () => {
  it("renders session header, permanent navigation, and WAIT update form when authorized", () => {
    render(<WaitUpdateActionRoute sessionId={sessionId} />);

    expect(screen.getByRole("heading", { name: /Formulir Pembaruan WAIT/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ringkasan" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Analisis" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Riwayat" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Kembali ke Ringkasan/i })).toBeInTheDocument();
  });

  it("renders controlled ineligible state when SUBMIT_WAIT_UPDATE is not authorized", () => {
    vi.mocked(useSessionCurrentStep).mockReturnValue({
      status: "success",
      currentStep: makeStep({ workflow_actions: ["BUY", "WAIT", "SKIP"] }),
      detail: makeDetail({ current_step: makeStep({ workflow_actions: ["BUY", "WAIT", "SKIP"] }) }),
      refetch: vi.fn().mockResolvedValue({ status: "success" }),
    });

    render(<WaitUpdateActionRoute sessionId={sessionId} />);

    expect(screen.getByRole("heading", { name: "WAIT Update tidak tersedia" })).toBeInTheDocument();
    expect(screen.getByText("Sesi ini tidak dapat menerima WAIT Update pada tahap saat ini.")).toBeInTheDocument();
    expect(screen.queryByLabelText(/Gambar Orderbook Terbaru/i)).toBeNull();
  });

  it("renders exactly one orderbook file input and no chart file inputs", () => {
    render(<WaitUpdateActionRoute sessionId={sessionId} />);

    expect(screen.getByLabelText(/Gambar Orderbook Terbaru/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Chart 3 Bulan/i)).toBeNull();
    expect(screen.queryByLabelText(/Chart 6 Bulan/i)).toBeNull();
  });

  it("validates missing orderbook file, price, and timestamp before calling API", async () => {
    const user = userEvent.setup();
    render(<WaitUpdateActionRoute sessionId={sessionId} />);

    expect(screen.getByLabelText(/Harga Saat Ini/i)).toHaveAttribute("inputmode", "decimal");

    const submitBtn = screen.getByRole("button", { name: "Kirim Pembaruan WAIT" });
    await user.click(submitBtn);

    expect(screen.getByRole("alert")).toHaveTextContent("Pilih satu berkas gambar orderbook.");
    expect(uploadWaitUpdateInput).not.toHaveBeenCalled();

    const file = new File(["orderbook content"], "orderbook-super-long-filename-that-must-wrap-safely.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/Gambar Orderbook Terbaru/i), file);
    expect(screen.getByText(/File terpilih: orderbook-super-long-filename/).className).toContain("break-all");
    await user.click(submitBtn);

    expect(screen.getByRole("alert")).toHaveTextContent("Harga saat ini harus berupa angka positif.");

    await user.type(screen.getByLabelText(/Harga Saat Ini/i), "5000");
    await user.click(submitBtn);

    expect(screen.getByRole("alert")).toHaveTextContent("Waktu pengamatan harus diisi.");
  });

  it("submits valid form to uploadWaitUpdateInput and submitWaitUpdateAnalysis, refetches detail, and navigates", async () => {
    const user = userEvent.setup();
    const refetchMock = vi.fn().mockResolvedValue({ status: "success" });
    vi.mocked(useSessionCurrentStep).mockReturnValue({
      status: "success",
      currentStep: makeStep(),
      detail: makeDetail(),
      refetch: refetchMock,
    });

    vi.mocked(uploadWaitUpdateInput).mockResolvedValue({
      evidence_id: "ev-1",
      session_id: sessionId,
      evidence_type: "ORDERBOOK",
      original_filename: "orderbook.png",
      mime_type: "image/png",
      size_bytes: 1024,
      current_price: "5000",
      observation_period: "MORNING",
      observation_timestamp: "2026-01-01T08:00:00Z",
      uploaded_at: "2026-01-01T08:00:00Z",
      session_status: "WAITING",
    });

    vi.mocked(submitWaitUpdateAnalysis).mockResolvedValue({
      analysis_request_id: "req-1",
      session_id: sessionId,
      analysis_type: "WAIT_UPDATE",
      request_status: "PENDING",
      evidence_id: "ev-1",
      observation_period: "MORNING",
      session_status: "WAITING",
      created_at: "2026-01-01T08:00:00Z",
    });

    render(<WaitUpdateActionRoute sessionId={sessionId} />);

    const file = new File(["orderbook content"], "orderbook.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/Gambar Orderbook Terbaru/i), file);
    await user.type(screen.getByLabelText(/Harga Saat Ini/i), "5000");
    await user.selectOptions(screen.getByLabelText(/Periode Pengamatan/i), "MIDDAY");
    await user.type(screen.getByLabelText(/Waktu Pengamatan/i), "2026-01-01T12:00");

    await user.click(screen.getByRole("button", { name: "Kirim Pembaruan WAIT" }));

    await waitFor(() => {
      expect(uploadWaitUpdateInput).toHaveBeenCalledWith(sessionId, expect.objectContaining({
        orderbook: file,
        current_price: "5000",
        observation_period: "MIDDAY",
      }));
    });

    expect(submitWaitUpdateAnalysis).toHaveBeenCalledWith(sessionId);
    expect(refetchMock).toHaveBeenCalledTimes(1);
    expect(pushMock).toHaveBeenCalledWith(`/sessions/${sessionId}`);
  });

  it("handles server submission failure with sanitized error feedback while preserving user inputs", async () => {
    const user = userEvent.setup();
    vi.mocked(uploadWaitUpdateInput).mockRejectedValueOnce(new Error("500 internal server exception trace"));

    render(<WaitUpdateActionRoute sessionId={sessionId} />);

    const file = new File(["orderbook content"], "orderbook.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/Gambar Orderbook Terbaru/i), file);
    await user.type(screen.getByLabelText(/Harga Saat Ini/i), "5000");
    await user.type(screen.getByLabelText(/Waktu Pengamatan/i), "2026-01-01T08:00");

    await user.click(screen.getByRole("button", { name: "Kirim Pembaruan WAIT" }));

    expect(await screen.findByText("WAIT Update belum dapat dikirim")).toBeInTheDocument();
    expect(screen.getByText("WAIT Update belum dapat dikirim. Periksa kembali data yang dimasukkan lalu coba lagi.")).toBeInTheDocument();
    expect(screen.queryByText("500 internal server")).toBeNull();

    expect(screen.getByLabelText(/Harga Saat Ini/i)).toHaveValue(5000);
  });

  it("resets form input fields when sessionId changes to B", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<WaitUpdateActionRoute sessionId="session-a" />);

    await user.type(screen.getByLabelText(/Harga Saat Ini/i), "5000");
    expect(screen.getByLabelText(/Harga Saat Ini/i)).toHaveValue(5000);

    vi.mocked(useRouteSession).mockReturnValue({
      status: "success",
      session: { ...makeSession(), id: "session-b" },
    });

    rerender(<WaitUpdateActionRoute sessionId="session-b" />);

    expect(screen.getByLabelText(/Harga Saat Ini/i)).toHaveValue(null);
  });

  it("contains no polling, localStorage, sessionStorage, or Gemini calls", () => {
    const source = readFileSync("src/features/sessions/wait-update-action-route.tsx", "utf8");
    expect(source).not.toMatch(/setInterval|setTimeout|localStorage|sessionStorage|SessionWorkspace|JobStatus/);
    expect(OBSERVATION_PERIOD_OPTIONS).toHaveLength(3);
  });
});
