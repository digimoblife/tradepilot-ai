import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { readPositionUpdates, submitPositionUpdateAnalysis } from "@/features/trade-workspace/api";
import type { CurrentStep, PositionUpdatesRead } from "@/features/trade-workspace/types";

import { PositionUpdateRecovery } from "./position-update-recovery";

vi.mock("@/features/trade-workspace/api", () => ({
  readPositionUpdates: vi.fn(),
  submitPositionUpdateAnalysis: vi.fn(),
}));

const sessionId = "session-pos-123";

function makeStep(overrides: Partial<CurrentStep> = {}): CurrentStep {
  return {
    code: "POSITION_MONITORING",
    mode: "ACTIONABLE",
    workflow_actions: ["SUBMIT_POSITION_UPDATE", "CLOSE"],
    active_request: {
      id: "req-pos-1",
      analysis_type: "POSITION_UPDATE",
      status: "PROCESSING",
    },
    failed_request: null,
    read_only: false,
    ...overrides,
  };
}

function makeReadResponse(overrides: Partial<PositionUpdatesRead> = {}): PositionUpdatesRead {
  return {
    position: null,
    updates: [
      {
        analysis_request_id: "req-pos-1",
        session_id: sessionId,
        analysis_type: "POSITION_UPDATE",
        request_status: "PROCESSING",
        current_price: "5000",
        observation_period: "MORNING",
        observation_timestamp: "2026-01-01T08:00:00Z",
        processed_response: null,
        error_code: null,
        error_message: null,
        created_at: "2026-01-01T08:00:00Z",
        started_at: "2026-01-01T08:00:00Z",
        completed_at: null,
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PositionUpdateRecovery", () => {
  it("does not render and does not call GET when no active or failed POSITION_UPDATE request exists", () => {
    const step = makeStep({ active_request: null, failed_request: null });
    const { container } = render(
      <PositionUpdateRecovery sessionId={sessionId} step={step} refetch={vi.fn()} />,
    );

    expect(container.firstChild).toBeNull();
    expect(readPositionUpdates).not.toHaveBeenCalled();
  });

  it("ignores INITIAL_ANALYSIS candidate request and does not call GET", () => {
    const step = makeStep({
      active_request: {
        id: "req-init-1",
        analysis_type: "INITIAL_ANALYSIS",
        status: "PROCESSING",
      },
    });
    const { container } = render(
      <PositionUpdateRecovery sessionId={sessionId} step={step} refetch={vi.fn()} />,
    );

    expect(container.firstChild).toBeNull();
    expect(readPositionUpdates).not.toHaveBeenCalled();
  });

  it("ignores WAIT_UPDATE candidate request and does not call GET", () => {
    const step = makeStep({
      active_request: {
        id: "req-wait-1",
        analysis_type: "WAIT_UPDATE",
        status: "PROCESSING",
      },
    });
    const { container } = render(
      <PositionUpdateRecovery sessionId={sessionId} step={step} refetch={vi.fn()} />,
    );

    expect(container.firstChild).toBeNull();
    expect(readPositionUpdates).not.toHaveBeenCalled();
  });

  it("performs immediate status read on mount and presents processing state for PENDING/PROCESSING request", async () => {
    vi.mocked(readPositionUpdates).mockResolvedValue(makeReadResponse());

    render(<PositionUpdateRecovery sessionId={sessionId} step={makeStep()} refetch={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Position Update sedang diproses" })).toBeInTheDocument();
    expect(screen.getByText("Data posisi terbaru sedang dianalisis. Hasilnya akan tersedia setelah proses selesai.")).toBeInTheDocument();
    expect(readPositionUpdates).toHaveBeenCalledWith(sessionId, expect.any(AbortSignal));
  });

  it("renders completed state with link to Analysis route when status is COMPLETED and stops polling", async () => {
    const step = makeStep();
    vi.mocked(readPositionUpdates).mockResolvedValue(
      makeReadResponse({
        updates: [
          {
            analysis_request_id: "req-pos-1",
            session_id: sessionId,
            analysis_type: "POSITION_UPDATE",
            request_status: "COMPLETED",
            current_price: "5000",
            observation_period: "MORNING",
            observation_timestamp: "2026-01-01T08:00:00Z",
            processed_response: { update_summary: "Posisi stabil" },
            error_code: null,
            error_message: null,
            created_at: "2026-01-01T08:00:00Z",
            started_at: "2026-01-01T08:00:00Z",
            completed_at: "2026-01-01T08:05:00Z",
          },
        ],
      }),
    );

    render(<PositionUpdateRecovery sessionId={sessionId} step={step} refetch={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Position Update selesai" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Lihat Hasil Analisis" })).toHaveAttribute(
      "href",
      `/sessions/${sessionId}/analysis`,
    );
  });

  it("renders failed state with retry button when authorized by workflow actions", async () => {
    const user = userEvent.setup();
    const step = makeStep({
      active_request: null,
      failed_request: {
        id: "req-pos-1",
        analysis_type: "POSITION_UPDATE",
        status: "FAILED",
        retry_allowed: true,
      },
    });

    vi.mocked(readPositionUpdates).mockResolvedValue(
      makeReadResponse({
        updates: [
          {
            analysis_request_id: "req-pos-1",
            session_id: sessionId,
            analysis_type: "POSITION_UPDATE",
            request_status: "FAILED",
            current_price: "5000",
            observation_period: "MORNING",
            observation_timestamp: "2026-01-01T08:00:00Z",
            processed_response: null,
            error_code: "ANALYSIS_FAILED",
            error_message: "Gagal memproses gambar",
            created_at: "2026-01-01T08:00:00Z",
            started_at: "2026-01-01T08:00:00Z",
            completed_at: null,
          },
        ],
      }),
    );

    vi.mocked(submitPositionUpdateAnalysis).mockResolvedValue({
      analysis_request_id: "req-pos-2",
      session_id: sessionId,
      position_id: "pos-1",
      evidence_id: "ev-pos-1",
      analysis_type: "POSITION_UPDATE",
      request_status: "PENDING",
      observation_period: "MORNING",
      session_status: "OPEN_POSITION",
      position_status: "OPEN",
      created_at: "2026-01-01T08:10:00Z",
    });

    const refetchMock = vi.fn().mockResolvedValue({});

    render(<PositionUpdateRecovery sessionId={sessionId} step={step} refetch={refetchMock} />);

    expect(await screen.findByRole("heading", { name: "Position Update belum berhasil" })).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: "Coba Lagi" });
    await user.click(retryBtn);

    expect(submitPositionUpdateAnalysis).toHaveBeenCalledWith(sessionId);
    await waitFor(() => expect(refetchMock).toHaveBeenCalled());
  });

  it("renders read-only failed state without retry button when retry is not authorized", async () => {
    const step = makeStep({
      workflow_actions: [],
      active_request: null,
      failed_request: {
        id: "req-pos-1",
        analysis_type: "POSITION_UPDATE",
        status: "FAILED",
        retry_allowed: false,
      },
    });

    vi.mocked(readPositionUpdates).mockResolvedValue(
      makeReadResponse({
        updates: [
          {
            analysis_request_id: "req-pos-1",
            session_id: sessionId,
            analysis_type: "POSITION_UPDATE",
            request_status: "FAILED",
            current_price: "5000",
            observation_period: "MORNING",
            observation_timestamp: "2026-01-01T08:00:00Z",
            processed_response: null,
            error_code: "ANALYSIS_FAILED",
            error_message: "Gagal memproses gambar",
            created_at: "2026-01-01T08:00:00Z",
            started_at: "2026-01-01T08:00:00Z",
            completed_at: null,
          },
        ],
      }),
    );

    render(<PositionUpdateRecovery sessionId={sessionId} step={step} refetch={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Position Update belum berhasil" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Coba Lagi" })).toBeNull();
  });

  it("displays read error feedback on GET failure and supports GET-only reload", async () => {
    const user = userEvent.setup();
    vi.mocked(readPositionUpdates).mockRejectedValue(new Error("500 Internal Server Error"));

    const refetchMock = vi.fn().mockResolvedValue({});

    render(<PositionUpdateRecovery sessionId={sessionId} step={makeStep()} refetch={refetchMock} />);

    expect(await screen.findByRole("heading", { name: "Status Position Update belum dapat dimuat" })).toBeInTheDocument();

    const reloadBtn = screen.getByRole("button", { name: "Muat Ulang" });
    await user.click(reloadBtn);

    expect(refetchMock).toHaveBeenCalled();
  });

  it("aborts in-flight GET and resets state when sessionId prop changes", () => {
    vi.mocked(readPositionUpdates).mockReturnValue(new Promise(() => {}));

    const { rerender } = render(
      <PositionUpdateRecovery sessionId="session-1" step={makeStep()} refetch={vi.fn()} />,
    );

    rerender(<PositionUpdateRecovery sessionId="session-2" step={makeStep({ active_request: null })} refetch={vi.fn()} />);

    expect(screen.queryByRole("heading", { name: "Position Update sedang diproses" })).toBeNull();
  });
});
