import { readFileSync } from "node:fs";

import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getSessionDetail } from "@/features/trade-workspace/api";
import { SessionAnalysisView } from "./session-analysis-view";

vi.mock("@/features/trade-workspace/api", () => ({ getSessionDetail: vi.fn() }));
vi.mock("./use-route-session", () => ({
  useRouteSession: (id: string) => ({
    status: "success",
    session: {
      id,
      ticker: "BBRI",
      company_name: "Bank BRI",
      status: "ANALYZED",
      note: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      closed_at: null,
    },
  }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/sessions/session-a/analysis" }));

const sessionId = "session-a";
const initial = { summary: "Ringkasan awal yang dipertahankan", orderbook_analysis: "Bid kuat", three_month_chart_analysis: "Tren tiga bulan", six_month_chart_analysis: "Tren enam bulan", support: { low: 100, high: 101, note: "Area support" }, resistance: { low: 110, high: 111, note: "Area resistance" }, entry_area: { low: 102, high: 104, note: "Area entry" }, stop_recommendation: { level: 99, note: "Stop" }, target_recommendation: { level: 115, note: "Target" }, probabilities: { upside: 0.6, downside: 0.4 }, risks: ["Volatilitas"], trading_plan: "Rencana bertahap", conclusion: "Tetap disiplin" };
const wait = { update_summary: "Pembaruan WAIT", current_price: 105.5, orderbook_assessment: "Bid masih mendukung", change_from_previous_analysis: "Belum berubah", current_entry_condition: "Tunggu konfirmasi", upside_probability: 0.6, downside_probability: 0.4, key_risks: ["Volatilitas"], recommended_action: "WAIT", next_plan: "Pantau orderbook", conclusion: "Belum masuk" };
const position = { update_summary: "Pembaruan posisi", current_price: 106, position_condition: "Posisi terjaga", orderbook_assessment: "Likuiditas cukup", change_from_previous_analysis: "Momentum stabil", target_realism: "Target realistis", downside_risk: "Risiko terbatas", target_probability: 0.6, trading_plan: "Pertahankan posisi", monitoring_points: ["Pantau support"], warnings: ["Pantau volatilitas"], conclusion: "Tetap waspada" };

function request(id: string, type: string, completedAt: string, payload: object, overrides: object = {}, targetSessionId: string = sessionId) {
  return { request_id: id, session_id: targetSessionId, status: "COMPLETED", analysis_type: type, completed_at: completedAt, processed_response: payload, ...overrides };
}

function detail(overrides: object = {}, targetSessionId: string = sessionId) {
  return { session: { id: targetSessionId }, initial_evidence: [], decisions: [], wait_updates: [], position: null, position_updates: [], closure: null, latest_analysis: null, recent_activity: [], current_step: { code: "DECISION", mode: "ACTIONABLE", workflow_actions: [], active_request: null, failed_request: null, read_only: false }, initial_analysis: request("initial", "INITIAL_ANALYSIS", "2026-01-01T00:00:00Z", initial, {}, targetSessionId), ...overrides };
}

beforeEach(() => vi.clearAllMocks());

describe("SessionAnalysisView", () => {
  it("renders explicit Initial Analysis sections and preserves backend values", async () => {
    vi.mocked(getSessionDetail).mockResolvedValue(detail({ initial_analysis: request("initial", "INITIAL_ANALYSIS", "2026-01-01T00:00:00Z", { ...initial, internal_debug: "jangan tampil" }) }) as never);
    render(<SessionAnalysisView sessionId={sessionId} />);
    expect(await screen.findByRole("heading", { name: "Ringkasan" })).toBeInTheDocument();
    expect(screen.getByText("Ringkasan awal yang dipertahankan")).toBeInTheDocument();
    expect(screen.getByText("0.6")).toBeInTheDocument();
    expect(screen.queryByText("jangan tampil")).toBeNull();
  });

  it("renders explicit WAIT and Position sections, selects the latest, and keeps one latest marker", async () => {
    vi.mocked(getSessionDetail).mockResolvedValue(detail({ wait_updates: [request("wait", "WAIT_UPDATE", "2026-02-01T00:00:00Z", { ...wait, provider_note: "ignore" })], position_updates: [request("position", "POSITION_UPDATE", "2026-03-01T00:00:00Z", position)] }) as never);
    const user = userEvent.setup(); render(<SessionAnalysisView sessionId={sessionId} />);
    expect(await screen.findByText("Pembaruan posisi")).toBeInTheDocument();
    expect(screen.getAllByText(/Terbaru/)).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: /Analisis WAIT/ }));
    expect(screen.getByText("Pembaruan WAIT")).toBeInTheDocument();
    expect(screen.getByText("105.5")).toBeInTheDocument();
    expect(screen.queryByText("ignore")).toBeNull();
  });

  it("uses stable ID descending as tie-breaker for equal completed_at timestamps", async () => {
    vi.mocked(getSessionDetail).mockResolvedValue(
      detail({
        initial_analysis: null,
        wait_updates: [
          request("req-1", "WAIT_UPDATE", "2026-02-01T00:00:00Z", { ...wait, update_summary: "Pembaruan WAIT Req 1" }),
          request("req-2", "WAIT_UPDATE", "2026-02-01T00:00:00Z", { ...wait, update_summary: "Pembaruan WAIT Req 2" }),
        ],
      }) as never,
    );
    render(<SessionAnalysisView sessionId={sessionId} />);
    expect(await screen.findByText("Pembaruan WAIT Req 2")).toBeInTheDocument();
    const buttons = screen.getAllByRole("button", { name: /Analisis WAIT/ });
    expect(buttons[0]).toHaveTextContent("Terbaru");
    expect(buttons[0]).toHaveAttribute("aria-pressed", "true");
  });

  it("selecting a historical record changes content but does not move the Terbaru marker", async () => {
    vi.mocked(getSessionDetail).mockResolvedValue(
      detail({
        initial_analysis: request("initial", "INITIAL_ANALYSIS", "2026-01-01T00:00:00Z", initial),
        wait_updates: [request("wait", "WAIT_UPDATE", "2026-02-01T00:00:00Z", wait)],
      }) as never,
    );
    const user = userEvent.setup();
    render(<SessionAnalysisView sessionId={sessionId} />);
    expect(await screen.findByText("Pembaruan WAIT")).toBeInTheDocument();

    const initialButton = screen.getByRole("button", { name: /Analisis Awal/ });
    const waitButton = screen.getByRole("button", { name: /Analisis WAIT/ });

    expect(waitButton).toHaveTextContent("Terbaru");
    expect(waitButton).toHaveAttribute("aria-pressed", "true");
    expect(initialButton).not.toHaveTextContent("Terbaru");

    await user.click(initialButton);

    expect(screen.getByText("Ringkasan awal yang dipertahankan")).toBeInTheDocument();
    expect(waitButton).toHaveTextContent("Terbaru");
    expect(initialButton).not.toHaveTextContent("Terbaru");
    expect(initialButton).toHaveAttribute("aria-pressed", "true");
  });

  it("renders empty state when no completed supported records exist", async () => {
    vi.mocked(getSessionDetail).mockResolvedValue(
      detail({
        initial_analysis: null,
        wait_updates: [],
        position_updates: [],
      }) as never,
    );
    render(<SessionAnalysisView sessionId={sessionId} />);
    expect(await screen.findByRole("heading", { name: "Belum ada analisis" })).toBeInTheDocument();
    expect(screen.getByText("Belum ada hasil analisis yang tersedia untuk sesi ini.")).toBeInTheDocument();
    expect(screen.getAllByRole("navigation", { name: "Navigasi sesi" })).toHaveLength(2);
  });

  it("renders sanitized read error state and allows GET recovery via Muat Ulang", async () => {
    vi.mocked(getSessionDetail).mockRejectedValueOnce(new Error("Internal server error 500 JSON fail"));
    render(<SessionAnalysisView sessionId={sessionId} />);

    expect(await screen.findByRole("heading", { name: "Analisis belum dapat dimuat" })).toBeInTheDocument();
    expect(screen.getByText("Data analisis belum dapat dimuat. Silakan periksa kembali.")).toBeInTheDocument();
    expect(screen.queryByText("Internal server error")).toBeNull();

    vi.mocked(getSessionDetail).mockResolvedValueOnce(detail() as never);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Muat Ulang" }));

    expect(await screen.findByText("Ringkasan awal yang dipertahankan")).toBeInTheDocument();
    expect(getSessionDetail).toHaveBeenCalledTimes(2);
  });

  it("clears Session A content immediately and ignores late Session A success when sessionId changes to B", async () => {
    let resolveA: (value: unknown) => void = () => {};
    const promiseA = new Promise((resolve) => {
      resolveA = resolve;
    });

    vi.mocked(getSessionDetail).mockImplementation((id) => {
      if (id === "session-a") return promiseA as never;
      return Promise.resolve(
        detail(
          { initial_analysis: request("initial-b", "INITIAL_ANALYSIS", "2026-01-02T00:00:00Z", { ...initial, summary: "Ringkasan B" }, {}, "session-b") },
          "session-b",
        ),
      ) as never;
    });

    const { rerender } = render(<SessionAnalysisView sessionId="session-a" />);
    expect(screen.getByRole("status")).toHaveTextContent("Memuat analisis…");

    rerender(<SessionAnalysisView sessionId="session-b" />);

    await screen.findByText("Ringkasan B");

    resolveA(
      detail(
        { initial_analysis: request("initial-a", "INITIAL_ANALYSIS", "2026-01-01T00:00:00Z", { ...initial, summary: "Ringkasan A Late" }, {}, "session-a") },
        "session-a",
      ),
    );

    await waitFor(() => {
      expect(screen.queryByText("Ringkasan A Late")).toBeNull();
    });
    expect(screen.getByText("Ringkasan B")).toBeInTheDocument();
  });

  it("keeps a usable record with unknown fields and skips absent optional values without inventing data", async () => {
    vi.mocked(getSessionDetail).mockResolvedValue(detail({ initial_analysis: request("initial", "INITIAL_ANALYSIS", "2026-01-01T00:00:00Z", { summary: "Hanya ringkasan", extra_payload: "ignored" }) }) as never);
    render(<SessionAnalysisView sessionId={sessionId} />);
    expect(await screen.findByText("Hanya ringkasan")).toBeInTheDocument();
    expect(screen.queryByText("ignored")).toBeNull();
    expect(screen.queryByText("0")).toBeNull();
  });

  it("excludes unsupported, wrong-session, and incomplete records", async () => {
    vi.mocked(getSessionDetail).mockResolvedValue(detail({ wait_updates: [request("other", "WAIT_UPDATE", "2026-04-01T00:00:00Z", wait, { session_id: "other" }), request("pending", "WAIT_UPDATE", "2026-04-02T00:00:00Z", wait, { status: "PENDING" })], position_updates: [request("unsupported", "OTHER", "2026-04-03T00:00:00Z", { summary: "Tidak boleh" })] }) as never);
    render(<SessionAnalysisView sessionId={sessionId} />);
    await screen.findByText("Ringkasan awal yang dipertahankan");
    expect(screen.queryByText("Pembaruan WAIT")).toBeNull();
    expect(screen.queryByText("Tidak boleh")).toBeNull();
  });

  it("shows the safe unavailable state for a completed payload with no known displayable field", async () => {
    vi.mocked(getSessionDetail).mockResolvedValue(detail({ initial_analysis: request("initial", "INITIAL_ANALYSIS", "2026-01-01T00:00:00Z", { internal_debug: "only unknown" }) }) as never);
    render(<SessionAnalysisView sessionId={sessionId} />);
    expect(await screen.findByRole("heading", { name: "Hasil analisis tidak dapat ditampilkan" })).toBeInTheDocument();
    expect(screen.getByText("Data analisis ini belum dapat ditampilkan dengan baik.")).toBeInTheDocument();
    expect(screen.queryByText("only unknown")).toBeNull();
  });

  it("contains no generic payload rendering, decisions, raw JSON, mutation, or polling", () => {
    const source = readFileSync("src/features/sessions/session-analysis-view.tsx", "utf8");
    expect(source).not.toMatch(/Object\.entries\(.*payload|JSON\.stringify|fetch\(|POST|PUT|PATCH|DELETE|setInterval|setTimeout|localStorage|sessionStorage|SessionWorkspace|JobStatus|retryInitialAnalysis/);
    expect(source).not.toMatch(/>BUY<|>SKIP</);
  });
});
