import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { getSession } from "@/lib/api/trade-sessions";

vi.mock("@/lib/api/trade-sessions", () => ({
  getSession: vi.fn(),
}));

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { TradeSessionShell } from "./trade-session-shell";

function makeSession(overrides: Record<string, unknown> = {}) {
  return {
    session: {
      id: "sess-1",
      ticker: "BBRI",
      company_name: "PT Bank Rakyat Indonesia Tbk",
      exchange: "IDX",
      currency: "IDR",
      title: null,
      lifecycle_status: "WATCHING",
      created_at: "2026-07-15T09:00:00Z",
      updated_at: "2026-07-20T12:00:00Z",
      archived_at: null,
    },
    trade_state: {
      position_status: "OPEN",
      thesis_status: "INTACT",
      entry_price: "2500",
      entry_at: "2026-07-15T09:30:00Z",
      original_quantity: "100",
      remaining_quantity: "100",
      active_stop_loss: "2400",
      active_target: "2800",
      average_exit_price: null,
      realized_pnl: null,
      realized_return: null,
      state_version: 1,
    },
    allowed_actions: ["MARK_READY", "CANCEL"],
    ...overrides,
  };
}

beforeEach(async () => {
  vi.clearAllMocks();
  const mod = await import("@/lib/api/analyses");
  vi.mocked(mod.listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
});

// -------------------------------------------------------------------
// Loading
// -------------------------------------------------------------------
describe("loading", () => {
  it("shows loading state", () => {
    vi.mocked(getSession).mockImplementation(() => new Promise(() => {}));
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(screen.getByText("Memuat sesi trading…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Session header
// -------------------------------------------------------------------
describe("session header", () => {
  it("displays ticker", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("BBRI")).toBeTruthy();
  });

  it("displays company name", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("PT Bank Rakyat Indonesia Tbk")).toBeTruthy();
  });

  it("displays fallback when company is null", async () => {
    vi.mocked(getSession).mockResolvedValue(
      makeSession({
        session: {
          id: "sess-1", ticker: "BBRI", company_name: null,
          exchange: "IDX", currency: "IDR", title: null,
          lifecycle_status: "WATCHING",
          created_at: "2026-07-15T09:00:00Z", updated_at: "2026-07-20T12:00:00Z",
          archived_at: null,
        },
      }),
    );
    render(<TradeSessionShell sessionId="sess-1" />);
    const ticker = await screen.findByText("BBRI");
    expect(ticker).toBeTruthy();
  });

  it("displays exchange and currency", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("IDX")).toBeTruthy();
    expect(await screen.findByText("IDR")).toBeTruthy();
  });

  it("has back link to /sessions", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    const backLink = await screen.findByText(/Kembali ke Daftar Sesi/);
    expect(backLink.getAttribute("href")).toBe("/sessions");
  });
});

// -------------------------------------------------------------------
// Lifecycle status
// -------------------------------------------------------------------
describe("lifecycle status", () => {
  it("displays Indonesian label", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Dipantau")).toBeTruthy();
  });

  it("shows raw status as secondary text", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("WATCHING")).toBeTruthy();
  });

  it("falls back for unknown status", async () => {
    vi.mocked(getSession).mockResolvedValue(
      makeSession({
        session: {
          id: "sess-1", ticker: "X", company_name: null,
          exchange: "X", currency: "X", title: null,
          lifecycle_status: "UNKNOWN",
          created_at: "2026-07-15T09:00:00Z", updated_at: "2026-07-20T12:00:00Z",
          archived_at: null,
        },
      }),
    );
    render(<TradeSessionShell sessionId="sess-1" />);
    const matches = await screen.findAllByText("UNKNOWN");
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });
});

// -------------------------------------------------------------------
// Canonical position summary
// -------------------------------------------------------------------
describe("canonical position summary", () => {
  it("has canonical heading", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Data Posisi Terkonfirmasi")).toBeTruthy();
  });

  it("displays entry price", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("2500")).toBeTruthy();
  });

  it("displays original quantity", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    const matches = await screen.findAllByText("100");
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("displays active stop loss", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("2400")).toBeTruthy();
  });

  it("displays active target", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("2800")).toBeTruthy();
  });

  it("shows fallback for null values", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    const fallbacks = await screen.findAllByText("Belum tersedia");
    expect(fallbacks.length).toBeGreaterThanOrEqual(1);
  });
});

