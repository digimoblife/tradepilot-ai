import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { submitInitialAnalysis, uploadInitialEvidence } from "@/features/trade-workspace/api";
import { InitialEvidenceActionRoute } from "./initial-evidence-action-route";

const push = vi.fn();
const refetch = vi.fn();
let step = "INITIAL_EVIDENCE" as "INITIAL_EVIDENCE" | "INITIAL_ANALYSIS" | "PROCESSING";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/features/trade-workspace/api", () => ({ uploadInitialEvidence: vi.fn(), submitInitialAnalysis: vi.fn() }));
vi.mock("./use-route-session", () => ({
  useRouteSession: (id: string) => ({ status: "success", session: { id, ticker: "BBRI", company_name: "Bank BRI" } }),
}));
vi.mock("./use-session-current-step", () => ({
  useSessionCurrentStep: () => ({
    status: "success",
    currentStep: {
      code: step,
      mode: step === "PROCESSING" ? "PROCESSING" : "ACTIONABLE",
      workflow_actions: step === "INITIAL_EVIDENCE" ? ["SUBMIT_INITIAL_EVIDENCE"] : step === "INITIAL_ANALYSIS" ? ["REQUEST_INITIAL_ANALYSIS"] : [],
      active_request: null, failed_request: null, read_only: false,
    },
    refetch,
  }),
}));

const sessionA = "11111111-1111-4111-8111-111111111111";
const sessionB = "22222222-2222-4222-8222-222222222222";

function choose(label: string, name: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { files: [new File([name], name, { type: "image/png" })] } });
}

beforeEach(() => {
  vi.clearAllMocks();
  step = "INITIAL_EVIDENCE";
  refetch.mockResolvedValue({ status: "success", currentStep: { code: "INITIAL_ANALYSIS" } });
});

describe("InitialEvidenceActionRoute", () => {
  it("renders exactly the required role inputs and validates their complete selection", () => {
    render(<InitialEvidenceActionRoute sessionId={sessionA} />);
    expect(screen.getAllByLabelText(/Orderbook|Chart 3 Bulan|Chart 6 Bulan|Foreign Flow/)).toHaveLength(4);
    expect(screen.getByLabelText("Foreign Flow — 1W")).toBeRequired();
    const submit = screen.getByRole("button", { name: "Unggah Bukti Awal" });
    expect(submit).toBeDisabled();
    choose("Orderbook", "orderbook-long-file-name-that-must-wrap-on-small-devices.png");
    choose("Chart 3 Bulan", "three.png");
    expect(submit).toBeDisabled();
    choose("Chart 6 Bulan", "six.png");
    expect(screen.getByRole("button", { name: "Unggah Bukti Awal" })).toBeDisabled();
    choose("Foreign Flow — 1W", "foreign-flow.png");
    expect(submit).toBeEnabled();
    expect(screen.getByText(/orderbook-long-file-name/).className).toContain("break-all");
  });

  it("sends one atomic upload under rapid submits and reconciles canonical authority", async () => {
    let resolve!: () => void;
    vi.mocked(uploadInitialEvidence).mockImplementation(() => new Promise<void>((done) => { resolve = done; }) as never);
    render(<InitialEvidenceActionRoute sessionId={sessionA} />);
    choose("Orderbook", "orderbook.png"); choose("Chart 3 Bulan", "three.png"); choose("Chart 6 Bulan", "six.png"); choose("Foreign Flow — 1W", "foreign-flow.png");
    const form = screen.getByRole("button", { name: "Unggah Bukti Awal" }).closest("form")!;
    fireEvent.submit(form); fireEvent.submit(form);
    expect(uploadInitialEvidence).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Unggah Bukti Awal" })).toBeDisabled();
    resolve();
    await waitFor(() => expect(refetch).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Bukti Awal berhasil disimpan. Memeriksa status terbaru sesi…")).toBeInTheDocument();
  });

  it("clears selections on a route change and ignores a stale Session A result", async () => {
    let resolve!: () => void;
    vi.mocked(uploadInitialEvidence).mockImplementation(() => new Promise<void>((done) => { resolve = done; }) as never);
    const view = render(<InitialEvidenceActionRoute sessionId={sessionA} />);
    choose("Orderbook", "orderbook.png"); choose("Chart 3 Bulan", "three.png"); choose("Chart 6 Bulan", "six.png"); choose("Foreign Flow — 1W", "foreign-flow.png");
    fireEvent.submit(screen.getByRole("button", { name: "Unggah Bukti Awal" }).closest("form")!);
    view.rerender(<InitialEvidenceActionRoute sessionId={sessionB} />);
    expect(screen.queryByText("orderbook.png")).toBeNull();
    resolve();
    await Promise.resolve();
    expect(refetch).not.toHaveBeenCalled();
  });

  it("uses a distinct analysis action without files and navigates once after acceptance", async () => {
    step = "INITIAL_ANALYSIS";
    vi.mocked(submitInitialAnalysis).mockResolvedValue({ id: "request-1" } as never);
    render(<InitialEvidenceActionRoute sessionId={sessionA} />);
    expect(screen.queryByLabelText("Orderbook")).toBeNull();
    const submit = screen.getByRole("button", { name: "Mulai Analisis Awal" });
    fireEvent.click(submit); fireEvent.click(submit);
    await waitFor(() => expect(submitInitialAnalysis).toHaveBeenCalledTimes(1));
    expect(push).toHaveBeenCalledTimes(1);
    expect(push).toHaveBeenCalledWith(`/sessions/${sessionA}`);
  });
});
