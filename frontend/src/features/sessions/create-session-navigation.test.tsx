import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NewSessionPage from "@/app/sessions/new/page";
import SessionDetailPage from "@/app/sessions/[sessionId]/page";
import { createSession, getSession, getSessionWorkspaceData } from "@/features/trade-workspace/api";
import type { TradeSession } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/sessions/11111111-1111-4111-8111-111111111111",
}));

vi.mock("@/features/trade-workspace/api", () => ({
  createSession: vi.fn(),
  getSession: vi.fn(),
  analyzeSession: vi.fn().mockResolvedValue({}),
  getSessionWorkspaceData: vi.fn().mockResolvedValue({
    session: {
      id: "33333333-3333-4333-8333-333333333333",
      ticker: "BBRI",
      company_name: "Bank Rakyat Indonesia",
      status: "DRAFT",
      note: null,
      created_at: "2026-08-04T00:00:00Z",
      updated_at: "2026-08-04T00:00:00Z",
      closed_at: null,
      archived_at: null,
    },
    analysis: null,
    position: null,
    closure: null,
    decision: null,
  }),
  acquireMarketEvidence: vi.fn().mockResolvedValue({ snapshot: {} }),
}));

const createdId = "33333333-3333-4333-8333-333333333333";
const createdSession: TradeSession = {
  id: createdId,
  ticker: "BBRI",
  company_name: "Bank Rakyat Indonesia",
  status: "DRAFT",
  note: "Respons create bukan detail authoritative",
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
  await user.type(screen.getByLabelText("Kode Saham"), "bbri");
  await user.type(screen.getByLabelText("Nama Perusahaan"), "Bank Rakyat Indonesia");
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("UX3.5 create success navigation", () => {
  it("pushes the returned canonical ID once only after create succeeds and start analysis is clicked", async () => {
    const user = userEvent.setup();
    const request = deferred<TradeSession>();
    vi.mocked(createSession).mockImplementation(() => request.promise);
    const view = render(<NewSessionPage />);
    await fillRequired(user);

    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));
    expect(screen.getByRole("button", { name: "Membuat sesi…" })).toBeDisabled();
    expect(mockPush).not.toHaveBeenCalled();

    await act(async () => request.resolve(createdSession));

    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Mulai Analisa AI/i }));

    expect(mockPush).toHaveBeenCalledTimes(1);
    expect(mockPush).toHaveBeenCalledWith(`/sessions/${createdId}`);
    expect(mockPush).not.toHaveBeenCalledWith("/sessions");
    expect(mockPush).not.toHaveBeenCalledWith("/trade-workspace");

    view.rerender(<NewSessionPage />);
    expect(createSession).toHaveBeenCalledTimes(1);
    expect(mockPush).toHaveBeenCalledTimes(1);
  });

  it("keeps repeated click submission to one POST", async () => {
    const user = userEvent.setup();
    const request = deferred<TradeSession>();
    vi.mocked(createSession).mockImplementation(() => request.promise);
    const { container } = render(<NewSessionPage />);
    await fillRequired(user);
    const form = container.querySelector("form")!;

    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(createSession).toHaveBeenCalledTimes(1);

    await act(async () => request.resolve(createdSession));
    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
  });

  it("keeps repeated Enter submission to one POST", async () => {
    const user = userEvent.setup();
    const request = deferred<TradeSession>();
    vi.mocked(createSession).mockImplementation(() => request.promise);
    render(<NewSessionPage />);
    await fillRequired(user);

    screen.getByLabelText("Nama Perusahaan").focus();
    await user.keyboard("{Enter}{Enter}");
    expect(createSession).toHaveBeenCalledTimes(1);

    await act(async () => request.resolve(createdSession));
    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
  });

  it.each([
    ["validation", null],
    ["authentication", new AuthenticationError(401, "AUTHENTICATION_EXPIRED", "raw")],
    ["server", new ApiError(500, "INTERNAL_ERROR", "raw")],
    ["network", new TypeError("raw")],
  ])("does not navigate after %s failure", async (_label, error) => {
    const user = userEvent.setup();
    if (error) vi.mocked(createSession).mockRejectedValue(error);
    render(<NewSessionPage />);

    if (error) await fillRequired(user);
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));

    if (error) await screen.findByRole("alert");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("does not navigate when a successful response lacks a usable canonical ID", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue({ ...createdSession, id: "not-a-canonical-id" });
    render(<NewSessionPage />);
    await fillRequired(user);

    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));
    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Mulai Analisa AI/i }));
    expect(mockPush).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent("Halaman sesi baru tidak dapat dibuka");
  });

  it("offers manual retry when router push throws", async () => {
    const user = userEvent.setup();
    mockPush.mockImplementationOnce(() => {
      throw new Error("navigation.error");
    });
    vi.mocked(createSession).mockResolvedValue(createdSession);
    render(<NewSessionPage />);
    await fillRequired(user);

    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));
    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Mulai Analisa AI/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Halaman sesi baru tidak dapat dibuka secara otomatis");
    const retry = screen.getByRole("button", { name: "Buka sesi" });
    expect(retry).toBeVisible();

    mockPush.mockImplementationOnce(() => undefined);
    await user.click(retry);
    expect(mockPush).toHaveBeenCalledWith(`/sessions/${createdId}`);
  });

  it("leaves post-navigation detail loading to the canonical route without recreating", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue(createdSession);
    const createView = render(<NewSessionPage />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));
    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Mulai Analisa AI/i }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith(`/sessions/${createdId}`));
    createView.unmount();

    const detailRequest = deferred<{ session: TradeSession; analysis: any; position: any; closure: any; decision: any }>();
    vi.mocked(getSessionWorkspaceData).mockImplementation(() => detailRequest.promise);
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId: createdId }) }));

    expect(screen.getByRole("status")).toHaveTextContent("Memuat konteks sesi");
    expect(createSession).toHaveBeenCalledTimes(1);
    await act(async () => detailRequest.resolve({ session: createdSession, analysis: null, position: null, closure: null, decision: null }));
  });

  it("leaves post-navigation detail not-found recovery to the canonical route without recreating", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue(createdSession);
    const createView = render(<NewSessionPage />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));
    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Mulai Analisa AI/i }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith(`/sessions/${createdId}`));
    createView.unmount();

    vi.mocked(getSessionWorkspaceData).mockRejectedValue(new ApiError(404, "NOT_FOUND", "Sesi tidak ditemukan atau tidak dapat diakses."));
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId: createdId }) }));

    expect(await screen.findByText(/Sesi tidak ditemukan/i)).toBeVisible();
    expect(createSession).toHaveBeenCalledTimes(1);
  });

  it("leaves post-navigation detail authentication-required recovery to the canonical route without recreating", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue(createdSession);
    const createView = render(<NewSessionPage />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));
    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Mulai Analisa AI/i }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith(`/sessions/${createdId}`));
    createView.unmount();

    vi.mocked(getSessionWorkspaceData).mockRejectedValue(new AuthenticationError(401, "EXPIRED", "Sesi Anda telah berakhir."));
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId: createdId }) }));

    expect(await screen.findByText(/Sesi Anda telah berakhir/i)).toBeVisible();
    expect(createSession).toHaveBeenCalledTimes(1);
  });

  it("leaves post-navigation detail generic failure recovery to the canonical route without recreating", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue(createdSession);
    const createView = render(<NewSessionPage />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: /Ambil Data|Buat Sesi/i }));
    expect(await screen.findByRole("button", { name: /Mulai Analisa AI/i })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Mulai Analisa AI/i }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith(`/sessions/${createdId}`));
    createView.unmount();

    vi.mocked(getSessionWorkspaceData).mockRejectedValue(new ApiError(500, "INTERNAL", "Gagal memuat data workspace sesi."));
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId: createdId }) }));

    expect(await screen.findByText(/Gagal memuat data workspace sesi/i)).toBeVisible();
    expect(createSession).toHaveBeenCalledTimes(1);
  });
});
