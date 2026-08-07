import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listSessions } from "@/features/trade-workspace/api";
import type { TradeSessionListItem } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { useSessionsList } from "./use-sessions-list";

vi.mock("@/features/trade-workspace/api", () => ({
  listSessions: vi.fn(),
}));

function session(id: string, ticker: string, archivedAt: string | null = null): TradeSessionListItem {
  return {
    id,
    ticker,
    company_name: `${ticker} Company`,
    status: "DRAFT",
    note: null,
    created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T00:00:00Z",
    closed_at: null,
    archived_at: archivedAt,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function HookHarness() {
  const { state, retry } = useSessionsList();
  return (
    <div>
      <span>{state.status}</span>
      {state.status === "success"
        ? state.sessions.map((item) => <span key={item.id}>{item.ticker}</span>)
        : null}
      <button type="button" onClick={retry}>Retry harness</button>
    </div>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useSessionsList", () => {
  it("loads once on stable renders, preserves backend order, and excludes archived rows", async () => {
    const sessions = [
      session("session-b", "BBBB"),
      session("session-archived", "HIDE", "2026-08-04T01:00:00Z"),
      session("session-a", "AAAA"),
    ];
    vi.mocked(listSessions).mockResolvedValue({ sessions });

    const view = render(<HookHarness />);
    expect(screen.getByText("loading")).toBeInTheDocument();
    await screen.findByText("BBBB");

    expect(screen.getByText("AAAA")).toBeInTheDocument();
    expect(screen.queryByText("HIDE")).toBeNull();
    expect(screen.getAllByText(/AAAA|BBBB/).map((node) => node.textContent)).toEqual([
      "BBBB",
      "AAAA",
    ]);
    expect(listSessions).toHaveBeenCalledWith(expect.any(AbortSignal));

    view.rerender(<HookHarness />);
    expect(listSessions).toHaveBeenCalledTimes(1);
  });

  it.each([
    new AuthenticationError(401, "AUTHENTICATION_REQUIRED", "hidden"),
    new ApiError(401, "INTERNAL_ERROR", "hidden"),
  ])("maps 401 authentication failures to a protected state", async (error) => {
    vi.mocked(listSessions).mockRejectedValue(error);
    render(<HookHarness />);

    await waitFor(() => {
      expect(screen.getByText("authentication-required")).toBeInTheDocument();
    });
  });

  it("maps server and network failures to a generic error state", async () => {
    vi.mocked(listSessions)
      .mockRejectedValueOnce(new ApiError(500, "INTERNAL_ERROR", "database.internal"))
      .mockRejectedValueOnce(new TypeError("network.internal"));

    const first = render(<HookHarness />);
    await screen.findByText("error");
    first.unmount();

    render(<HookHarness />);
    await screen.findByText("error");
  });

  it("starts a fresh retry, clears the previous result, and ignores stale success", async () => {
    const first = deferred<{ sessions: TradeSessionListItem[] }>();
    const second = deferred<{ sessions: TradeSessionListItem[] }>();
    vi.mocked(listSessions)
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise);

    render(<HookHarness />);
    await userEvent.click(screen.getByRole("button", { name: "Retry harness" }));
    expect(screen.getByText("loading")).toBeInTheDocument();

    await act(async () => {
      second.resolve({ sessions: [session("new", "NEW")] });
    });
    expect(screen.getByText("NEW")).toBeInTheDocument();

    await act(async () => {
      first.resolve({ sessions: [session("stale", "STALE")] });
      await Promise.resolve();
    });
    expect(screen.queryByText("STALE")).toBeNull();
    expect(screen.getByText("NEW")).toBeInTheDocument();
    expect(listSessions).toHaveBeenCalledTimes(2);
  });

  it("does not present the previous successful list while a retry is unresolved", async () => {
    const retry = deferred<{ sessions: TradeSessionListItem[] }>();
    vi.mocked(listSessions)
      .mockResolvedValueOnce({ sessions: [session("old", "OLD")] })
      .mockImplementationOnce(() => retry.promise);

    render(<HookHarness />);
    await screen.findByText("OLD");
    await userEvent.click(screen.getByRole("button", { name: "Retry harness" }));

    expect(screen.getByText("loading")).toBeInTheDocument();
    expect(screen.queryByText("OLD")).toBeNull();

    await act(async () => {
      retry.resolve({ sessions: [session("new", "NEW")] });
    });
    expect(screen.getByText("NEW")).toBeInTheDocument();
  });

  it("ignores a stale failure after a later retry succeeds", async () => {
    const first = deferred<{ sessions: TradeSessionListItem[] }>();
    const second = deferred<{ sessions: TradeSessionListItem[] }>();
    vi.mocked(listSessions)
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise);

    render(<HookHarness />);
    await userEvent.click(screen.getByRole("button", { name: "Retry harness" }));

    await act(async () => {
      second.resolve({ sessions: [session("new", "NEW")] });
    });
    await act(async () => {
      first.reject(new ApiError(500, "INTERNAL_ERROR", "stale failure"));
      await Promise.resolve();
    });

    expect(screen.getByText("NEW")).toBeInTheDocument();
    expect(screen.queryByText("error")).toBeNull();
  });

  it("aborts on unmount and ignores late completion without a state-update warning", async () => {
    const pending = deferred<{ sessions: TradeSessionListItem[] }>();
    let signal: AbortSignal | undefined;
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.mocked(listSessions).mockImplementation((requestSignal) => {
      signal = requestSignal;
      return pending.promise;
    });

    const view = render(<HookHarness />);
    view.unmount();
    expect(signal?.aborted).toBe(true);

    await act(async () => {
      pending.resolve({ sessions: [session("late", "LATE")] });
      await Promise.resolve();
    });
    expect(consoleError).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });
});
