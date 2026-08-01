import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { SessionWorkspace } from "./workspace";
import { getAvailableActions, getSession, getSessionDetail, readInitialAnalysis, readInitialEvidence } from "./api";
import type { SessionDetailAggregate, TradeSession } from "./types";

vi.mock("./api", () => ({
  getAvailableActions: vi.fn(), getSession: vi.fn(), getSessionDetail: vi.fn(),
  readInitialAnalysis: vi.fn(), readInitialEvidence: vi.fn(), readPositionUpdates: vi.fn(),
}));

const session: TradeSession = {
  id: "session-a", ticker: "BBRI", company_name: "Bank BRI", status: "CLOSED",
  note: "Catatan awal", created_at: "2026-07-30T00:00:00Z", updated_at: "2026-07-31T00:00:00Z", closed_at: "2026-07-31T01:00:00Z",
};

const aggregate: SessionDetailAggregate = {
  session: { id: session.id, ticker: session.ticker, company_name: session.company_name, status: session.status, initial_note: session.note, created_at: session.created_at, updated_at: session.updated_at, closed_at: session.closed_at },
  initial_evidence: [], initial_analysis: { processed_response: { recommended_action: "BUY" } },
  decisions: [{ decision: "BUY", created_at: "2026-07-30T02:00:00Z" }, { decision: "WAIT", created_at: "2026-07-30T03:00:00Z" }],
  wait_updates: [], position: null, position_updates: [], closure: null,
};

afterEach(() => cleanup());

describe("P10.2 session header", () => {
  it("uses the aggregate endpoint and displays authoritative session metadata and latest decision", async () => {
    vi.mocked(getSession).mockResolvedValue(session);
    vi.mocked(getSessionDetail).mockResolvedValue(aggregate);
    vi.mocked(getAvailableActions).mockResolvedValue({ session_id: session.id, session_status: "CLOSED", available_actions: [] });
    vi.mocked(readInitialAnalysis).mockRejectedValue(new Error("none"));
    vi.mocked(readInitialEvidence).mockResolvedValue({ evidence: [] });

    render(<SessionWorkspace sessionId={session.id} knownEvidence={[]} onEvidence={vi.fn()} />);

    expect(await screen.findByText("BBRI")).toBeInTheDocument();
    expect(screen.getByText("Bank BRI")).toBeInTheDocument();
    expect(screen.getAllByText("Ditutup").length).toBeGreaterThan(0);
    expect(within(screen.getByRole("banner", { name: "Ringkasan sesi" })).getByText("WAIT")).toBeInTheDocument();
    expect(within(screen.getByRole("banner", { name: "Ringkasan sesi" })).getByText(/30 Jul 2026/)).toBeInTheDocument();
    expect(within(screen.getByRole("banner", { name: "Ringkasan sesi" })).getAllByText(/31 Jul 2026/)).toHaveLength(2);
    expect(getSessionDetail).toHaveBeenCalledWith(session.id);
  });

  it("shows an empty active-decision state and no fabricated closed time", async () => {
    const draft = { ...session, status: "DRAFT" as const, closed_at: null };
    vi.mocked(getSession).mockResolvedValue(draft);
    vi.mocked(getSessionDetail).mockResolvedValue({ ...aggregate, session: { ...aggregate.session, status: "DRAFT", closed_at: null }, decisions: [] });
    vi.mocked(getAvailableActions).mockResolvedValue({ session_id: session.id, session_status: "DRAFT", available_actions: [] });
    vi.mocked(readInitialAnalysis).mockRejectedValue(new Error("none"));
    vi.mocked(readInitialEvidence).mockResolvedValue({ evidence: [] });

    render(<SessionWorkspace sessionId={session.id} knownEvidence={[]} onEvidence={vi.fn()} />);

    expect(await screen.findByText("Belum ada keputusan")).toBeInTheDocument();
    expect(within(screen.getByRole("banner", { name: "Ringkasan sesi" })).getByText("—")).toBeInTheDocument();
  });
});
