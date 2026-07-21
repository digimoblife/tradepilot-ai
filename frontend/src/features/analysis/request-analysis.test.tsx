import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { requestAnalysis } from "@/lib/api/analyses";
import { listEvidence } from "@/lib/api/evidence";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

vi.mock("@/lib/api/analyses", () => ({
  requestAnalysis: vi.fn(),
}));

vi.mock("@/lib/api/evidence", () => ({
  listEvidence: vi.fn(),
}));

import { RequestAnalysis } from "./request-analysis";

function mockEvidenceComplete() {
  vi.mocked(listEvidence).mockResolvedValue({
    evidence: [
      { id: "e1", session_id: "sess-a", evidence_type: "ORDERBOOK_SCREENSHOT", status: "AVAILABLE", original_filename: null, mime_type: null, file_size_bytes: null, checksum_sha256: null, market_timestamp: null, uploaded_at: "", caption: null, supersedes_evidence_id: null },
      { id: "e2", session_id: "sess-a", evidence_type: "CHART_THREE_MONTH", status: "AVAILABLE", original_filename: null, mime_type: null, file_size_bytes: null, checksum_sha256: null, market_timestamp: null, uploaded_at: "", caption: null, supersedes_evidence_id: null },
      { id: "e3", session_id: "sess-a", evidence_type: "CHART_SIX_MONTH", status: "AVAILABLE", original_filename: null, mime_type: null, file_size_bytes: null, checksum_sha256: null, market_timestamp: null, uploaded_at: "", caption: null, supersedes_evidence_id: null },
    ],
    total: 3,
  });
}

function mockEvidenceMissing() {
  vi.mocked(listEvidence).mockResolvedValue({
    evidence: [],
    total: 0,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(requestAnalysis).mockReset();
  vi.mocked(listEvidence).mockReset();
});

// -------------------------------------------------------------------
// Rendering
// -------------------------------------------------------------------
describe("rendering", () => {
  it("shows the analysis type in Indonesian", async () => {
    mockEvidenceComplete();
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    expect(await screen.findByText("Analisis Awal")).toBeTruthy();
  });

  it("shows evidence checklist", async () => {
    mockEvidenceComplete();
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    expect(await screen.findByText("Evidence yang Diperlukan:")).toBeTruthy();
    expect(await screen.findByText("Screenshot Orderbook")).toBeTruthy();
    expect(await screen.findByText("Chart 3 Bulan")).toBeTruthy();
    expect(await screen.findByText("Chart 6 Bulan")).toBeTruthy();
  });

  it("shows loading state while checking evidence", () => {
    vi.mocked(listEvidence).mockImplementation(() => new Promise(() => {}));
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    expect(screen.getByText("Memeriksa kelengkapan evidence…")).toBeTruthy();
  });

  it("shows close button when onClose is provided", () => {
    mockEvidenceComplete();
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" onClose={vi.fn()} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });
});

// -------------------------------------------------------------------
// Evidence blocking
// -------------------------------------------------------------------
describe("evidence blocking", () => {
  it("enables submit when all evidence is present", async () => {
    mockEvidenceComplete();
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    await waitFor(() => {
      expect(screen.getByText("Jalankan Analisis Awal")).toBeTruthy();
    });
    expect(screen.getByText("Jalankan Analisis Awal")).toBeEnabled();
  });

  it("disables submit when evidence is missing", async () => {
    mockEvidenceMissing();
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    await waitFor(() => {
      expect(screen.getByText("Jalankan Analisis Awal")).toBeTruthy();
    });
    expect(screen.getByText("Jalankan Analisis Awal")).toBeDisabled();
  });

  it("shows missing evidence message", async () => {
    mockEvidenceMissing();
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    expect(await screen.findByText(/Unggah evidence yang diperlukan/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Submission
// -------------------------------------------------------------------
describe("submission", () => {
  it("calls requestAnalysis when submitted", async () => {
    mockEvidenceComplete();
    vi.mocked(requestAnalysis).mockResolvedValue({
      job_id: "job-1", session_id: "sess-a", analysis_type: "INITIAL_ANALYSIS",
      status: "PENDING", attempt_count: 0, max_attempts: 3,
      available_at: "", created_at: "", previous_session_status: null,
    });
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    const btn = await screen.findByText("Jalankan Analisis Awal");
    await userEvent.click(btn);
    await waitFor(() => {
      expect(requestAnalysis).toHaveBeenCalledWith("sess-a", { analysis_type: "INITIAL_ANALYSIS" });
    });
  });

  it("prevents duplicate submission while pending", async () => {
    mockEvidenceComplete();
    vi.mocked(requestAnalysis).mockImplementation(() => new Promise(() => {}));
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    const btn = await screen.findByText("Jalankan Analisis Awal");
    await userEvent.click(btn);
    expect(await screen.findByText("Mengirim…")).toBeTruthy();
    expect(screen.getByText("Mengirim…")).toBeDisabled();
  });

  it("calls onSuccess with job data", async () => {
    mockEvidenceComplete();
    const job = {
      job_id: "job-1", session_id: "sess-a", analysis_type: "INITIAL_ANALYSIS",
      status: "PENDING", attempt_count: 0, max_attempts: 3,
      available_at: "", created_at: "", previous_session_status: null,
    };
    vi.mocked(requestAnalysis).mockResolvedValue(job);
    const onSuccess = vi.fn();
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" onSuccess={onSuccess} />);
    const btn = await screen.findByText("Jalankan Analisis Awal");
    await userEvent.click(btn);
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(job);
    });
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows API error", async () => {
    mockEvidenceComplete();
    vi.mocked(requestAnalysis).mockRejectedValue(new ApiError(400, "ERROR", "Gagal."));
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    const btn = await screen.findByText("Jalankan Analisis Awal");
    await userEvent.click(btn);
    expect(await screen.findByText("Gagal.")).toBeTruthy();
  });

  it("shows auth error", async () => {
    mockEvidenceComplete();
    vi.mocked(requestAnalysis).mockRejectedValue(new AuthenticationError(401, "AUTH", "Auth"));
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    const btn = await screen.findByText("Jalankan Analisis Awal");
    await userEvent.click(btn);
    expect(await screen.findByText("Silakan masuk terlebih dahulu.")).toBeTruthy();
  });

  it("shows conflict error for duplicate job", async () => {
    mockEvidenceComplete();
    vi.mocked(requestAnalysis).mockRejectedValue(new ApiError(409, "JOB_ALREADY_EXISTS", "Job exists"));
    render(<RequestAnalysis sessionId="sess-a" analysisType="INITIAL_ANALYSIS" />);
    const btn = await screen.findByText("Jalankan Analisis Awal");
    await userEvent.click(btn);
    expect(await screen.findByText(/sedang diproses/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Safety
// -------------------------------------------------------------------
describe("safety", () => {
  it("does not use direct fetch", () => {
    const src = RequestAnalysis.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
  });
});
