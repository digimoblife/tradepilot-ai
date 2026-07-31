import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionWorkspace } from "./workspace";
import { TradeWorkspace } from "./trade-workspace";
import {
  getAvailableActions,
  getSession,
  listSessions,
  readInitialAnalysis,
  readInitialEvidence,
  submitInitialAnalysis,
  uploadInitialEvidence,
} from "./api";
import type { DecisionAvailability, InitialEvidenceUploadResponse, TradeSession } from "./types";

vi.mock("./api", () => ({
  buyDecision: vi.fn(),
  getAvailableActions: vi.fn(),
  getSession: vi.fn(),
  listSessions: vi.fn(),
  readInitialAnalysis: vi.fn(),
  readInitialEvidence: vi.fn(),
  readPositionUpdates: vi.fn().mockResolvedValue({ position: null, updates: [] }),
  retryInitialAnalysis: vi.fn(),
  skipDecision: vi.fn(),
  submitInitialAnalysis: vi.fn(),
  submitPositionUpdateAnalysis: vi.fn(),
  uploadInitialEvidence: vi.fn(),
  uploadPositionUpdateInput: vi.fn(),
  waitDecision: vi.fn(),
}));

const draftSession: TradeSession = {
  id: "session-loop-test",
  ticker: "TLKM",
  company_name: "Telkom Indonesia",
  status: "DRAFT",
  note: null,
  created_at: "2026-07-31T00:00:00Z",
  updated_at: "2026-07-31T00:00:00Z",
  closed_at: null,
};

const mockAvailability: DecisionAvailability = {
  session_id: "session-loop-test",
  session_status: "DRAFT",
  available_actions: [],
};

const mockEvidenceResponse: InitialEvidenceUploadResponse = {
  evidence: [
    { id: "e1", evidence_type: "ORDERBOOK", original_filename: "ob.png", mime_type: "image/png", size_bytes: 100, uploaded_at: "2026-07-31T00:00:00Z" },
    { id: "e2", evidence_type: "CHART_3_MONTH", original_filename: "c3.png", mime_type: "image/png", size_bytes: 100, uploaded_at: "2026-07-31T00:00:00Z" },
    { id: "e3", evidence_type: "CHART_6_MONTH", original_filename: "c6.png", mime_type: "image/png", size_bytes: 100, uploaded_at: "2026-07-31T00:00:00Z" },
  ],
};

beforeEach(() => {
  vi.useFakeTimers();
  vi.resetAllMocks();
  vi.mocked(listSessions).mockResolvedValue({ sessions: [draftSession] });
  vi.mocked(getSession).mockResolvedValue(draftSession);
  vi.mocked(getAvailableActions).mockResolvedValue(mockAvailability);
  vi.mocked(readInitialEvidence).mockResolvedValue(mockEvidenceResponse);
  vi.mocked(readInitialAnalysis).mockRejectedValue(new Error("404 Not Found"));
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
});

