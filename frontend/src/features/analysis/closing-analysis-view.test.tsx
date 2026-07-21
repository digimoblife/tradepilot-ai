import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { closingAnalysisFixture } from "@/test/fixtures";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { ClosingAnalysisView } from "./closing-analysis-view";

function makeAcceptedSummary(
  overrides: Partial<AnalysisSummary> = {},
): AnalysisSummary {
  return {
    id: "ca-1",
    session_id: "sess-a",
    analysis_type: "CLOSING_ANALYSIS",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-25T15:05:00+07:00",
    created_at: "2026-07-25T15:00:00+07:00",
    prompt_version: "1.0.0",
    schema_name: "closing_analysis",
    schema_version: "1.0.0",
    supersedes_analysis_id: null,
    ...overrides,
  };
}

function makeDetail(
  overrides: Partial<AnalysisDetail> = {},
): AnalysisDetail {
  return {
    id: "ca-1",
    session_id: "sess-a",
    analysis_type: "CLOSING_ANALYSIS",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-25T15:05:00+07:00",
    created_at: "2026-07-25T15:00:00+07:00",
    prompt_name: "closing_analysis",
    prompt_version: "1.0.0",
    schema_name: "closing_analysis",
    schema_version: "1.0.0",
    payload: JSON.parse(JSON.stringify(closingAnalysisFixture)) as Record<string, unknown>,
    supersedes_analysis_id: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

function mockAccepted() {
  vi.mocked(listAnalyses).mockResolvedValue({
    analyses: [makeAcceptedSummary()],
    total: 1,
  });
  vi.mocked(getAnalysis).mockResolvedValue(makeDetail());
}

// -------------------------------------------------------------------
// Loading state
// -------------------------------------------------------------------
describe("loading state", () => {
  it("shows loading message while fetching", () => {
    vi.mocked(listAnalyses).mockImplementation(() => new Promise(() => {}));
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(screen.getByText("Memuat closing analysis…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Data loading and selection
// -------------------------------------------------------------------
describe("data loading and selection", () => {
  it("calls listAnalyses with exact session ID", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<ClosingAnalysisView sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "CLOSING_ANALYSIS",
      });
    });
  });

  it("selects latest accepted CLOSING_ANALYSIS", async () => {
    const older = makeAcceptedSummary({ id: "old", accepted_at: "2026-07-24T15:00:00+07:00" });
    const newer = makeAcceptedSummary({ id: "new", accepted_at: "2026-07-25T15:00:00+07:00" });
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [older, newer], total: 2 });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ id: "new" }));
    render(<ClosingAnalysisView sessionId="sess-a" />);
    await waitFor(() => {
      expect(getAnalysis).toHaveBeenCalledWith("new");
    });
  });

  it("ignores rejected records", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary({ acceptance_status: "REJECTED" })],
      total: 1,
    });
    const onEmpty = vi.fn();
    render(<ClosingAnalysisView sessionId="sess-a" onEmpty={onEmpty} />);
    await waitFor(() => {
      expect(onEmpty).toHaveBeenCalled();
    });
  });

  it("calls getAnalysis with the selected ID", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary({ id: "detail-id" })],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ id: "detail-id" }));
    render(<ClosingAnalysisView sessionId="sess-a" />);
    await waitFor(() => {
      expect(getAnalysis).toHaveBeenCalledWith("detail-id");
    });
  });

  it("notifies onEmpty when no accepted record exists", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const onEmpty = vi.fn();
    render(<ClosingAnalysisView sessionId="sess-a" onEmpty={onEmpty} />);
    await waitFor(() => {
      expect(onEmpty).toHaveBeenCalled();
    });
  });

  it("notifies onLoaded when data is available", async () => {
    mockAccepted();
    const onLoaded = vi.fn();
    render(<ClosingAnalysisView sessionId="sess-a" onLoaded={onLoaded} />);
    await waitFor(() => {
      expect(onLoaded).toHaveBeenCalled();
    });
  });
});

