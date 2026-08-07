import { readFileSync } from "node:fs";

import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { readWaitUpdateAnalysis, retryWaitUpdateAnalysis } from "@/features/trade-workspace/api";
import type { CurrentStep, WaitUpdateAnalysisRead } from "@/features/trade-workspace/types";
import { WaitUpdateRecovery } from "./wait-update-recovery";

vi.mock("@/features/trade-workspace/api", () => ({
  readWaitUpdateAnalysis: vi.fn(),
  retryWaitUpdateAnalysis: vi.fn(),
}));

const sessionId = "session-wait-123";

function makeStep(overrides: Partial<CurrentStep> = {}): CurrentStep {
  return {
    code: "PROCESSING",
    mode: "PROCESSING",
    workflow_actions: [],
    active_request: {
      id: "req-wait-1",
      analysis_type: "WAIT_UPDATE",
      status: "PROCESSING",
    },
    failed_request: null,
    read_only: false,
    ...overrides,
  };
}

function makeReadResponse(overrides: Partial<WaitUpdateAnalysisRead> = {}): WaitUpdateAnalysisRead {
  return {
    analysis_request_id: "req-wait-1",
    session_id: sessionId,
    analysis_type: "WAIT_UPDATE",
    request_status: "PROCESSING",
    session_status: "WAITING",
    processed_response: null,
    error_code: null,
    error_message: null,
    observation_period: "MORNING",
    created_at: "2026-01-01T08:00:00Z",
    started_at: "2026-01-01T08:00:01Z",
    completed_at: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("WaitUpdateRecovery", () => {
  it("does not render when step has no active or failed WAIT_UPDATE request", () => {
    const step: CurrentStep = {
      code: "DECISION",
      mode: "ACTIONABLE",
      workflow_actions: ["BUY", "WAIT", "SKIP"],
      active_request: null,
      failed_request: null,
      read_only: false,
    };

    const { container } = render(
      <WaitUpdateRecovery sessionId={sessionId} step={step} refetch={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
    expect(readWaitUpdateAnalysis).not.toHaveBeenCalled();
  });

  it("performs immediate status read on mount and displays processing UI", async () => {
    vi.mocked(readWaitUpdateAnalysis).mockResolvedValue(makeReadResponse());
    const refetch = vi.fn().mockResolvedValue({});

    render(<WaitUpdateRecovery sessionId={sessionId} step={makeStep()} refetch={refetch} />);

    expect(readWaitUpdateAnalysis).toHaveBeenCalledWith(sessionId, expect.any(AbortSignal));
    expect(await screen.findByRole("heading", { name: "WAIT Update sedang diproses" })).toBeInTheDocument();
    expect(screen.getByText("Data terbaru sedang dianalisis. Hasilnya akan tersedia setelah proses selesai.")).toBeInTheDocument();
  });

  it("displays completed UI with link to Analysis route when status is COMPLETED", async () => {
    vi.mocked(readWaitUpdateAnalysis).mockResolvedValue(
      makeReadResponse({ request_status: "COMPLETED", completed_at: "2026-01-01T08:05:00Z" }),
    );
    const refetch = vi.fn().mockResolvedValue({});

    render(<WaitUpdateRecovery sessionId={sessionId} step={makeStep()} refetch={refetch} />);

    expect(await screen.findByRole("heading", { name: "WAIT Update selesai" })).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Lihat Hasil Analisis" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", `/sessions/${sessionId}/analysis`);
    expect(refetch).toHaveBeenCalled();
  });

  it("displays failed UI and handles retry when retry workflow action is authorized", async () => {
    const user = userEvent.setup();
    const failedStep = makeStep({
      code: "FAILED_REQUEST",
      mode: "FAILED",
      workflow_actions: ["RETRY_WAIT_UPDATE"],
      active_request: null,
      failed_request: {
        id: "req-wait-1",
        analysis_type: "WAIT_UPDATE",
        status: "FAILED",
        retry_allowed: true,
      },
    });

    vi.mocked(readWaitUpdateAnalysis).mockResolvedValue(
      makeReadResponse({ request_status: "FAILED", error_message: "Processing error" }),
    );
    vi.mocked(retryWaitUpdateAnalysis).mockResolvedValue({
      analysis_request_id: "req-wait-1",
      session_id: sessionId,
      analysis_type: "WAIT_UPDATE",
      request_status: "PENDING",
      session_status: "WAITING",
      observation_period: "MORNING",
      created_at: "2026-01-01T08:10:00Z",
    });

    const refetch = vi.fn().mockResolvedValue({});

    render(<WaitUpdateRecovery sessionId={sessionId} step={failedStep} refetch={refetch} />);

    expect(await screen.findByRole("heading", { name: "WAIT Update belum berhasil" })).toBeInTheDocument();
    const retryBtn = screen.getByRole("button", { name: "Coba Lagi" });
    expect(retryBtn).toBeInTheDocument();

    await user.click(retryBtn);

    await waitFor(() => {
      expect(retryWaitUpdateAnalysis).toHaveBeenCalledWith(sessionId);
    });
    expect(refetch).toHaveBeenCalled();
  });

  it("displays sanitized error feedback with GET-only reload button when status read fails", async () => {
    const user = userEvent.setup();
    vi.mocked(readWaitUpdateAnalysis).mockRejectedValue(new Error("500 read exception"));
    const refetch = vi.fn().mockResolvedValue({});

    render(<WaitUpdateRecovery sessionId={sessionId} step={makeStep()} refetch={refetch} />);

    expect(await screen.findByRole("heading", { name: "Status WAIT Update belum dapat dimuat" })).toBeInTheDocument();
    const reloadBtn = screen.getByRole("button", { name: "Muat Ulang" });
    expect(reloadBtn).toBeInTheDocument();

    await user.click(reloadBtn);
    expect(refetch).toHaveBeenCalled();
  });

  it("resets recovery state when sessionId changes to B", async () => {
    vi.mocked(readWaitUpdateAnalysis).mockResolvedValue(makeReadResponse());
    const { rerender } = render(
      <WaitUpdateRecovery sessionId="session-a" step={makeStep()} refetch={vi.fn()} />,
    );

    expect(await screen.findByRole("heading", { name: "WAIT Update sedang diproses" })).toBeInTheDocument();

    const noStep: CurrentStep = {
      code: "DECISION",
      mode: "ACTIONABLE",
      workflow_actions: ["BUY", "WAIT", "SKIP"],
      active_request: null,
      failed_request: null,
      read_only: false,
    };

    rerender(<WaitUpdateRecovery sessionId="session-b" step={noStep} refetch={vi.fn()} />);

    expect(screen.queryByRole("heading", { name: "WAIT Update sedang diproses" })).toBeNull();
  });

  it("contains no polling timers in component root, localStorage, sessionStorage, or Gemini calls", () => {
    const source = readFileSync("src/features/sessions/wait-update-recovery.tsx", "utf8");
    expect(source).not.toMatch(/localStorage|sessionStorage|SessionWorkspace|JobStatus/);
  });
});