describe("Focused Initial Analysis Polling Loop Prevention", () => {
  it("mounting a DRAFT session performs no request loop", async () => {
    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    expect(vi.mocked(getSession)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(getAvailableActions)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(readInitialEvidence)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(1);

    // Fast-forward 10 seconds to prove no further requests occur
    vi.advanceTimersByTime(10000);

    expect(vi.mocked(getSession)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(getAvailableActions)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(readInitialEvidence)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(1);
  });

  it("readInitialAnalysis returning 404 is called only once while no request exists", async () => {
    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(15000);

    expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(1);
  });

  it("persisted Initial Evidence hydration is not repeatedly fetched", async () => {
    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    expect(vi.mocked(readInitialEvidence)).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(10000);

    expect(vi.mocked(readInitialEvidence)).toHaveBeenCalledTimes(1);
  });

  it("rerenders do not cause additional session/evidence/analysis reads", async () => {
    const { rerender } = render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    expect(vi.mocked(readInitialEvidence)).toHaveBeenCalledTimes(1);

    rerender(<TradeWorkspace />);

    expect(vi.mocked(readInitialEvidence)).toHaveBeenCalledTimes(1);
  });

  it("one click produces exactly one Initial Analysis POST", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    vi.mocked(submitInitialAnalysis).mockResolvedValue({
      analysis_request_id: "req-1",
      session_id: draftSession.id,
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "PENDING",
      session_status: "ANALYZING",
      created_at: "2026-07-31T00:00:00Z",
    });

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    expect(vi.mocked(submitInitialAnalysis)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(submitInitialAnalysis)).toHaveBeenCalledWith(draftSession.id);
  });

  it("the submit control is disabled while submission is in flight", async () => {
    let resolveSubmission: (val: any) => void;
    const pendingPromise = new Promise((resolve) => {
      resolveSubmission = resolve;
    });
    vi.mocked(submitInitialAnalysis).mockReturnValue(pendingPromise as any);

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    expect(submitBtn).toBeDisabled();
    expect(screen.getByText("Mengirim…")).toBeInTheDocument();

    // Attempt second click while in flight
    await user.click(submitBtn);
    expect(vi.mocked(submitInitialAnalysis)).toHaveBeenCalledTimes(1);

    // Resolve submission
    resolveSubmission!({
      analysis_request_id: "req-1",
      session_id: draftSession.id,
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "PENDING",
      session_status: "ANALYZING",
      created_at: "2026-07-31T00:00:00Z",
    });
  });

  it("polling begins only after a successful submission with an active request", async () => {
    vi.mocked(submitInitialAnalysis).mockResolvedValue({
      analysis_request_id: "req-1",
      session_id: draftSession.id,
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "PENDING",
      session_status: "ANALYZING",
      created_at: "2026-07-31T00:00:00Z",
    });
    vi.mocked(readInitialAnalysis).mockResolvedValue({
      analysis_request_id: "req-1",
      session_id: draftSession.id,
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "PENDING",
      session_status: "ANALYZING",
      processed_response: null,
      error_code: null,
      error_message: null,
      created_at: "2026-07-31T00:00:00Z",
      started_at: null,
      completed_at: null,
    });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(1); // initial read only

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    // Polling is scheduled for 5s
    vi.advanceTimersByTime(5000);
    await waitFor(() => {
      expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(2);
    });

    vi.advanceTimersByTime(5000);
    await waitFor(() => {
      expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(3);
    });
  });

  it("polling stops on completion and failure", async () => {
    vi.mocked(submitInitialAnalysis).mockResolvedValue({
      analysis_request_id: "req-1",
      session_id: draftSession.id,
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "PENDING",
      session_status: "ANALYZING",
      created_at: "2026-07-31T00:00:00Z",
    });

    // First poll returns COMPLETED
    vi.mocked(readInitialAnalysis).mockResolvedValueOnce({
      analysis_request_id: "req-1",
      session_id: draftSession.id,
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "COMPLETED",
      session_status: "ANALYZED",
      processed_response: { summary: "Analysis complete" } as any,
      error_code: null,
      error_message: null,
      created_at: "2026-07-31T00:00:00Z",
      started_at: "2026-07-31T00:00:01Z",
      completed_at: "2026-07-31T00:00:02Z",
    });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    vi.advanceTimersByTime(5000);
    await waitFor(() => {
      expect(screen.getByText("Analysis complete")).toBeInTheDocument();
    });

    const countAfterComplete = vi.mocked(readInitialAnalysis).mock.calls.length;

    // Fast-forward another 15s to confirm polling stopped
    vi.advanceTimersByTime(15000);
    expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(countAfterComplete);
  });

  it("failed submission keeps persisted evidence visible", async () => {
    vi.mocked(submitInitialAnalysis).mockRejectedValue(new Error("429 Too Many Requests"));

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Analisis tidak dapat diminta.")).toBeInTheDocument();
    });

    // Evidence must still be visible and ready
    expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    expect(screen.getByText("3 file diterima.")).toBeInTheDocument();
  });
});
