import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { archiveSession, getSession, markReady } from "@/lib/api/trade-sessions";
import { cancelSession } from "@/lib/api/trade-actions";
import { listEvidence } from "@/lib/api/evidence";
import { getTimeline } from "@/lib/api/timeline";
import { getJobStatus, requestAnalysis } from "@/lib/api/analyses";

vi.mock("@/lib/api/trade-sessions", () => ({
  getSession: vi.fn(),
  markReady: vi.fn(),
  archiveSession: vi.fn(),
}));

vi.mock("@/lib/api/trade-actions", () => ({
  cancelSession: vi.fn(),
}));

vi.mock("@/lib/api/evidence", () => ({
  listEvidence: vi.fn(),
  downloadEvidenceFile: vi.fn().mockResolvedValue(new Blob(["test"], { type: "image/png" })),
}));

vi.mock("@/lib/api/analyses", () => ({
  requestAnalysis: vi.fn(),
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
  getJobStatus: vi.fn(),
  retryJob: vi.fn(),
}));

vi.mock("@/lib/api/timeline", () => ({
  getTimeline: vi.fn(),
}));

import { TradeSessionShell } from "./trade-session-shell";

beforeAll(() => {
  globalThis.URL.createObjectURL = vi.fn(() => "blob:test");
  globalThis.URL.revokeObjectURL = vi.fn();
});

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

function makeReadySession(overrides: Record<string, unknown> = {}) {
  return makeSession({
    session: {
      id: "sess-1",
      ticker: "BBRI",
      company_name: "PT Bank Rakyat Indonesia Tbk",
      exchange: "IDX",
      currency: "IDR",
      title: null,
      lifecycle_status: "READY_FOR_ANALYSIS",
      created_at: "2026-07-15T09:00:00Z",
      updated_at: "2026-07-20T12:00:00Z",
      archived_at: null,
    },
    trade_state: {
      position_status: "NOT_OPENED",
      thesis_status: "INTACT",
      entry_price: null,
      entry_at: null,
      original_quantity: null,
      remaining_quantity: null,
      active_stop_loss: null,
      active_target: null,
      average_exit_price: null,
      realized_pnl: null,
      realized_return: null,
      state_version: 1,
    },
    allowed_actions: ["CANCEL", "ARCHIVE"],
    ...overrides,
  });
}

function mockEvidenceComplete() {
  vi.mocked(listEvidence).mockResolvedValue({
    evidence: [
      { id: "e1", session_id: "sess-1", evidence_type: "ORDERBOOK_SCREENSHOT", status: "AVAILABLE", original_filename: null, mime_type: null, file_size_bytes: null, checksum_sha256: null, market_timestamp: null, uploaded_at: "", caption: null, supersedes_evidence_id: null },
      { id: "e2", session_id: "sess-1", evidence_type: "CHART_THREE_MONTH", status: "AVAILABLE", original_filename: null, mime_type: null, file_size_bytes: null, checksum_sha256: null, market_timestamp: null, uploaded_at: "", caption: null, supersedes_evidence_id: null },
      { id: "e3", session_id: "sess-1", evidence_type: "CHART_SIX_MONTH", status: "AVAILABLE", original_filename: null, mime_type: null, file_size_bytes: null, checksum_sha256: null, market_timestamp: null, uploaded_at: "", caption: null, supersedes_evidence_id: null },
    ],
    total: 3,
  });
}

async function clickInitialAnalysisAction(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Jalankan Analisis Awal" }));
}

async function clickInitialAnalysisSubmit(user: ReturnType<typeof userEvent.setup>) {
  await waitFor(() => {
    expect(screen.getAllByRole("button", { name: "Jalankan Analisis Awal" }).length).toBeGreaterThan(1);
  });
  const buttons = screen.getAllByRole("button", { name: "Jalankan Analisis Awal" });
  await user.click(buttons[buttons.length - 1]);
}

