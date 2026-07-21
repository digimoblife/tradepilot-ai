import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { partialExitReviewFixture } from "@/test/fixtures";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { PartialExitReviewView } from "./partial-exit-review-view";

function makeAcceptedSummary(
  overrides: Partial<AnalysisSummary> = {},
): AnalysisSummary {
  return {
    id: "per-1",
    session_id: "sess-a",
    analysis_type: "PARTIAL_EXIT_REVIEW",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-21T10:05:00+07:00",
    created_at: "2026-07-21T10:00:00+07:00",
    prompt_version: "1.0.0",
    schema_name: "partial_exit_review",
    schema_version: "1.0.0",
    supersedes_analysis_id: null,
    ...overrides,
  };
}

function makeDetail(
  overrides: Partial<AnalysisDetail> = {},
): AnalysisDetail {
  return {
    id: "per-1",
    session_id: "sess-a",
    analysis_type: "PARTIAL_EXIT_REVIEW",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-21T10:05:00+07:00",
    created_at: "2026-07-21T10:00:00+07:00",
    prompt_name: "partial_exit_review",
    prompt_version: "1.0.0",
    schema_name: "partial_exit_review",
    schema_version: "1.0.0",
    payload: JSON.parse(JSON.stringify(partialExitReviewFixture)) as Record<string, unknown>,
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
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(screen.getByText("Memuat review partial exit…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Data loading and selection
// -------------------------------------------------------------------
describe("data loading and selection", () => {
  it("calls listAnalyses with exact session ID", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<PartialExitReviewView sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "PARTIAL_EXIT_REVIEW",
      });
    });
  });

  it("selects latest accepted PARTIAL_EXIT_REVIEW", async () => {
    const older = makeAcceptedSummary({ id: "old", accepted_at: "2026-07-20T10:00:00+07:00" });
    const newer = makeAcceptedSummary({ id: "new", accepted_at: "2026-07-21T10:00:00+07:00" });
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [older, newer], total: 2 });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ id: "new" }));
    render(<PartialExitReviewView sessionId="sess-a" />);
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
    render(<PartialExitReviewView sessionId="sess-a" onEmpty={onEmpty} />);
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
    render(<PartialExitReviewView sessionId="sess-a" />);
    await waitFor(() => {
      expect(getAnalysis).toHaveBeenCalledWith("detail-id");
    });
  });

  it("notifies onEmpty when no accepted record exists", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const onEmpty = vi.fn();
    render(<PartialExitReviewView sessionId="sess-a" onEmpty={onEmpty} />);
    await waitFor(() => {
      expect(onEmpty).toHaveBeenCalled();
    });
  });

  it("notifies onLoaded when data is available", async () => {
    mockAccepted();
    const onLoaded = vi.fn();
    render(<PartialExitReviewView sessionId="sess-a" onLoaded={onLoaded} />);
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
    const { container } = render(<PartialExitReviewView sessionId="sess-a" />);
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
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Gagal.")).toBeTruthy();
  });

  it("shows authentication error safely", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(
      new AuthenticationError(401, "AUTH_REQUIRED", "Auth"),
    );
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(
      await screen.findByText("Silakan masuk terlebih dahulu untuk melihat review partial exit."),
    ).toBeTruthy();
  });

  it("shows unknown error fallback", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(
      await screen.findByText("Gagal memuat review partial exit. Silakan coba lagi."),
    ).toBeTruthy();
  });

  it("has retry button", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Coba Lagi")).toBeTruthy();
  });

  it("retry re-fetches", async () => {
    vi.mocked(listAnalyses).mockRejectedValueOnce(new Error("fail"));
    vi.mocked(listAnalyses).mockResolvedValueOnce({ analyses: [makeAcceptedSummary()], total: 1 });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail());
    render(<PartialExitReviewView sessionId="sess-a" />);
    const btn = await screen.findByText("Coba Lagi");
    await userEvent.click(btn);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledTimes(2);
    });
  });
});

// -------------------------------------------------------------------
// BBRI-Style required display areas
// -------------------------------------------------------------------
describe("BBRI-style display", () => {
  beforeEach(mockAccepted);

  it("renders market summary with OHLC", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Hari Ini")).toBeTruthy();
    expect(await screen.findByText("Open")).toBeTruthy();
    expect(await screen.findByText("High")).toBeTruthy();
    expect(await screen.findByText("Low")).toBeTruthy();
    expect(await screen.findByText("Last / Close")).toBeTruthy();
    expect(await screen.findByText("Rata-rata")).toBeTruthy();
    expect(await screen.findByText("Perubahan (%)")).toBeTruthy();
  });

  it("renders partial exit confirmation", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Eksekusi Partial Exit")).toBeTruthy();
    expect(await screen.findByText("Partial Take Profit")).toBeTruthy();
  });

  it("renders realized result summary", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Hasil Realisasi")).toBeTruthy();
    const pnl = await screen.findAllByText("Realized P&L");
    expect(pnl.length).toBe(2);
    expect(await screen.findByText("Realized Return")).toBeTruthy();
  });

  it("renders remaining position assessment", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Kondisi Posisi Tersisa")).toBeTruthy();
    expect(await screen.findByText("Penilaian terhadap sisa posisi setelah partial exit.")).toBeTruthy();
  });

  it("renders thesis assessment", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Penilaian Thesis")).toBeTruthy();
    expect(await screen.findByText("Thesis masih berlaku.")).toBeTruthy();
  });

  it("renders remaining target realism section", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Apakah Target Masih Realistis?")).toBeTruthy();
    expect(await screen.findByText("Target masih realistis.")).toBeTruthy();
  });

  it("renders stop-loss status", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Status Stop Loss")).toBeTruthy();
    expect(await screen.findByText("Stop loss aman.")).toBeTruthy();
  });

  it("renders trading plan", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Trading Plan Sisa Posisi")).toBeTruthy();
    expect(await screen.findByText("Sisa posisi masih menguntungkan.")).toBeTruthy();
  });

  it("renders AI assessment", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Penilaian AI")).toBeTruthy();
    expect(await screen.findByText("Sisa posisi layak dipertahankan.")).toBeTruthy();
  });

  it("renders remaining target probability", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    const el = await screen.findAllByText("55%");
    expect(el.length).toBe(2);
  });

  it("renders downside probability", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("28%")).toBeTruthy();
  });

  it("renders confidence", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("68%")).toBeTruthy();
  });

  it("renders estimate disclaimer", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Estimasi AI, bukan kepastian.")).toBeTruthy();
  });

  it("renders material changes section", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Perubahan Material dari Update Sebelumnya")).toBeTruthy();
  });

  it("renders warnings section", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Tidak ada peringatan tambahan.")).toBeTruthy();
  });

  it("renders realized profit value", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("4.800")).toBeTruthy();
  });

  it("renders remaining quantity", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    const els = await screen.findAllByText("100");
    expect(els.length).toBeGreaterThanOrEqual(1);
  });
});

