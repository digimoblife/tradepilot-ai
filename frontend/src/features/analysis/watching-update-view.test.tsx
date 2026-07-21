import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { watchingUpdateFixture } from "@/test/fixtures";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

vi.mock("@/lib/api/analyses", () => ({
  listAnalyses: vi.fn(),
  getAnalysis: vi.fn(),
}));

import { WatchingUpdateView } from "./watching-update-view";

function makeAcceptedSummary(
  overrides: Partial<AnalysisSummary> = {},
): AnalysisSummary {
  return {
    id: "wu-1",
    session_id: "sess-a",
    analysis_type: "WATCHING_UPDATE",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-16T14:05:00+07:00",
    created_at: "2026-07-16T14:00:00+07:00",
    prompt_version: "1.0.0",
    schema_name: "watching_update",
    schema_version: "1.0.0",
    supersedes_analysis_id: "a0000000-0000-4000-8000-000000000001",
    ...overrides,
  };
}

function makeDetail(
  overrides: Partial<AnalysisDetail> = {},
): AnalysisDetail {
  return {
    id: "wu-1",
    session_id: "sess-a",
    analysis_type: "WATCHING_UPDATE",
    acceptance_status: "ACCEPTED",
    accepted_at: "2026-07-16T14:05:00+07:00",
    created_at: "2026-07-16T14:00:00+07:00",
    prompt_name: "watching_update",
    prompt_version: "1.0.0",
    schema_name: "watching_update",
    schema_version: "1.0.0",
    payload: JSON.parse(JSON.stringify(watchingUpdateFixture)),
    supersedes_analysis_id: "a0000000-0000-4000-8000-000000000001",
    ...overrides,
  };
}

beforeEach(() => {
  cleanup();
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
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(screen.getByText("Memuat pembaruan setup…")).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Data loading and selection
// -------------------------------------------------------------------
describe("data loading and selection", () => {
  it("calls listAnalyses with exact session ID", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<WatchingUpdateView sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "WATCHING_UPDATE",
      });
    });
  });

  it("selects latest accepted WATCHING_UPDATE", async () => {
    const older = makeAcceptedSummary({ id: "old", accepted_at: "2026-07-15T14:00:00+07:00" });
    const newer = makeAcceptedSummary({ id: "new", accepted_at: "2026-07-16T14:00:00+07:00" });
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [older, newer], total: 2 });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ id: "new" }));
    render(<WatchingUpdateView sessionId="sess-a" />);
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
    render(<WatchingUpdateView sessionId="sess-a" onEmpty={onEmpty} />);
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
    render(<WatchingUpdateView sessionId="sess-a" />);
    await waitFor(() => {
      expect(getAnalysis).toHaveBeenCalledWith("detail-id");
    });
  });

  it("notifies onEmpty when no accepted WATCHING_UPDATE exists", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const onEmpty = vi.fn();
    render(<WatchingUpdateView sessionId="sess-a" onEmpty={onEmpty} />);
    await waitFor(() => {
      expect(onEmpty).toHaveBeenCalled();
    });
  });

  it("notifies onLoaded when data is available", async () => {
    mockAccepted();
    const onLoaded = vi.fn();
    render(<WatchingUpdateView sessionId="sess-a" onLoaded={onLoaded} />);
    await waitFor(() => {
      expect(onLoaded).toHaveBeenCalled();
    });
  });
});

// -------------------------------------------------------------------
// Empty state
// -------------------------------------------------------------------
describe("empty state", () => {
  it("renders null when no accepted watching update exists", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const { container } = render(<WatchingUpdateView sessionId="sess-a" />);
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
    vi.mocked(listAnalyses).mockRejectedValue(
      new ApiError(500, "INTERNAL_ERROR", "Gagal memuat."),
    );
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Gagal memuat.")).toBeTruthy();
  });

  it("shows authentication error safely", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(
      new AuthenticationError(401, "AUTHENTICATION_REQUIRED", "Auth"),
    );
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Silakan masuk terlebih dahulu untuk melihat pembaruan setup."),
    ).toBeTruthy();
  });

  it("shows safe unknown error fallback", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Gagal memuat pembaruan setup. Silakan coba lagi."),
    ).toBeTruthy();
  });

  it("has retry button on error", async () => {
    vi.mocked(listAnalyses).mockRejectedValue(new Error("fail"));
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Coba Lagi")).toBeTruthy();
  });

  it("retry re-fetches analyses", async () => {
    vi.mocked(listAnalyses).mockRejectedValueOnce(new Error("fail"));
    vi.mocked(listAnalyses).mockResolvedValueOnce({
      analyses: [makeAcceptedSummary()],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail());
    render(<WatchingUpdateView sessionId="sess-a" />);
    const retryButton = await screen.findByText("Coba Lagi");
    await userEvent.click(retryButton);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledTimes(2);
    });
  });
});