beforeEach(async () => {
  vi.clearAllMocks();
  window.sessionStorage.clear();
  const mod = await import("@/lib/api/analyses");
  vi.mocked(mod.listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
  vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });
  vi.mocked(getTimeline).mockResolvedValue({ events: [], total: 0 });
  vi.mocked(requestAnalysis).mockResolvedValue({
    job_id: "job-1",
    session_id: "sess-1",
    analysis_type: "INITIAL_ANALYSIS",
    status: "QUEUED",
    attempt_count: 0,
    max_attempts: 3,
    available_at: "2026-07-20T12:00:00Z",
    created_at: "2026-07-20T12:00:00Z",
    previous_session_status: "READY_FOR_ANALYSIS",
  });
  vi.mocked(getJobStatus).mockResolvedValue({
    job_id: "job-1",
    session_id: "sess-1",
    analysis_type: "INITIAL_ANALYSIS",
    status: "QUEUED",
    attempt_count: 0,
    max_attempts: 3,
    available_at: "2026-07-20T12:00:00Z",
    started_at: null,
    completed_at: null,
    last_error_code: null,
    last_error_message: null,
    analysis_id: null,
    created_at: "2026-07-20T12:00:00Z",
    updated_at: "2026-07-20T12:00:00Z",
  });
  vi.mocked(markReady).mockResolvedValue({ id: "sess-1", lifecycle_status: "READY_FOR_ANALYSIS" });
  vi.mocked(archiveSession).mockResolvedValue({
    id: "sess-1",
    lifecycle_status: "ARCHIVED",
    archived_at: "2026-07-20T12:00:00Z",
  });
  vi.mocked(cancelSession).mockResolvedValue({
    action: {
      id: "action-1",
      session_id: "sess-1",
      action_type: "SESSION_CANCELLED",
      confirmed_at: "2026-07-20T12:00:00Z",
      price: null,
      quantity: null,
    },
    session_status: "CANCELLED",
    trade_state: {
      position_status: "NOT_OPENED",
      entry_price: null,
      original_quantity: null,
      remaining_quantity: null,
      active_stop_loss: null,
      active_target: null,
      average_exit_price: null,
      realized_pnl: null,
      state_version: 1,
    },
  });
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

  it("renders lifecycle actions as semantic buttons", async () => {
    vi.mocked(getSession).mockResolvedValue(
      makeSession({ allowed_actions: ["MARK_READY", "CANCEL", "ARCHIVE"] }),
    );
    render(<TradeSessionShell sessionId="sess-1" />);
    expect(await screen.findByRole("button", { name: "Tandai Siap" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Batalkan" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Arsipkan" })).toBeTruthy();
  });

  it("supports keyboard activation for Tandai Siap", async () => {
    const user = userEvent.setup();
    vi.mocked(getSession)
      .mockResolvedValueOnce(makeSession({ allowed_actions: ["MARK_READY"] }))
      .mockResolvedValueOnce(makeSession({
        session: {
          id: "sess-1",
          ticker: "BBRI",
          company_name: "PT Bank Rakyat Indonesia Tbk",
          exchange: "IDX",
          currency: "IDR",
          title: null,
          lifecycle_status: "READY_FOR_ANALYSIS",
          created_at: "2026-07-15T09:00:00Z",
          updated_at: "2026-07-20T12:00:00Z",
          archived_at: null,
        },
        allowed_actions: ["CANCEL", "ARCHIVE"],
      }));

    render(<TradeSessionShell sessionId="sess-1" />);
    const button = await screen.findByRole("button", { name: "Tandai Siap" });
    button.focus();
    expect(button).toHaveFocus();

    await user.keyboard("{Enter}");

    await waitFor(() => { expect(markReady).toHaveBeenCalledWith("sess-1"); });
    await screen.findByText("Siap Dianalisis");
  });

  it("shows backend incomplete-evidence feedback without inventing frontend rules", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/errors");
    vi.mocked(getSession).mockResolvedValue(makeSession({ allowed_actions: ["MARK_READY"] }));
    vi.mocked(markReady).mockRejectedValue(
      new ApiError(
        422,
        "ANALYSIS_REQUIRED_EVIDENCE_MISSING",
        "Missing required evidence: CHART_THREE_MONTH, ORDERBOOK_SCREENSHOT",
      ),
    );

    render(<TradeSessionShell sessionId="sess-1" />);
    await user.click(await screen.findByRole("button", { name: "Tandai Siap" }));

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Belum bisa menandai sesi siap: Missing required evidence: CHART_THREE_MONTH, ORDERBOOK_SCREENSHOT",
    );
  });

  it("marks ready and refreshes authoritative session data after success", async () => {
    const user = userEvent.setup();
    vi.mocked(getSession)
      .mockResolvedValueOnce(makeSession({ allowed_actions: ["MARK_READY"] }))
      .mockResolvedValueOnce(makeSession({
        session: {
          id: "sess-1",
          ticker: "BBRI",
          company_name: "PT Bank Rakyat Indonesia Tbk",
          exchange: "IDX",
          currency: "IDR",
          title: null,
          lifecycle_status: "READY_FOR_ANALYSIS",
          created_at: "2026-07-15T09:00:00Z",
          updated_at: "2026-07-20T12:00:00Z",
          archived_at: null,
        },
        allowed_actions: ["CANCEL", "ARCHIVE"],
      }));

    render(<TradeSessionShell sessionId="sess-1" />);
    await user.click(await screen.findByRole("button", { name: "Tandai Siap" }));

    await waitFor(() => { expect(markReady).toHaveBeenCalledWith("sess-1"); });
    await waitFor(() => { expect(getSession).toHaveBeenCalledTimes(2); });
    expect(await screen.findByText("Siap Dianalisis")).toBeTruthy();
  });

  it("confirms cancel and calls the cancel endpoint", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(getSession)
      .mockResolvedValueOnce(makeSession({ allowed_actions: ["CANCEL"] }))
      .mockResolvedValueOnce(makeSession({
        session: {
          id: "sess-1",
          ticker: "BBRI",
          company_name: "PT Bank Rakyat Indonesia Tbk",
          exchange: "IDX",
          currency: "IDR",
          title: null,
          lifecycle_status: "CANCELLED",
          created_at: "2026-07-15T09:00:00Z",
          updated_at: "2026-07-20T12:00:00Z",
          archived_at: null,
        },
        allowed_actions: ["ARCHIVE"],
      }));

    render(<TradeSessionShell sessionId="sess-1" />);
    await user.click(await screen.findByRole("button", { name: "Batalkan" }));

    await waitFor(() => { expect(cancelSession).toHaveBeenCalledTimes(1); });
    expect(cancelSession).toHaveBeenCalledWith(
      expect.objectContaining({
        session_id: "sess-1",
        reason: "USER_CANCELLED_SESSION",
        cancelled_at: expect.any(String),
        idempotency_key: expect.stringContaining("ui_cancel_sess-1_"),
      }),
    );
  });

  it("does not cancel when confirmation is rejected", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    vi.mocked(getSession).mockResolvedValue(makeSession({ allowed_actions: ["CANCEL"] }));

    render(<TradeSessionShell sessionId="sess-1" />);
    await user.click(await screen.findByRole("button", { name: "Batalkan" }));

    expect(cancelSession).not.toHaveBeenCalled();
  });

  it("confirms archive and calls the archive endpoint", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(getSession)
      .mockResolvedValueOnce(makeSession({ allowed_actions: ["ARCHIVE"] }))
      .mockResolvedValueOnce(makeSession({
        session: {
          id: "sess-1",
          ticker: "BBRI",
          company_name: "PT Bank Rakyat Indonesia Tbk",
          exchange: "IDX",
          currency: "IDR",
          title: null,
          lifecycle_status: "ARCHIVED",
          created_at: "2026-07-15T09:00:00Z",
          updated_at: "2026-07-20T12:00:00Z",
          archived_at: "2026-07-20T12:00:00Z",
        },
        allowed_actions: [],
      }));

    render(<TradeSessionShell sessionId="sess-1" />);
    await user.click(await screen.findByRole("button", { name: "Arsipkan" }));

    await waitFor(() => { expect(archiveSession).toHaveBeenCalledWith("sess-1"); });
  });

  it("shows backend errors safely", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/errors");
    vi.mocked(getSession).mockResolvedValue(makeSession({ allowed_actions: ["MARK_READY"] }));
    vi.mocked(markReady).mockRejectedValue(
      new ApiError(422, "SESSION_TRANSITION_INVALID", "<script>alert('x')</script>"),
    );

    render(<TradeSessionShell sessionId="sess-1" />);
    await user.click(await screen.findByRole("button", { name: "Tandai Siap" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Belum bisa menandai sesi siap: <script>alert('x')</script>",
    );
    expect(document.querySelector("script")).toBeNull();
  });

  it("prevents duplicate lifecycle submits", async () => {
    const user = userEvent.setup();
    let resolveReady: ((value: { id: string; lifecycle_status: string }) => void) | null = null;
    vi.mocked(markReady).mockImplementation(
      () => new Promise((resolve) => { resolveReady = resolve; }),
    );
    vi.mocked(getSession)
      .mockResolvedValueOnce(makeSession({ allowed_actions: ["MARK_READY", "CANCEL"] }))
      .mockResolvedValue(makeSession({ allowed_actions: ["CANCEL", "ARCHIVE"] }));

    render(<TradeSessionShell sessionId="sess-1" />);
    const button = await screen.findByRole("button", { name: "Tandai Siap" });

    await user.dblClick(button);

    expect(markReady).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Memproses…" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Batalkan" })).toBeDisabled();

    resolveReady?.({ id: "sess-1", lifecycle_status: "READY_FOR_ANALYSIS" });
    await waitFor(() => { expect(getSession).toHaveBeenCalledTimes(2); });
  });
});

