import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ArchivedSessionsListSurface } from "@/features/sessions/archived-sessions-list-surface";
import { listArchivedSessions } from "@/features/trade-workspace/api";
import type { TradeSessionListItem } from "@/features/trade-workspace/types";
import { ApiError } from "@/lib/api/errors";

vi.mock("@/features/trade-workspace/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/trade-workspace/api")>();
  return {
    ...actual,
    listArchivedSessions: vi.fn(),
  };
});

function makeArchivedSession(overrides: Partial<TradeSessionListItem> = {}): TradeSessionListItem {
  return {
    id: "s-archived-1",
    ticker: "BBRI",
    company_name: "Bank Rakyat Indonesia",
    status: "CLOSED",
    note: null,
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T10:00:00Z",
    closed_at: "2026-08-01T09:00:00Z",
    archived_at: "2026-08-01T10:00:00Z",
    ...overrides,
  };
}

describe("ArchivedSessionsListSurface", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially while request is in flight", () => {
    vi.mocked(listArchivedSessions).mockReturnValue(new Promise(() => {}));

    render(<ArchivedSessionsListSurface />);

    expect(screen.getByRole("status")).toHaveTextContent("Memuat sesi yang diarsipkan…");
    expect(screen.queryByText("Belum ada sesi yang diarsipkan")).toBeNull();
  });

  it("renders error state on API failure and allows retrying request", async () => {
    const user = userEvent.setup();
    vi.mocked(listArchivedSessions)
      .mockRejectedValueOnce(new ApiError(500, "INTERNAL_ERROR", "Internal Error"))
      .mockResolvedValueOnce({
        sessions: [makeArchivedSession()],
      });

    render(<ArchivedSessionsListSurface />);

    expect(
      await screen.findByText("Daftar sesi yang diarsipkan tidak dapat dimuat. Silakan coba lagi."),
    ).toBeInTheDocument();

    const retryButton = screen.getByRole("button", { name: "Coba lagi" });
    await user.click(retryButton);

    expect(await screen.findByText("BBRI")).toBeInTheDocument();
    expect(listArchivedSessions).toHaveBeenCalledTimes(2);
  });

  it("renders empty state when user has no archived sessions", async () => {
    vi.mocked(listArchivedSessions).mockResolvedValue({ sessions: [] });

    render(<ArchivedSessionsListSurface />);

    expect(await screen.findByRole("heading", { name: "Belum ada sesi yang diarsipkan" })).toBeInTheDocument();
    expect(
      screen.getByText("Sesi yang Anda arsipkan setelah selesai akan muncul di sini."),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Kembali ke Sesi" })[0]).toHaveAttribute("href", "/sessions");
  });

  it("renders populated archived sessions with multiple terminal statuses", async () => {
    const closedSession = makeArchivedSession({
      id: "s-closed-1",
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      status: "CLOSED",
      archived_at: "2026-08-01T10:00:00Z",
      closed_at: "2026-08-01T09:00:00Z",
    });
    const skippedSession = makeArchivedSession({
      id: "s-skipped-2",
      ticker: "TLKM",
      company_name: "PT Telkom Indonesia Tbk",
      status: "CLOSED_SKIPPED",
      archived_at: "2026-08-02T14:00:00Z",
      closed_at: "2026-08-02T13:30:00Z",
    });

    vi.mocked(listArchivedSessions).mockResolvedValue({
      sessions: [closedSession, skippedSession],
    });

    render(<ArchivedSessionsListSurface />);

    expect(await screen.findByText("BBRI")).toBeInTheDocument();
    expect(screen.getByText("Bank Rakyat Indonesia")).toBeInTheDocument();
    expect(screen.getByText("Selesai")).toBeInTheDocument();

    expect(screen.getByText("TLKM")).toBeInTheDocument();
    expect(screen.getByText("PT Telkom Indonesia Tbk")).toBeInTheDocument();
    expect(screen.getByText("Dilewati")).toBeInTheDocument();

    const viewLinks = screen.getAllByRole("link", { name: "Lihat Sesi" });
    expect(viewLinks[0]).toHaveAttribute("href", "/sessions/s-closed-1");
    expect(viewLinks[1]).toHaveAttribute("href", "/sessions/s-skipped-2");
  });

  it("exposes no session-flow actions or trading buttons in archived list items", async () => {
    vi.mocked(listArchivedSessions).mockResolvedValue({
      sessions: [makeArchivedSession()],
    });

    render(<ArchivedSessionsListSurface />);

    await screen.findByText("BBRI");

    expect(screen.queryByText("BUY")).toBeNull();
    expect(screen.queryByText("WAIT")).toBeNull();
    expect(screen.queryByText("SKIP")).toBeNull();
    expect(screen.queryByText("Analisis Awal")).toBeNull();
    expect(screen.queryByText("Pembaruan WAIT")).toBeNull();
    expect(screen.queryByText("Pembaruan Posisi")).toBeNull();
    expect(screen.queryByText("Tutup Posisi")).toBeNull();
    expect(screen.queryByText("Arsipkan Sesi")).toBeNull();
    expect(screen.queryByText("Pulihkan Sesi")).toBeNull();
    expect(screen.queryByText("Kembalikan Sesi")).toBeNull();
  });

  it("renders long company name fixture safely without breaking component layout", async () => {
    const longSession = makeArchivedSession({
      company_name: "PT Bank Central Asia Tbk Perseroan Terbatas Dan Anak Perusahaan Terkait Strategis Internasional",
    });

    vi.mocked(listArchivedSessions).mockResolvedValue({
      sessions: [longSession],
    });

    render(<ArchivedSessionsListSurface />);

    expect(
      await screen.findByText(
        "PT Bank Central Asia Tbk Perseroan Terbatas Dan Anak Perusahaan Terkait Strategis Internasional",
      ),
    ).toBeInTheDocument();
  });
});
