import { readFileSync } from "node:fs";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SessionDetailAggregate } from "@/features/trade-workspace/types";
import { SessionWaitingSummary } from "./session-waiting-summary";

const sessionId = "session-wait-123";

function makeDetail(overrides: Partial<SessionDetailAggregate> = {}): SessionDetailAggregate {
  return {
    session: {
      id: sessionId,
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      status: "WAITING",
      initial_note: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      closed_at: null,
    },
    initial_evidence: [],
    initial_analysis: {},
    decisions: [
      {
        decision_id: "dec-1",
        decision: "WAIT",
        created_at: "2026-01-01T00:00:00Z",
      },
    ],
    wait_updates: [],
    position: null,
    position_updates: [],
    closure: null,
    current_step: {
      code: "WAIT_UPDATE",
      mode: "ACTIONABLE",
      workflow_actions: ["SUBMIT_WAIT_UPDATE", "BUY", "WAIT", "SKIP"],
      active_request: null,
      failed_request: null,
      read_only: false,
    },
    latest_analysis: {
      analysis_type: "INITIAL_ANALYSIS",
      completed_at: "2026-01-01T00:00:00Z",
      has_result: true,
    },
    recent_activity: [],
    ...overrides,
  };
}

describe("SessionWaitingSummary", () => {
  it("renders WAITING summary card when session is in WAITING state", () => {
    render(<SessionWaitingSummary sessionId={sessionId} detail={makeDetail()} />);

    expect(screen.getByRole("heading", { name: "Menunggu Update" })).toBeInTheDocument();
    expect(
      screen.getByText("Sesi ini sedang menunggu data orderbook terbaru sebelum analisis berikutnya dilakukan."),
    ).toBeInTheDocument();
    expect(screen.getByText("Belum ada posisi yang dibuka.")).toBeInTheDocument();
  });

  it("does not render when session is not in WAITING state or WAIT_UPDATE step", () => {
    const detail = makeDetail({
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
      current_step: {
        code: "POSITION_MONITORING",
        mode: "ACTIONABLE",
        workflow_actions: ["SUBMIT_POSITION_UPDATE", "CLOSE"],
        active_request: null,
        failed_request: null,
        read_only: false,
      },
    });

    const { container } = render(<SessionWaitingSummary sessionId={sessionId} detail={detail} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders Kirim Pembaruan WAIT primary action linking to exact approved route when authorized", () => {
    render(<SessionWaitingSummary sessionId={sessionId} detail={makeDetail()} />);

    const primaryLink = screen.getByRole("link", { name: "Kirim Pembaruan WAIT" });
    expect(primaryLink).toBeInTheDocument();
    expect(primaryLink).toHaveAttribute("href", `/sessions/${sessionId}/wait-update`);
  });

  it("omits Kirim Pembaruan WAIT link when SUBMIT_WAIT_UPDATE is not authorized by backend", () => {
    const detail = makeDetail({
      current_step: {
        code: "WAIT_UPDATE",
        mode: "ACTIONABLE",
        workflow_actions: ["BUY", "WAIT", "SKIP"],
        active_request: null,
        failed_request: null,
        read_only: false,
      },
    });

    render(<SessionWaitingSummary sessionId={sessionId} detail={detail} />);

    expect(screen.queryByRole("link", { name: "Kirim Pembaruan WAIT" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Menunggu Update" })).toBeInTheDocument();
  });

  it("renders Lihat Analisis Terbaru linking to Analysis route when latest analysis has result", () => {
    render(<SessionWaitingSummary sessionId={sessionId} detail={makeDetail()} />);

    const analysisLink = screen.getByRole("link", { name: "Lihat Analisis Terbaru" });
    expect(analysisLink).toBeInTheDocument();
    expect(analysisLink).toHaveAttribute("href", `/sessions/${sessionId}/analysis`);
  });

  it("renders correctly for WAITING without prior WAIT updates", () => {
    const detail = makeDetail({ wait_updates: [] });
    render(<SessionWaitingSummary sessionId={sessionId} detail={detail} />);

    expect(screen.getByRole("heading", { name: "Menunggu Update" })).toBeInTheDocument();
    expect(screen.getByText("Belum ada posisi yang dibuka.")).toBeInTheDocument();
  });

  it("renders correctly for WAITING with prior WAIT updates", () => {
    const detail = makeDetail({
      wait_updates: [{ id: "wu-1", created_at: "2026-01-02T00:00:00Z" }],
      latest_analysis: {
        analysis_type: "WAIT_UPDATE",
        completed_at: "2026-01-02T00:00:00Z",
        has_result: true,
      },
    });
    render(<SessionWaitingSummary sessionId={sessionId} detail={detail} />);

    expect(screen.getByRole("heading", { name: "Menunggu Update" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Kirim Pembaruan WAIT" })).toBeInTheDocument();
  });

  it("does not expose Position Update or Close actions or form fields", () => {
    render(<SessionWaitingSummary sessionId={sessionId} detail={makeDetail()} />);

    expect(screen.queryByText(/Perbarui Posisi/i)).toBeNull();
    expect(screen.queryByText(/Tutup Posisi/i)).toBeNull();
    expect(screen.queryByLabelText(/Orderbook/i)).toBeNull();
    expect(screen.queryByLabelText(/Harga Saat Ini/i)).toBeNull();
  });

  it("contains no polling, localStorage, sessionStorage, or Gemini calls", () => {
    const source = readFileSync("src/features/sessions/session-waiting-summary.tsx", "utf8");
    expect(source).not.toMatch(/setInterval|setTimeout|localStorage|sessionStorage|SessionWorkspace|JobStatus/);
  });
});
