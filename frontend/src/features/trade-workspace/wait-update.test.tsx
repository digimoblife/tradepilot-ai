import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WaitUpdatePanel } from "./wait-update";
import {
  readWaitUpdateAnalysis,
  retryWaitUpdateAnalysis,
  submitWaitUpdateAnalysis,
  uploadWaitUpdateInput,
} from "./api";
import type { WaitUpdateAnalysisRead } from "./types";

vi.mock("./api", () => ({
  readWaitUpdateAnalysis: vi.fn(),
  retryWaitUpdateAnalysis: vi.fn(),
  submitWaitUpdateAnalysis: vi.fn(),
  uploadWaitUpdateInput: vi.fn(),
}));

const sessionProps = {
  sessionId: "session-a",
  sessionStatus: "WAITING" as const,
  onProcessing: vi.fn(),
  onFinished: vi.fn(),
};

const completed: WaitUpdateAnalysisRead = {
  analysis_request_id: "request-a",
  session_id: "session-a",
  analysis_type: "WAIT_UPDATE",
  request_status: "COMPLETED",
  session_status: "WAITING",
  processed_response: {
    update_summary: "Ringkasan update",
    current_price: "123.45",
    orderbook_assessment: "Orderbook cukup kuat",
    change_from_previous_analysis: "Lebih baik",
    current_entry_condition: "Tunggu konfirmasi",
    key_risks: ["Volatilitas"],
    upside_probability: 0.6,
    downside_probability: 0.4,
    recommended_action: "WAIT",
    next_plan: "Pantau orderbook",
    conclusion: "Belum ada entry",
  },
  error_code: null,
  error_message: null,
  observation_period: "MORNING",
  created_at: "2026-07-30T00:00:00Z",
  started_at: "2026-07-30T00:00:01Z",
  completed_at: "2026-07-30T00:00:02Z",
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(readWaitUpdateAnalysis).mockRejectedValue(new Error("not found"));
});