// -------------------------------------------------------------------
// Seven required display areas
// -------------------------------------------------------------------
describe("required display areas", () => {
  beforeEach(mockAccepted);

  it("renders current setup status section", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Status Setup Saat Ini")).toBeTruthy();
    expect(
      await screen.findByText("Thesis tetap valid."),
    ).toBeTruthy();
  });

  it("renders comparison with previous analysis section", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Perbandingan dengan Analisis Sebelumnya"),
    ).toBeTruthy();
    expect(
      await screen.findByText(
        "Tidak ada perubahan signifikan sejak analisis sebelumnya.",
      ),
    ).toBeTruthy();
  });

  it("renders entry validity section", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Validitas Entry")).toBeTruthy();
  });

  it("renders confirmation status section", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Status Konfirmasi Setup"),
    ).toBeTruthy();
  });

  it("renders chase risk section", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Risiko Mengejar Harga"),
    ).toBeTruthy();
  });

  it("renders proposed levels section", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Level Harga yang Diusulkan"),
    ).toBeTruthy();
  });

  it("renders recommended action section", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Tindakan yang Direkomendasikan"),
    ).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Schema-shaped nested fields
// -------------------------------------------------------------------
describe("schema-shaped rendering", () => {
  beforeEach(mockAccepted);

  it("renders strengthening evidence list", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    await screen.findByText("Status Setup Saat Ini");
    // The fixture has empty strengthening_evidence
  });

  it("renders invalidation condition", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText(
        "Invalidate jika harga turun di bawah 2.450",
      ),
    ).toBeTruthy();
  });

  it("renders comparison summary", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText(
        "Tidak ada perubahan signifikan sejak analisis sebelumnya.",
      ),
    ).toBeTruthy();
  });

  it("renders support price levels", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Support utama.", { exact: false }),
    ).toBeTruthy();
    expect(
      await screen.findByText("Support kedua.", { exact: false }),
    ).toBeTruthy();
  });

  it("renders resistance price levels", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Resistance utama.", { exact: false }),
    ).toBeTruthy();
    expect(
      await screen.findByText("Resistance kedua.", { exact: false }),
    ).toBeTruthy();
  });

  it("fixture has entry assessment summary", () => {
    expect(watchingUpdateFixture.entry_assessment.summary).toBe(
      "Harga mendekati area entry.",
    );
  });

  it("renders trading plan conditions", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText("Entry jika harga di atas 2.500."),
    ).toBeTruthy();
    expect(
      await screen.findByText("Jangan entry jika harga > 2.550."),
    ).toBeTruthy();
  });

  it("fixture warnings section is empty", () => {
    expect(
      watchingUpdateFixture.warnings_and_missing_information.warnings,
    ).toEqual([]);
    expect(
      watchingUpdateFixture.warnings_and_missing_information.missing_information,
    ).toEqual([]);
  });

  it("fixture has expected enum values", () => {
    expect(watchingUpdateFixture.ai_assessment.bias).toBe("BULLISH");
    expect(watchingUpdateFixture.orderbook_analysis.buyer_strength).toBe("MODERATE");
  });
});

// -------------------------------------------------------------------
// Proposal versus canonical
// -------------------------------------------------------------------
describe("proposal versus canonical", () => {
  beforeEach(mockAccepted);

  it("entry is labelled as AI proposal", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText(
        "Usulan AI, belum menjadi posisi terkonfirmasi.",
      ),
    ).toBeTruthy();
  });

  it("proposed levels have AI proposal wording", async () => {
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(
      await screen.findByText(
        "Usulan AI, belum menjadi nilai terkonfirmasi.",
      ),
    ).toBeTruthy();
  });
});

