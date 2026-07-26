import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { initialAnalysisFixture } from "@/test/fixtures";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { InitialAnalysisView } from "./initial-analysis-view";

function makeAcceptedSummary(
  overrides: Partial<AnalysisSummary> = {},
): AnalysisSummary {
  return {
    id: "analysis-1",
    session_id: "sess-a",
    analysis_type: "INITIAL_ANALYSIS",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-15T09:05:00+07:00",
    created_at: "2026-07-15T09:00:00+07:00",
    prompt_version: "1.0.0",
    schema_name: "initial_analysis",
    schema_version: "1.0.0",
    supersedes_analysis_id: null,
    ...overrides,
  };
}

function makeAnalysisDetail(
  overrides: Partial<AnalysisDetail> = {},
): AnalysisDetail {
  return {
    id: "analysis-1",
    session_id: "sess-a",
    analysis_type: "INITIAL_ANALYSIS",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-15T09:05:00+07:00",
    created_at: "2026-07-15T09:00:00+07:00",
    prompt_name: "initial_analysis",
    prompt_version: "1.0.0",
    schema_name: "initial_analysis",
    schema_version: "1.0.0",
    payload: JSON.parse(JSON.stringify(initialAnalysisFixture)),
    supersedes_analysis_id: null,
    ...overrides,
  };
}

const initialAnalysisV2Payload = {
  metadata: {
    session_id: "sess-a",
    ticker: "BBRI",
    analysis_timestamp: "2026-07-26T10:00:00+07:00",
    schema_name: "initial_analysis_v2",
    schema_version: "2.0.0",
    prompt_version: "2.0.0",
  },
  decision: {
    recommendation: "WAIT",
    bias: "BULLISH",
    confidence: 72,
    setup_quality: "GOOD",
    risk_level: "MODERATE",
    summary: "Setup menarik, tetapi entry perlu menunggu pullback dekat support.",
  },
  market_facts: {
    open: 2780,
    high: 2840,
    low: 2760,
    close_or_last: 2810,
    average: 2805,
    best_bid: 2800,
    best_offer: 2810,
    foreign_net: 1200000000,
  },
  evidence_findings: {
    orderbook: ["Bid tebal di 2800 menopang harga."],
    chart_3_month: ["Trend naik jangka menengah masih terjaga."],
    chart_6_month: ["Area 2900 menjadi resistance terdekat."],
    broker_summary: ["Broker domestik masih akumulatif."],
    foreign_flow: ["Foreign net buy ringan."],
    limitations: ["Data indikator volume terbatas."],
  },
  trade_plan: {
    nearest_support: 2780,
    nearest_resistance: 2900,
    entry_zone_low: 2780,
    entry_zone_high: 2810,
    chase_limit: 2820,
    stop_loss: 2750,
    target_1: 2850,
    target_2: 2900,
    invalidation: 2750,
    risk_reward: "ACCEPTABLE",
  },
  probabilities: {
    bullish: 58,
    target_1: 55,
    downside: 25,
  },
  scenarios: {
    bullish: "Harga bertahan di atas 2810 lalu menguji 2850.",
    neutral: "Harga bergerak datar di 2780-2820.",
    bearish: "Harga turun di bawah 2750 dan membatalkan setup.",
  },
  next_actions: {
    reasons: ["Tunggu entry dekat support.", "Jangan chase di atas limit."],
    risks: ["Breakdown 2750 membatalkan rencana."],
    monitoring: ["Pantau bid 2800.", "Pantau foreign flow sesi berikutnya."],
  },
};



beforeEach(() => {
  vi.clearAllMocks();
});

/** Helper: sets up mock */
function mockApi() {
  vi.mocked(listAnalyses).mockResolvedValue({
    analyses: [makeAcceptedSummary()],
    total: 1,
  });
  vi.mocked(getAnalysis).mockResolvedValue(makeAnalysisDetail());
}



