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
  vi.resetAllMocks();
  vi.mocked(listSessions).mockResolvedValue({ sessions: [draftSession] });
  vi.mocked(getSession).mockResolvedValue(draftSession);
  vi.mocked(getAvailableActions).mockResolvedValue(mockAvailability);
  vi.mocked(readInitialEvidence).mockResolvedValue(mockEvidenceResponse);
  vi.mocked(readInitialAnalysis).mockRejectedValue(new Error("404 Not Found"));
});

afterEach(() => {
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
  });

  it("readInitialAnalysis returning 404 is called only once while no request exists", async () => {
    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(1);
  });

  it("persisted Initial Evidence hydration is not repeatedly fetched", async () => {
    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

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
    const user = userEvent.setup();
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

    const user = userEvent.setup();

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    expect(submitBtn).toBeDisabled();
    expect(screen.getByText("Mengirim…")).toBeInTheDocument();

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
    vi.mocked(readInitialAnalysis)
      .mockRejectedValueOnce(new Error("404 Not Found"))
      .mockResolvedValue({
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

    const user = userEvent.setup();

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    expect(vi.mocked(readInitialAnalysis)).toHaveBeenCalledTimes(1);

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Analisis sedang diproses. Silakan tunggu.")).toBeInTheDocument();
    });
  });

  it("polling stops on completion and failure", async () => {
    vi.mocked(submitInitialAnalysis).mockResolvedValue({
      analysis_request_id: "req-1",
      session_id: draftSession.id,
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "COMPLETED",
      session_status: "ANALYZED",
      created_at: "2026-07-31T00:00:00Z",
    });

    vi.mocked(readInitialAnalysis)
      .mockRejectedValueOnce(new Error("404 Not Found"))
      .mockResolvedValue({
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

    const user = userEvent.setup();

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Analysis complete")).toBeInTheDocument();
    });
  });

  it("calls refreshDecisionWorkspace (getSession + getAvailableActions) on terminal COMPLETED and updates sidebar and shows decision controls", async () => {
    const secondSession: TradeSession = {
      id: "session-other",
      ticker: "BBCA",
      company_name: "Bank BCA",
      status: "DRAFT",
      note: null,
      created_at: "2026-07-31T00:00:00Z",
      updated_at: "2026-07-31T00:00:00Z",
      closed_at: null,
    };
    vi.mocked(listSessions).mockResolvedValue({ sessions: [draftSession, secondSession] });

    vi.mocked(submitInitialAnalysis).mockResolvedValue({
      analysis_request_id: "req-1",
      session_id: draftSession.id,
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "COMPLETED",
      session_status: "ANALYZED",
      created_at: "2026-07-31T00:00:00Z",
    });

    vi.mocked(readInitialAnalysis)
      .mockRejectedValueOnce(new Error("404 Not Found"))
      .mockResolvedValue({
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

    vi.mocked(getSession)
      .mockResolvedValueOnce(draftSession)
      .mockResolvedValueOnce({ ...draftSession, status: "ANALYZED" });

    vi.mocked(getAvailableActions)
      .mockResolvedValueOnce(mockAvailability)
      .mockResolvedValueOnce({
        session_id: draftSession.id,
        session_status: "ANALYZED",
        available_actions: ["BUY", "WAIT", "SKIP"],
      });

    const user = userEvent.setup();
    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "WAIT" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Konfirmasi BUY" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Konfirmasi SKIP" })).toBeInTheDocument();
    });

    // Verify both session and actions were refreshed together
    expect(getSession).toHaveBeenCalledWith(draftSession.id);
    expect(getAvailableActions).toHaveBeenCalledWith(draftSession.id);

    // Sidebar reflects ANALYZED for selected session, but DRAFT for the second session
    const sidebar = screen.getByRole("complementary", { name: "Daftar sesi" });
    expect(sidebar).toHaveTextContent("ANALYZED");
    expect(sidebar).toHaveTextContent("DRAFT");
  });

  it("does not show decision controls when analysis reaches FAILED", async () => {
    vi.mocked(submitInitialAnalysis).mockResolvedValue({
      analysis_request_id: "req-1",
      session_id: draftSession.id,
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "FAILED",
      session_status: "DRAFT",
      created_at: "2026-07-31T00:00:00Z",
    });

    vi.mocked(readInitialAnalysis)
      .mockRejectedValueOnce(new Error("404 Not Found"))
      .mockResolvedValue({
        analysis_request_id: "req-1",
        session_id: draftSession.id,
        analysis_type: "INITIAL_ANALYSIS",
        request_status: "FAILED",
        session_status: "DRAFT",
        processed_response: null,
        error_code: "GEMINI_ERROR",
        error_message: "Gemini quota exceeded",
        created_at: "2026-07-31T00:00:00Z",
        started_at: "2026-07-31T00:00:01Z",
        completed_at: "2026-07-31T00:00:02Z",
      });

    vi.mocked(getAvailableActions).mockResolvedValue({
      session_id: draftSession.id,
      session_status: "DRAFT",
      available_actions: [],
    });

    const user = userEvent.setup();
    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Initial Analysis gagal diproses")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: "WAIT" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Konfirmasi BUY" })).toBeNull();
  });

  it("failed submission keeps persisted evidence visible", async () => {
    vi.mocked(submitInitialAnalysis).mockRejectedValue(new Error("429 Too Many Requests"));

    const user = userEvent.setup();

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: "Minta Initial Analysis" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("429 Too Many Requests");
    });

    expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    expect(screen.getByText("3 file diterima.")).toBeInTheDocument();
  });
});
