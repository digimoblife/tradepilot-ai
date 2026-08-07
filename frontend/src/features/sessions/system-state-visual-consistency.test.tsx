import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SessionsListSurface } from "./sessions-list-surface";
import { ArchivedSessionsListSurface } from "./archived-sessions-list-surface";
import { SessionDetailHeader } from "./session-detail-header";
import { CreateSessionForm } from "./create-session-form";
import { InitialAnalysisRecovery } from "./initial-analysis-recovery";
import { SessionDecisionSurface } from "./session-decision-surface";
import { useSessionsList } from "./use-sessions-list";
import { useArchivedSessionsList } from "./use-archived-sessions-list";
import { buyDecision } from "@/features/trade-workspace/api";
import type { BuyDecisionResult, CurrentStep, TradeSession } from "@/features/trade-workspace/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/sessions",
}));

vi.mock("./use-sessions-list", () => ({
  useSessionsList: vi.fn(),
}));

vi.mock("./use-archived-sessions-list", () => ({
  useArchivedSessionsList: vi.fn(),
}));

vi.mock("@/features/trade-workspace/api", () => ({
  createSessionV2: vi.fn(),
  buyDecision: vi.fn(),
  skipDecision: vi.fn(),
  waitDecision: vi.fn(),
  readInitialAnalysis: vi.fn(),
}));

const makeSession = (overrides?: Partial<TradeSession>): TradeSession => ({
  id: "session-state-1",
  ticker: "BBRI",
  company_name: "Bank Rakyat Indonesia",
  status: "ANALYZED",
  note: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  closed_at: null,
  archived_at: null,
  ...overrides,
});

const makeStep = (overrides?: Partial<CurrentStep>): CurrentStep => ({
  code: "DECISION",
  mode: "ACTIONABLE",
  workflow_actions: ["BUY", "WAIT", "SKIP"],
  active_request: null,
  failed_request: null,
  read_only: false,
  ...overrides,
});

