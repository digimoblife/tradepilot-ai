import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { retryJob } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { AnalysisJobStatus } from "@/types/analysis-job";

vi.mock("@/lib/api/analyses", () => ({
  retryJob: vi.fn(),
}));

import { AnalysisFailure } from "./analysis-failure";

function makeStatus(overrides: Partial<AnalysisJobStatus> = {}): AnalysisJobStatus {
  return {
    job_id: "job-1",
    session_id: "sess-a",
    analysis_type: "INITIAL_ANALYSIS",
    status: "FAILED",
    attempt_count: 1,
    max_attempts: 3,
    available_at: null,
    started_at: null,
    completed_at: null,
    last_error_code: "PROVIDER_ERROR",
    last_error_message: "Provider returned an unexpected response.",
    analysis_id: null,
    created_at: "2026-07-20T10:00:00Z",
    updated_at: "2026-07-20T10:05:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(retryJob).mockReset();
});

// -------------------------------------------------------------------
// Rendering
// -------------------------------------------------------------------
describe("rendering", () => {
  it("shows failure heading", () => {
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" />);
    expect(screen.getByText("Analisis Gagal")).toBeTruthy();
  });

  it("shows error category label", () => {
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" />);
    expect(screen.getByText("Kesalahan Provider")).toBeTruthy();
  });

  it("shows Indonesian summary for known error code", () => {
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" />);
    expect(screen.getByText(/AI Provider mengalami kendala/)).toBeTruthy();
  });

  it("shows provider-specific Gemini summary for authentication/configuration failure", () => {
    render(
      <AnalysisFailure
        jobStatus={makeStatus({
          last_error_code: "AI_PROVIDER_AUTHENTICATION_FAILED",
          last_error_message: "Model not found: gemini-3.5-flash",
        })}
        sessionId="sess-a"
      />
    );
    expect(screen.getByText(/kredensial Gemini tidak valid/i)).toBeTruthy();
  });

  it("shows fallback summary for unknown code", () => {
    render(<AnalysisFailure jobStatus={makeStatus({ last_error_code: "UNKNOWN_CODE", last_error_message: "Something broke." })} sessionId="sess-a" />);
    expect(screen.getByText("Something broke.")).toBeTruthy();
  });

  it("shows retry button when attempts remain", () => {
    render(<AnalysisFailure jobStatus={makeStatus({ attempt_count: 1, max_attempts: 3 })} sessionId="sess-a" />);
    expect(screen.getByText("Coba Lagi")).toBeTruthy();
  });

  it("shows retry button when max attempts reached", () => {
    render(<AnalysisFailure jobStatus={makeStatus({ attempt_count: 3, max_attempts: 3 })} sessionId="sess-a" />);
    expect(screen.getByText("Coba Lagi")).toBeTruthy();
  });

  it("shows Indonesian exhausted-attempts feedback", () => {
    render(
      <AnalysisFailure
        jobStatus={makeStatus({
          attempt_count: 3,
          max_attempts: 3,
          last_error_code: "JOB_ATTEMPTS_EXHAUSTED",
          last_error_message: "raw backend detail",
        })}
        sessionId="sess-a"
      />,
    );
    expect(screen.getByText("Percobaan Habis")).toBeTruthy();
    expect(screen.getByText(/percobaan otomatis habis/i)).toBeTruthy();
  });

  it("shows technical details only in expandable section", () => {
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" />);
    expect(screen.getByText("Detail teknis")).toBeTruthy();
    expect(screen.getByText(/Kode:/)).toBeTruthy();
    expect(screen.getByText(/PROVIDER_ERROR/)).toBeTruthy();
  });

  it("shows Tutup button when onClear provided", () => {
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" onClear={vi.fn()} />);
    expect(screen.getByText("Tutup")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Retry
// -------------------------------------------------------------------
describe("retry", () => {
  it("calls retryJob when retry button clicked", async () => {
    vi.mocked(retryJob).mockResolvedValue({
      job_id: "job-1", status: "PENDING", attempt_count: 2, max_attempts: 3,
    });
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" />);
    await userEvent.click(screen.getByText("Coba Lagi"));
    await waitFor(() => {
      expect(retryJob).toHaveBeenCalledWith("job-1");
    });
  });

  it("calls onRetry after successful retry", async () => {
    vi.mocked(retryJob).mockResolvedValue({
      job_id: "job-1", status: "PENDING", attempt_count: 2, max_attempts: 3,
    });
    const onRetry = vi.fn();
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" onRetry={onRetry} />);
    await userEvent.click(screen.getByText("Coba Lagi"));
    await waitFor(() => {
      expect(onRetry).toHaveBeenCalledWith("job-1");
    });
  });

  it("prevents duplicate retry while pending", async () => {
    vi.mocked(retryJob).mockImplementation(() => new Promise(() => {}));
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" />);
    await userEvent.click(screen.getByText("Coba Lagi"));
    expect(await screen.findByText("Mengirim ulang…")).toBeTruthy();
    expect(screen.getByText("Mengirim ulang…")).toBeDisabled();
  });

  it("shows API error on retry failure", async () => {
    vi.mocked(retryJob).mockRejectedValue(new ApiError(400, "ERROR", "Gagal."));
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" />);
    await userEvent.click(screen.getByText("Coba Lagi"));
    expect(await screen.findByText("Gagal.")).toBeTruthy();
  });

  it("shows auth error safely", async () => {
    vi.mocked(retryJob).mockRejectedValue(new AuthenticationError(401, "AUTH", "Auth"));
    render(<AnalysisFailure jobStatus={makeStatus()} sessionId="sess-a" />);
    await userEvent.click(screen.getByText("Coba Lagi"));
    expect(await screen.findByText("Silakan masuk terlebih dahulu.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Safety
// -------------------------------------------------------------------
describe("safety", () => {
  it("does not use direct fetch", () => {
    const src = AnalysisFailure.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
  });

  it("does not expose raw provider output", () => {
    const src = AnalysisFailure.toString();
    expect(src).not.toContain("PROVIDER_RESPONSE");
    expect(src).not.toContain("rawProvider");
    expect(src).not.toContain("stack");
  });
});