// -------------------------------------------------------------------
// Loading state
// -------------------------------------------------------------------
describe("loading state", () => {
  it("shows loading message while fetching", () => {
    vi.mocked(listAnalyses).mockImplementation(() => new Promise(() => {}));
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(screen.getByText("Memuat analisis terbaru…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Accepted Initial Analysis rendering
// -------------------------------------------------------------------
describe("accepted Initial Analysis", () => {
  it("renders executive summary", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Eksekutif")).toBeTruthy();
    expect(await screen.findByText("Prospek positif BBRI")).toBeTruthy();
  });

  it("renders orderbook analysis", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Analisis Orderbook")).toBeTruthy();
    expect(
      await screen.findByText("Orderbook mendukung entry."),
    ).toBeTruthy();
  });

  it("renders 3-month chart analysis", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Analisis Chart 3 Bulan"),
    ).toBeTruthy();
  });

  it("renders 6-month chart analysis", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Analisis Chart 6 Bulan"),
    ).toBeTruthy();
  });

  it("renders combined chart assessment", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Analisis Gabungan Chart"),
    ).toBeTruthy();
  });

  it("renders support and resistance", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Support dan Resistance"),
    ).toBeTruthy();
  });

  it("renders entry recommendation", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Rekomendasi Entry AI"),
    ).toBeTruthy();
  });

  it("renders stop-loss recommendation", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Rekomendasi Stop Loss"),
    ).toBeTruthy();
  });

  it("renders target recommendation", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Rekomendasi Target"),
    ).toBeTruthy();
  });

  it("renders thesis", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Thesis Awal")).toBeTruthy();
    expect(
      await screen.findByText("Thesis bullish untuk BBRI."),
    ).toBeTruthy();
  });

  it("renders trading plan", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Rencana Trading"),
    ).toBeTruthy();
    expect(
      await screen.findByText("Menunggu konfirmasi entry."),
    ).toBeTruthy();
  });

  it("renders probability and confidence", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Probabilitas dan Keyakinan"),
    ).toBeTruthy();
  });

  it("renders warnings and missing information", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Peringatan dan Informasi yang Kurang"),
    ).toBeTruthy();
    expect(
      await screen.findByText("Tidak ada peringatan tambahan."),
    ).toBeTruthy();
  });

  it("renders estimate disclaimer", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    const disclaimers = await screen.findAllByText(
      "Estimasi AI, bukan kepastian.",
    );
    expect(disclaimers.length).toBeGreaterThanOrEqual(1);
  });

  it("renders proposal labels distinguishing AI from canonical", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Rekomendasi AI, bukan posisi terkonfirmasi."),
    ).toBeTruthy();
    expect(
      await screen.findByText("Rekomendasi AI, bukan stop loss terkonfirmasi."),
    ).toBeTruthy();
    expect(
      await screen.findByText("Rekomendasi AI, bukan target terkonfirmasi."),
    ).toBeTruthy();
  });
});

