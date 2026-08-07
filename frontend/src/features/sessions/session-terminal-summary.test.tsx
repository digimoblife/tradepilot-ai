import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SessionTerminalSummary } from "@/features/sessions/session-terminal-summary";
import { archiveSessionV2, restoreSessionV2 } from "@/features/trade-workspace/api";
import type { SessionDetailAggregate } from "@/features/trade-workspace/types";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

vi.mock("@/features/trade-workspace/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/trade-workspace/api")>();
  return {
    ...actual,
    archiveSessionV2: vi.fn(),
    restoreSessionV2: vi.fn(),
  };
});

const sessionId = "session-closed-123";

function makeDetail(overrides: Partial<SessionDetailAggregate> = {}): SessionDetailAggregate {
  return {
    session: {
      id: sessionId,
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      status: "CLOSED",
      initial_note: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T12:00:00Z",
      closed_at: "2026-01-01T12:00:00Z",
      archived_at: null,
    },
    current_step: {
      code: "TERMINAL_CLOSED",
      mode: "READ_ONLY",
      workflow_actions: [],
      active_request: null,
      failed_request: null,
      read_only: true,
    },
    decisions: [
      {
        decision_id: "dec-buy-1",
        decision: "BUY",
        reason: null,
        note: "Buy setup confirmed",
        created_at: "2026-01-01T01:00:00Z",
      },
    ],
    position: {
      id: "pos-1",
      entry_price: 5000,
      quantity: 100,
      stop_loss: 4800,
      target_price: 5500,
      entry_timestamp: "2026-01-01T01:05:00Z",
    },
    closure: {
      id: "cls-1",
      close_price: 5400,
      close_reason: "Target tercapai",
      note: "Profit taking",
      close_timestamp: "2026-01-01T12:00:00Z",
    },
    initial_evidence: [],
    initial_analysis: null,
    wait_updates: [],
    position_updates: [],
    latest_analysis: null,
    recent_activity: [],
    ...overrides,
  };
}

