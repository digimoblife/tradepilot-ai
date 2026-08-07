import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CloseActionRoute } from "@/features/sessions/close-action-route";
import { InitialEvidenceActionRoute } from "@/features/sessions/initial-evidence-action-route";
import { PositionUpdateActionRoute } from "@/features/sessions/position-update-action-route";
import { SessionAnalysisView } from "@/features/sessions/session-analysis-view";
import { SessionCurrentStepSection } from "@/features/sessions/session-current-step-section";
import { SessionHistoryView, buildSessionHistoryEvents } from "@/features/sessions/session-history-view";
import { SessionTerminalSummary } from "@/features/sessions/session-terminal-summary";
import { WaitUpdateActionRoute } from "@/features/sessions/wait-update-action-route";
import { useRouteSession } from "@/features/sessions/use-route-session";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import { getSessionDetail } from "@/features/trade-workspace/api";
import type { SessionDetailAggregate, TradeSession } from "@/features/trade-workspace/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  usePathname: () => "/sessions/session-gate-123",
}));

vi.mock("@/features/sessions/use-route-session", () => ({
  useRouteSession: vi.fn(),
}));

vi.mock("@/features/sessions/use-session-current-step", () => ({
  useSessionCurrentStep: vi.fn(),
}));

vi.mock("@/features/trade-workspace/api", () => ({
  getSessionDetail: vi.fn(),
}));

const sessionId = "session-gate-123";

function makeSession(overrides: Partial<TradeSession> = {}): TradeSession {
  return {
    id: sessionId,
    ticker: "BBRI",
    company_name: "Bank Rakyat Indonesia",
    status: "OPEN_POSITION",
    note: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T12:00:00Z",
    closed_at: null,
    archived_at: null,
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
      initial_note: "Initial note",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T12:00:00Z",
      closed_at: null,
      archived_at: null,
    },
    initial_evidence: [
      {
        id: "ev-1",
        evidence_type: "ORDERBOOK",
        original_filename: "orderbook.png",
        uploaded_at: "2026-01-01T01:00:00Z",
      },
    ],
    initial_analysis: {
      request_id: "req-1",
      session_id: sessionId,
      analysis_type: "INITIAL_ANALYSIS",
      status: "COMPLETED",
      completed_at: "2026-01-01T02:00:00Z",
      processed_response: {
        summary: "Ringkasan awal yang dipertahankan",
        orderbook_analysis: "Bid kuat",
        three_month_chart_analysis: "Tren tiga bulan",
        six_month_chart_analysis: "Tren enam bulan",
        support: { low: 4800, high: 4900, note: "Area support" },
        resistance: { low: 5400, high: 5500, note: "Area resistance" },
        entry_area: { low: 4950, high: 5050, note: "Area entry" },
        stop_recommendation: { level: 4800, note: "Stop" },
        target_recommendation: { level: 5500, note: "Target" },
        probabilities: { upside: 0.6, downside: 0.4 },
        risks: ["Volatilitas"],
        trading_plan: "Rencana bertahap",
        conclusion: "Tetap disiplin",
      },
    },
    decisions: [
      {
        decision_id: "dec-1",
        decision: "BUY",
        reason: null,
        note: "Buy signal",
        created_at: "2026-01-01T03:00:00Z",
      },
    ],
    wait_updates: [],
    position: {
      status: "OPEN",
      entry_price: 5000,
      quantity: 100,
      stop_loss: 4800,
      target_price: 5500,
      entry_timestamp: "2026-01-01T03:00:00Z",
      note: "Bought 100 shares",
      closed_at: null,
    },
    position_updates: [
      {
        request_id: "req-pos-1",
        session_id: sessionId,
        analysis_type: "POSITION_UPDATE",
        status: "COMPLETED",
        observation_period: "MIDDAY",
        completed_at: "2026-01-01T08:00:00Z",
      },
    ],
    closure: null,
    current_step: {
      code: "POSITION_MONITORING",
      mode: "ACTIONABLE",
      workflow_actions: ["SUBMIT_POSITION_UPDATE", "CLOSE"],
      active_request: null,
      failed_request: null,
      read_only: false,
    },
    latest_analysis: {
      analysis_type: "POSITION_UPDATE",
      completed_at: "2026-01-01T08:00:00Z",
      has_result: true,
    },
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
    currentStep: {
      code: "POSITION_MONITORING",
      mode: "ACTIONABLE",
      workflow_actions: ["SUBMIT_POSITION_UPDATE", "CLOSE"],
      active_request: null,
      failed_request: null,
      read_only: false,
    },
    detail: makeDetail(),
    refetch: vi.fn().mockResolvedValue({ status: "success" }),
  });

  vi.mocked(getSessionDetail).mockResolvedValue(makeDetail());
});