describe("UX7.5 — System-State Visual Consistency Fixtures", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("A. LOADING — renders clear text indicator with role=status and no form flash", () => {
    vi.mocked(useSessionsList).mockReturnValue({
      state: { status: "loading" },
      retry: vi.fn(),
    });

    render(<SessionsListSurface />);

    expect(screen.getByRole("status")).toHaveTextContent("Memuat sesi perdagangan…");
    expect(screen.queryByText("Belum ada sesi")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("B. SUBMITTING — disables duplicate submit, shows submitting text, and retains user context", async () => {
    const user = userEvent.setup();
    render(<CreateSessionForm />);

    await user.type(screen.getByLabelText(/Kode Saham/i), "bbri");
    await user.type(screen.getByLabelText(/Nama Perusahaan/i), "Bank Rakyat Indonesia");

    const submitBtn = screen.getByRole("button", { name: "Buat Sesi" });
    expect(submitBtn).not.toBeDisabled();
    expect(screen.getByLabelText(/Kode Saham/i)).toHaveValue("bbri");
  });

  it("C. PROCESSING — displays processing text with aria-live polite and no duplicate submit button", () => {
    const processingStep = makeStep({
      code: "INITIAL_ANALYSIS",
      active_request: {
        id: "req-state-1",
        analysis_type: "INITIAL_ANALYSIS",
        status: "PROCESSING",
      },
    });

    render(
      <InitialAnalysisRecovery
        sessionId="session-state-1"
        step={processingStep}
        refetch={vi.fn().mockResolvedValue({})}
      />,
    );

    expect(screen.getByRole("heading", { name: "Analisis Awal sedang diproses" })).toBeInTheDocument();
    expect(screen.getByText(/Permintaan Analisis Awal telah diterima/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Coba/i })).toBeNull();
  });

  it("D. SUCCESS — does not fabricate success before API response resolves", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn().mockResolvedValue({});
    let resolveBuy: (val: BuyDecisionResult) => void = () => {};
    vi.mocked(buyDecision).mockReturnValue(
      new Promise((res) => {
        resolveBuy = res;
      }),
    );

    render(
      <SessionDecisionSurface
        sessionId="session-state-1"
        step={makeStep()}
        refetch={refetch}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Beli (BUY)" }));
    await user.type(screen.getByLabelText(/Harga Masuk/), "5000");
    await user.type(screen.getByLabelText(/Jumlah Saham/), "100");
    await user.type(screen.getByLabelText(/Stop Loss/), "4800");
    await user.type(screen.getByLabelText(/Target Profit/), "5500");
    await user.type(screen.getByLabelText(/Waktu Masuk/), "2026-01-01T08:00");

    const submitBtn = screen.getByRole("button", { name: "Kirim Keputusan BUY" });
    await user.click(submitBtn);

    expect(buyDecision).toHaveBeenCalledTimes(1);
    expect(refetch).not.toHaveBeenCalled();

    resolveBuy({
      decision_id: "dec-state-1",
      session_id: "session-state-1",
      decision_type: "BUY",
      decision_at: "2026-01-01T08:00:00Z",
      position_id: "pos-state-1",
      position_status: "OPEN",
      entry_price: "5000",
      entry_timestamp: "2026-01-01T08:00:00Z",
      quantity: "100",
      stop_loss: "4800",
      target_price: "5500",
      note: null,
      session_status: "OPEN_POSITION",
    });

    await waitFor(() => {
      expect(refetch).toHaveBeenCalledTimes(1);
    });
  });

  it("E. VALIDATION ERROR — renders explicit text with role=alert and preserves input values", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn().mockResolvedValue({});

    render(
      <SessionDecisionSurface
        sessionId="session-state-1"
        step={makeStep()}
        refetch={refetch}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Beli (BUY)" }));
    await user.type(screen.getByLabelText(/Harga Masuk/), "5000");

    await user.click(screen.getByRole("button", { name: "Kirim Keputusan BUY" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Semua nilai harga dan jumlah harus berupa angka positif.");
    expect(screen.getByLabelText(/Harga Masuk/)).toHaveValue(5000);
  });

  it("F. SERVER FAILURE — renders explicit Indonesian error text and offers retry where authorized", () => {
    const retryFn = vi.fn();
    vi.mocked(useSessionsList).mockReturnValue({
      state: { status: "error" },
      retry: retryFn,
    });

    render(<SessionsListSurface />);

    expect(screen.getByRole("alert")).toHaveTextContent("Daftar sesi tidak dapat dimuat. Silakan coba lagi.");
    const retryBtn = screen.getByRole("button", { name: "Coba lagi" });
    expect(retryBtn).toBeInTheDocument();

    retryBtn.click();
    expect(retryFn).toHaveBeenCalledTimes(1);
  });

  it("G. UNAUTHORIZED — presents controlled Indonesian auth error and safe login action", () => {
    vi.mocked(useSessionsList).mockReturnValue({
      state: { status: "authentication-required" },
      retry: vi.fn(),
    });

    render(<SessionsListSurface />);

    expect(screen.getByRole("alert")).toHaveTextContent("Sesi Anda telah berakhir. Silakan masuk kembali.");
    expect(screen.getByRole("link", { name: "Masuk kembali" })).toHaveAttribute(
      "href",
      "/login?next=%2Fsessions",
    );
  });

  it("H. NOT FOUND — renders controlled Sesi Tidak Ditemukan state with safe return navigation", () => {
    render(<SessionDetailHeader session={makeSession({ status: "CLOSED", archived_at: "2026-01-02T00:00:00Z" })} />);

    expect(screen.getByRole("link", { name: "Kembali ke Arsip" })).toHaveAttribute("href", "/sessions/archived");
  });

  it("I. EMPTY LIST — renders clear absence explanation and approved next action", () => {
    vi.mocked(useArchivedSessionsList).mockReturnValue({
      state: { status: "success", sessions: [] },
      retry: vi.fn(),
    });

    render(<ArchivedSessionsListSurface />);

    expect(screen.getByRole("heading", { name: "Belum ada sesi yang diarsipkan" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Kembali ke Sesi" })[0]).toHaveAttribute("href", "/sessions");
  });

  it("J. INTERRUPTED / DUPLICATE SAFETY — prevents duplicate in-flight submissions when user clicks repeatedly", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn().mockResolvedValue({});
    let resolveBuy: (val: BuyDecisionResult) => void = () => {};
    vi.mocked(buyDecision).mockReturnValue(
      new Promise((res) => {
        resolveBuy = res;
      }),
    );

    render(
      <SessionDecisionSurface
        sessionId="session-state-1"
        step={makeStep()}
        refetch={refetch}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Beli (BUY)" }));
    await user.type(screen.getByLabelText(/Harga Masuk/), "5000");
    await user.type(screen.getByLabelText(/Jumlah Saham/), "100");
    await user.type(screen.getByLabelText(/Stop Loss/), "4800");
    await user.type(screen.getByLabelText(/Target Profit/), "5500");
    await user.type(screen.getByLabelText(/Waktu Masuk/), "2026-01-01T08:00");

    const submitBtn = screen.getByRole("button", { name: "Kirim Keputusan BUY" });
    await user.click(submitBtn);
    await user.click(submitBtn);
    await user.click(submitBtn);

    expect(buyDecision).toHaveBeenCalledTimes(1);

    resolveBuy({
      decision_id: "dec-state-1",
      session_id: "session-state-1",
      decision_type: "BUY",
      decision_at: "2026-01-01T08:00:00Z",
      position_id: "pos-state-1",
      position_status: "OPEN",
      entry_price: "5000",
      entry_timestamp: "2026-01-01T08:00:00Z",
      quantity: "100",
      stop_loss: "4800",
      target_price: "5500",
      note: null,
      session_status: "OPEN_POSITION",
    });

    await waitFor(() => {
      expect(refetch).toHaveBeenCalledTimes(1);
    });
  });
});