describe("SessionTerminalSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null for non-terminal session status", () => {
    const draftDetail = makeDetail({
      session: {
        id: sessionId,
        ticker: "BBRI",
        company_name: "Bank Rakyat Indonesia",
        status: "DRAFT",
        initial_note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        closed_at: null,
        archived_at: null,
      },
    });

    const { container } = render(<SessionTerminalSummary sessionId={sessionId} detail={draftDetail} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders CLOSED terminal summary with position facts and Archive action button", () => {
    const detail = makeDetail();
    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    expect(screen.getByRole("heading", { name: "Sesi Selesai" })).toBeInTheDocument();
    expect(
      screen.getByText("Posisi telah ditutup dan sesi ini sekarang hanya dapat dibaca."),
    ).toBeInTheDocument();

    expect(screen.getByText("5.400")).toBeInTheDocument();
    expect(screen.getByText("Target tercapai")).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "Arsipkan Sesi" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Kembalikan ke Daftar" })).toBeNull();
  });

  it("renders CLOSED_SKIPPED terminal summary with SKIP facts and Archive action button", () => {
    const detail = makeDetail({
      session: {
        id: sessionId,
        ticker: "BBRI",
        company_name: "Bank Rakyat Indonesia",
        status: "CLOSED_SKIPPED",
        initial_note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T08:00:00Z",
        closed_at: "2026-01-01T08:00:00Z",
        archived_at: null,
      },
      decisions: [
        {
          decision_id: "dec-skip-1",
          decision: "SKIP",
          reason: "RISK_TOO_HIGH",
          note: "Risk reward tidak seimbang",
          created_at: "2026-01-01T08:00:00Z",
        },
      ],
      position: null,
      closure: null,
    });

    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    expect(screen.getByRole("heading", { name: "Sesi Dilewati" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Arsipkan Sesi" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Kembalikan ke Daftar" })).toBeNull();
  });

  it("opens two-step Archive confirmation panel, allows cancelling without API call", async () => {
    const user = userEvent.setup();
    const detail = makeDetail();
    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    const archiveButton = screen.getByRole("button", { name: "Arsipkan Sesi" });
    await user.click(archiveButton);

    expect(screen.getByRole("heading", { name: "Arsipkan Sesi BBRI?" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Sesi BBRI akan dipindahkan dari daftar Sesi ke Sesi Diarsipkan. Data, analisis, dan riwayat sesi tetap tersimpan, dan sesi dapat dikembalikan ke daftar selesai nanti.",
      ),
    ).toBeInTheDocument();

    const cancelButton = screen.getByRole("button", { name: "Batal" });
    await user.click(cancelButton);

    expect(archiveSessionV2).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Arsipkan Sesi" })).toBeInTheDocument();
  });

  it("confirms archive, calls V2 API, and navigates to Archived Sessions after success", async () => {
    const user = userEvent.setup();
    vi.mocked(archiveSessionV2).mockResolvedValue({
      id: sessionId,
      status: "CLOSED",
      archived_at: "2026-08-07T12:00:00Z",
    });

    const detail = makeDetail();
    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    await user.click(screen.getByRole("button", { name: "Arsipkan Sesi" }));
    const confirmButton = screen.getAllByRole("button", { name: "Arsipkan Sesi" })[0];
    await user.click(confirmButton);

    await waitFor(() => {
      expect(archiveSessionV2).toHaveBeenCalledWith(sessionId);
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/sessions/archived");
    });
  });

  it("renders Restore action button for archived CLOSED session and shows confirmation modal", async () => {
    const user = userEvent.setup();
    const detail = makeDetail({
      session: {
        id: sessionId,
        ticker: "BBRI",
        company_name: "Bank Rakyat Indonesia",
        status: "CLOSED",
        initial_note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T15:00:00Z",
        closed_at: "2026-01-01T15:00:00Z",
        archived_at: "2026-01-02T00:00:00Z",
      },
    });

    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    expect(screen.getByText("Diarsipkan")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Arsipkan Sesi" })).toBeNull();

    const restoreButton = screen.getByRole("button", { name: "Kembalikan ke Daftar" });
    await user.click(restoreButton);

    expect(screen.getByRole("heading", { name: "Kembalikan sesi ini ke daftar?" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Sesi BBRI akan dikembalikan ke bagian Selesai pada daftar Sesi. Status selesai, data, analisis, dan riwayat tetap sama. Trading tidak akan dibuka kembali.",
      ),
    ).toBeInTheDocument();
  });

  it("confirms Restore for archived CLOSED session, calls V2 Restore API, and navigates to /sessions", async () => {
    const user = userEvent.setup();
    vi.mocked(restoreSessionV2).mockResolvedValue({
      id: sessionId,
      status: "CLOSED",
      archived_at: null,
    });

    const detail = makeDetail({
      session: {
        id: sessionId,
        ticker: "BBRI",
        company_name: "Bank Rakyat Indonesia",
        status: "CLOSED",
        initial_note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T15:00:00Z",
        closed_at: "2026-01-01T15:00:00Z",
        archived_at: "2026-01-02T00:00:00Z",
      },
    });

    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    await user.click(screen.getByRole("button", { name: "Kembalikan ke Daftar" }));
    const confirmButton = screen.getAllByRole("button", { name: "Kembalikan ke Daftar" })[0];
    await user.click(confirmButton);

    await waitFor(() => {
      expect(restoreSessionV2).toHaveBeenCalledWith(sessionId);
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/sessions");
    });
  });

  it("confirms Restore for archived CLOSED_SKIPPED session and preserves terminal status without reopening trading", async () => {
    const user = userEvent.setup();
    vi.mocked(restoreSessionV2).mockResolvedValue({
      id: sessionId,
      status: "CLOSED_SKIPPED",
      archived_at: null,
    });

    const detail = makeDetail({
      session: {
        id: sessionId,
        ticker: "BBRI",
        company_name: "Bank Rakyat Indonesia",
        status: "CLOSED_SKIPPED",
        initial_note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T08:00:00Z",
        closed_at: "2026-01-01T08:00:00Z",
        archived_at: "2026-01-02T00:00:00Z",
      },
      decisions: [
        {
          decision_id: "dec-skip-1",
          decision: "SKIP",
          reason: "RISK_TOO_HIGH",
          note: null,
          created_at: "2026-01-01T08:00:00Z",
        },
      ],
      position: null,
      closure: null,
    });

    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    await user.click(screen.getByRole("button", { name: "Kembalikan ke Daftar" }));
    const confirmButton = screen.getAllByRole("button", { name: "Kembalikan ke Daftar" })[0];
    await user.click(confirmButton);

    await waitFor(() => {
      expect(restoreSessionV2).toHaveBeenCalledWith(sessionId);
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/sessions");
    });
    expect(screen.queryByText("BUY")).toBeNull();
    expect(screen.queryByText("WAIT")).toBeNull();
  });

  it("displays Indonesian error feedback when Restore API fails and keeps session archived in UI state", async () => {
    const user = userEvent.setup();
    vi.mocked(restoreSessionV2).mockRejectedValue(new Error("Sesi tidak dapat dikembalikan ke daftar. Coba lagi."));

    const detail = makeDetail({
      session: {
        id: sessionId,
        ticker: "BBRI",
        company_name: "Bank Rakyat Indonesia",
        status: "CLOSED",
        initial_note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T15:00:00Z",
        closed_at: "2026-01-01T15:00:00Z",
        archived_at: "2026-01-02T00:00:00Z",
      },
    });

    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    await user.click(screen.getByRole("button", { name: "Kembalikan ke Daftar" }));
    const confirmButton = screen.getAllByRole("button", { name: "Kembalikan ke Daftar" })[0];
    await user.click(confirmButton);

    await waitFor(() => {
      expect(restoreSessionV2).toHaveBeenCalledWith(sessionId);
    });

    expect(await screen.findByText("Sesi tidak dapat dikembalikan ke daftar. Coba lagi.")).toBeInTheDocument();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("exposes no trading action buttons, forms, or reopen controls in terminal summary", () => {
    const detail = makeDetail();
    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByText(/Buka Kembali/i)).toBeNull();
    expect(screen.queryByText(/Hapus/i)).toBeNull();
  });

  it("returns focus to trigger button when Archive or Restore confirmation is cancelled", async () => {
    const user = userEvent.setup();
    const detail = makeDetail();
    render(<SessionTerminalSummary sessionId={sessionId} detail={detail} />);

    const archiveBtn = screen.getByRole("button", { name: "Arsipkan Sesi" });
    await user.click(archiveBtn);
    expect(screen.getByRole("heading", { name: "Arsipkan Sesi BBRI?" })).toBeInTheDocument();

    const cancelBtn = screen.getByRole("button", { name: "Batal" });
    await user.click(cancelBtn);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Arsipkan Sesi" })).toHaveFocus();
    });
  });
});