describe("Guided Lifecycle Flow (UX5-G)", () => {
  describe("Flow A: DRAFT -> Initial Evidence -> BUY -> Position Update -> Close -> CLOSED", () => {
    it("renders Open Position summary with Position Update and Close entry actions", () => {
      render(<SessionCurrentStepSection sessionId={sessionId} />);

      expect(screen.getByRole("heading", { name: "Posisi Terbuka" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Kirim Pembaruan Posisi" })).toHaveAttribute(
        "href",
        `/sessions/${sessionId}/position-update`,
      );
      expect(screen.getByRole("link", { name: "Tutup Posisi" })).toHaveAttribute(
        "href",
        `/sessions/${sessionId}/close`,
      );
    });

    it("renders terminal read-only view when session reaches CLOSED state", () => {
      const closedDetail = makeDetail({
        session: {
          id: sessionId,
          ticker: "BBRI",
          company_name: "Bank Rakyat Indonesia",
          status: "CLOSED",
          initial_note: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T15:00:00Z",
          closed_at: "2026-01-01T15:00:00Z",
          archived_at: null,
        },
        position: {
          status: "CLOSED",
          entry_price: 5000,
          quantity: 100,
          stop_loss: 4800,
          target_price: 5500,
          entry_timestamp: "2026-01-01T03:00:00Z",
          note: null,
          closed_at: "2026-01-01T15:00:00Z",
        },
        closure: {
          closure_id: "cls-1",
          close_price: 5400,
          close_timestamp: "2026-01-01T15:00:00Z",
          close_reason: "Target harga tercapai",
          note: "Penutupan berelaba",
          realized_profit_loss: 40000,
        },
        current_step: {
          code: "TERMINAL_CLOSED",
          mode: "READ_ONLY",
          workflow_actions: [],
          active_request: null,
          failed_request: null,
          read_only: true,
        },
      });

      render(<SessionTerminalSummary sessionId={sessionId} detail={closedDetail} />);

      expect(screen.getByRole("heading", { name: "Sesi Selesai" })).toBeInTheDocument();
      expect(screen.getByText("Ditutup")).toBeInTheDocument();
      expect(screen.getByText("5.400")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Lihat Analisis" })).toHaveAttribute(
        "href",
        `/sessions/${sessionId}/analysis`,
      );
      expect(screen.getByRole("link", { name: "Lihat Riwayat" })).toHaveAttribute(
        "href",
        `/sessions/${sessionId}/history`,
      );
      expect(screen.getByRole("button", { name: "Arsipkan Sesi" })).toBeInTheDocument();
    });
  });

  describe("Flow B: DRAFT -> WAIT -> WAIT Update -> BUY -> CLOSE", () => {
    it("builds correct chronological history events for WAIT -> WAIT Update -> BUY -> CLOSE", () => {
      const waitBuyDetail = makeDetail({
        decisions: [
          {
            decision_id: "dec-wait",
            decision: "WAIT",
            reason: null,
            note: "Tunggu momentum",
            created_at: "2026-01-01T03:00:00Z",
          },
          {
            decision_id: "dec-buy",
            decision: "BUY",
            reason: null,
            note: "Setup valid",
            created_at: "2026-01-01T06:00:00Z",
          },
        ],
        wait_updates: [
          {
            request_id: "req-wait-1",
            session_id: sessionId,
            analysis_type: "WAIT_UPDATE",
            status: "COMPLETED",
            observation_period: "MORNING",
            completed_at: "2026-01-01T04:00:00Z",
          },
        ],
        closure: {
          closure_id: "cls-1",
          close_price: 5400,
          close_timestamp: "2026-01-01T15:00:00Z",
          close_reason: "Target tercapai",
          note: null,
          realized_profit_loss: 40000,
        },
      });

      const events = buildSessionHistoryEvents(waitBuyDetail);
      const titles = events.map((e) => e.title);

      expect(titles).toContain("Keputusan WAIT");
      expect(titles).toContain("WAIT Update Selesai");
      expect(titles).toContain("Keputusan BUY");
      expect(titles).toContain("Posisi Dibuka");
      expect(titles).toContain("Posisi Ditutup");
    });
  });

  describe("Flow C & D: CLOSED_SKIPPED terminal journeys", () => {
    it("renders CLOSED_SKIPPED terminal summary with SKIP facts and no position or closure facts", () => {
      const skippedDetail = makeDetail({
        session: {
          id: sessionId,
          ticker: "BBRI",
          company_name: "Bank Rakyat Indonesia",
          status: "CLOSED_SKIPPED",
          initial_note: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T04:00:00Z",
          closed_at: "2026-01-01T04:00:00Z",
          archived_at: null,
        },
        decisions: [
          {
            decision_id: "dec-skip",
            decision: "SKIP",
            reason: "RISK_TOO_HIGH",
            note: "Risk reward tidak seimbang",
            created_at: "2026-01-01T04:00:00Z",
          },
        ],
        position: null,
        closure: null,
        current_step: {
          code: "TERMINAL_SKIPPED",
          mode: "READ_ONLY",
          workflow_actions: [],
          active_request: null,
          failed_request: null,
          read_only: true,
        },
      });

      render(<SessionTerminalSummary sessionId={sessionId} detail={skippedDetail} />);

      expect(screen.getByRole("heading", { name: "Sesi Dilewati" })).toBeInTheDocument();
      expect(screen.getByText("Risiko Terlalu Tinggi")).toBeInTheDocument();
      expect(screen.queryByText("Harga Penutupan")).toBeNull();
      expect(screen.queryByText("Harga Masuk")).toBeNull();
    });
  });

  describe("Direct URL Eligibility & Focused Action Route Guards", () => {
    it("blocks Close action route when session is in terminal state", () => {
      vi.mocked(useSessionCurrentStep).mockReturnValue({
        status: "success",
        currentStep: {
          code: "TERMINAL_CLOSED",
          mode: "READ_ONLY",
          workflow_actions: [],
          active_request: null,
          failed_request: null,
          read_only: true,
        },
        detail: makeDetail({
          session: {
            id: sessionId,
            ticker: "BBRI",
            company_name: "Bank Rakyat Indonesia",
            status: "CLOSED",
            initial_note: null,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T15:00:00Z",
            closed_at: "2026-01-01T15:00:00Z",
          },
        }),
        refetch: vi.fn().mockResolvedValue({ status: "success" }),
      });

      render(<CloseActionRoute sessionId={sessionId} />);

      expect(screen.getByRole("heading", { name: "Penutupan posisi tidak tersedia" })).toBeInTheDocument();
      expect(screen.getByText("Sesi ini tidak dapat ditutup pada tahap saat ini.")).toBeInTheDocument();
      expect(screen.queryByLabelText(/Harga Penutupan/i)).toBeNull();
    });

    it("blocks Position Update action route when session is in terminal state", () => {
      vi.mocked(useSessionCurrentStep).mockReturnValue({
        status: "success",
        currentStep: {
          code: "TERMINAL_CLOSED",
          mode: "READ_ONLY",
          workflow_actions: [],
          active_request: null,
          failed_request: null,
          read_only: true,
        },
        detail: makeDetail({
          session: {
            id: sessionId,
            ticker: "BBRI",
            company_name: "Bank Rakyat Indonesia",
            status: "CLOSED",
            initial_note: null,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T15:00:00Z",
            closed_at: "2026-01-01T15:00:00Z",
          },
        }),
        refetch: vi.fn().mockResolvedValue({ status: "success" }),
      });

      render(<PositionUpdateActionRoute sessionId={sessionId} />);

      expect(screen.getByRole("heading", { name: "Position Update tidak tersedia" })).toBeInTheDocument();
      expect(screen.queryByLabelText(/Harga Saat Ini/i)).toBeNull();
    });

    it("blocks WAIT Update action route when session is in terminal state", () => {
      vi.mocked(useSessionCurrentStep).mockReturnValue({
        status: "success",
        currentStep: {
          code: "TERMINAL_CLOSED",
          mode: "READ_ONLY",
          workflow_actions: [],
          active_request: null,
          failed_request: null,
          read_only: true,
        },
        detail: makeDetail({
          session: {
            id: sessionId,
            ticker: "BBRI",
            company_name: "Bank Rakyat Indonesia",
            status: "CLOSED",
            initial_note: null,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T15:00:00Z",
            closed_at: "2026-01-01T15:00:00Z",
          },
        }),
        refetch: vi.fn().mockResolvedValue({ status: "success" }),
      });

      render(<WaitUpdateActionRoute sessionId={sessionId} />);

      expect(screen.getByRole("heading", { name: "WAIT Update tidak tersedia" })).toBeInTheDocument();
    });

    it("blocks Initial Evidence action route when session is in terminal state", () => {
      vi.mocked(useSessionCurrentStep).mockReturnValue({
        status: "success",
        currentStep: {
          code: "TERMINAL_CLOSED",
          mode: "READ_ONLY",
          workflow_actions: [],
          active_request: null,
          failed_request: null,
          read_only: true,
        },
        detail: makeDetail({
          session: {
            id: sessionId,
            ticker: "BBRI",
            company_name: "Bank Rakyat Indonesia",
            status: "CLOSED",
            initial_note: null,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T15:00:00Z",
            closed_at: "2026-01-01T15:00:00Z",
          },
        }),
        refetch: vi.fn().mockResolvedValue({ status: "success" }),
      });

      render(<InitialEvidenceActionRoute sessionId={sessionId} />);

      expect(screen.getByRole("heading", { name: "Bukti Awal Tidak Tersedia" })).toBeInTheDocument();
    });
  });

  describe("Analysis and History Read-Only View Integration", () => {
    it("renders Analysis view in read-only mode for completed analysis records", async () => {
      render(<SessionAnalysisView sessionId={sessionId} />);

      expect(await screen.findByRole("heading", { name: "Analisis" })).toBeInTheDocument();
      expect(screen.queryByRole("form")).toBeNull();
    });

    it("renders History view in read-only mode with complete chronological events", () => {
      render(<SessionHistoryView sessionId={sessionId} />);

      expect(screen.getByRole("heading", { name: "BBRI" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Riwayat Sesi" })).toBeInTheDocument();
      expect(screen.queryByRole("form")).toBeNull();
    });
  });
});
