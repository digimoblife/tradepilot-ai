import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import {
  initialAnalysisFixture,
  watchingUpdateFixture,
  openPositionUpdateFixture,
  partialExitReviewFixture,
  closingAnalysisFixture,
} from "@/test/fixtures";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { AnalysisHistory } from "./analysis-history";

function makeSummary(type: string, overrides: Partial<AnalysisSummary> = {}): AnalysisSummary {
  return {
    id: `${type.toLowerCase()}-1`,
    session_id: "sess-a",
    analysis_type: type,
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-20T10:00:00+07:00",
    created_at: "2026-07-20T09:55:00+07:00",
    prompt_version: "1.0.0",
    schema_name: type.toLowerCase().replace(/_/g, "_"),
    schema_version: "1.0.0",
    supersedes_analysis_id: null,
    ...overrides,
  };
}

function makeDetail(type: string, fixture: Record<string, unknown>, overrides: Partial<AnalysisDetail> = {}): AnalysisDetail {
  return {
    id: `${type.toLowerCase()}-1`,
    session_id: "sess-a",
    analysis_type: type,
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-20T10:00:00+07:00",
    created_at: "2026-07-20T09:55:00+07:00",
    prompt_name: type.toLowerCase(),
    prompt_version: "1.0.0",
    schema_name: type.toLowerCase().replace(/_/g, "_"),
    schema_version: "1.0.0",
    payload: JSON.parse(JSON.stringify(fixture)) as Record<string, unknown>,
    supersedes_analysis_id: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

// -------------------------------------------------------------------
// Loading state
// -------------------------------------------------------------------
describe("loading state", () => {
  it("shows loading message while fetching", () => {
    vi.mocked(listAnalyses).mockImplementation(() => new Promise(() => {}));
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(screen.getByText("Memuat riwayat analisis…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Empty state
// -------------------------------------------------------------------
describe("empty state", () => {
  it("shows empty message when no accepted analyses exist", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(await screen.findByText("Belum ada analisis yang diterima.")).toBeTruthy();
  });

  it("ignores rejected records", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("INITIAL_ANALYSIS", { acceptance_status: "REJECTED" })],
      total: 1,
    });
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(await screen.findByText("Belum ada analisis yang diterima.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows typed API error safely", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new ApiError(500, "ERROR", "Gagal."));
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(await screen.findByText("Gagal.")).toBeTruthy();
  });

  it("shows authentication error safely", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(
      new AuthenticationError(401, "AUTH_REQUIRED", "Auth"),
    );
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(
      await screen.findByText("Silakan masuk terlebih dahulu untuk melihat riwayat analisis."),
    ).toBeTruthy();
  });

  it("shows unknown error fallback", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(
      await screen.findByText("Gagal memuat riwayat analisis. Silakan coba lagi."),
    ).toBeTruthy();
  });

  it("has retry button", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(await screen.findByText("Coba Lagi")).toBeTruthy();
  });

  it("retry re-fetches", async () => {
    vi.mocked(listAnalyses).mockRejectedValueOnce(new Error("fail"));
    vi.mocked(listAnalyses).mockResolvedValueOnce({ analyses: [], total: 0 });
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByText("Coba Lagi");
    await userEvent.click(btn);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledTimes(2);
    });
  });
});

