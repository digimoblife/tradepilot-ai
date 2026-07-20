import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { SessionList } from "./session-list";

// Mock the trade-sessions API module
vi.mock("@/lib/api/trade-sessions", () => ({
  listSessions: vi.fn(),
}));

const { listSessions } = await import("@/lib/api/trade-sessions");

function makeSession(overrides: Record<string, unknown> = {}) {
  return {
    id: "sid-1",
    ticker: "BBRI",
    company_name: "PT Bank Rakyat Indonesia Tbk",
    exchange: "IDX",
    currency: "IDR",
    title: null,
    lifecycle_status: "WATCHING",
    created_at: "2026-07-15T09:00:00Z",
    updated_at: "2026-07-20T12:00:00Z",
    archived_at: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

// -------------------------------------------------------------------
// Rendering
// -------------------------------------------------------------------
describe("rendering", () => {
  it("shows ticker for each session", async () => {
    vi.mocked(listSessions).mockResolvedValue({
      sessions: [
        makeSession({ id: "sid-1", ticker: "BBRI" }),
        makeSession({ id: "sid-2", ticker: "TLKM" }),
      ],
      total: 2,
    });
    render(<SessionList />);
    expect(await screen.findByText("BBRI")).toBeTruthy();
    expect(await screen.findByText("TLKM")).toBeTruthy();
  });

  it("shows company name when present", async () => {
    vi.mocked(listSessions).mockResolvedValue({
      sessions: [makeSession()],
      total: 1,
    });
    render(<SessionList />);
    expect(await screen.findByText("PT Bank Rakyat Indonesia Tbk")).toBeTruthy();
  });

  it("shows fallback when company name is null", async () => {
    vi.mocked(listSessions).mockResolvedValue({
      sessions: [makeSession({ company_name: null })],
      total: 1,
    });
    render(<SessionList />);
    expect(await screen.findByText(/Saham BBRI/)).toBeTruthy();
  });

  it("shows exchange and currency", async () => {
    vi.mocked(listSessions).mockResolvedValue({
      sessions: [makeSession()],
      total: 1,
    });
    render(<SessionList />);
    expect(await screen.findByText("IDX")).toBeTruthy();
    expect(await screen.findByText("IDR")).toBeTruthy();
  });

  it("shows lifecycle label in Indonesian", async () => {
    vi.mocked(listSessions).mockResolvedValue({
      sessions: [makeSession({ lifecycle_status: "OPEN_POSITION" })],
      total: 1,
    });
    render(<SessionList />);
    expect(await screen.findByText("Posisi Terbuka")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Empty state
// -------------------------------------------------------------------
describe("empty state", () => {
  it("shows empty message when no sessions", async () => {
    vi.mocked(listSessions).mockResolvedValue({ sessions: [], total: 0 });
    render(<SessionList />);
    expect(await screen.findByText("Belum ada sesi trading.")).toBeTruthy();
  });

  it("shows new-session link on empty state", async () => {
    vi.mocked(listSessions).mockResolvedValue({ sessions: [], total: 0 });
    render(<SessionList />);
    const link = await screen.findByText("Buat Sesi Baru");
    expect(link.getAttribute("href")).toBe("/sessions/new");
  });
});

// -------------------------------------------------------------------
// Loading state
// -------------------------------------------------------------------
describe("loading state", () => {
  it("shows loading indicator", () => {
    // Keep promise pending
    vi.mocked(listSessions).mockImplementation(() => new Promise(() => {}));
    render(<SessionList />);
    expect(screen.getByText("Memuat sesi trading…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Error state
// -------------------------------------------------------------------
describe("error state", () => {
  it("shows API error message", async () => {
    const { ApiError } = await import("@/lib/api/errors");
    vi.mocked(listSessions).mockRejectedValue(
      new ApiError(422, "EVIDENCE_FILE_UNSUPPORTED", "Format file tidak didukung."),
    );
    render(<SessionList />);
    expect(await screen.findByText("Format file tidak didukung.")).toBeTruthy();
  });

  it("shows authentication message for auth errors", async () => {
    const { AuthenticationError } = await import("@/lib/api/errors");
    vi.mocked(listSessions).mockRejectedValue(
      new AuthenticationError(401, "AUTHENTICATION_REQUIRED", "Autentikasi diperlukan."),
    );
    render(<SessionList />);
    expect(
      await screen.findByText(
        "Silakan masuk terlebih dahulu untuk melihat sesi trading.",
      ),
    ).toBeTruthy();
  });

  it("shows generic message for unknown errors", async () => {
    vi.mocked(listSessions).mockRejectedValue(new Error("something broke"));
    render(<SessionList />);
    expect(
      await screen.findByText("Terjadi kesalahan. Silakan coba lagi."),
    ).toBeTruthy();
  });

  it("renders retry button on error", async () => {
    const { ApiError } = await import("@/lib/api/errors");
    vi.mocked(listSessions).mockRejectedValue(
      new ApiError(500, "INTERNAL_ERROR", "Server error"),
    );
    render(<SessionList />);
    expect(await screen.findByText("Coba Lagi")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Status label mapping
// -------------------------------------------------------------------
describe("status label mapping", () => {
  const cases: [string, string][] = [
    ["DRAFT", "Draf"],
    ["READY_FOR_ANALYSIS", "Siap Dianalisis"],
    ["ANALYZING", "Sedang Dianalisis"],
    ["WATCHING", "Dipantau"],
    ["OPEN_POSITION", "Posisi Terbuka"],
    ["PARTIALLY_CLOSED", "Ditutup Sebagian"],
    ["CLOSED_TAKE_PROFIT", "Selesai"],
    ["CLOSED_STOP_LOSS", "Selesai"],
    ["CLOSED_MANUAL", "Selesai"],
    ["CANCELLED", "Dibatalkan"],
    ["ARCHIVED", "Diarsipkan"],
  ];

  for (const [status, expected] of cases) {
    it(`maps ${status} to ${expected}`, async () => {
      vi.mocked(listSessions).mockResolvedValue({
        sessions: [makeSession({ lifecycle_status: status })],
        total: 1,
      });
      render(<SessionList />);
      expect(await screen.findByText(expected)).toBeTruthy();
    });
  }

  it("falls back to raw value for unknown status", async () => {
    vi.mocked(listSessions).mockResolvedValue({
      sessions: [makeSession({ lifecycle_status: "UNKNOWN_STATUS" })],
      total: 1,
    });
    render(<SessionList />);
    expect(await screen.findByText("UNKNOWN_STATUS")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Navigation
// -------------------------------------------------------------------
describe("navigation", () => {
  it("new-session link points to /sessions/new", async () => {
    vi.mocked(listSessions).mockResolvedValue({ sessions: [], total: 0 });
    render(<SessionList />);
    const link = await screen.findByText("Buat Sesi Baru");
    expect(link.getAttribute("href")).toBe("/sessions/new");
  });

  it("each card links to /sessions/{id}", async () => {
    vi.mocked(listSessions).mockResolvedValue({
      sessions: [
        makeSession({ id: "abc-123" }),
        makeSession({ id: "def-456", ticker: "TLKM" }),
      ],
      total: 2,
    });
    render(<SessionList />);
    const links = await screen.findAllByRole("link");
    const sessionLinks = links.filter(
      (l) => l.getAttribute("href")?.startsWith("/sessions/") && l.getAttribute("href") !== "/sessions/new",
    );
    expect(sessionLinks).toHaveLength(2);
    expect(sessionLinks[0].getAttribute("href")).toBe("/sessions/abc-123");
    expect(sessionLinks[1].getAttribute("href")).toBe("/sessions/def-456");
  });
});

// -------------------------------------------------------------------
// Boundaries
// -------------------------------------------------------------------
describe("boundaries", () => {
  it("uses TP-1101 client, not direct fetch", () => {
    // SessionList imports listSessions from @/lib/api/trade-sessions
    // No fetch() call should exist in the page or feature components
    const src = SessionList.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });
});