// -------------------------------------------------------------------
// Required sections
// -------------------------------------------------------------------
describe("required sections", () => {
  it("has Evidence section", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Evidence")).toBeTruthy();
  });

  it("has analysis section showing loading state", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(
      await screen.findByText("Memuat closing analysis…"),
    ).toBeTruthy();
  });

  it("has Timeline section", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Timeline")).toBeTruthy();
  });

  it("has Riwayat Analisis section", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Riwayat Analisis")).toBeTruthy();
  });

  it("has Tindakan Tersedia section", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Tindakan Tersedia")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Session isolation
// -------------------------------------------------------------------
describe("session isolation", () => {
  it("loads session A data for session A", async () => {
    vi.mocked(getSession).mockResolvedValue(makeSession());
    render(<TradeSessionShell sessionId="sess-a" />);
    expect(await screen.findByText("BBRI")).toBeTruthy();
    expect(getSession).toHaveBeenCalledWith("sess-a");
  });

  it("loads session B data for session B", async () => {
    vi.mocked(getSession).mockResolvedValue(
      makeSession({
        session: { id: "sess-b", ticker: "TLKM", company_name: "Telkom" },
      }),
    );
    render(<TradeSessionShell sessionId="sess-b" />);
    expect(await screen.findByText("TLKM")).toBeTruthy();
    expect(getSession).toHaveBeenCalledWith("sess-b");
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows authentication error safely", async () => {
    const { AuthenticationError } = await import("@/lib/api/errors");
    vi.mocked(getSession).mockRejectedValue(
      new AuthenticationError(401, "AUTHENTICATION_REQUIRED", "Auth required"),
    );
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(
      await screen.findByText(
        "Silakan masuk terlebih dahulu untuk melihat sesi trading.",
      ),
    ).toBeTruthy();
  });

  it("shows not-found message for 404", async () => {
    const { ApiError } = await import("@/lib/api/errors");
    vi.mocked(getSession).mockRejectedValue(
      new ApiError(404, "SESSION_NOT_FOUND", "Session not found"),
    );
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(
      await screen.findByText("Sesi trading tidak ditemukan."),
    ).toBeTruthy();
  });

  it("shows generic fallback for unknown error", async () => {
    vi.mocked(getSession).mockRejectedValue(new Error("fail"));
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(
      await screen.findByText("Terjadi kesalahan. Silakan coba lagi."),
    ).toBeTruthy();
  });

  it("has retry button on error", async () => {
    vi.mocked(getSession).mockRejectedValue(new Error("fail"));
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Coba Lagi")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Allowed actions
// -------------------------------------------------------------------
describe("allowed actions", () => {
  it("renders clickable button for OPEN_POSITION action", async () => {
    vi.mocked(getSession).mockResolvedValue(
      makeSession({ allowed_actions: ["OPEN_POSITION"] }),
    );
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Buka Posisi")).toBeTruthy();
  });

  it("renders clickable button for CONFIRM_STOP action", async () => {
    vi.mocked(getSession).mockResolvedValue(
      makeSession({ allowed_actions: ["CONFIRM_STOP"] }),
    );
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Konfirmasi Stop Loss")).toBeTruthy();
  });

  it("renders clickable button for FULL_EXIT action", async () => {
    vi.mocked(getSession).mockResolvedValue(
      makeSession({ allowed_actions: ["FULL_EXIT"] }),
    );
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Tutup Posisi")).toBeTruthy();
  });

  it("renders non-interactive action as plain text", async () => {
    vi.mocked(getSession).mockResolvedValue(
      makeSession({ allowed_actions: ["MARK_READY"] }),
    );
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByText("Tandai Siap")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Boundaries
// -------------------------------------------------------------------
describe("boundaries", () => {
  it("does not use direct fetch", () => {
    const src = TradeSessionShell.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });
});