// -------------------------------------------------------------------
// Session isolation
// -------------------------------------------------------------------
describe("session isolation", () => {
  it("session A request uses session A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    render(<WatchingUpdateView sessionId="sess-a" />);
    await waitFor(() => {
      expect(listAnalyses).toHaveBeenCalledWith("sess-a", {
        analysis_type: "WATCHING_UPDATE",
      });
    });
  });

  it("switching to session B clears session A", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary({ id: "a", session_id: "sess-a" })],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ id: "a", session_id: "sess-a" }));
    const { unmount } = render(<WatchingUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Status Setup Saat Ini")).toBeTruthy();
    unmount();

    vi.mocked(listAnalyses).mockResolvedValue({ analyses: [], total: 0 });
    const onEmpty = vi.fn();
    render(<WatchingUpdateView sessionId="sess-b" onEmpty={onEmpty} />);
    await waitFor(() => {
      expect(onEmpty).toHaveBeenCalled();
    });
  });

  it("stale A response cannot overwrite B", async () => {
    let resolveA: (v: unknown) => void;
    const promiseA = new Promise((r) => { resolveA = r; });
    const listSpy = vi.mocked(listAnalyses);
    const getSpy = vi.mocked(getAnalysis);

    // Session A component mounted then immediately unmounted
    listSpy.mockImplementationOnce(
      () => promiseA as Promise<{ analyses: AnalysisSummary[]; total: number }>,
    );
    const { unmount } = render(<WatchingUpdateView sessionId="sess-a" />);
    unmount();

    // Session B component loads and reports empty
    listSpy.mockResolvedValue({ analyses: [], total: 0 });
    const onEmptyB = vi.fn();
    render(<WatchingUpdateView sessionId="sess-b" onEmpty={onEmptyB} />);
    await waitFor(() => {
      expect(onEmptyB).toHaveBeenCalled();
    });

    // Stale A promise resolves after B is already showing empty
    resolveA!({ analyses: [makeAcceptedSummary({ id: "stale-a" })], total: 1 });
    await new Promise((r) => setTimeout(r, 100));

    // getAnalysis should have been called only if stale data overwrote B
    expect(getSpy).not.toHaveBeenCalledWith("stale-a");
  });
});

// -------------------------------------------------------------------
// Safety and boundaries
// -------------------------------------------------------------------
describe("safety and boundaries", () => {
  it("does not use direct fetch", () => {
    const src = WatchingUpdateView.toString();
    expect(src).not.toContain("fetch(");
    expect(src).not.toContain('"/api/');
    expect(src).not.toContain("http://localhost");
  });

  it("does not render analysis request controls", async () => {
    mockAccepted();
    render(<WatchingUpdateView sessionId="sess-a" />);
    await screen.findByText("Status Setup Saat Ini");
    const body = document.body.textContent ?? "";
    expect(body).not.toContain("Minta Analisis");
    expect(body).not.toContain("Request Analysis");
  });

  it("does not import TP-1201 fixture at runtime", async () => {
    vi.mocked(listAnalyses).mockResolvedValue({
      analyses: [makeAcceptedSummary()],
      total: 1,
    });
    vi.mocked(getAnalysis).mockResolvedValue(makeDetail({ payload: null }));
    const onEmpty = vi.fn();
    render(<WatchingUpdateView sessionId="sess-a" onEmpty={onEmpty} />);
    await waitFor(() => {
      expect(onEmpty).toHaveBeenCalled();
    });
  });

  it("does not expose runtime internals", () => {
    const src = WatchingUpdateView.toString();
    expect(src).not.toContain("stack");
    expect(src).not.toContain("rawProvider");
  });

  it("renders estimate disclaimer", async () => {
    mockAccepted();
    render(<WatchingUpdateView sessionId="sess-a" />);
    expect(await screen.findByText("Estimasi AI, bukan kepastian.")).toBeTruthy();
  });
});