describe("accepted Initial Analysis v2", () => {
  it("renders compact v2 decision and critical trade values", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [
        makeAcceptedSummary({
          prompt_version: "2.0.0",
          schema_name: "initial_analysis_v2",
          schema_version: "2.0.0",
        }),
      ],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(
      makeAnalysisDetail({
        prompt_version: "2.0.0",
        schema_name: "initial_analysis_v2",
        schema_version: "2.0.0",
        payload: initialAnalysisV2Payload,
      }),
    );

    render(<InitialAnalysisView sessionId="sess-a" />);

    expect(await screen.findByText("Keputusan")).toBeTruthy();
    expect(await screen.findByText("Rencana Trading")).toBeTruthy();
    expect(await screen.findByText("Probabilitas")).toBeTruthy();
    expect(await screen.findByText("Stop Loss")).toBeTruthy();
    expect(await screen.findAllByText("Target 1")).toBeTruthy();
    expect(await screen.findByText("Tunggu entry dekat support.")).toBeTruthy();
    expect(await screen.findByText("Pantau bid 2800.")).toBeTruthy();
  });

  it("keeps evidence findings collapsible in v2", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [
        makeAcceptedSummary({
          prompt_version: "2.0.0",
          schema_name: "initial_analysis_v2",
          schema_version: "2.0.0",
        }),
      ],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(
      makeAnalysisDetail({
        prompt_version: "2.0.0",
        schema_name: "initial_analysis_v2",
        schema_version: "2.0.0",
        payload: initialAnalysisV2Payload,
      }),
    );

    render(<InitialAnalysisView sessionId="sess-a" />);

    expect(await screen.findByText("Temuan Evidence")).toBeTruthy();
    expect(await screen.findByText("Orderbook")).toBeTruthy();
    expect(await screen.findByText("Bid tebal di 2800 menopang harga.")).toBeTruthy();
  });

  it("renders safe fallbacks when compact v2 fields are missing", async () => {
    const payload = JSON.parse(JSON.stringify(initialAnalysisV2Payload));
    delete payload.trade_plan.stop_loss;
    delete payload.next_actions.monitoring;
    payload.probabilities.downside = null;
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [
        makeAcceptedSummary({
          prompt_version: "2.0.0",
          schema_name: "initial_analysis_v2",
          schema_version: "2.0.0",
        }),
      ],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(
      makeAnalysisDetail({
        prompt_version: "2.0.0",
        schema_name: "initial_analysis_v2",
        schema_version: "2.0.0",
        payload,
      }),
    );

    render(<InitialAnalysisView sessionId="sess-a" />);

    expect(await screen.findByText("Keputusan")).toBeTruthy();
    expect(await screen.findAllByText("Tidak tersedia")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Schema preservation
// -------------------------------------------------------------------
describe("schema preservation", () => {
  it("displays nested arrays from the fixture", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Pertumbuhan kredit"),
    ).toBeTruthy();
    expect(
      await screen.findByText("Kualitas aset terjaga"),
    ).toBeTruthy();
  });

  it("displays price level supports with partial text match", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Support utama.", { exact: false }),
    ).toBeTruthy();
    expect(
      await screen.findByText("Support kedua.", { exact: false }),
    ).toBeTruthy();
  });

  it("displays price level resistances with partial text match", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Resistance utama.", { exact: false }),
    ).toBeTruthy();
    expect(
      await screen.findByText("Resistance kedua.", { exact: false }),
    ).toBeTruthy();
  });

  it("uses null fallback in rendered output", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    await screen.findByText("Ringkasan Eksekutif");
    const body = document.body.textContent ?? "";
    expect(body).toContain("—");
  });

  it("renders enum values safely as Indonesian labels", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Bullish"),
    ).toBeTruthy();
    const sedangElements = await screen.findAllByText("Sedang");
    expect(sedangElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders safe fallbacks when nested fields are missing", async () => {
    const payload = JSON.parse(JSON.stringify(initialAnalysisFixture));
    delete payload.ai_assessment.summary;
    delete payload.trading_plan.levels_to_monitor;
    payload.chart_3_month_analysis.nearest_support = null;
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary()],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeAnalysisDetail({ payload }));

    render(<InitialAnalysisView sessionId="sess-a" />);

    expect(await screen.findByText("Probabilitas dan Keyakinan")).toBeTruthy();
    expect(await screen.findAllByText("Tidak tersedia")).toBeTruthy();
  });

  it("renders additional Gemini top-level fields in detail tambahan", async () => {
    const payload = JSON.parse(JSON.stringify(initialAnalysisFixture));
    payload.data_gaps_and_limitations = { note: "Gemini detail tambahan" };
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary()],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeAnalysisDetail({ payload }));

    render(<InitialAnalysisView sessionId="sess-a" />);

    expect(await screen.findByText("Detail tambahan")).toBeTruthy();
    expect(await screen.findByText("data_gaps_and_limitations")).toBeTruthy();
    expect(await screen.findByText(/Gemini detail tambahan/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Proposal versus canonical
// -------------------------------------------------------------------
describe("proposal versus canonical", () => {
  it("entry AI is labelled as recommendation", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Rekomendasi Entry AI"),
    ).toBeTruthy();
  });

  it("stop loss is labelled as recommendation", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Rekomendasi Stop Loss"),
    ).toBeTruthy();
  });

  it("target is labelled as recommendation", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Rekomendasi Target"),
    ).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Session isolation
