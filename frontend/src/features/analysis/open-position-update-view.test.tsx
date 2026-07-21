import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { openPositionUpdateFixture } from "@/test/fixtures";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { OpenPositionUpdateView } from "./open-position-update-view";

function makeAcceptedSummary(
  overrides: Partial<AnalysisSummary> = {},
): AnalysisSummary {
  return {
    id: "opu-1",
    session_id: "sess-a",
    analysis_type: "OPEN_POSITION_UPDATE",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-18T10:05:00+07:00",
    created_at: "2026-07-18T10:00:00+07:00",
    prompt_version: "1.0.0",
    schema_name: "open_position_update",
    schema_version: "1.0.0",
    supersedes_analysis_id: null,
    ...overrides,
  };
}

function makeDetail(
  overrides: Partial<AnalysisDetail> = {},
): AnalysisDetail {
  return {
    id: "opu-1",
    session_id: "sess-a",
    analysis_type: "OPEN_POSITION_UPDATE",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-18T10:05:00+07:00",
    created_at: "2026-07-18T10:00:00+07:00",
    prompt_name: "open_position_update",
    prompt_version: "1.0.0",
    schema_name: "open_position_update",
    schema_version: "1.0.0",
    payload: JSON.parse(JSON.stringify(openPositionUpdateFixture)),
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
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(screen.getByText("Memuat pembaruan posisi…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Data loading and selection
// -------------------------------------------------------------------
describe("data loading and selection", () => {
  it("calls listAnalyses with exact session ID", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "OPEN_POSITION_UPDATE",
      });
    });
  });

  it("selects latest accepted OPEN_POSITION_UPDATE", async () => {
    const older = makeAcceptedSummary({ id: "old", accepted_at: "2026-07-17T10:00:00+07:00" });
    const newer = makeAcceptedSummary({ id: "new", accepted_at: "2026-07-18T10:00:00+07:00" });
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [older, newer], total: 2 });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ id: "new" }));
    render(<OpenPositionUpdateView sessionId="sess-a" />);
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
    render(<OpenPositionUpdateView sessionId="sess-a" onEmpty={onEmpty} />);
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
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    await waitFor(() => {
      expect(getAnalysis).toHaveBeenCalledWith("detail-id");
    });
  });

  it("notifies onEmpty when no accepted record exists", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const onEmpty = vi.fn();
    render(<OpenPositionUpdateView sessionId="sess-a" onEmpty={onEmpty} />);
    await waitFor(() => {
      expect(onEmpty).toHaveBeenCalled();
    });
  });

  it("notifies onLoaded when data is available", async () => {
    mockAccepted();
    const onLoaded = vi.fn();
    render(<OpenPositionUpdateView sessionId="sess-a" onLoaded={onLoaded} />);
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
    const { container } = render(<OpenPositionUpdateView sessionId="sess-a" />);
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
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Gagal.")).toBeTruthy();
  });

  it("shows authentication error safely", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(
      new AuthenticationError(401, "AUTH_REQUIRED", "Auth"),
    );
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Silakan masuk terlebih dahulu untuk melihat pembaruan posisi.")).toBeTruthy();
  });

  it("shows unknown error fallback", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Gagal memuat pembaruan posisi. Silakan coba lagi.")).toBeTruthy();
  });

  it("has retry button", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Coba Lagi")).toBeTruthy();
  });

  it("retry re-fetches", async () => {
    vi.mocked(listAnalyses).mockRejectedValueOnce(new Error("fail"));
    vi.mocked(listAnalyses).mockResolvedValueOnce({ analyses: [makeAcceptedSummary()], total: 1 });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail());
    render(<OpenPositionUpdateView sessionId="sess-a" />);
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

  it("renders market summary with OHLC and average", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Hari Ini")).toBeTruthy();
    // OHLC values rendered via AnalysisValue labels
    expect(await screen.findByText("Open")).toBeTruthy();
    expect(await screen.findByText("High")).toBeTruthy();
    expect(await screen.findByText("Low")).toBeTruthy();
    expect(await screen.findByText("Last / Close")).toBeTruthy();
    expect(await screen.findByText("Rata-rata")).toBeTruthy();
    expect(await screen.findByText("Perubahan (%)")).toBeTruthy();
  });

  it("renders orderbook observations", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Yang Terlihat dari Orderbook")).toBeTruthy();
    expect(await screen.findByText("Orderbook mendukung posisi.")).toBeTruthy();
  });

  it("renders position status", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Kondisi Posisi Saat Ini")).toBeTruthy();
    expect(await screen.findByText("Posisi berjalan sesuai rencana.")).toBeTruthy();
  });

  it("renders target realism section", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Apakah Target Profit Masih Realistis?")).toBeTruthy();
    expect(await screen.findByText("Target masih realistis.")).toBeTruthy();
  });

  it("renders stop-loss status", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Status Stop Loss")).toBeTruthy();
    expect(await screen.findByText("Stop loss aman.")).toBeTruthy();
  });

  it("renders trading plan", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Trading Plan Selanjutnya")).toBeTruthy();
    expect(await screen.findByText("Posisi masih menguntungkan.")).toBeTruthy();
  });

  it("renders AI assessment", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Penilaian AI Saat Ini")).toBeTruthy();
    expect(await screen.findByText("Posisi menguntungkan.")).toBeTruthy();
  });

  it("renders target probability", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    const el = await screen.findAllByText("60%");
    expect(el.length).toBeGreaterThanOrEqual(1);
  });

  it("renders downside probability", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("30%")).toBeTruthy();
  });

  it("renders confidence", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("70%")).toBeTruthy();
  });

  it("renders estimate disclaimer", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Estimasi AI, bukan kepastian.")).toBeTruthy();
  });

  it("renders material changes section", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Perubahan Material dari Update Sebelumnya")).toBeTruthy();
  });

  it("renders warnings section", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Tidak ada peringatan tambahan.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Active versus proposed
// -------------------------------------------------------------------
describe("active versus proposed", () => {
  beforeEach(mockAccepted);

  it("renders active target label", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Target Aktif")).toBeTruthy();
  });

  it("renders active stop loss label", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Stop Loss Aktif")).toBeTruthy();
  });

  it("has AI position assessment label", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Penilaian AI terhadap posisi terkonfirmasi.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Schema-shaped fixture tests
// -------------------------------------------------------------------
describe("schema-shaped fixture tests", () => {
  beforeEach(mockAccepted);

  it("renders buyer observations", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Bid stabil di 2.820.")).toBeTruthy();
  });

  it("renders seller observations", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Offer tipis di 2.830.")).toBeTruthy();
  });

  it("renders today summary narrative", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Pergerakan sesuai ekspektasi.")).toBeTruthy();
  });

  it("renders thesis status", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Thesis masih valid.")).toBeTruthy();
  });

  it("renders strengthening evidence", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Harga bertahan di atas support.")).toBeTruthy();
  });

  it("renders target obstacle", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Resistance 2.900.")).toBeTruthy();
  });

  it("renders plan conditions", async () => {
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Harga di atas stop loss.")).toBeTruthy();
  });

  it("fixture has expected enum values", () => {
    expect(openPositionUpdateFixture.position_assessment.health).toBe("HEALTHY_WITH_CAUTION");
    expect(openPositionUpdateFixture.ai_assessment.bias).toBe("BULLISH");
  });

  it("fixture warnings section is empty", () => {
    expect(openPositionUpdateFixture.warnings_and_missing_information.warnings).toEqual([]);
  });
});

