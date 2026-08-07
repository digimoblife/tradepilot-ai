import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useRouteSession } from "@/features/sessions/use-route-session";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import type { CurrentStep, SessionDetailAggregate, TradeSession } from "@/features/trade-workspace/types";

import { SessionHistoryView, buildSessionHistoryEvents } from "./session-history-view";

vi.mock("next/navigation", () => ({
  usePathname: () => "/sessions/session-hist-123/history",
}));

vi.mock("@/features/sessions/use-route-session", () => ({
  useRouteSession: vi.fn(),
}));

vi.mock("@/features/sessions/use-session-current-step", () => ({
  useSessionCurrentStep: vi.fn(),
}));

const sessionId = "session-hist-123";

function makeSession(): TradeSession {
  return {
    id: sessionId,
    ticker: "BBRI",
    company_name: "Bank Rakyat Indonesia",
    status: "CLOSED",
    note: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T15:00:00Z",
    closed_at: "2026-01-01T15:00:00Z",
    archived_at: null,
  };
}

function makeFullDetail(): SessionDetailAggregate {
  return {
    session: {
      id: sessionId,
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      status: "CLOSED",
      initial_note: "Catatan sesi awal",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T15:00:00Z",
      closed_at: "2026-01-01T15:00:00Z",
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
      request_id: "req-init",
      status: "COMPLETED",
      completed_at: "2026-01-01T02:00:00Z",
    },
    decisions: [
      {
        decision_id: "dec-wait",
        decision: "WAIT",
        reason: null,
        note: "Tunggu konfirmasi tren",
        created_at: "2026-01-01T03:00:00Z",
      },
      {
        decision_id: "dec-buy",
        decision: "BUY",
        reason: null,
        note: "Breakout terkonfirmasi",
        created_at: "2026-01-01T06:00:00Z",
      },
    ],
    wait_updates: [
      {
        request_id: "req-wait-1",
        status: "COMPLETED",
        observation_period: "MORNING",
        completed_at: "2026-01-01T04:00:00Z",
      },
      {
        request_id: "req-wait-2",
        status: "COMPLETED",
        observation_period: "MIDDAY",
        completed_at: "2026-01-01T05:00:00Z",
      },
    ],
    position: {
      status: "CLOSED",
      entry_price: 5000,
      quantity: 100,
      stop_loss: 4800,
      target_price: 5500,
      entry_timestamp: "2026-01-01T07:00:00Z",
      note: "Posisi beli",
      closed_at: "2026-01-01T15:00:00Z",
    },
    position_updates: [
      {
        request_id: "req-pos-1",
        status: "COMPLETED",
        observation_period: "AFTERNOON",
        completed_at: "2026-01-01T10:00:00Z",
      },
    ],
    closure: {
      closure_id: "cls-1",
      close_price: 5400,
      close_timestamp: "2026-01-01T15:00:00Z",
      close_reason: "Target harga tercapai",
      note: "Penutupan sukses",
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
    latest_analysis: null,
    recent_activity: [],
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
      code: "TERMINAL_CLOSED",
      mode: "READ_ONLY",
      workflow_actions: [],
      active_request: null,
      failed_request: null,
      read_only: true,
    },
    detail: makeFullDetail(),
    refetch: vi.fn().mockResolvedValue({}),
  });
});

describe("buildSessionHistoryEvents", () => {
  it("orders events in ascending chronological order (oldest first, newest last)", () => {
    const events = buildSessionHistoryEvents(makeFullDetail());
    expect(events.length).toBe(10);

    const titles = events.map((e) => e.title);
    expect(titles).toEqual([
      "Sesi Dibuat",
      "Bukti Awal Diunggah",
      "Analisis Awal Selesai",
      "Keputusan WAIT",
      "WAIT Update Selesai",
      "WAIT Update Selesai",
      "Keputusan BUY",
      "Posisi Dibuka",
      "Position Update Selesai",
      "Posisi Ditutup",
    ]);
  });

  it("preserves multiple WAIT Updates and Position Updates separately", () => {
    const events = buildSessionHistoryEvents(makeFullDetail());
    const waitUpdates = events.filter((e) => e.type === "WAIT_UPDATE_COMPLETED");
    const posUpdates = events.filter((e) => e.type === "POSITION_UPDATE_COMPLETED");

    expect(waitUpdates.length).toBe(2);
    expect(posUpdates.length).toBe(1);
    expect(waitUpdates[0].id).not.toBe(waitUpdates[1].id);
  });

  it("correctly builds SKIP path history for skipped session", () => {
    const detail = makeFullDetail();
    detail.session.status = "CLOSED_SKIPPED";
    detail.decisions = [
      {
        decision_id: "dec-skip",
        decision: "SKIP",
        reason: "RISK_TOO_HIGH",
        note: "Ratio risk reward jelek",
        created_at: "2026-01-01T03:00:00Z",
      },
    ];
    detail.position = null;
    detail.closure = null;
    detail.wait_updates = [];
    detail.position_updates = [];

    const events = buildSessionHistoryEvents(detail);
    const titles = events.map((e) => e.title);

    expect(titles).toEqual([
      "Sesi Dibuat",
      "Bukti Awal Diunggah",
      "Analisis Awal Selesai",
      "Keputusan SKIP",
    ]);

    const skipEvent = events.find((e) => e.type === "SKIP_DECISION");
    expect(skipEvent?.facts?.[0].value).toBe("Risiko Terlalu Tinggi");
  });
});