// -------------------------------------------------------------------
// Initial analysis trigger
// -------------------------------------------------------------------
describe("initial analysis trigger", () => {
  it("shows Jalankan Analisis Awal for READY_FOR_ANALYSIS sessions", async () => {
    vi.mocked(getSession).mockResolvedValue(makeReadySession());

    render(<TradeSessionShell sessionId="sess-1" />);

    expect(await screen.findByRole("button", { name: "Jalankan Analisis Awal" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Batalkan" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Arsipkan" })).toBeTruthy();
  });

  it("blocks the initial analysis request when required evidence is incomplete", async () => {
    const user = userEvent.setup();
    vi.mocked(getSession).mockResolvedValue(makeReadySession());
    vi.mocked(listEvidence).mockResolvedValue({ evidence: [], total: 0 });

    render(<TradeSessionShell sessionId="sess-1" />);
    await clickInitialAnalysisAction(user);

    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Jalankan Analisis Awal" }).length).toBeGreaterThan(1);
    });
    const submit = screen.getAllByRole("button", { name: "Jalankan Analisis Awal" }).at(-1)!;
    expect(submit).toBeDisabled();
    expect(await screen.findByText(/Unggah evidence yang diperlukan/)).toBeTruthy();
    expect(requestAnalysis).not.toHaveBeenCalled();
  });

  it("calls the authenticated initial analysis endpoint from READY_FOR_ANALYSIS", async () => {
    const user = userEvent.setup();
    vi.mocked(getSession).mockResolvedValue(makeReadySession());
    mockEvidenceComplete();

    render(<TradeSessionShell sessionId="sess-1" />);
    await clickInitialAnalysisAction(user);
    await clickInitialAnalysisSubmit(user);

    await waitFor(() => {
      expect(requestAnalysis).toHaveBeenCalledWith("sess-1", { analysis_type: "INITIAL_ANALYSIS" });
    });
    expect(await screen.findByText("Dalam Antrian")).toBeTruthy();
  });

  it("prevents duplicate initial analysis submits", async () => {
    const user = userEvent.setup();
    let resolveRequest: ((value: Awaited<ReturnType<typeof requestAnalysis>>) => void) | null = null;
    vi.mocked(getSession).mockResolvedValue(makeReadySession());
    mockEvidenceComplete();
    vi.mocked(requestAnalysis).mockImplementation(
      () => new Promise((resolve) => { resolveRequest = resolve; }),
    );

    render(<TradeSessionShell sessionId="sess-1" />);
    await clickInitialAnalysisAction(user);
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Jalankan Analisis Awal" }).length).toBeGreaterThan(1);
    });
    const submit = screen.getAllByRole("button", { name: "Jalankan Analisis Awal" }).at(-1)!;
    await user.dblClick(submit);

    expect(requestAnalysis).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("button", { name: "Mengirim…" })).toBeDisabled();

    resolveRequest?.({
      job_id: "job-1",
      session_id: "sess-1",
      analysis_type: "INITIAL_ANALYSIS",
      status: "QUEUED",
      attempt_count: 0,
      max_attempts: 3,
      available_at: "2026-07-20T12:00:00Z",
      created_at: "2026-07-20T12:00:00Z",
      previous_session_status: "READY_FOR_ANALYSIS",
    });
    await screen.findByText("Dalam Antrian");
  });

  it("shows failed job state from the initial analysis request", async () => {
    const user = userEvent.setup();
    vi.mocked(getSession).mockResolvedValue(makeReadySession());
    mockEvidenceComplete();
    vi.mocked(getJobStatus).mockResolvedValue({
      job_id: "job-1",
      session_id: "sess-1",
      analysis_type: "INITIAL_ANALYSIS",
      status: "FAILED",
      attempt_count: 1,
      max_attempts: 3,
      available_at: null,
      started_at: "2026-07-20T12:01:00Z",
      completed_at: "2026-07-20T12:02:00Z",
      last_error_code: "PROVIDER_ERROR",
      last_error_message: "Provider gagal.",
      analysis_id: null,
      created_at: "2026-07-20T12:00:00Z",
      updated_at: "2026-07-20T12:02:00Z",
    });

    render(<TradeSessionShell sessionId="sess-1" />);
    await clickInitialAnalysisAction(user);
    await clickInitialAnalysisSubmit(user);

    expect(await screen.findByText("Analisis Gagal")).toBeTruthy();
  });

  it("refreshes session state after a terminal failed job response", async () => {
    const user = userEvent.setup();
    vi.mocked(getSession)
      .mockResolvedValueOnce(makeReadySession())
      .mockResolvedValueOnce(makeReadySession({ session: { ...makeReadySession().session, lifecycle_status: "READY_FOR_ANALYSIS" } }));
    mockEvidenceComplete();
    vi.mocked(getJobStatus).mockResolvedValue({
      job_id: "job-1",
      session_id: "sess-1",
      analysis_type: "INITIAL_ANALYSIS",
      status: "FAILED",
      attempt_count: 3,
      max_attempts: 3,
      available_at: null,
      started_at: "2026-07-20T12:01:00Z",
      completed_at: "2026-07-20T12:02:00Z",
      last_error_code: "AI_PROVIDER_INVALID_REQUEST",
      last_error_message: "Model not found: gemini-3.5-flash",
      analysis_id: null,
      created_at: "2026-07-20T12:00:00Z",
      updated_at: "2026-07-20T12:02:00Z",
    });

    render(<TradeSessionShell sessionId="sess-1" />);
    await clickInitialAnalysisAction(user);
    await clickInitialAnalysisSubmit(user);

    expect(await screen.findByText("Analisis Gagal")).toBeTruthy();
    await waitFor(() => {
      expect(getSession).toHaveBeenCalledTimes(3);
    });
  });

  it("refreshes session, timeline, and analysis history after successful analysis", async () => {
    const user = userEvent.setup();
    vi.mocked(getSession)
      .mockResolvedValueOnce(makeReadySession())
      .mockResolvedValueOnce(makeSession({ allowed_actions: ["OPEN_POSITION"] }));
    mockEvidenceComplete();
    const analysesMod = await import("@/lib/api/analyses");
    vi.mocked(analysesMod.listAnalyses)
      .mockResolvedValueOnce({ analyses: [], total: 0 })
      .mockResolvedValue({
        analyses: [{
          id: "analysis-1",
          session_id: "sess-1",
          analysis_type: "INITIAL_ANALYSIS",
          acceptance_status: "ACCEPTED",
          accepted_at: "2026-07-20T12:02:00Z",
          created_at: "2026-07-20T12:02:00Z",
          prompt_version: "1.0.0",
          schema_name: "initial_analysis",
          schema_version: "1.0.0",
          supersedes_analysis_id: null,
        }],
        total: 1,
      });
    vi.mocked(getTimeline)
      .mockResolvedValueOnce({ events: [], total: 0 })
      .mockResolvedValue({
        events: [{
          id: "event-1",
          session_id: "sess-1",
          event_type: "ANALYSIS_ACCEPTED",
          occurred_at: "2026-07-20T12:02:00Z",
          created_at: "2026-07-20T12:02:00Z",
          summary: "Initial analysis generated",
          price: null,
          quantity: null,
          related_action: null,
          related_analysis: {
            id: "analysis-1",
            analysis_type: "INITIAL_ANALYSIS",
            accepted_at: "2026-07-20T12:02:00Z",
            schema_name: "initial_analysis",
            schema_version: "1.0.0",
          },
        }],
        total: 1,
      });
    vi.mocked(getJobStatus).mockResolvedValue({
      job_id: "job-1",
      session_id: "sess-1",
      analysis_type: "INITIAL_ANALYSIS",
      status: "COMPLETED",
      attempt_count: 1,
      max_attempts: 3,
      available_at: null,
      started_at: "2026-07-20T12:01:00Z",
      completed_at: "2026-07-20T12:02:00Z",
      last_error_code: null,
      last_error_message: null,
      analysis_id: "analysis-1",
      created_at: "2026-07-20T12:00:00Z",
      updated_at: "2026-07-20T12:02:00Z",
    });

    render(<TradeSessionShell sessionId="sess-1" />);
    await clickInitialAnalysisAction(user);
    await clickInitialAnalysisSubmit(user);

    await waitFor(() => { expect(getSession).toHaveBeenCalledTimes(2); });
    expect(await screen.findByText("Initial analysis generated")).toBeTruthy();
    expect(await screen.findByText("Analisis Awal")).toBeTruthy();
  });

  it("shows Indonesian error feedback for backend request rejection", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/errors");
    vi.mocked(getSession).mockResolvedValue(makeReadySession());
    mockEvidenceComplete();
    vi.mocked(requestAnalysis).mockRejectedValue(
      new ApiError(422, "ANALYSIS_REQUIRED_EVIDENCE_MISSING", "Missing required evidence: CHART_SIX_MONTH"),
    );

    render(<TradeSessionShell sessionId="sess-1" />);
    await clickInitialAnalysisAction(user);
    await clickInitialAnalysisSubmit(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Gagal menjalankan analisis awal: Missing required evidence: CHART_SIX_MONTH",
    );
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
