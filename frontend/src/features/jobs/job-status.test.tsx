import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { getJobStatus } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { AnalysisJobStatus } from "@/types/analysis-job";

vi.mock("@/lib/api/analyses", () => ({
  getJobStatus: vi.fn(),
}));

import { JobStatus } from "./job-status";

function makeStatus(overrides: Partial<AnalysisJobStatus> = {}): AnalysisJobStatus {
  return {
    job_id: "job-1",
    session_id: "sess-a",
    analysis_type: "INITIAL_ANALYSIS",
    status: "PENDING",
    attempt_count: 0,
    max_attempts: 3,
    available_at: null,
    started_at: null,
    completed_at: null,
    last_error_code: null,
    last_error_message: null,
    analysis_id: null,
    created_at: "2026-07-20T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

function renderJob(overrides: Partial<AnalysisJobStatus> = {}) {
  vi.mocked(getJobStatus).mockResolvedValue(makeStatus(overrides));
  return render(<JobStatus jobId="job-1" sessionId="sess-a" />);
}

// -------------------------------------------------------------------
// Display states
// -------------------------------------------------------------------
describe("display states", () => {
  const states: Array<{ status: string; label: string }> = [
    { status: "PENDING", label: "Dalam Antrian" },
    { status: "BUILDING_CONTEXT", label: "Membangun Konteks" },
    { status: "CALLING_PROVIDER", label: "Menghubungi AI Provider" },
    { status: "VALIDATING", label: "Memvalidasi Hasil" },
    { status: "REPAIRING", label: "Memperbaiki Hasil" },
    { status: "FALLBACK", label: "Mencoba Provider Cadangan" },
    { status: "COMPLETED", label: "Selesai" },
    { status: "FAILED", label: "Analisis Gagal" },
  ];

  states.forEach(({ status, label }) => {
    it(`shows "${label}" for ${status}`, async () => {
      renderJob({ status });
      expect(await screen.findByText(label)).toBeTruthy();
    });
  });
});

// -------------------------------------------------------------------
// Polling
// -------------------------------------------------------------------
describe("polling", () => {
  it("calls getJobStatus on mount", async () => {
    renderJob({ status: "PENDING" });
    await waitFor(() => {
      expect(getJobStatus).toHaveBeenCalledWith("job-1");
    });
  });

  it("polls again after interval for non-terminal status", async () => {
    vi.mocked(getJobStatus).mockResolvedValue(makeStatus({ status: "PENDING" }));
    render(<JobStatus jobId="job-1" sessionId="sess-a" />);
    await waitFor(() => {
      expect(getJobStatus).toHaveBeenCalledTimes(1);
    });
    // Wait for the second poll (3000ms interval + async)
    await new Promise((r) => setTimeout(r, 3200));
    expect(getJobStatus).toHaveBeenCalledTimes(2);
  }, 10000);

  it("stops polling after COMPLETED", async () => {
    vi.mocked(getJobStatus).mockResolvedValue(makeStatus({ status: "COMPLETED", analysis_id: "analysis-1" }));
    render(<JobStatus jobId="job-1" sessionId="sess-a" />);
    await waitFor(() => {
      expect(getJobStatus).toHaveBeenCalledTimes(1);
    });
    await new Promise((r) => setTimeout(r, 5000));
    expect(getJobStatus).toHaveBeenCalledTimes(1);
  }, 10000);

  it("stops polling after FAILED", async () => {
    vi.mocked(getJobStatus).mockResolvedValue(makeStatus({ status: "FAILED" }));
    render(<JobStatus jobId="job-1" sessionId="sess-a" />);
    await waitFor(() => {
      expect(getJobStatus).toHaveBeenCalledTimes(1);
    });
    await new Promise((r) => setTimeout(r, 5000));
    expect(getJobStatus).toHaveBeenCalledTimes(1);
  }, 10000);

  it("cleans up timers on unmount", async () => {
    vi.mocked(getJobStatus).mockResolvedValue(makeStatus({ status: "PENDING" }));
    const { unmount } = render(<JobStatus jobId="job-1" sessionId="sess-a" />);
    await waitFor(() => {
      expect(getJobStatus).toHaveBeenCalledTimes(1);
    });
    unmount();
    await new Promise((r) => setTimeout(r, 5000));
    expect(getJobStatus).toHaveBeenCalledTimes(1);
  }, 10000);
});

// -------------------------------------------------------------------
// Completion
// -------------------------------------------------------------------
describe("completion", () => {
  it("calls onCompleted with analysis_id when COMPLETED", async () => {
    vi.mocked(getJobStatus).mockResolvedValue(makeStatus({ status: "COMPLETED", analysis_id: "analysis-1" }));
    const onCompleted = vi.fn();
    render(<JobStatus jobId="job-1" sessionId="sess-a" onCompleted={onCompleted} />);
    await waitFor(() => {
      expect(onCompleted).toHaveBeenCalledWith("analysis-1");
    });
  });

  it("calls onFailed when FAILED", async () => {
    vi.mocked(getJobStatus).mockResolvedValue(makeStatus({ status: "FAILED" }));
    const onFailed = vi.fn();
    render(<JobStatus jobId="job-1" sessionId="sess-a" onFailed={onFailed} />);
    await waitFor(() => {
      expect(onFailed).toHaveBeenCalled();
    });
  });
});

// -------------------------------------------------------------------
// Attempt count
// -------------------------------------------------------------------
describe("attempt count", () => {
  it("shows attempt count when > 0", async () => {
    renderJob({ status: "PENDING", attempt_count: 2, max_attempts: 3 });
    expect(await screen.findByText(/2\/3/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows API error safely", async () => {
    vi.mocked(getJobStatus).mockRejectedValue(new ApiError(500, "ERROR", "Gagal."));
    render(<JobStatus jobId="job-1" sessionId="sess-a" />);
    expect(await screen.findByText("Gagal.")).toBeTruthy();
  });

  it("shows auth error safely", async () => {
    vi.mocked(getJobStatus).mockRejectedValue(new AuthenticationError(401, "AUTH", "Auth"));
    render(<JobStatus jobId="job-1" sessionId="sess-a" />);
    expect(await screen.findByText("Silakan masuk terlebih dahulu.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Safety
// -------------------------------------------------------------------
describe("safety", () => {
  it("does not use direct fetch", () => {
    const src = JobStatus.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
  });
});