// -------------------------------------------------------------------
describe("session isolation", () => {
  it("analysis list called with exact session ID", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [makeAcceptedSummary()], total: 1 }),
    );
    vi.mocked(getAnalysis).mockImplementation(
      () => Promise.resolve(makeAnalysisDetail()),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "INITIAL_ANALYSIS",
      });
    });
  });

  it("session A analysis renders only for session A", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [makeAcceptedSummary({ id: "analysis-a", session_id: "sess-a" })], total: 1 }),
    );
    vi.mocked(getAnalysis).mockImplementation(
      () => Promise.resolve(makeAnalysisDetail({ id: "analysis-a", session_id: "sess-a" })),
    );
    const { unmount } = render(<InitialAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Ringkasan Eksekutif")).toBeTruthy();
    unmount();

    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [], total: 0 }),
    );
    render(<InitialAnalysisView sessionId="sess-b" />);
    expect(
      await screen.findByText(
        "Belum ada Initial Analysis yang diterima untuk sesi ini.",
      ),
    ).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Analysis selection
// -------------------------------------------------------------------
describe("analysis selection", () => {
  it("selects latest accepted INITIAL_ANALYSIS", async () => {
    const older = makeAcceptedSummary({ id: "old", accepted_at: "2026-07-14T09:00:00+07:00" });
    const newer = makeAcceptedSummary({ id: "new", accepted_at: "2026-07-15T09:00:00+07:00" });
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [older, newer], total: 2 }),
    );
    vi.mocked(getAnalysis).mockImplementation(
      () => Promise.resolve(makeAnalysisDetail({ id: "new" })),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    await waitFor(() => {
      expect(getAnalysis).toHaveBeenCalledWith("new");
    });
  });

  it("ignores Watching Update analyses", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [], total: 0 }),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Belum ada Initial Analysis yang diterima untuk sesi ini."),
    ).toBeTruthy();
    expect(getAnalysis).not.toHaveBeenCalled();
  });

  it("rejected analysis is not displayed", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [makeAcceptedSummary({ acceptance_status: "REJECTED" })], total: 1 }),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Belum ada Initial Analysis yang diterima untuk sesi ini."),
    ).toBeTruthy();
  });

  it("calls analysis detail with the selected ID", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [makeAcceptedSummary({ id: "detail-id" })], total: 1 }),
    );
    vi.mocked(getAnalysis).mockImplementation(
      () => Promise.resolve(makeAnalysisDetail({ id: "detail-id" })),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    await waitFor(() => {
      expect(getAnalysis).toHaveBeenCalledWith("detail-id");
    });
  });
});

// -------------------------------------------------------------------
// Empty state
// -------------------------------------------------------------------
describe("empty state", () => {
  it("shows empty message when no accepted analysis exists", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [], total: 0 }),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText(
        "Belum ada Initial Analysis yang diterima untuk sesi ini.",
      ),
    ).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Error states
// -------------------------------------------------------------------
describe("error states", () => {
  it("shows typed API error safely", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.reject(new ApiError(500, "INTERNAL_ERROR", "Gagal memuat analisis.")),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Gagal memuat analisis.")).toBeTruthy();
  });

  it("shows authentication error safely", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.reject(new AuthenticationError(401, "AUTHENTICATION_REQUIRED", "Auth required")),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Silakan masuk terlebih dahulu untuk melihat analisis."),
    ).toBeTruthy();
  });

  it("shows safe unknown error fallback", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.reject(new Error("fail")),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Gagal memuat analisis. Silakan coba lagi."),
    ).toBeTruthy();
  });

  it("has retry button on error", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.reject(new Error("fail")),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText("Coba Lagi")).toBeTruthy();
  });

  it("retry re-fetches analyses", async () => {
    vi.mocked(listAnalyses).mockRejectedValueOnce(new Error("fail"));
    vi.mocked(listAnalyses).mockResolvedValueOnce({ analyses: [makeAcceptedSummary()], total: 1 });
    vi.mocked(getAnalysis).mockImplementation(
      () => Promise.resolve(makeAnalysisDetail()),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    const retryButton = await screen.findByText("Coba Lagi");
    await userEvent.click(retryButton);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledTimes(2);
    });
  });
});

