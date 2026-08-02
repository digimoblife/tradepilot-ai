import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradeWorkspace } from "./trade-workspace";
import {
  getAvailableActions,
  getSession,
  getSessionDetail,
  listSessions,
  readInitialAnalysis,
  readInitialEvidence,
  uploadInitialEvidence,
} from "./api";
import type { DecisionAvailability, InitialEvidenceUploadResponse, TradeSession } from "./types";

vi.mock("./api", () => ({
  buyDecision: vi.fn(),
  getAvailableActions: vi.fn(),
  getSession: vi.fn(),
  getSessionDetail: vi.fn().mockResolvedValue(null),
  listSessions: vi.fn(),
  readInitialAnalysis: vi.fn(),
  readInitialEvidence: vi.fn(),
  readPositionUpdates: vi.fn().mockResolvedValue({ position: null, updates: [] }),
  retryInitialAnalysis: vi.fn(),
  skipDecision: vi.fn(),
  submitInitialAnalysis: vi.fn(),
  submitPositionUpdateAnalysis: vi.fn(),
  uploadInitialEvidence: vi.fn(),
  uploadPositionUpdateInput: vi.fn(),
  waitDecision: vi.fn(),
}));

const draftSession: TradeSession = {
  id: "session-tlkm",
  ticker: "TLKM",
  company_name: "Telkom Indonesia",
  status: "DRAFT",
  note: null,
  created_at: "2026-07-31T00:00:00Z",
  updated_at: "2026-07-31T00:00:00Z",
  closed_at: null,
};

const mockAvailability: DecisionAvailability = {
  session_id: "session-tlkm",
  session_status: "DRAFT",
  available_actions: [],
};

const mockPersistedEvidence: InitialEvidenceUploadResponse = {
  evidence: [
    {
      id: "ev-1",
      evidence_type: "ORDERBOOK",
      original_filename: "orderbook.png",
      mime_type: "image/png",
      size_bytes: 12345,
      uploaded_at: "2026-07-31T10:00:00Z",
    },
    {
      id: "ev-2",
      evidence_type: "CHART_3_MONTH",
      original_filename: "chart3m.png",
      mime_type: "image/png",
      size_bytes: 23456,
      uploaded_at: "2026-07-31T10:00:00Z",
    },
    {
      id: "ev-3",
      evidence_type: "CHART_6_MONTH",
      original_filename: "chart6m.png",
      mime_type: "image/png",
      size_bytes: 34567,
      uploaded_at: "2026-07-31T10:00:00Z",
    },
  ],
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getSessionDetail).mockImplementation(() => Promise.resolve(null as never));
  vi.mocked(listSessions).mockResolvedValue({ sessions: [draftSession] });
  vi.mocked(getSession).mockResolvedValue(draftSession);
  vi.mocked(getAvailableActions).mockResolvedValue(mockAvailability);
  vi.mocked(readInitialAnalysis).mockRejectedValue(new Error("No analysis"));
});

afterEach(() => {
  cleanup();
});

describe("Initial Evidence Hydration", () => {
  it("fresh session with no evidence requires all three file uploads", async () => {
    vi.mocked(readInitialEvidence).mockResolvedValue({ evidence: [] });

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence Initial Analysis")).toBeInTheDocument();
    });

    expect(screen.getByText("Unggah Evidence")).toBeInTheDocument();
    expect(uploadInitialEvidence).not.toHaveBeenCalled();
  });

  it("keeps upload disabled until all three required files are selected and submits that file set", async () => {
    const user = userEvent.setup();
    vi.mocked(readInitialEvidence).mockResolvedValue({ evidence: [] });
    vi.mocked(uploadInitialEvidence).mockResolvedValue(mockPersistedEvidence);
    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByLabelText("Order Book")).toBeInTheDocument();
    });

    const uploadButton = screen.getByRole("button", { name: "Unggah Evidence" });
    expect(uploadButton).toBeDisabled();
    const files = {
      orderbook: new File(["orderbook"], "orderbook.png", { type: "image/png" }),
      chart3m: new File(["chart3m"], "chart-3m.png", { type: "image/png" }),
      chart6m: new File(["chart6m"], "chart-6m.png", { type: "image/png" }),
    };

    await user.upload(screen.getByLabelText("Order Book"), files.orderbook);
    await user.upload(screen.getByLabelText("Grafik 3 Bulan"), files.chart3m);
    await user.upload(screen.getByLabelText("Grafik 6 Bulan"), files.chart6m);

    expect(uploadButton).toBeEnabled();
    expect(screen.getByText("orderbook.png")).toBeInTheDocument();
    expect(screen.getByText("chart-3m.png")).toBeInTheDocument();
    expect(screen.getByText("chart-6m.png")).toBeInTheDocument();
    fireEvent.submit(uploadButton.closest("form")!);

    await waitFor(() => expect(uploadInitialEvidence).toHaveBeenCalledWith("session-tlkm", {
      orderbook: files.orderbook,
      chart_3_month: files.chart3m,
      chart_6_month: files.chart6m,
    }));
  });

  it("reopened session with all three persisted evidence types does not require re-upload", async () => {
    vi.mocked(readInitialEvidence).mockResolvedValue(mockPersistedEvidence);

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    expect(screen.getByText("3 file diterima.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Minta Initial Analysis" })).toBeInTheDocument();
    expect(screen.queryByText("Evidence Initial Analysis")).not.toBeInTheDocument();
    expect(uploadInitialEvidence).not.toHaveBeenCalled();
  });

  it("persisted evidence remains recognized after a simulated refresh/remount", async () => {
    vi.mocked(readInitialEvidence).mockResolvedValue(mockPersistedEvidence);

    const { unmount } = render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    unmount();

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });
    expect(screen.getByText("3 file diterima.")).toBeInTheDocument();
  });

  it("failed Initial Analysis submission does not clear persisted evidence", async () => {
    vi.mocked(readInitialEvidence).mockResolvedValue(mockPersistedEvidence);
    vi.mocked(readInitialAnalysis).mockResolvedValue({
      analysis_request_id: "req-1",
      session_id: "session-tlkm",
      analysis_type: "INITIAL_ANALYSIS",
      request_status: "FAILED",
      session_status: "DRAFT",
      processed_response: null,
      error_code: "QUEUE_UNAVAILABLE",
      error_message: "Analysis queue is unavailable",
      created_at: "2026-07-31T10:05:00Z",
      started_at: null,
      completed_at: null,
    });

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Initial Analysis gagal diproses")).toBeInTheDocument();
    });
    expect(screen.getByText("Analisis gagal diproses. Silakan coba lagi.")).toBeInTheDocument();
    expect(screen.queryByText("Analysis queue is unavailable")).not.toBeInTheDocument();

    // Evidence must not disappear
    expect(screen.queryByText("Evidence Initial Analysis")).not.toBeInTheDocument();
    expect(uploadInitialEvidence).not.toHaveBeenCalled();
  });

  it("local file selection state remains separate from server-persisted evidence", async () => {
    vi.mocked(readInitialEvidence).mockResolvedValue({ evidence: [] });

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence Initial Analysis")).toBeInTheDocument();
    });

    expect(uploadInitialEvidence).not.toHaveBeenCalled();
  });

  it("no duplicate upload request is made during hydration", async () => {
    vi.mocked(readInitialEvidence).mockResolvedValue(mockPersistedEvidence);

    render(<TradeWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Evidence siap")).toBeInTheDocument();
    });

    expect(uploadInitialEvidence).not.toHaveBeenCalled();
  });
});