describe("SessionHistoryView", () => {
  it("renders header, permanent navigation, title, and chronological timeline stream", () => {
    render(<SessionHistoryView sessionId={sessionId} />);

    expect(screen.getByRole("heading", { name: "BBRI" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Riwayat Sesi" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Kembali ke Ringkasan" })).toHaveAttribute(
      "href",
      `/sessions/${sessionId}`,
    );

    expect(screen.getByText("Sesi Dibuat")).toBeInTheDocument();
    expect(screen.getByText("Posisi Ditutup")).toBeInTheDocument();
  });

  it("renders links to Analysis for analysis-related events", () => {
    render(<SessionHistoryView sessionId={sessionId} />);

    const analysisLinks = screen.getAllByRole("link", { name: "Lihat Hasil Analisis →" });
    expect(analysisLinks.length).toBeGreaterThan(0);
    expect(analysisLinks[0]).toHaveAttribute("href", `/sessions/${sessionId}/analysis`);
  });

  it("displays text badge for archived sessions without inserting Archive events into timeline", () => {
    const detail = makeFullDetail();
    detail.session.archived_at = "2026-01-02T00:00:00Z";

    vi.mocked(useRouteSession).mockReturnValue({
      status: "success",
      session: { ...makeSession(), archived_at: "2026-01-02T00:00:00Z" },
    });

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
      detail,
      refetch: vi.fn().mockResolvedValue({}),
    });

    render(<SessionHistoryView sessionId={sessionId} />);

    expect(screen.getByText("Diarsipkan")).toBeInTheDocument();
    expect(screen.queryByText("Sesi Diarsipkan")).toBeNull();
  });

  it("renders controlled empty state when no events exist", () => {
    const emptyDetail = makeFullDetail();
    emptyDetail.session.created_at = "";
    emptyDetail.initial_evidence = [];
    emptyDetail.initial_analysis = null;
    emptyDetail.decisions = [];
    emptyDetail.wait_updates = [];
    emptyDetail.position = null;
    emptyDetail.position_updates = [];
    emptyDetail.closure = null;

    vi.mocked(useSessionCurrentStep).mockReturnValue({
      status: "success",
      currentStep: {
        code: "INITIAL_EVIDENCE",
        mode: "ACTIONABLE",
        workflow_actions: [],
        active_request: null,
        failed_request: null,
        read_only: false,
      },
      detail: emptyDetail,
      refetch: vi.fn().mockResolvedValue({ status: "success", currentStep: {} as unknown as CurrentStep, detail: emptyDetail }),
    });

    render(<SessionHistoryView sessionId={sessionId} />);

    expect(screen.getByRole("heading", { name: "Riwayat belum tersedia" })).toBeInTheDocument();
    expect(screen.getByText("Belum ada aktivitas yang tercatat untuk sesi ini.")).toBeInTheDocument();
  });

  it("renders sanitized error state with GET-only retry button on fetch failure", () => {
    vi.mocked(useSessionCurrentStep).mockReturnValue({
      status: "unavailable",
      refetch: vi.fn().mockResolvedValue({ status: "unavailable" }),
    });

    render(<SessionHistoryView sessionId={sessionId} />);

    expect(screen.getByRole("heading", { name: "Riwayat belum dapat dimuat" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Muat Ulang" })).toBeInTheDocument();
  });

  it("exposes no trading action form inputs or submit buttons", () => {
    render(<SessionHistoryView sessionId={sessionId} />);

    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("form")).toBeNull();
  });
});