// -------------------------------------------------------------------
// Session isolation
// -------------------------------------------------------------------
describe("session isolation", () => {
  it("session A request uses session A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "OPEN_POSITION_UPDATE",
      });
    });
  });

  it("switching to session B clears A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary({ id: "a", session_id: "sess-a" })],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ id: "a", session_id: "sess-a" }));
    const { unmount } = render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Hari Ini")).toBeTruthy();
    unmount();

    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const onEmpty = vi.fn();
    render(<OpenPositionUpdateView sessionId="sess-b" onEmpty={onEmpty} />);
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
    const { unmount } = render(<OpenPositionUpdateView sessionId="sess-a" />);
    unmount();

    listSpy.mockResolvedValue({ analyses: [], total: 0 });
    const onEmptyB = vi.fn();
    render(<OpenPositionUpdateView sessionId="sess-b" onEmpty={onEmptyB} />);
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
    const src = OpenPositionUpdateView.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });

  it("does not render analysis request controls", async () => {
    mockAccepted();
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    await screen.findByText("Ringkasan Hari Ini");
    const body = document.body.textContent ?? "";
    expect(body).not.toContain("Minta Analisis");
    expect(body).not.toContain("Request Analysis");
  });

  it("does not expose runtime internals", () => {
    const src = OpenPositionUpdateView.toString();
    expect(src).not.toContain("stack");
    expect(src).not.toContain("rawProvider");
  });

  it("renders section heading for context", async () => {
    mockAccepted();
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Hari Ini")).toBeTruthy();
  });

  it("handles null payload as empty", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary()], total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ payload: null }));
    const onEmpty = vi.fn();
    render(<OpenPositionUpdateView sessionId="sess-a" onEmpty={onEmpty} />);
    await waitFor(() => { expect(onEmpty).toHaveBeenCalled(); });
  });

  it("renders proposed stop loss when revised_stop_proposed is true", async () => {
    const detail = makeDetail();
    const payload = JSON.parse(JSON.stringify(openPositionUpdateFixture));
    payload.stop_loss_assessment.revised_stop_proposed = true;
    payload.stop_loss_assessment.proposed_stop_loss = 2800;
    detail.payload = payload as Record<string, unknown>;
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [makeAcceptedSummary()], total: 1 });
    vi.mocked(getAnalysis).mockResolvedValue(detail);
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText(/Usulan Stop Loss Baru/)).toBeTruthy();
    expect(await screen.findByText(/Usulan AI — belum terkonfirmasi./)).toBeTruthy();
  });

  it("renders proposed target when revised_target_proposed is true", async () => {
    const detail = makeDetail();
    const payload = JSON.parse(JSON.stringify(openPositionUpdateFixture));
    payload.target_assessment.revised_target_proposed = true;
    payload.target_assessment.proposed_target = 3100;
    detail.payload = payload as Record<string, unknown>;
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [makeAcceptedSummary()], total: 1 });
    vi.mocked(getAnalysis).mockResolvedValue(detail);
    render(<OpenPositionUpdateView sessionId="sess-a" />);
    expect(await screen.findByText(/Usulan Target Baru/)).toBeTruthy();
    expect(await screen.findByText(/Usulan AI — belum terkonfirmasi./)).toBeTruthy();
  });
});