describe("WAIT Update frontend", () => {
  it("shows only the approved form for WAITING and uploads one multipart input without submitting analysis", async () => {
    const user = userEvent.setup();
    const file = new File(["image"], "orderbook.png", { type: "image/png" });
    vi.mocked(uploadWaitUpdateInput).mockResolvedValue({
      evidence_id: "evidence-a",
      session_id: "session-a",
      evidence_type: "ORDERBOOK",
      original_filename: "orderbook.png",
      mime_type: "image/png",
      size_bytes: 5,
      current_price: "123.45",
      observation_period: "MIDDAY",
      observation_timestamp: "2026-07-30T05:00:00Z",
      uploaded_at: "2026-07-30T05:01:00Z",
      session_status: "WAITING",
    });
    render(<WaitUpdatePanel {...sessionProps} />);

    expect(await screen.findByRole("heading", { name: "WAIT Update" })).toBeTruthy();
    expect(screen.getByLabelText("Orderbook")).toBeTruthy();
    expect(screen.getByLabelText("Harga saat ini")).toBeTruthy();
    expect(screen.getByLabelText("Periode observasi")).toBeTruthy();
    expect(screen.getByLabelText("Waktu observasi")).toBeTruthy();
    expect(screen.queryByLabelText(/chart|grafik/i)).toBeNull();
    expect(screen.getByRole("option", { name: "Pagi" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Siang" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Sore" })).toBeTruthy();

    await user.upload(screen.getByLabelText("Orderbook"), file);
    await user.type(screen.getByLabelText("Harga saat ini"), "123.45");
    fireEvent.change(screen.getByLabelText("Periode observasi"), { target: { value: "MIDDAY" } });
    fireEvent.change(screen.getByLabelText("Waktu observasi"), { target: { value: "2026-07-30T12:00" } });
    fireEvent.submit(screen.getByRole("button", { name: "Terima Input WAIT Update" }).closest("form")!);

    await waitFor(() => expect(uploadWaitUpdateInput).toHaveBeenCalledTimes(1));
    expect(uploadWaitUpdateInput).toHaveBeenCalledWith("session-a", {
      orderbook: file,
      current_price: "123.45",
      observation_period: "MIDDAY",
      observation_timestamp: expect.any(String),
    });
    expect(submitWaitUpdateAnalysis).not.toHaveBeenCalled();
    expect(await screen.findByText(/Input WAIT Update diterima/)).toBeTruthy();
  });

  it("requires input, sends one bodyless submission, and prevents duplicate clicks", async () => {
    const user = userEvent.setup();
    const file = new File(["image"], "orderbook.png", { type: "image/png" });
    vi.mocked(uploadWaitUpdateInput).mockResolvedValue({
      evidence_id: "evidence-a", session_id: "session-a", evidence_type: "ORDERBOOK",
      original_filename: "orderbook.png", mime_type: "image/png", size_bytes: 5,
      current_price: "123", observation_period: "MORNING",
      observation_timestamp: "2026-07-30T05:00:00Z", uploaded_at: "2026-07-30T05:01:00Z",
      session_status: "WAITING",
    });
    vi.mocked(submitWaitUpdateAnalysis).mockResolvedValue({
      analysis_request_id: "request-a", session_id: "session-a", analysis_type: "WAIT_UPDATE",
      request_status: "PENDING", evidence_id: "evidence-a", observation_period: "MORNING",
      session_status: "ANALYZING", created_at: "2026-07-30T00:00:00Z",
    });
    render(<WaitUpdatePanel {...sessionProps} />);
    await screen.findByRole("heading", { name: "WAIT Update" });
    await user.upload(screen.getByLabelText("Orderbook"), file);
    await user.type(screen.getByLabelText("Harga saat ini"), "123");
    fireEvent.change(screen.getByLabelText("Periode observasi"), { target: { value: "MORNING" } });
    fireEvent.change(screen.getByLabelText("Waktu observasi"), { target: { value: "2026-07-30T08:00" } });
    fireEvent.submit(screen.getByRole("button", { name: "Terima Input WAIT Update" }).closest("form")!);
    await screen.findByText(/Input WAIT Update diterima/);

    let resolveSubmission: (() => void) | undefined;
    vi.mocked(submitWaitUpdateAnalysis).mockReturnValue(new Promise((resolve) => {
      resolveSubmission = () => resolve({
        analysis_request_id: "request-a", session_id: "session-a", analysis_type: "WAIT_UPDATE",
        request_status: "PENDING", evidence_id: "evidence-a", observation_period: "MORNING",
        session_status: "ANALYZING", created_at: "2026-07-30T00:00:00Z",
      });
    }));
    const submitButton = screen.getByRole("button", { name: "Minta WAIT Update Analysis" });
    await user.click(submitButton);
    await user.click(submitButton);
    expect(submitWaitUpdateAnalysis).toHaveBeenCalledTimes(1);
    expect(submitWaitUpdateAnalysis).toHaveBeenCalledWith("session-a");
    resolveSubmission?.();
    expect(await screen.findByRole("status")).toHaveTextContent("sedang diproses");
    expect(sessionProps.onProcessing).toHaveBeenCalledTimes(1);
  });

  it("renders all approved completed sections and never renders raw or input snapshot fields", async () => {
    vi.mocked(readWaitUpdateAnalysis).mockResolvedValue(completed);
    render(<WaitUpdatePanel {...sessionProps} />);
    expect(await screen.findByRole("heading", { name: "Hasil WAIT Update" })).toBeTruthy();
    for (const label of [
      "Ringkasan Update", "Harga Saat Ini", "Analisis Orderbook",
      "Perubahan Dibanding Analisis Sebelumnya", "Kondisi Entry Saat Ini",
      "Risiko Utama", "Peluang Kenaikan", "Peluang Penurunan",
      "Rekomendasi BUY, WAIT, atau SKIP", "Trading Plan Berikutnya", "Kesimpulan AI",
    ]) expect(screen.getByRole("heading", { name: label })).toBeTruthy();
    expect(screen.queryByText(/raw_response|input_snapshot/i)).toBeNull();
    expect(sessionProps.onFinished).toHaveBeenCalled();
  });

  it("offers explicit recovery for FAILED and PENDING plus WAITING without uploading again", async () => {
    const user = userEvent.setup();
    const failed: WaitUpdateAnalysisRead = {
      ...completed,
      request_status: "FAILED",
      processed_response: null,
      error_code: "SAFE_ERROR",
      error_message: "Kesalahan tersanitasi",
    };
    vi.mocked(readWaitUpdateAnalysis).mockResolvedValue(failed);
    vi.mocked(retryWaitUpdateAnalysis).mockResolvedValue({
      analysis_request_id: "request-a", session_id: "session-a", analysis_type: "WAIT_UPDATE",
      request_status: "PENDING", session_status: "ANALYZING", observation_period: "MORNING",
      created_at: "2026-07-30T00:00:00Z",
    });
    render(<WaitUpdatePanel {...sessionProps} />);
    await screen.findByText("WAIT Update gagal diproses");
    expect(screen.getByText("Coba Lagi")).toBeTruthy();
    await user.click(screen.getByText("Coba Lagi"));
    await waitFor(() => expect(retryWaitUpdateAnalysis).toHaveBeenCalledTimes(1));
    expect(retryWaitUpdateAnalysis).toHaveBeenCalledWith("session-a");
    expect(uploadWaitUpdateInput).not.toHaveBeenCalled();
    expect(sessionProps.onProcessing).toHaveBeenCalledTimes(1);
  });

  it("does not show an active form for non-WAITING sessions", async () => {
    render(<WaitUpdatePanel {...sessionProps} sessionStatus="ANALYZED" />);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByRole("heading", { name: "WAIT Update" })).toBeNull();
    expect(screen.queryByLabelText("Orderbook")).toBeNull();
  });
});
