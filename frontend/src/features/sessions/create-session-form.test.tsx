import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import NewSessionPage from "@/app/sessions/new/page";
import { createSession, acquireMarketEvidence } from "@/features/trade-workspace/api";
import type { TradeSession } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { CreateSessionForm } from "./create-session-form";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/features/trade-workspace/api", () => ({
  createSession: vi.fn(),
  analyzeSession: vi.fn().mockResolvedValue({}),
  acquireMarketEvidence: vi.fn().mockResolvedValue({
    snapshot: {
      symbol: "BBRI",
      quote: { last_price: 545, change_percent: 0.5 },
      orderbook: { bid_ask_ratio: 1.2, spread: 5 },
      foreign_flow: { foreign_status: "ACCUMULATION" },
      broker_flow: { bandar_status: "ACCUMULATION" },
    },
    validation: { is_valid: true, completeness_status: "COMPLETE", critical_errors: [], warnings: [] },
  }),
}));

const createdSession: TradeSession = {
  id: "33333333-3333-4333-8333-333333333333",
  ticker: "BBRI",
  company_name: "Bank Rakyat Indonesia",
  status: "DRAFT",
  note: null,
  created_at: "2026-08-04T00:00:00Z",
  updated_at: "2026-08-04T00:00:00Z",
  closed_at: null,
  archived_at: null,
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function fillRequired(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Kode Saham"), "  bbri ");
  await user.type(screen.getByLabelText("Nama Perusahaan"), "  Bank Rakyat Indonesia  ");
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("CreateSessionForm", () => {
  it("renders the dedicated route with one-screen quick start product fields", () => {
    render(<NewSessionPage />);
    expect(screen.getByRole("heading", { level: 1, name: "Buat Sesi Baru" })).toBeVisible();
    expect(screen.getByLabelText("Kode Saham")).toBeVisible();
    expect(screen.getByLabelText("Nama Perusahaan")).toBeVisible();
    expect(screen.getByLabelText(/Catatan/)).toBeVisible();
    expect(screen.getByRole("button", { name: "BBCA" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Swing Trade" })).toBeVisible();
    expect(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i })).toBeVisible();
    expect(screen.getByRole("link", { name: "Batal" })).toHaveAttribute("href", "/sessions");
  });

  it("rejects empty and whitespace-only required fields without calling the API", async () => {
    const user = userEvent.setup();
    render(<CreateSessionForm />);

    await user.type(screen.getByLabelText("Kode Saham"), "   ");
    await user.type(screen.getByLabelText("Nama Perusahaan"), "   ");
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));

    expect(screen.getByText("Kode saham wajib diisi.")).toBeVisible();
    expect(screen.getByText("Nama perusahaan wajib diisi.")).toBeVisible();
    expect(screen.getByLabelText("Kode Saham")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Nama Perusahaan")).toHaveAttribute("aria-invalid", "true");
    expect(createSession).not.toHaveBeenCalled();
  });

  it("submits one exact canonical payload with backend-aligned normalization", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue(createdSession);
    render(<CreateSessionForm />);
    await fillRequired(user);
    await user.type(screen.getByLabelText(/Catatan/), "  pertahankan spasi catatan  ");
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));

    await waitFor(() => expect(createSession).toHaveBeenCalledTimes(1));
    expect(createSession).toHaveBeenCalledWith(
      {
        ticker: "BBRI",
        company_name: "Bank Rakyat Indonesia",
        note: "  pertahankan spasi catatan  ",
      },
      expect.any(AbortSignal),
    );
  });

  it("submits an empty optional Note as null", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue(createdSession);
    render(<CreateSessionForm />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));

    await waitFor(() => expect(createSession).toHaveBeenCalledTimes(1));
    expect(vi.mocked(createSession).mock.calls[0][0]).toEqual({
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      note: null,
    });
  });

  it("auto-populates company name when clicking popular ticker chip", async () => {
    const user = userEvent.setup();
    render(<CreateSessionForm />);

    await user.click(screen.getByRole("button", { name: "BBCA" }));
    expect(screen.getByLabelText("Kode Saham")).toHaveValue("BBCA");
    expect(screen.getByLabelText("Nama Perusahaan")).toHaveValue("Bank Central Asia Tbk");
  });

  it("uses a synchronous guard for repeated submit events while pending", async () => {
    const user = userEvent.setup();
    const request = deferred<TradeSession>();
    vi.mocked(createSession).mockImplementation(() => request.promise);
    const { container, unmount } = render(<CreateSessionForm />);
    await fillRequired(user);
    const form = container.querySelector("form")!;

    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(createSession).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Membuat sesi…" })).toBeDisabled();

    unmount();
    await act(async () => request.resolve(createdSession));
  });

  it("retains the successful response and triggers onCreated when clicking Mulai Analisa AI", async () => {
    const user = userEvent.setup();
    const onCreated = vi.fn();
    vi.mocked(createSession).mockResolvedValue(createdSession);
    const view = render(<CreateSessionForm onCreated={onCreated} />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));

    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Mulai Analisa AI/i }));
    expect(onCreated).toHaveBeenCalledWith(createdSession);
    view.unmount();
  });

  it.each([
    new ApiError(422, "VALIDATION_ERROR", "database.internal raw detail"),
    new ApiError(500, "INTERNAL_ERROR", "stack trace secret"),
    new TypeError("network.internal"),
  ])("shows safe feedback, preserves every value, and allows one deliberate resubmit", async (error) => {
    const user = userEvent.setup();
    vi.mocked(createSession)
      .mockRejectedValueOnce(error)
      .mockResolvedValueOnce(createdSession);
    const view = render(<CreateSessionForm />);
    await fillRequired(user);
    await user.type(screen.getByLabelText(/Catatan/), "Catatan tetap");
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Sesi tidak dapat dibuat");
    expect(screen.getByRole("alert")).not.toHaveTextContent(/database|stack trace|secret|network\.internal/i);
    expect(screen.getByLabelText("Kode Saham")).toHaveValue("  bbri ");
    expect(screen.getByLabelText("Nama Perusahaan")).toHaveValue("  Bank Rakyat Indonesia  ");
    expect(screen.getByLabelText(/Catatan/)).toHaveValue("Catatan tetap");
    expect(createSession).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));
    await waitFor(() => expect(createSession).toHaveBeenCalledTimes(2));
    view.unmount();
  });

  it("handles authentication failure with safe login recovery and preserved values", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockRejectedValue(
      new AuthenticationError(401, "AUTHENTICATION_EXPIRED", "token secret"),
    );
    const view = render(<CreateSessionForm />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));

    expect(await screen.findByRole("alert")).not.toHaveTextContent("token secret");
    expect(screen.getByRole("link", { name: "Masuk kembali" })).toHaveAttribute(
      "href",
      "/login?next=%2Fsessions%2Fnew",
    );
    expect(screen.getByLabelText("Kode Saham")).toHaveValue("  bbri ");
    view.unmount();
  });

  it("aborts its client request on unmount without late state updates", async () => {
    const user = userEvent.setup();
    const request = deferred<TradeSession>();
    let signal: AbortSignal | undefined;
    vi.mocked(createSession).mockImplementation((_input, requestSignal) => {
      signal = requestSignal;
      return request.promise;
    });
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const view = render(<CreateSessionForm />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));

    view.unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => request.resolve(createdSession));
    expect(consoleError).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });

  it("uses a mobile-safe single-column form with touch-safe controls", () => {
    const { container } = render(<CreateSessionForm />);
    for (const field of screen.getAllByRole("textbox")) {
      expect(field).toHaveClass("w-full", "min-w-0", "text-base");
    }
    expect(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i })).toHaveClass("min-h-11", "w-full", "sm:w-auto");
    expect(screen.getByRole("link", { name: "Batal" })).toHaveClass("min-h-11", "w-full", "sm:w-auto");
    expect(container.querySelector("form")).toHaveClass("min-w-0");
    expect(container.innerHTML).not.toMatch(/\bw-\[[0-9]+(?:px|rem)/);
  });
});
