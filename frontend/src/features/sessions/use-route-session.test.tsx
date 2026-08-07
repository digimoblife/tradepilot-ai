import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getSession } from "@/features/trade-workspace/api";
import type { TradeSession } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { useRouteSession } from "./use-route-session";

vi.mock("@/features/trade-workspace/api", () => ({
  getSession: vi.fn(),
}));

const sessionAId = "11111111-1111-4111-8111-111111111111";
const sessionBId = "22222222-2222-4222-8222-222222222222";

function session(id: string, ticker: string): TradeSession {
  return {
    id,
    ticker,
    company_name: `${ticker} Company`,
    status: "DRAFT",
    note: null,
    created_at: "2026-08-04T00:00:00Z",
    updated_at: "2026-08-04T00:00:00Z",
    closed_at: null,
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

function HookHarness({ sessionId }: { sessionId: string }) {
  const state = useRouteSession(sessionId);
  return (
    <div>
      <span>{state.status}</span>
      {state.status === "success" ? <span>{state.session.ticker}</span> : null}
    </div>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useRouteSession", () => {
  it("loads a valid URL-owned session and keeps same-ID rerenders stable", async () => {
    vi.mocked(getSession).mockResolvedValue(session(sessionAId, "AAAA"));
    const view = render(<HookHarness sessionId={sessionAId} />);

    expect(screen.getByText("loading")).toBeInTheDocument();
    await screen.findByText("AAAA");
    expect(getSession).toHaveBeenCalledWith(sessionAId, expect.any(AbortSignal));

    view.rerender(<HookHarness sessionId={sessionAId} />);
    expect(getSession).toHaveBeenCalledTimes(1);
  });

  it("rejects a malformed UUID without calling the API", () => {
    render(<HookHarness sessionId="not-a-uuid" />);

    expect(screen.getByText("not-found")).toBeInTheDocument();
    expect(getSession).not.toHaveBeenCalled();
  });

  it.each([
    [new ApiError(404, "SESSION_NOT_FOUND", "hidden"), "not-found"],
    [new AuthenticationError(401, "AUTHENTICATION_REQUIRED", "hidden"), "authentication-required"],
    [new ApiError(401, "INTERNAL_ERROR", "hidden"), "authentication-required"],
    [new ApiError(500, "INTERNAL_ERROR", "database detail"), "error"],
    [new TypeError("network detail"), "error"],
  ])("maps API failure safely to %s", async (error, expectedStatus) => {
    vi.mocked(getSession).mockRejectedValue(error);
    render(<HookHarness sessionId={sessionAId} />);

    await waitFor(() => {
      expect(screen.getByText(expectedStatus)).toBeInTheDocument();
    });
  });

  it("aborts A, clears it immediately, and ignores a late A success after navigation to B", async () => {
    const a = deferred<TradeSession>();
    const b = deferred<TradeSession>();
    let aSignal: AbortSignal | undefined;

    vi.mocked(getSession).mockImplementation((id, signal) => {
      if (id === sessionAId) {
        aSignal = signal;
        return a.promise;
      }
      return b.promise;
    });

    const view = render(<HookHarness sessionId={sessionAId} />);
    expect(screen.getByText("loading")).toBeInTheDocument();

    view.rerender(<HookHarness sessionId={sessionBId} />);
    expect(screen.getByText("loading")).toBeInTheDocument();
    expect(screen.queryByText("AAAA")).toBeNull();
    expect(aSignal?.aborted).toBe(true);

    await act(async () => {
      a.resolve(session(sessionAId, "AAAA"));
      await Promise.resolve();
    });
    expect(screen.queryByText("AAAA")).toBeNull();
    expect(screen.getByText("loading")).toBeInTheDocument();

    await act(async () => {
      b.resolve(session(sessionBId, "BBBB"));
    });
    expect(screen.getByText("BBBB")).toBeInTheDocument();
    expect(screen.queryByText("AAAA")).toBeNull();
  });

  it("removes previously successful A data synchronously while B loads", async () => {
    const b = deferred<TradeSession>();
    vi.mocked(getSession).mockImplementation((id) =>
      id === sessionAId ? Promise.resolve(session(sessionAId, "AAAA")) : b.promise,
    );

    const view = render(<HookHarness sessionId={sessionAId} />);
    await screen.findByText("AAAA");

    view.rerender(<HookHarness sessionId={sessionBId} />);
    expect(screen.queryByText("AAAA")).toBeNull();
    expect(screen.getByText("loading")).toBeInTheDocument();

    await act(async () => {
      b.resolve(session(sessionBId, "BBBB"));
    });
    expect(screen.getByText("BBBB")).toBeInTheDocument();
    expect(screen.queryByText("AAAA")).toBeNull();
  });

  it("ignores a late A error while B remains authoritative", async () => {
    const a = deferred<TradeSession>();
    const b = deferred<TradeSession>();
    vi.mocked(getSession).mockImplementation((id) =>
      id === sessionAId ? a.promise : b.promise,
    );

    const view = render(<HookHarness sessionId={sessionAId} />);
    view.rerender(<HookHarness sessionId={sessionBId} />);

    await act(async () => {
      a.reject(new ApiError(500, "INTERNAL_ERROR", "stale A error"));
      await Promise.resolve();
    });
    expect(screen.getByText("loading")).toBeInTheDocument();
    expect(screen.queryByText("error")).toBeNull();

    await act(async () => {
      b.resolve(session(sessionBId, "BBBB"));
    });
    expect(screen.getByText("BBBB")).toBeInTheDocument();
  });

  it("aborts on unmount and ignores completion", async () => {
    const pending = deferred<TradeSession>();
    let signal: AbortSignal | undefined;
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.mocked(getSession).mockImplementation((_id, requestSignal) => {
      signal = requestSignal;
      return pending.promise;
    });

    const view = render(<HookHarness sessionId={sessionAId} />);
    view.unmount();
    expect(signal?.aborted).toBe(true);

    await act(async () => {
      pending.resolve(session(sessionAId, "AAAA"));
      await Promise.resolve();
    });
    expect(consoleError).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });
});