// -------------------------------------------------------------------
// Empty state
// -------------------------------------------------------------------
describe("empty state", () => {
  it("renders null when no accepted record exists", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const { container } = render(<ClosingAnalysisView sessionId="sess-a" />);
    await waitFor(() => {
      expect(container.innerHTML).toBe("");
    });
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows typed API error safely", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new ApiError(500, "ERROR", "Gagal."));
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Gagal.")).toBeTruthy();
  });

  it("shows authentication error safely", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(
      new AuthenticationError(401, "AUTH_REQUIRED", "Auth"),
    );
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Silakan masuk terlebih dahulu untuk melihat closing analysis."),
    ).toBeTruthy();
  });

  it("shows unknown error fallback", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Gagal memuat closing analysis. Silakan coba lagi."),
    ).toBeTruthy();
  });

  it("has retry button", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Coba Lagi")).toBeTruthy();
  });

  it("retry re-fetches", async () => {
    vi.mocked(listAnalyses).mockRejectedValueOnce(new Error("fail"));
    vi.mocked(listAnalyses).mockResolvedValueOnce({ analyses: [makeAcceptedSummary()], total: 1 });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail());
    render(<ClosingAnalysisView sessionId="sess-a" />);
    const btn = await screen.findByText("Coba Lagi");
    await userEvent.click(btn);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledTimes(2);
    });
  });
});

// -------------------------------------------------------------------
// 12 original display areas
// -------------------------------------------------------------------
describe("12 original display areas", () => {
  beforeEach(mockAccepted);

  it("renders closing summary (final result)", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Penutupan")).toBeTruthy();
    expect(await screen.findByText("Take Profit")).toBeTruthy();
  });

  it("renders trade result with weighted exit", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Hasil Final Trade")).toBeTruthy();
    expect(await screen.findByText("Profit")).toBeTruthy();
    expect(await screen.findByText("2.916")).toBeTruthy();
  });

  it("renders trade timeline", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Timeline Perjalanan Trade")).toBeTruthy();
    expect(await screen.findByText("Sesi trading berhasil.")).toBeTruthy();
  });

  it("renders final thesis evaluation", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Evaluasi Thesis")).toBeTruthy();
    expect(await screen.findByText("Thesis terbukti benar.")).toBeTruthy();
  });

  it("renders execution quality", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Kualitas Eksekusi")).toBeTruthy();
    expect(await screen.findByText("Eksekusi berjalan baik.")).toBeTruthy();
  });

  it("renders risk management quality", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    const titles = await screen.findAllByText("Manajemen Risiko");
    expect(titles.length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText("Manajemen risiko baik.")).toBeTruthy();
  });

  it("renders what worked section", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Yang Berjalan Baik & Tidak Berjalan Baik")).toBeTruthy();
  });

  it("renders avoidable mistakes", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Kesalahan yang Bisa Dihindari")).toBeTruthy();
    expect(await screen.findByText("Tidak ada kesalahan yang teridentifikasi.")).toBeTruthy();
  });

  it("renders lessons learned", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Pelajaran yang Dipetik")).toBeTruthy();
    expect(await screen.findByText("Entry di area support memberikan hasil optimal.")).toBeTruthy();
  });

  it("renders final grade from AI evaluation", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Penilaian Akhir AI")).toBeTruthy();
    expect(await screen.findByText("B")).toBeTruthy();
    expect(await screen.findByText("Analisis berjalan sesuai harapan.")).toBeTruthy();
  });

  it("renders journal summary", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Jurnal")).toBeTruthy();
    expect(await screen.findByText("Ringkasan Sesi BBRI")).toBeTruthy();
    expect(await screen.findByText("Entry di support penting.")).toBeTruthy();
  });

  it("renders warnings section", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Peringatan dan Informasi yang Kurang")).toBeTruthy();
    expect(await screen.findByText("Tidak ada peringatan tambahan.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Result and process distinction
// -------------------------------------------------------------------
describe("result and process distinction", () => {
  beforeEach(mockAccepted);

  it("shows factual trade outcome (PROFIT)", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Profit")).toBeTruthy();
  });

  it("shows AI evaluation grade separate from facts", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    const grade = await screen.findByText("B");
    expect(grade.closest("section")?.textContent).toContain("Penilaian Akhir AI");
  });

  it("shows process quality score", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    const scores = await screen.findAllByText("85%");
    expect(scores.length).toBeGreaterThanOrEqual(1);
  });

  it("shows result aligned with process boolean", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Hasil Selaras Proses")).toBeTruthy();
    const ya = await screen.findAllByText("Ya");
    expect(ya.length).toBeGreaterThanOrEqual(1);
  });

  it("displays estimate disclaimer in AI evaluation", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Estimasi AI, bukan kepastian.")).toBeTruthy();
  });

  it("shows gross P&L as factual number", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("11.600")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Schema-shaped fixture tests
// -------------------------------------------------------------------
describe("schema-shaped fixture tests", () => {
  beforeEach(mockAccepted);

  it("renders closing reason from fixture", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Take Profit")).toBeTruthy();
  });

  it("renders entry price from trade result", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("2.800")).toBeTruthy();
  });

  it("renders gross return percentage", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("4.14%")).toBeTruthy();
  });

  it("renders thesis outcome label", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Terkonfirmasi Penuh")).toBeTruthy();
  });

  it("renders execution quality labels", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    const goods = await screen.findAllByText("Baik");
    expect(goods.length).toBeGreaterThanOrEqual(4);
  });

  it("renders journal title", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Sesi BBRI")).toBeTruthy();
  });

  it("renders tags", async () => {
    render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("bbri")).toBeTruthy();
    expect(await screen.findByText("swing_trade")).toBeTruthy();
  });

  it("fixture has expected enum values", () => {
    expect(closingAnalysisFixture.closing_confirmation.closing_reason).toBe("TAKE_PROFIT");
    expect(closingAnalysisFixture.trade_result.outcome).toBe("PROFIT");
    expect(closingAnalysisFixture.final_thesis_evaluation.outcome).toBe("FULLY_CONFIRMED");
    expect(closingAnalysisFixture.plan_execution_evaluation.overall_quality).toBe("GOOD");
    expect(closingAnalysisFixture.final_ai_evaluation.trade_grade).toBe("B");
  });

  it("fixture warnings section is empty", () => {
    expect(closingAnalysisFixture.warnings_and_missing_information.warnings).toEqual([]);
  });
});