// -------------------------------------------------------------------
// Active versus proposed
// -------------------------------------------------------------------
describe("active versus proposed", () => {
  beforeEach(mockAccepted);

  it("renders active target label", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    const el = await screen.findAllByText("Target Aktif");
    expect(el.length).toBe(2);
  });

  it("renders active stop loss label", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    const el = await screen.findAllByText("Stop Loss Aktif");
    expect(el.length).toBe(2);
  });

  it("shows proposed target when revised_target_proposed is true", async () => {
    const detail = makeDetail();
    const payload = JSON.parse(JSON.stringify(partialExitReviewFixture));
    payload.remaining_target_assessment.revised_target_proposed = true;
    payload.remaining_target_assessment.proposed_target = 3200;
    detail.payload = payload as Record<string, unknown>;
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary()],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(detail);
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText(/Usulan Target Baru/)).toBeTruthy();
    expect(await screen.findByText(/Usulan AI — belum terkonfirmasi./)).toBeTruthy();
  });

  it("shows proposed stop when revised_stop_proposed is true", async () => {
    const detail = makeDetail();
    const payload = JSON.parse(JSON.stringify(partialExitReviewFixture));
    payload.stop_loss_assessment.revised_stop_proposed = true;
    payload.stop_loss_assessment.proposed_stop_loss = 2900;
    detail.payload = payload as Record<string, unknown>;
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary()],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(detail);
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText(/Usulan Stop Loss Baru/)).toBeTruthy();
    expect(await screen.findByText(/Usulan AI — belum terkonfirmasi./)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Schema-shaped fixture tests
// -------------------------------------------------------------------
describe("schema-shaped fixture tests", () => {
  beforeEach(mockAccepted);

  it("renders entry price from result summary", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("2.800")).toBeTruthy();
  });

  it("renders exit price", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    const el = await screen.findAllByText("2.920");
    expect(el.length).toBe(2);
  });

  it("renders realized profit loss from result summary", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("4.800")).toBeTruthy();
  });

  it("renders remaining position summary narrative", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Sisa posisi masih aman.")).toBeTruthy();
  });

  it("renders strengthening evidence", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Harga terus naik.")).toBeTruthy();
  });

  it("renders target obstacle", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Resistance 2.950.")).toBeTruthy();
  });

  it("renders full exit condition", async () => {
    render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Full exit di target 3.000.")).toBeTruthy();
  });

  it("fixture has expected enum values", () => {
    expect(partialExitReviewFixture.remaining_position_assessment.health).toBe("HEALTHY");
    expect(partialExitReviewFixture.ai_assessment.bias).toBe("BULLISH");
    expect(partialExitReviewFixture.thesis_assessment.status).toBe("INTACT");
    expect(partialExitReviewFixture.trading_plan.current_action).toBe("HOLD");
  });

  it("fixture warnings section is empty", () => {
    expect(partialExitReviewFixture.warnings_and_missing_information.warnings).toEqual([]);
  });
});

// -------------------------------------------------------------------
// Session isolation
// -------------------------------------------------------------------
describe("session isolation", () => {
  it("session A request uses session A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<PartialExitReviewView sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "PARTIAL_EXIT_REVIEW",
      });
    });
  });

  it("switching to session B clears A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary({ id: "a", session_id: "sess-a" })],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ id: "a", session_id: "sess-a" }));
    const { unmount } = render(<PartialExitReviewView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Hari Ini")).toBeTruthy();
    unmount();

    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const onEmpty = vi.fn();
    render(<PartialExitReviewView sessionId="sess-b" onEmpty={onEmpty} />);
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
    const { unmount } = render(<PartialExitReviewView sessionId="sess-a" />);
    unmount();

    listSpy.mockResolvedValue({ analyses: [], total: 0 });
    const onEmptyB = vi.fn();
    render(<PartialExitReviewView sessionId="sess-b" onEmpty={onEmptyB} />);
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
    const src = PartialExitReviewView.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });

  it("does not render analysis request controls", async () => {
    mockAccepted();
    render(<PartialExitReviewView sessionId="sess-a" />);
    await screen.findByText("Ringkasan Hari Ini");
    const body = document.body.textContent ?? "";
    expect(body).not.toContain("Minta Analisis");
    expect(body).not.toContain("Request Analysis");
  });
});
