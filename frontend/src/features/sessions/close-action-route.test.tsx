import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useRouteSession } from "@/features/sessions/use-route-session";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import { closePosition } from "@/features/trade-workspace/api";
import type { CurrentStep, SessionDetailAggregate, TradeSession } from "@/features/trade-workspace/types";

import { CloseActionRoute } from "./close-action-route";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  usePathname: () => "/sessions/session-pos-123/close",
}));

vi.mock("@/features/sessions/use-route-session", () => ({
  useRouteSession: vi.fn(),
}));

vi.mock("@/features/sessions/use-session-current-step", () => ({
  useSessionCurrentStep: vi.fn(),
}));

vi.mock("@/features/trade-workspace/api", () => ({
  closePosition: vi.fn(),
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

describe("CloseActionRoute", () => {
  it("renders header, permanent navigation, back link, non-delete notice, and form when session is OPEN_POSITION & eligible", () => {
    render(<CloseActionRoute sessionId={sessionId} />);

    expect(screen.getByRole("heading", { name: "BBRI" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tutup Posisi" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Kembali ke Ringkasan" })).toHaveAttribute(
      "href",
      `/sessions/${sessionId}`,
    );
    expect(screen.getByText("Menutup posisi tidak menghapus sesi atau riwayatnya.")).toBeInTheDocument();
  });

  it("renders controlled ineligible state when session is not OPEN_POSITION or lacks CLOSE action", () => {
    vi.mocked(useSessionCurrentStep).mockReturnValue({
      status: "success",
      currentStep: makeStep({ workflow_actions: ["SUBMIT_POSITION_UPDATE"] }),
      detail: makeDetail(),
      refetch: vi.fn().mockResolvedValue({}),
    });

    render(<CloseActionRoute sessionId={sessionId} />);

    expect(screen.getByRole("heading", { name: "Penutupan posisi tidak tersedia" })).toBeInTheDocument();
    expect(screen.getByText("Sesi ini tidak dapat ditutup pada tahap saat ini.")).toBeInTheDocument();
    expect(screen.queryByLabelText(/Harga Penutupan/i)).toBeNull();
  });

  it("validates missing close price, timestamp, and reason before showing confirmation", async () => {
    const user = userEvent.setup();
    render(<CloseActionRoute sessionId={sessionId} />);

    expect(screen.getByLabelText(/Harga Penutupan/i)).toHaveAttribute("inputmode", "decimal");

    const continueBtn = screen.getByRole("button", { name: "Lanjutkan" });
    await user.click(continueBtn);

    expect(screen.getByRole("alert")).toHaveTextContent("Harga penutupan harus berupa angka positif.");
    expect(closePosition).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(/Harga Penutupan/i), "5400");
    await user.click(continueBtn);
    expect(screen.getByRole("alert")).toHaveTextContent("Waktu penutupan harus diisi.");

    await user.type(screen.getByLabelText(/Waktu Penutupan/i), "2026-01-01T15:00");
    await user.click(continueBtn);
    expect(screen.getByRole("alert")).toHaveTextContent("Alasan penutupan harus diisi.");
  });

  it("opens two-step neutral confirmation panel without firing API call, and allows cancelling back to form", async () => {
    const user = userEvent.setup();
    render(<CloseActionRoute sessionId={sessionId} />);

    await user.type(screen.getByLabelText(/Harga Penutupan/i), "5400");
    await user.type(screen.getByLabelText(/Waktu Penutupan/i), "2026-01-01T15:00");
    await user.type(screen.getByLabelText(/Alasan Penutupan/i), "Target harga tercapai");
    await user.type(screen.getByLabelText(/Catatan/i), "Profit terrealisasi");

    await user.click(screen.getByRole("button", { name: "Lanjutkan" }));

    expect(screen.getByRole("heading", { name: "Konfirmasi Penutupan Posisi" })).toBeInTheDocument();
    expect(screen.getByText("Posisi akan ditutup dan sesi menjadi selesai. Seluruh data dan riwayat tetap tersimpan, dan sesi tidak akan diarsipkan secara otomatis.")).toBeInTheDocument();
    expect(closePosition).not.toHaveBeenCalled();

    const cancelBtn = screen.getByRole("button", { name: "Batal" });
    await user.click(cancelBtn);

    expect(screen.getByLabelText(/Harga Penutupan/i)).toHaveValue(5400);
    expect(screen.getByLabelText(/Alasan Penutupan/i)).toHaveValue("Target harga tercapai");
    expect(closePosition).not.toHaveBeenCalled();
  });

  it("submits API request on confirmation, refetches canonical detail, and navigates to Summary page", async () => {
    const user = userEvent.setup();
    const refetchMock = vi.fn().mockResolvedValue({});

    vi.mocked(useSessionCurrentStep).mockReturnValue({
      status: "success",
      currentStep: makeStep(),
      detail: makeDetail(),
      refetch: refetchMock,
    });

    vi.mocked(closePosition).mockResolvedValue({
      closure_id: "cls-123",
      session_id: sessionId,
      position_id: "pos-1",
      close_price: "5400",
      close_timestamp: "2026-01-01T15:00:00Z",
      close_reason: "Target harga tercapai",
      note: "Profit terrealisasi",
      realized_profit_loss: "40000",
      position_status: "CLOSED",
      session_status: "CLOSED",
      closed_at: "2026-01-01T15:00:00Z",
      created_at: "2026-01-01T15:00:00Z",
    });

    render(<CloseActionRoute sessionId={sessionId} />);

    await user.type(screen.getByLabelText(/Harga Penutupan/i), "5400");
    await user.type(screen.getByLabelText(/Waktu Penutupan/i), "2026-01-01T15:00");
    await user.type(screen.getByLabelText(/Alasan Penutupan/i), "Target harga tercapai");
    await user.type(screen.getByLabelText(/Catatan/i), "Profit terrealisasi");

    await user.click(screen.getByRole("button", { name: "Lanjutkan" }));
    await user.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));

    await waitFor(() => {
      expect(closePosition).toHaveBeenCalledWith(sessionId, {
        close_price: "5400",
        close_timestamp: expect.any(String),
        close_reason: "Target harga tercapai",
        note: "Profit terrealisasi",
      });
    });

    expect(refetchMock).toHaveBeenCalled();
    expect(pushMock).toHaveBeenCalledWith(`/sessions/${sessionId}`);
  });

  it("displays sanitized error feedback on API failure and preserves form values", async () => {
    const user = userEvent.setup();
    vi.mocked(closePosition).mockRejectedValue(new Error("500 internal server error"));

    render(<CloseActionRoute sessionId={sessionId} />);

    await user.type(screen.getByLabelText(/Harga Penutupan/i), "5400");
    await user.type(screen.getByLabelText(/Waktu Penutupan/i), "2026-01-01T15:00");
    await user.type(screen.getByLabelText(/Alasan Penutupan/i), "Target harga tercapai");

    await user.click(screen.getByRole("button", { name: "Lanjutkan" }));
    await user.click(screen.getByRole("button", { name: "Konfirmasi Tutup Posisi" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Posisi belum dapat ditutup. Periksa kembali data yang dimasukkan lalu coba lagi.",
    );

    expect(screen.getByLabelText(/Harga Penutupan/i)).toHaveValue(5400);
  });

  it("resets form and confirmation state when sessionId prop changes", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<CloseActionRoute sessionId="session-1" />);

    await user.type(screen.getByLabelText(/Harga Penutupan/i), "5400");
    await user.type(screen.getByLabelText(/Waktu Penutupan/i), "2026-01-01T15:00");
    await user.type(screen.getByLabelText(/Alasan Penutupan/i), "Target");
    await user.click(screen.getByRole("button", { name: "Lanjutkan" }));

    expect(screen.getByRole("heading", { name: "Konfirmasi Penutupan Posisi" })).toBeInTheDocument();

    rerender(<CloseActionRoute sessionId="session-2" />);

    expect(screen.queryByRole("heading", { name: "Konfirmasi Penutupan Posisi" })).toBeNull();
    expect(screen.getByLabelText(/Harga Penutupan/i)).toHaveValue(null);
  });
});
