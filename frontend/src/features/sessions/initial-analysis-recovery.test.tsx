import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { readInitialAnalysis, retryInitialAnalysis } from "@/features/trade-workspace/api";
import type { CurrentStep } from "@/features/trade-workspace/types";
import { InitialAnalysisRecovery } from "./initial-analysis-recovery";

vi.mock("@/features/trade-workspace/api", () => ({ readInitialAnalysis: vi.fn(), retryInitialAnalysis: vi.fn() }));
const sessionId = "11111111-1111-4111-8111-111111111111";
const step = (status: "PENDING" | "PROCESSING" | "FAILED" = "PROCESSING", retry = false) => ({ code: status === "FAILED" ? "FAILED_REQUEST" : "PROCESSING", mode: status === "FAILED" ? "FAILED" : "PROCESSING", workflow_actions: retry ? ["RETRY_INITIAL_ANALYSIS"] : [], active_request: status === "FAILED" ? null : { id: "request-1", analysis_type: "INITIAL_ANALYSIS", status }, failed_request: status === "FAILED" ? { id: "request-1", analysis_type: "INITIAL_ANALYSIS", status, retry_allowed: retry } : null, read_only: false }) as CurrentStep;
const request = (status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED") => ({ analysis_request_id: "request-1", session_id: sessionId, analysis_type: "INITIAL_ANALYSIS", request_status: status, session_status: "ANALYZING", created_at: "2026-08-05T00:00:00Z", started_at: null, completed_at: null, processed_response: null, error_code: "raw", error_message: "do not render" });

beforeEach(() => { vi.clearAllMocks(); });
afterEach(() => vi.useRealTimers());

describe("InitialAnalysisRecovery", () => {
  it("recovers a processing request by session without submitting another analysis", async () => {
    vi.mocked(readInitialAnalysis).mockResolvedValue(request("PROCESSING") as never);
    render(<InitialAnalysisRecovery sessionId={sessionId} step={step()} refetch={vi.fn()} />);
    expect(await screen.findByText("Analisis Awal sedang diproses")).toBeInTheDocument();
    expect(readInitialAnalysis).toHaveBeenCalledWith(sessionId, expect.any(AbortSignal));
    expect(retryInitialAnalysis).not.toHaveBeenCalled();
  });

  it("recovers PENDING with the same factual processing presentation", async () => {
    vi.mocked(readInitialAnalysis).mockResolvedValue(request("PENDING") as never);
    render(<InitialAnalysisRecovery sessionId={sessionId} step={step("PENDING")} refetch={vi.fn()} />);
    expect(await screen.findByText("Analisis Awal sedang diproses")).toBeInTheDocument();
    expect(screen.getByText(/meninggalkan halaman ini dan kembali lagi/)).toBeInTheDocument();
  });

  it("stops on completion, refetches detail once, and only links to Analysis", async () => {
    const refetch = vi.fn(); vi.mocked(readInitialAnalysis).mockResolvedValue(request("COMPLETED") as never);
    render(<InitialAnalysisRecovery sessionId={sessionId} step={step()} refetch={refetch} />);
    expect(await screen.findByText("Analisis Awal selesai")).toBeInTheDocument();
    await waitFor(() => expect(refetch).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("link", { name: "Lihat Analisis" })).toHaveAttribute("href", `/sessions/${sessionId}/analysis`);
    expect(screen.queryByText("do not render")).toBeNull();
  });

  it("shows retry only from canonical retry authority and guards rapid clicks", async () => {
    vi.mocked(readInitialAnalysis).mockResolvedValue(request("FAILED") as never);
    vi.mocked(retryInitialAnalysis).mockResolvedValue({ analysis_request_id: "request-1" } as never);
    render(<InitialAnalysisRecovery sessionId={sessionId} step={step("FAILED", true)} refetch={vi.fn()} />);
    const button = await screen.findByRole("button", { name: "Coba Analisis Lagi" });
    button.click(); button.click();
    await waitFor(() => expect(retryInitialAnalysis).toHaveBeenCalledTimes(1));
  });

  it("fails closed for a request from another session or wrong analysis type", async () => {
    vi.mocked(readInitialAnalysis).mockResolvedValue({ ...request("PROCESSING"), session_id: "other", analysis_type: "WAIT_UPDATE" } as never);
    render(<InitialAnalysisRecovery sessionId={sessionId} step={step()} refetch={vi.fn()} />);
    await waitFor(() => expect(readInitialAnalysis).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("Analisis Awal sedang diproses")).toBeNull();
  });

  it("does not expose retry when FAILED lacks canonical authority", async () => {
    vi.mocked(readInitialAnalysis).mockResolvedValue(request("FAILED") as never);
    render(<InitialAnalysisRecovery sessionId={sessionId} step={step("FAILED", false)} refetch={vi.fn()} />);
    expect(await screen.findByText("Analisis Awal gagal diproses")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Coba Analisis Lagi" })).toBeNull();
  });

  it("sanitizes failed request errors and does not poll without Current Step request identity", async () => {
    vi.mocked(readInitialAnalysis).mockResolvedValue(request("FAILED") as never);
    const { rerender } = render(<InitialAnalysisRecovery sessionId={sessionId} step={step("FAILED", false)} refetch={vi.fn()} />);
    expect(await screen.findByText("Analisis Awal gagal diproses")).toBeInTheDocument();
    expect(screen.queryByText("do not render")).toBeNull();
    rerender(<InitialAnalysisRecovery sessionId={sessionId} step={{ ...step(), active_request: null, failed_request: null }} refetch={vi.fn()} />);
    expect(readInitialAnalysis).toHaveBeenCalledTimes(1);
  });
});
