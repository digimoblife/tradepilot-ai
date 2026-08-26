import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SessionDetailHeader } from "@/features/sessions/session-detail-header";
import { SessionTerminalSummary } from "@/features/sessions/session-terminal-summary";
import type { SessionDetailAggregate, TradeSession } from "@/features/trade-workspace/types";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/sessions/sess-archived-closed",
}));

const archivedClosedSession: TradeSession = {
  id: "sess-archived-closed",
  ticker: "BBRI",
  company_name: "Bank Rakyat Indonesia",
  status: "CLOSED",
  note: "Catatan awal BBRI",
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T12:00:00Z",
  closed_at: "2026-08-01T12:00:00Z",
  archived_at: "2026-08-02T10:00:00Z",
};

const archivedSkippedSession: TradeSession = {
  id: "sess-archived-skipped",
  ticker: "TLKM",
  company_name: "PT Telkom Indonesia Tbk",
  status: "CLOSED_SKIPPED",
  note: "Catatan awal TLKM",
  created_at: "2026-08-02T00:00:00Z",
  updated_at: "2026-08-02T15:00:00Z",
  closed_at: "2026-08-02T15:00:00Z",
  archived_at: "2026-08-03T09:00:00Z",
};

function makeArchivedClosedDetail(): SessionDetailAggregate {
  return {
    session: {
      ...archivedClosedSession,
      initial_note: archivedClosedSession.note,
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
        decision_id: "dec-1",
        decision: "BUY",
        reason: null,
        note: "Buy setup",
        created_at: "2026-08-01T01:00:00Z",
      },
    ],
    position: {
      id: "pos-1",
      entry_price: 5000,
      quantity: 100,
      stop_loss: 4800,
      target_price: 5500,
      entry_timestamp: "2026-08-01T01:05:00Z",
    },
    closure: {
      id: "cls-1",
      close_price: 5400,
      close_reason: "Target profit tercapai",
      note: "Profit taking",
      close_timestamp: "2026-08-01T12:00:00Z",
    },
    initial_evidence: [],
    initial_analysis: null,
    wait_updates: [],
    position_updates: [],
    latest_analysis: null,
    recent_activity: [],
  };
}

function makeArchivedSkippedDetail(): SessionDetailAggregate {
  return {
    session: {
      ...archivedSkippedSession,
      initial_note: archivedSkippedSession.note,
    },
    current_step: {
      code: "TERMINAL_SKIPPED",
      mode: "READ_ONLY",
      workflow_actions: [],
      active_request: null,
      failed_request: null,
      read_only: true,
    },
    decisions: [
      {
        decision_id: "dec-skip-1",
        decision: "SKIP",
        reason: "RISK_TOO_HIGH",
        note: "Risk reward ratio poor",
        created_at: "2026-08-02T15:00:00Z",
      },
    ],
    position: null,
    closure: null,
    initial_evidence: [],
    initial_analysis: null,
    wait_updates: [],
    position_updates: [],
    latest_analysis: null,
    recent_activity: [],
  };
}

describe("UX6.3 - Archived Session Read-Only Detail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders direct archived CLOSED session detail with archive metadata, readable facts, and Return to Archive list link", () => {
    render(
      <>
        <SessionDetailHeader session={archivedClosedSession} />
        <SessionTerminalSummary sessionId={archivedClosedSession.id} detail={makeArchivedClosedDetail()} />
      </>,
    );

    expect(screen.getByRole("heading", { name: "BBRI" })).toBeInTheDocument();
    expect(screen.getByText("Bank Rakyat Indonesia")).toBeInTheDocument();
    expect(screen.getByText("Selesai")).toBeInTheDocument();

    expect(screen.getByText("Sesi ini telah diarsipkan.")).toBeInTheDocument();
    expect(screen.getByText(/historis hanya-baca/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kembali ke Arsip" })).toHaveAttribute(
      "href",
      "/sessions/archived",
    );

    expect(screen.getByText("5.400")).toBeInTheDocument();
    expect(screen.getByText("Target profit tercapai")).toBeInTheDocument();
    expect(screen.getByText("Profit taking")).toBeInTheDocument();
    expect(screen.getByText("5.000")).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Arsipkan Sesi" })).toBeNull();
  });

  it("renders direct archived CLOSED_SKIPPED session detail with SKIP facts, archive metadata, and Return to Archive list link", () => {
    render(
      <>
        <SessionDetailHeader session={archivedSkippedSession} />
        <SessionTerminalSummary sessionId={archivedSkippedSession.id} detail={makeArchivedSkippedDetail()} />
      </>,
    );

    expect(screen.getByRole("heading", { name: "TLKM" })).toBeInTheDocument();
    expect(screen.getByText("PT Telkom Indonesia Tbk")).toBeInTheDocument();
    expect(screen.getByText("Dilewati")).toBeInTheDocument();

    expect(screen.getByText("Sesi ini telah diarsipkan.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kembali ke Arsip" })).toHaveAttribute(
      "href",
      "/sessions/archived",
    );

    expect(screen.getByText("Risiko Terlalu Tinggi")).toBeInTheDocument();
    expect(screen.getByText("Risk reward ratio poor")).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Arsipkan Sesi" })).toBeNull();
  });

  it("exposes zero trading actions, session-flow buttons, or Restore mutation controls in archived detail", () => {
    render(
      <>
        <SessionDetailHeader session={archivedClosedSession} />
        <SessionTerminalSummary sessionId={archivedClosedSession.id} detail={makeArchivedClosedDetail()} />
      </>,
    );

    expect(screen.queryByText("BUY")).toBeNull();
    expect(screen.queryByText("WAIT")).toBeNull();
    expect(screen.queryByText("SKIP")).toBeNull();
    expect(screen.queryByText("Kirim Bukti Awal")).toBeNull();
    expect(screen.queryByText("Pembaruan WAIT")).toBeNull();
    expect(screen.queryByText("Pembaruan Posisi")).toBeNull();
    expect(screen.queryByText("Tutup Posisi")).toBeNull();
    expect(screen.getByRole("button", { name: "Kembalikan ke Daftar" })).toBeInTheDocument();
  });
});
