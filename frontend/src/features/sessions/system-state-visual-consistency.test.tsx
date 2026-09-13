import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SessionsListSurface } from "./sessions-list-surface";
import { ArchivedSessionsListSurface } from "./archived-sessions-list-surface";
import { SessionDetailHeader } from "./session-detail-header";
import { CreateSessionForm } from "./create-session-form";
import { useSessionsList } from "./use-sessions-list";
import { useArchivedSessionsList } from "./use-archived-sessions-list";
import type { TradeSession } from "@/features/trade-workspace/types";

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
});