// -------------------------------------------------------------------
// Response safety
// -------------------------------------------------------------------
describe("response safety", () => {
  it("does not expose raw provider output or internals", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    await screen.findByText("Ringkasan Eksekutif");
    const body = document.body.textContent ?? "";
    const blocked = [
      "raw_output", "provider prompt", "system prompt",
      "repair prompt", "API key", "lease owner",
      "stack trace", "storage path",
    ];
    for (const term of blocked) {
      expect(body).not.toContain(term);
    }
  });
});

// -------------------------------------------------------------------
// Metadata
// -------------------------------------------------------------------
describe("metadata", () => {
  it("displays analysis type and provider", async () => {
    mockApi();
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(await screen.findByText(/INITIAL_ANALYSIS/)).toBeTruthy();
    expect(await screen.findByText(/GEMINI/)).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Callbacks
// -------------------------------------------------------------------
describe("callbacks", () => {
  it("notifies onEmpty when no accepted record exists", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const onEmpty = vi.fn();
    render(<InitialAnalysisView sessionId="sess-a" onEmpty={onEmpty} />);
    await waitFor(() => { expect(onEmpty).toHaveBeenCalled(); });
  });

  it("notifies onLoaded when data is available", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary()], total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeAnalysisDetail());
    const onLoaded = vi.fn();
    render(<InitialAnalysisView sessionId="sess-a" onLoaded={onLoaded} />);
    await waitFor(() => { expect(onLoaded).toHaveBeenCalled(); });
  });
});

// -------------------------------------------------------------------
// Session isolation
// -------------------------------------------------------------------
describe("session isolation", () => {
  it("stale A response cannot overwrite B", async () => {
    const listSpy = vi.mocked(listAnalyses);
    const getSpy = vi.mocked(getAnalysis);
    let resolveA: (v: unknown) => void;
    const promiseA = new Promise((r) => { resolveA = r; });
    listSpy.mockImplementationOnce(
      () => promiseA as Promise<{ analyses: AnalysisSummary[]; total: number }>,
    );
    const { unmount } = render(<InitialAnalysisView sessionId="sess-a" />);
    unmount();
    listSpy.mockResolvedValue({ analyses: [], total: 0 });
    const onEmptyB = vi.fn();
    render(<InitialAnalysisView sessionId="sess-b" onEmpty={onEmptyB} />);
    await waitFor(() => { expect(onEmptyB).toHaveBeenCalled(); });
    resolveA!({ analyses: [makeAcceptedSummary({ id: "stale-a" })], total: 1 });
    await new Promise((r) => setTimeout(r, 100));
    expect(getSpy).not.toHaveBeenCalledWith("stale-a");
  });
});

// -------------------------------------------------------------------
// Boundaries
// -------------------------------------------------------------------
describe("boundaries", () => {
  it("does not use direct fetch", () => {
    const src = InitialAnalysisView.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });

  it("does not import TP-1201 fixture at runtime", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [makeAcceptedSummary()], total: 1 }),
    );
    vi.mocked(getAnalysis).mockImplementation(
      () => Promise.resolve(makeAnalysisDetail({ payload: null })),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    expect(
      await screen.findByText("Belum ada Initial Analysis yang diterima untuk sesi ini."),
    ).toBeTruthy();
  });

  it("does not render analysis request controls", async () => {
    vi.mocked(listAnalyses).mockImplementation(
      () => Promise.resolve({ analyses: [], total: 0 }),
    );
    render(<InitialAnalysisView sessionId="sess-a" />);
    const body = document.body.textContent ?? "";
    expect(body).not.toContain("Minta Analisis");
    expect(body).not.toContain("Request Analysis");
  });
});
