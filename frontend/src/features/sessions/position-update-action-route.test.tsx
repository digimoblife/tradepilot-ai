import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useRouteSession } from "@/features/sessions/use-route-session";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import { submitPositionUpdateAnalysis, uploadPositionUpdateInput } from "@/features/trade-workspace/api";
import type { CurrentStep, SessionDetailAggregate, TradeSession } from "@/features/trade-workspace/types";

import { PositionUpdateActionRoute } from "./position-update-action-route";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  usePathname: () => "/sessions/session-pos-123/position-update",
}));

vi.mock("@/features/sessions/use-route-session", () => ({
  useRouteSession: vi.fn(),
}));

vi.mock("@/features/sessions/use-session-current-step", () => ({
  useSessionCurrentStep: vi.fn(),
}));

vi.mock("@/features/trade-workspace/api", () => ({
  uploadPositionUpdateInput: vi.fn(),
  submitPositionUpdateAnalysis: vi.fn(),
}));

const sessionId = "session-pos-123";

function makeSession(): TradeSession {
  return {
    id: sessionId,
    ticker: "BBRI",
    company_name: "Bank Rakyat Indonesia",
    status: "OPEN_POSITION",
    note: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    closed_at: null,
  };
}

function makeStep(overrides: Partial<CurrentStep> = {}): CurrentStep {
  return {
    code: "POSITION_MONITORING",
    mode: "ACTIONABLE",
    workflow_actions: ["SUBMIT_POSITION_UPDATE", "CLOSE"],
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
      status: "OPEN_POSITION",
      initial_note: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      closed_at: null,
    },
    initial_evidence: [],
    initial_analysis: {},
    decisions: [],
    wait_updates: [],
    position: {
      status: "OPEN",
      entry_price: 5000,
      quantity: 100,
      stop_loss: 4800,
      target_price: 5500,
      entry_timestamp: "2026-01-01T08:00:00Z",
      note: null,
      closed_at: null,
    },
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
    refetch: vi.fn().mockResolvedValue({}),
  });
});