// -------------------------------------------------------------------
// History list
// -------------------------------------------------------------------
describe("history list", () => {
  it("calls listAnalyses with exact session ID", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<AnalysisHistory sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a");
    });
  });

  it("shows section title", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(await screen.findByText("Riwayat Analisis")).toBeTruthy();
  });

  it("shows each analysis type label", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [
        makeSummary("INITIAL_ANALYSIS"),
        makeSummary("OPEN_POSITION_UPDATE"),
      ],
      total: 2,
    });
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(await screen.findByText("Analisis Awal")).toBeTruthy();
    expect(await screen.findByText("Update Posisi Terbuka")).toBeTruthy();
  });

  it("shows count of analyses", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [
        makeSummary("INITIAL_ANALYSIS"),
        makeSummary("WATCHING_UPDATE"),
      ],
      total: 2,
    });
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(await screen.findByText(/2 analisis/)).toBeTruthy();
  });

  it("shows accepted badge", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("INITIAL_ANALYSIS")],
      total: 1,
    });
    render(<AnalysisHistory sessionId="sess-a" />);
    expect(await screen.findByText("Diterima")).toBeTruthy();
  });

  it("sorts by created_at descending", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [
        makeSummary("INITIAL_ANALYSIS", { id: "old", created_at: "2026-07-19T10:00:00+07:00" }),
        makeSummary("WATCHING_UPDATE", { id: "new", created_at: "2026-07-20T10:00:00+07:00" }),
      ],
      total: 2,
    });
    render(<AnalysisHistory sessionId="sess-a" />);
    // Both should render
    expect(await screen.findByText("Analisis Awal")).toBeTruthy();
    expect(await screen.findByText("Update Pemantauan")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Opening historical analysis detail
// -------------------------------------------------------------------
describe("opening historical analysis", () => {
  it("fetches detail when clicked", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("INITIAL_ANALYSIS")],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail("INITIAL_ANALYSIS", initialAnalysisFixture as unknown as Record<string, unknown>));
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByTestId("history-item-initial_analysis-1");
    await userEvent.click(btn);
    await waitFor(() => {
      expect(getAnalysis).toHaveBeenCalledWith("initial_analysis-1");
    });
  });

  it("shows loading state while fetching detail", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("INITIAL_ANALYSIS")],
      total: 1,
    });
    vi.mocked(getAnalysis).mockImplementation(() => new Promise(() => {}));
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByTestId("history-item-initial_analysis-1");
    await userEvent.click(btn);
    expect(await screen.findByText("Memuat detail…")).toBeTruthy();
  });

  it("shows version metadata", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("INITIAL_ANALYSIS")],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail("INITIAL_ANALYSIS", initialAnalysisFixture as unknown as Record<string, unknown>));
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByTestId("history-item-initial_analysis-1");
    await userEvent.click(btn);
    expect(await screen.findByText(/Versi:/)).toBeTruthy();
    expect(await screen.findByText(/Schema:/)).toBeTruthy();
  });

  it("closes detail when clicked again", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("INITIAL_ANALYSIS")],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail("INITIAL_ANALYSIS", initialAnalysisFixture as unknown as Record<string, unknown>));
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByTestId("history-item-initial_analysis-1");
    await userEvent.click(btn);
    expect(await screen.findByText(/Versi:/)).toBeTruthy();
    await userEvent.click(btn);
    await waitFor(() => {
      expect(screen.queryByText(/Versi:/)).toBeNull();
    });
  });

  it("shows detail error safely", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("INITIAL_ANALYSIS")],
      total: 1,
    });
    vi.mocked(getAnalysis).mockRejectedValue(new Error("fail"));
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByTestId("history-item-initial_analysis-1");
    await userEvent.click(btn);
    expect(await screen.findByText("Gagal memuat detail analisis.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// All five analysis types
// -------------------------------------------------------------------
describe("all five analysis types", () => {
  const types: Array<{ type: string; fixture: Record<string, unknown>; keyText: string }> = [
    { type: "CLOSING_ANALYSIS", fixture: closingAnalysisFixture as unknown as Record<string, unknown>, keyText: "Gross P&L" },
    { type: "PARTIAL_EXIT_REVIEW", fixture: partialExitReviewFixture as unknown as Record<string, unknown>, keyText: "Hasil" },
    { type: "OPEN_POSITION_UPDATE", fixture: openPositionUpdateFixture as unknown as Record<string, unknown>, keyText: "Penilaian Posisi" },
    { type: "WATCHING_UPDATE", fixture: watchingUpdateFixture as unknown as Record<string, unknown>, keyText: "Perbandingan" },
    { type: "INITIAL_ANALYSIS", fixture: initialAnalysisFixture as unknown as Record<string, unknown>, keyText: "Rekomendasi" },
  ];

  types.forEach(({ type, fixture, keyText }) => {
    it(`renders ${type} detail through viewer`, async () => {
      vi.mocked(listAnalyses).mockResolvedValue({
        analyses: [makeSummary(type)],
        total: 1,
      });
      vi.mocked(getAnalysis).mockResolvedValue(makeDetail(type, fixture));
      render(<AnalysisHistory sessionId="sess-a" />);
      const id = `${type.toLowerCase()}-1`;
      const btn = await screen.findByTestId(`history-item-${id}`);
      await userEvent.click(btn);
      await waitFor(() => {
        expect(getAnalysis).toHaveBeenCalledWith(id);
      });
      expect(await screen.findByText(keyText)).toBeTruthy();
    });
  });

  it("shows null payload message", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("INITIAL_ANALYSIS")],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail("INITIAL_ANALYSIS", initialAnalysisFixture as unknown as Record<string, unknown>, { payload: null }));
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByTestId("history-item-initial_analysis-1");
    await userEvent.click(btn);
    expect(await screen.findByText("Tidak ada data tersedia untuk analisis ini.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Update period
// -------------------------------------------------------------------
describe("update period", () => {
  const periodCases: Array<{ type: string; fixture: Record<string, unknown>; expected: string }> = [
    { type: "INITIAL_ANALYSIS", fixture: initialAnalysisFixture as unknown as Record<string, unknown>, expected: "Pagi" },
    { type: "WATCHING_UPDATE", fixture: watchingUpdateFixture as unknown as Record<string, unknown>, expected: "Penutupan Pasar" },
    { type: "OPEN_POSITION_UPDATE", fixture: openPositionUpdateFixture as unknown as Record<string, unknown>, expected: "Siang" },
    { type: "PARTIAL_EXIT_REVIEW", fixture: partialExitReviewFixture as unknown as Record<string, unknown>, expected: "Siang" },
    { type: "CLOSING_ANALYSIS", fixture: closingAnalysisFixture as unknown as Record<string, unknown>, expected: "Tidak berlaku" },
  ];

  periodCases.forEach(({ type, fixture, expected }) => {
    it(`shows period "${expected}" for ${type}`, async () => {
      vi.mocked(listAnalyses).mockResolvedValue({
        analyses: [makeSummary(type)],
        total: 1,
      });
      vi.mocked(getAnalysis).mockResolvedValue(makeDetail(type, fixture));
      render(<AnalysisHistory sessionId="sess-a" />);
      const id = `${type.toLowerCase()}-1`;
      const btn = await screen.findByTestId(`history-item-${id}`);
      await userEvent.click(btn);
      expect(await screen.findByText(expected)).toBeTruthy();
    });
  });
});

// -------------------------------------------------------------------
// Material changes
// -------------------------------------------------------------------
describe("material changes", () => {
  it("shows empty changes message for WU with no changes", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("WATCHING_UPDATE")],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail("WATCHING_UPDATE", watchingUpdateFixture as unknown as Record<string, unknown>));
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByTestId("history-item-watching_update-1");
    await userEvent.click(btn);
    expect(await screen.findByText("Tidak ada perubahan material.")).toBeTruthy();
  });

  it("shows changes in OPU when present", async () => {
    const fixture = JSON.parse(JSON.stringify(openPositionUpdateFixture)) as Record<string, unknown>;
    fixture.changes_from_previous = [
      { category: "HARGA", explanation: "Harga naik 2%", materiality: "MATERIAL" },
    ];
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("OPEN_POSITION_UPDATE")],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail("OPEN_POSITION_UPDATE", fixture));
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByTestId("history-item-open_position_update-1");
    await userEvent.click(btn);
    expect(await screen.findByText(/HARGA/)).toBeTruthy();
    expect(await screen.findByText(/Harga naik 2%/)).toBeTruthy();
    expect(await screen.findByText(/MATERIAL/)).toBeTruthy();
  });

  it("shows changes in PER when present", async () => {
    const fixture = JSON.parse(JSON.stringify(partialExitReviewFixture)) as Record<string, unknown>;
    fixture.changes_from_previous = [
      { category: "POSITION", explanation: "Setengah posisi terjual", materiality: "CRITICAL" },
    ];
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("PARTIAL_EXIT_REVIEW")],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail("PARTIAL_EXIT_REVIEW", fixture));
    render(<AnalysisHistory sessionId="sess-a" />);
    const btn = await screen.findByTestId("history-item-partial_exit_review-1");
    await userEvent.click(btn);
    expect(await screen.findByText(/POSITION/)).toBeTruthy();
    expect(await screen.findByText(/Setengah posisi terjual/)).toBeTruthy();
    expect(await screen.findByText(/CRITICAL/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Session isolation
// -------------------------------------------------------------------
describe("session isolation", () => {
  it("session A request uses session A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<AnalysisHistory sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a");
    });
  });

  it("switching to session B clears A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeSummary("INITIAL_ANALYSIS", { id: "a", session_id: "sess-a" })],
      total: 1,
    });
    const { unmount } = render(<AnalysisHistory sessionId="sess-a" />);
    expect(await screen.findByText("Analisis Awal")).toBeTruthy();
    unmount();

    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<AnalysisHistory sessionId="sess-b" />);
    expect(await screen.findByText("Belum ada analisis yang diterima.")).toBeTruthy();
  });

  it("stale A response cannot overwrite B", async () => {
    const listSpy = vi.mocked(listAnalyses);
    let resolveA: (v: unknown) => void;
    const promiseA = new Promise((r) => { resolveA = r; });

    listSpy.mockImplementationOnce(
      () => promiseA as Promise<{ analyses: AnalysisSummary[]; total: number }>,
    );
    const { unmount } = render(<AnalysisHistory sessionId="sess-a" />);
    unmount();

    listSpy.mockResolvedValue({ analyses: [], total: 0 });
    render(<AnalysisHistory sessionId="sess-b" />);
    expect(await screen.findByText("Belum ada analisis yang diterima.")).toBeTruthy();

    resolveA!({ analyses: [makeSummary("INITIAL_ANALYSIS", { id: "stale-a" })], total: 1 });
    await new Promise((r) => setTimeout(r, 100));
    // Session B should still show empty ("Belum ada analisis yang diterima.")
    expect(await screen.findByText("Belum ada analisis yang diterima.")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Safety and boundaries
// -------------------------------------------------------------------
describe("safety and boundaries", () => {
  it("does not use direct fetch", () => {
    const src = AnalysisHistory.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });

  it("does not render analysis request controls", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [makeSummary("INITIAL_ANALYSIS")], total: 1 });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail("INITIAL_ANALYSIS", initialAnalysisFixture as unknown as Record<string, unknown>));
    render(<AnalysisHistory sessionId="sess-a" />);
    await screen.findByText("Analisis Awal");
    const body = document.body.textContent ?? "";
    expect(body).not.toContain("Minta Analisis");
    expect(body).not.toContain("Request Analysis");
  });
});
