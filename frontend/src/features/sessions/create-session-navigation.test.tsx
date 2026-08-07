import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NewSessionPage from "@/app/sessions/new/page";
import SessionDetailPage from "@/app/sessions/[sessionId]/page";
import { createSession, getSession } from "@/features/trade-workspace/api";
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
  it("pushes the returned canonical ID once only after create succeeds", async () => {
    const user = userEvent.setup();
    const request = deferred<TradeSession>();
    vi.mocked(createSession).mockImplementation(() => request.promise);
    const view = render(<NewSessionPage />);
    await fillRequired(user);

    await user.click(screen.getByRole("button", { name: "Buat Sesi" }));
    expect(screen.getByRole("button", { name: "Membuat sesi…" })).toBeDisabled();
    expect(mockPush).not.toHaveBeenCalled();

    await act(async () => request.resolve(createdSession));

    expect(screen.getByRole("status")).toHaveTextContent("Sesi dibuat. Membuka sesi");
    expect(screen.getByRole("button", { name: "Sesi dibuat" })).toBeDisabled();
    expect(screen.queryByRole("link", { name: "Batal" })).toBeNull();
    expect(mockPush).toHaveBeenCalledTimes(1);
    expect(mockPush).toHaveBeenCalledWith(`/sessions/${createdId}`);
    expect(mockPush).not.toHaveBeenCalledWith("/sessions");
    expect(mockPush).not.toHaveBeenCalledWith("/trade-workspace");

    view.rerender(<NewSessionPage />);
    expect(createSession).toHaveBeenCalledTimes(1);
    expect(mockPush).toHaveBeenCalledTimes(1);
  });

  it("keeps repeated click submission to one POST and one navigation", async () => {
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
    expect(mockPush).toHaveBeenCalledTimes(1);

    fireEvent.submit(form);
    expect(createSession).toHaveBeenCalledTimes(1);
    expect(mockPush).toHaveBeenCalledTimes(1);
  });

  it("keeps repeated Enter submission to one POST and one navigation", async () => {
    const user = userEvent.setup();
    const request = deferred<TradeSession>();
    vi.mocked(createSession).mockImplementation(() => request.promise);
    render(<NewSessionPage />);
    await fillRequired(user);

    screen.getByLabelText("Nama Perusahaan").focus();
    await user.keyboard("{Enter}{Enter}");
    expect(createSession).toHaveBeenCalledTimes(1);

    await act(async () => request.resolve(createdSession));
    expect(mockPush).toHaveBeenCalledTimes(1);
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
    await user.click(screen.getByRole("button", { name: "Buat Sesi" }));

    if (error) await screen.findByRole("alert");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("does not navigate when a successful response lacks a usable canonical ID", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue({ ...createdSession, id: "not-a-canonical-id" });
    render(<NewSessionPage />);
    await fillRequired(user);

    await user.click(screen.getByRole("button", { name: "Buat Sesi" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Halaman sesi baru tidak dapat dibuka",
    );
    expect(screen.getByRole("button", { name: "Sesi dibuat" })).toBeDisabled();
    expect(mockPush).not.toHaveBeenCalled();
    expect(createSession).toHaveBeenCalledTimes(1);
  });

  it("offers deliberate navigation retry without issuing another POST when push cannot start", async () => {
    const user = userEvent.setup();
    vi.mocked(createSession).mockResolvedValue(createdSession);
    mockPush.mockImplementationOnce(() => {
      throw new Error("router internals");
    });
    render(<NewSessionPage />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: "Buat Sesi" }));

    expect(await screen.findByRole("alert")).not.toHaveTextContent("router internals");
    await user.click(screen.getByRole("button", { name: "Buka sesi" }));

    expect(mockPush).toHaveBeenCalledTimes(2);
    expect(mockPush).toHaveBeenLastCalledWith(`/sessions/${createdId}`);
    expect(createSession).toHaveBeenCalledTimes(1);
  });

  it("hands the returned route ID to the existing slow detail recovery boundary", async () => {
    const user = userEvent.setup();
    const detailRequest = deferred<TradeSession>();
    vi.mocked(createSession).mockResolvedValue(createdSession);
    const createView = render(<NewSessionPage />);
    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: "Buat Sesi" }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith(`/sessions/${createdId}`));
    createView.unmount();

    vi.mocked(getSession).mockImplementation(() => detailRequest.promise);
    const detailView = render(
      await SessionDetailPage({ params: Promise.resolve({ sessionId: createdId }) }),
    );

    expect(getSession).toHaveBeenCalledWith(createdId, expect.any(AbortSignal));
    expect(screen.getByRole("status")).toHaveTextContent("Memuat konteks sesi");
    expect(screen.queryByText(createdSession.ticker)).toBeNull();
    expect(screen.queryByText(createdSession.note!)).toBeNull();
    expect(screen.queryByText("AAAA")).toBeNull();

    await act(async () => {
      detailRequest.resolve({ ...createdSession, ticker: "NEWB", note: "Detail canonical" });
    });

    expect(await screen.findByText("NEWB")).toBeInTheDocument();
    expect(screen.queryByText(createdSession.ticker)).toBeNull();
    expect(createSession).toHaveBeenCalledTimes(1);

    detailView.unmount();
    vi.mocked(getSession).mockResolvedValue({
      ...createdSession,
      ticker: "NEWB",
      note: "Detail canonical",
    });
    render(await SessionDetailPage({ params: Promise.resolve({ sessionId: createdId }) }));
    expect(await screen.findByText("NEWB")).toBeInTheDocument();
    expect(getSession).toHaveBeenCalledTimes(2);
    expect(createSession).toHaveBeenCalledTimes(1);
  });

  it.each([
    [
      "not-found",
      new ApiError(404, "SESSION_NOT_FOUND", "raw ownership detail"),
      "Sesi tidak ditemukan atau tidak dapat diakses",
    ],
    [
      "authentication-required",
      new AuthenticationError(401, "AUTHENTICATION_EXPIRED", "raw auth detail"),
      "Sesi Anda telah berakhir",
    ],
    [
      "generic failure",
      new ApiError(500, "INTERNAL_ERROR", "raw database detail"),
      "Konteks sesi tidak dapat dimuat",
    ],
  ])(
    "leaves post-navigation detail %s recovery to the canonical route without recreating",
    async (_label, error, expectedCopy) => {
      const user = userEvent.setup();
      vi.mocked(createSession).mockResolvedValue(createdSession);
      const createView = render(<NewSessionPage />);
      await fillRequired(user);
      await user.click(screen.getByRole("button", { name: "Buat Sesi" }));
      await waitFor(() => expect(mockPush).toHaveBeenCalledWith(`/sessions/${createdId}`));
      createView.unmount();

      vi.mocked(getSession).mockRejectedValue(error);
      render(await SessionDetailPage({ params: Promise.resolve({ sessionId: createdId }) }));

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(expectedCopy);
      expect(alert).not.toHaveTextContent(/raw|database|ownership detail|auth detail/i);
      expect(getSession).toHaveBeenCalledWith(createdId, expect.any(AbortSignal));
      expect(createSession).toHaveBeenCalledTimes(1);
      expect(screen.queryByRole("heading", { name: "Buat Sesi Baru" })).toBeNull();
    },
  );
});