describe("PositionUpdateActionRoute", () => {
  it("renders header, permanent navigation, back link, and form when session is OPEN_POSITION & eligible", () => {
    render(<PositionUpdateActionRoute sessionId={sessionId} />);

    expect(screen.getByRole("heading", { name: "BBRI" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Formulir Pembaruan Posisi" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Kembali ke Ringkasan" })).toHaveAttribute(
      "href",
      `/sessions/${sessionId}`,
    );
  });

  it("renders controlled ineligible state when session is not OPEN_POSITION or lacks SUBMIT_POSITION_UPDATE action", () => {
    vi.mocked(useSessionCurrentStep).mockReturnValue({
      status: "success",
      currentStep: makeStep({ workflow_actions: ["CLOSE"] }),
      detail: makeDetail(),
      refetch: vi.fn().mockResolvedValue({}),
    });

    render(<PositionUpdateActionRoute sessionId={sessionId} />);

    expect(screen.getByRole("heading", { name: "Position Update tidak tersedia" })).toBeInTheDocument();
    expect(screen.getByText("Sesi ini tidak dapat menerima Position Update pada tahap saat ini.")).toBeInTheDocument();
    expect(screen.queryByLabelText(/Gambar Orderbook Terbaru/i)).toBeNull();
  });

  it("renders exactly one orderbook file input and no chart file inputs", () => {
    render(<PositionUpdateActionRoute sessionId={sessionId} />);

    expect(screen.getByLabelText(/Gambar Orderbook Terbaru/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Broker Flow — 1D (Optional)")).not.toBeRequired();
    expect(screen.queryByLabelText(/Chart 3 Bulan/i)).toBeNull();
    expect(screen.queryByLabelText(/Chart 6 Bulan/i)).toBeNull();
  });

  it("includes optional Broker Flow in the exact Position upload request", async () => {
    const user = userEvent.setup();
    const orderbook = new File(["orderbook"], "orderbook.png", { type: "image/png" });
    const brokerFlow = new File(["broker"], "broker-flow.png", { type: "image/png" });
    vi.mocked(uploadPositionUpdateInput).mockResolvedValue({} as never);
    vi.mocked(submitPositionUpdateAnalysis).mockResolvedValue({} as never);
    render(<PositionUpdateActionRoute sessionId={sessionId} />);

    await user.upload(screen.getByLabelText(/Gambar Orderbook Terbaru/i), orderbook);
    await user.upload(screen.getByLabelText("Broker Flow — 1D (Optional)"), brokerFlow);
    await user.type(screen.getByLabelText(/Harga Saat Ini/i), "5000");
    await user.type(screen.getByLabelText(/Waktu Pengamatan/i), "2026-08-08T10:00");
    await user.click(screen.getByRole("button", { name: "Kirim Pembaruan Posisi" }));

    await waitFor(() => expect(uploadPositionUpdateInput).toHaveBeenCalledWith(sessionId, expect.objectContaining({
      orderbook,
      broker_flow_1d: brokerFlow,
    })));
  });

  it("validates missing orderbook file, price, and timestamp before calling API", async () => {
    const user = userEvent.setup();
    render(<PositionUpdateActionRoute sessionId={sessionId} />);

    expect(screen.getByLabelText(/Harga Saat Ini/i)).toHaveAttribute("inputmode", "decimal");

    const submitBtn = screen.getByRole("button", { name: "Kirim Pembaruan Posisi" });
    await user.click(submitBtn);

    expect(screen.getByRole("alert")).toHaveTextContent("Pilih satu berkas gambar orderbook.");
    expect(uploadPositionUpdateInput).not.toHaveBeenCalled();

    const file = new File(["dummy content"], "orderbook-super-long-filename-that-must-wrap-safely.png", { type: "image/png" });
    const fileInput = screen.getByLabelText(/Gambar Orderbook Terbaru/i);
    await user.upload(fileInput, file);
    expect(screen.getByText(/File terpilih: orderbook-super-long-filename/).className).toContain("break-all");

    await user.click(submitBtn);
    expect(screen.getByRole("alert")).toHaveTextContent("Harga saat ini harus berupa angka positif.");
  });

  it("submits two-step API flow, refetches canonical detail, and navigates back to Summary on success", async () => {
    const user = userEvent.setup();
    const refetchMock = vi.fn().mockResolvedValue({});

    vi.mocked(useSessionCurrentStep).mockReturnValue({
      status: "success",
      currentStep: makeStep(),
      detail: makeDetail(),
      refetch: refetchMock,
    });

    vi.mocked(uploadPositionUpdateInput).mockResolvedValue({
      evidence_id: "ev-pos-1",
      session_id: sessionId,
      position_id: "pos-1",
      evidence_type: "ORDERBOOK",
      original_filename: "orderbook.png",
      mime_type: "image/png",
      size_bytes: 1024,
      current_price: "5200",
      observation_period: "MORNING",
      observation_timestamp: "2026-01-01T08:00:00Z",
      uploaded_at: "2026-01-01T08:00:00Z",
      session_status: "OPEN_POSITION",
      position_status: "OPEN",
    });

    vi.mocked(submitPositionUpdateAnalysis).mockResolvedValue({
      analysis_request_id: "req-pos-1",
      session_id: sessionId,
      position_id: "pos-1",
      evidence_id: "ev-pos-1",
      analysis_type: "POSITION_UPDATE",
      request_status: "PENDING",
      observation_period: "MORNING",
      session_status: "OPEN_POSITION",
      position_status: "OPEN",
      created_at: "2026-01-01T08:00:00Z",
    });

    render(<PositionUpdateActionRoute sessionId={sessionId} />);

    const file = new File(["dummy content"], "orderbook.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/Gambar Orderbook Terbaru/i), file);
    await user.type(screen.getByLabelText(/Harga Saat Ini/i), "5200");
    await user.type(screen.getByLabelText(/Waktu Pengamatan/i), "2026-01-01T08:00");

    const submitBtn = screen.getByRole("button", { name: "Kirim Pembaruan Posisi" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(uploadPositionUpdateInput).toHaveBeenCalledWith(sessionId, {
        orderbook: expect.any(File),
        current_price: "5200",
        observation_period: "MORNING",
        observation_timestamp: expect.any(String),
      });
      expect(submitPositionUpdateAnalysis).toHaveBeenCalledWith(sessionId);
    });

    expect(refetchMock).toHaveBeenCalled();
    expect(pushMock).toHaveBeenCalledWith(`/sessions/${sessionId}`);
  });

  it("displays sanitized error feedback on API failure and preserves form values", async () => {
    const user = userEvent.setup();
    vi.mocked(uploadPositionUpdateInput).mockRejectedValue(new Error("500 internal server error"));

    render(<PositionUpdateActionRoute sessionId={sessionId} />);

    const file = new File(["dummy content"], "orderbook.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/Gambar Orderbook Terbaru/i), file);
    await user.type(screen.getByLabelText(/Harga Saat Ini/i), "5200");
    await user.type(screen.getByLabelText(/Waktu Pengamatan/i), "2026-01-01T08:00");

    await user.click(screen.getByRole("button", { name: "Kirim Pembaruan Posisi" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Position Update belum dapat dikirim. Periksa kembali data yang dimasukkan lalu coba lagi.",
    );

    expect(screen.getByLabelText(/Harga Saat Ini/i)).toHaveValue(5200);
  });

  it("resets form state when sessionId prop changes", () => {
    const { rerender } = render(<PositionUpdateActionRoute sessionId="session-1" />);

    rerender(<PositionUpdateActionRoute sessionId="session-2" />);

    expect(screen.getByLabelText(/Harga Saat Ini/i)).toHaveValue(null);
  });
});
