import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionWorkspace } from "./workspace";
import {
  buyDecision,
  getAvailableActions,
  getSession,
  readInitialAnalysis,
  skipDecision,
  waitDecision,
} from "./api";
import type { DecisionAvailability, TradeSession } from "./types";

vi.mock("./api", () => ({
  buyDecision: vi.fn(),
  getAvailableActions: vi.fn(),
  getSession: vi.fn(),
  readInitialAnalysis: vi.fn(),
  retryInitialAnalysis: vi.fn(),
  skipDecision: vi.fn(),
  submitInitialAnalysis: vi.fn(),
  uploadInitialEvidence: vi.fn(),
  waitDecision: vi.fn(),
}));

const analyzed: TradeSession = {
  id: "session-a",
  ticker: "BBRI",
  company_name: "Bank BRI",
  status: "ANALYZED",
  note: null,
  created_at: "2026-07-30T00:00:00Z",
  updated_at: "2026-07-30T00:00:00Z",
  closed_at: null,
};

const availability: DecisionAvailability = {
  session_id: "session-a",
  session_status: "ANALYZED" as const,
  available_actions: ["BUY", "WAIT", "SKIP"],
};

function renderWorkspace(session: TradeSession = analyzed) {
  vi.mocked(getSession).mockResolvedValue(session);
  vi.mocked(getAvailableActions).mockResolvedValue({
    ...availability,
    session_id: session.id,
    session_status: session.status,
    available_actions: session.status === "OPEN_POSITION" ? ["CLOSE"] : availability.available_actions,
  });
  vi.mocked(readInitialAnalysis).mockRejectedValue(new Error("not requested"));
  return render(<SessionWorkspace sessionId={session.id} knownEvidence={[]} onEvidence={vi.fn()} />);
}

beforeEach(() => {
  vi.resetAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("rebuild decision UI", () => {
  it("loads selected-session actions and never activates CLOSE", async () => {
    renderWorkspace();
    expect(await screen.findByRole("button", { name: "WAIT" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Konfirmasi SKIP" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Konfirmasi BUY" })).toBeTruthy();
    expect(getAvailableActions).toHaveBeenCalledWith("session-a");

    cleanup();
    renderWorkspace({ ...analyzed, id: "session-open", status: "OPEN_POSITION" });
    await waitFor(() => expect(screen.queryByRole("button", { name: "CLOSE" })).toBeNull());
    expect(screen.queryByRole("button", { name: "Konfirmasi BUY" })).toBeNull();
  });

  it("sends WAIT without a body, prevents duplicates, and refreshes actions", async () => {
    const user = userEvent.setup();
    let resolveWait: (() => void) | undefined;
    vi.mocked(waitDecision).mockReturnValue(new Promise((resolve) => {
      resolveWait = () => resolve({
        decision_id: "wait-1",
        session_id: "session-a",
        decision_type: "WAIT",
        decision_at: "2026-07-30T00:00:00Z",
        session_status: "WAITING",
      });
    }));
    renderWorkspace();
    vi.mocked(getAvailableActions).mockResolvedValueOnce({ ...availability, session_status: "WAITING" });
    const waitButton = await screen.findByRole("button", { name: "WAIT" });
    await user.click(waitButton);
    await user.click(waitButton);
    expect(waitDecision).toHaveBeenCalledTimes(1);
    resolveWait?.();
    expect(await screen.findByRole("status")).toHaveTextContent("WAIT tersimpan");
    expect(getAvailableActions).toHaveBeenCalledTimes(2);
  });

  it("requires SKIP reason, exposes only approved reasons, and submits note exactly", async () => {
    const user = userEvent.setup();
    vi.mocked(skipDecision).mockResolvedValue({
      decision_id: "skip-1",
      session_id: "session-a",
      decision_type: "SKIP",
      reason: "OTHER",
      note: "Tidak yakin",
      decision_at: "2026-07-30T00:00:00Z",
      session_status: "CLOSED_SKIPPED",
      closed_at: "2026-07-30T00:00:00Z",
    });
    renderWorkspace();
    vi.mocked(getAvailableActions).mockResolvedValueOnce({
      session_id: "session-a",
      session_status: "CLOSED_SKIPPED",
      available_actions: [],
    });
    await screen.findByRole("combobox", { name: /Alasan SKIP/ });
    await user.click(screen.getByRole("button", { name: "Konfirmasi SKIP" }));
    expect(skipDecision).not.toHaveBeenCalled();
    const reason = screen.getByRole("combobox", { name: /Alasan SKIP/ });
    expect(reason.querySelectorAll("option")).toHaveLength(8);
    await user.selectOptions(reason, "OTHER");
    await user.type(screen.getByLabelText("Catatan SKIP (opsional)"), "Tidak yakin");
    await user.click(screen.getByRole("button", { name: "Konfirmasi SKIP" }));
    await waitFor(() => expect(skipDecision).toHaveBeenCalledWith("session-a", { reason: "OTHER", note: "Tidak yakin" }));
    expect(await screen.findByRole("status")).toHaveTextContent("CLOSED_SKIPPED");
  });

  it("sends exact BUY facts and displays the returned open position", async () => {
    const user = userEvent.setup();
    vi.mocked(buyDecision).mockResolvedValue({
      decision_id: "buy-1",
      session_id: "session-a",
      decision_type: "BUY",
      decision_at: "2026-07-30T00:00:00Z",
      position_id: "position-1",
      position_status: "OPEN",
      entry_price: "101.2345",
      entry_timestamp: "2026-07-30T09:15:00Z",
      quantity: "12.5",
      stop_loss: "95.125",
      target_price: "120.75",
      note: "confirmed",
      session_status: "OPEN_POSITION",
    });
    renderWorkspace();
    vi.mocked(getSession).mockResolvedValueOnce({ ...analyzed, status: "OPEN_POSITION" });
    vi.mocked(getAvailableActions).mockResolvedValueOnce({ session_id: "session-a", session_status: "OPEN_POSITION", available_actions: ["CLOSE"] });
    await screen.findByRole("button", { name: "Konfirmasi BUY" });
    const values = {
      "Harga entry": "101.2345",
      "Waktu entry": "2026-07-30T09:15:00Z",
      Kuantitas: "12.5",
      "Stop loss": "95.125",
      "Target price": "120.75",
    };
    for (const [label, value] of Object.entries(values)) await user.type(screen.getByLabelText(label), value);
    await user.type(screen.getByLabelText("Catatan BUY (opsional)"), "confirmed");
    await user.click(screen.getByRole("button", { name: "Konfirmasi BUY" }));
    await waitFor(() => expect(buyDecision).toHaveBeenCalledWith("session-a", {
      entry_price: "101.2345",
      entry_timestamp: "2026-07-30T09:15:00Z",
      quantity: "12.5",
      stop_loss: "95.125",
      target_price: "120.75",
      note: "confirmed",
    }));
    expect(await screen.findByRole("heading", { name: "Posisi OPEN" })).toBeTruthy();
    expect(screen.getByText("101.2345")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Konfirmasi BUY" })).toBeNull();
  });
});
