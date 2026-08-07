import { readFileSync } from "node:fs";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { CurrentStep, SessionDetailAggregate } from "@/features/trade-workspace/types";
import { SessionOpenPositionSummary } from "./session-open-position-summary";

const sessionId = "session-pos-123";

function makeDetail(overrides: Partial<SessionDetailAggregate> = {}): SessionDetailAggregate {
  return {
    session: {
      id: sessionId,
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      status: "OPEN_POSITION",
      initial_note: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      closed_at: null,
    },
    initial_evidence: [],
    initial_analysis: {},
    decisions: [],
    wait_updates: [],
    position: {
      status: "OPEN",
      entry_price: 5000,
      quantity: 100,
      stop_loss: 4800,
      target_price: 5500,
      entry_timestamp: "2026-01-01T08:00:00Z",
      note: "Catatan posisi awal",
      closed_at: null,
    },
    position_updates: [],
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
      analysis_type: "INITIAL_ANALYSIS",
      completed_at: "2026-01-01T07:55:00Z",
      has_result: true,
    },
    recent_activity: [],
    ...overrides,
  };
}

function makeStep(overrides: Partial<CurrentStep> = {}): CurrentStep {
  return {
    code: "POSITION_MONITORING",
    mode: "ACTIONABLE",
    workflow_actions: ["SUBMIT_POSITION_UPDATE", "CLOSE"],
    active_request: null,
    failed_request: null,
    read_only: false,
    ...overrides,
  };
}

describe("SessionOpenPositionSummary", () => {
  it("does not render when session status is not OPEN_POSITION", () => {
    const detail = makeDetail();
    detail.session.status = "WAITING";

    const { container } = render(
      <SessionOpenPositionSummary sessionId={sessionId} detail={detail} step={makeStep()} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("renders OPEN_POSITION heading, message, and backend position details", () => {
    render(
      <SessionOpenPositionSummary
        sessionId={sessionId}
        detail={makeDetail()}
        step={makeStep()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Posisi Terbuka" })).toBeInTheDocument();
    expect(screen.getByText("Sesi ini memiliki posisi yang sedang dipantau.")).toBeInTheDocument();

    expect(screen.getByText("Harga Entry")).toBeInTheDocument();
    expect(screen.getByText("Rp 5.000")).toBeInTheDocument();

    expect(screen.getByText("Jumlah")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();

    expect(screen.getByText("Stop Loss")).toBeInTheDocument();
    expect(screen.getByText("Rp 4.800")).toBeInTheDocument();

    expect(screen.getByText("Target Harga")).toBeInTheDocument();
    expect(screen.getByText("Rp 5.500")).toBeInTheDocument();

    expect(screen.getByText("Catatan")).toBeInTheDocument();
    expect(screen.getByText("Catatan posisi awal")).toBeInTheDocument();
  });

  it("renders safe fallback message when position object is null", () => {
    const detail = makeDetail({ position: null });

    render(
      <SessionOpenPositionSummary sessionId={sessionId} detail={detail} step={makeStep()} />,
    );

    expect(screen.getByRole("heading", { name: "Posisi Terbuka" })).toBeInTheDocument();
    expect(screen.getByText("Detail posisi belum tersedia.")).toBeInTheDocument();
  });

  it("renders Kirim Pembaruan Posisi link targeting approved route when authorized", () => {
    render(
      <SessionOpenPositionSummary
        sessionId={sessionId}
        detail={makeDetail()}
        step={makeStep()}
      />,
    );

    const updateLink = screen.getByRole("link", { name: "Kirim Pembaruan Posisi" });
    expect(updateLink).toBeInTheDocument();
    expect(updateLink).toHaveAttribute("href", `/sessions/${sessionId}/position-update`);
  });

  it("renders Tutup Posisi link targeting approved route when authorized", () => {
    render(
      <SessionOpenPositionSummary
        sessionId={sessionId}
        detail={makeDetail()}
        step={makeStep()}
      />,
    );

    const closeLink = screen.getByRole("link", { name: "Tutup Posisi" });
    expect(closeLink).toBeInTheDocument();
    expect(closeLink).toHaveAttribute("href", `/sessions/${sessionId}/close`);
  });

  it("renders Lihat Analisis Terbaru link when latest_analysis has result", () => {
    render(
      <SessionOpenPositionSummary
        sessionId={sessionId}
        detail={makeDetail()}
        step={makeStep()}
      />,
    );

    const analysisLink = screen.getByRole("link", { name: "Lihat Analisis Terbaru" });
    expect(analysisLink).toBeInTheDocument();
    expect(analysisLink).toHaveAttribute("href", `/sessions/${sessionId}/analysis`);
  });

  it("hides action links when workflow actions are not authorized or read_only is true", () => {
    const readOnlyStep = makeStep({
      workflow_actions: [],
      read_only: true,
    });

    render(
      <SessionOpenPositionSummary
        sessionId={sessionId}
        detail={makeDetail({ latest_analysis: null })}
        step={readOnlyStep}
      />,
    );

    expect(screen.queryByRole("link", { name: "Kirim Pembaruan Posisi" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Tutup Posisi" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Lihat Analisis Terbaru" })).toBeNull();
  });

  it("does not calculate P&L, unrealized gain/loss, or fetch live prices", () => {
    const source = readFileSync("src/features/sessions/session-open-position-summary.tsx", "utf8");
    expect(source).not.toMatch(/unrealized|pnl|profit_loss|fetchPrice|marketPrice/i);
  });
});