// -------------------------------------------------------------------
// Session isolation
// -------------------------------------------------------------------
describe("session isolation", () => {
  it("session A request uses session A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<ClosingAnalysisView sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "CLOSING_ANALYSIS",
      });
    });
  });

  it("switching to session B clears A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary({ id: "a", session_id: "sess-a" })],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ id: "a", session_id: "sess-a" }));
    const { unmount } = render(<ClosingAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Penutupan")).toBeTruthy();
    unmount();

    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const onEmpty = vi.fn();
    render(<ClosingAnalysisView sessionId="sess-b" onEmpty={onEmpty} />);
    await waitFor(() => {
      expect(onEmpty).toHaveBeenCalled();
    });
  });

  it("stale A response cannot overwrite B", async () => {
    const listSpy = vi.mocked(listAnalyses);
    const getSpy = vi.mocked(getAnalysis);
    let resolveA: (v: unknown) => void;
    const promiseA = new Promise((r) => { resolveA = r; });

    listSpy.mockImplementationOnce(
      () => promiseA as Promise<{ analyses: AnalysisSummary[]; total: number }>,
    );
    const { unmount } = render(<ClosingAnalysisView sessionId="sess-a" />);
    unmount();

    listSpy.mockResolvedValue({ analyses: [], total: 0 });
    const onEmptyB = vi.fn();
    render(<ClosingAnalysisView sessionId="sess-b" onEmpty={onEmptyB} />);
    await waitFor(() => {
      expect(onEmptyB).toHaveBeenCalled();
    });

    resolveA!({ analyses: [makeAcceptedSummary({ id: "stale-a" })], total: 1 });
    await new Promise((r) => setTimeout(r, 100));
    expect(getSpy).not.toHaveBeenCalledWith("stale-a");
  });
});

// -------------------------------------------------------------------
// Safety and boundaries
// -------------------------------------------------------------------
describe("safety and boundaries", () => {
  it("does not use direct fetch", () => {
    const src = ClosingAnalysisView.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });

  it("does not render analysis request controls", async () => {
    mockAccepted();
    render(<ClosingAnalysisView sessionId="sess-a" />);
    await screen.findByText("Ringkasan Penutupan");
    const body = document.body.textContent ?? "";
    expect(body).not.toContain("Minta Analisis");
    expect(body).not.toContain("Request Analysis");
  });
});
