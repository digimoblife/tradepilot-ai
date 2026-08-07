import { readFileSync } from "node:fs";
import path from "node:path";

import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getSessionDetail } from "@/features/trade-workspace/api";
import type { SessionDetailAggregate } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { useSessionCurrentStep } from "./use-session-current-step";

vi.mock("@/features/trade-workspace/api", () => ({ getSessionDetail: vi.fn() }));

const sessionA = "11111111-1111-4111-8111-111111111111";
const sessionB = "22222222-2222-4222-8222-222222222222";

function detail(code: "INITIAL_EVIDENCE" | "INITIAL_ANALYSIS"): SessionDetailAggregate {
  return {
    session: {
      id: sessionA, ticker: "BBRI", company_name: "Bank BRI", status: "DRAFT",
      initial_note: null, created_at: "2026-08-04T00:00:00Z",
      updated_at: "2026-08-04T00:00:00Z", closed_at: null,
    },
    initial_evidence: [], initial_analysis: null, decisions: [], wait_updates: [],
    position: null, position_updates: [], closure: null,
    latest_analysis: null, recent_activity: [],
    current_step: {
      code,
      mode: "ACTIONABLE",
      workflow_actions: code === "INITIAL_EVIDENCE"
        ? ["SUBMIT_INITIAL_EVIDENCE"]
        : ["REQUEST_INITIAL_ANALYSIS"],
      active_request: null, failed_request: null, read_only: false,
    },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

function Harness({ sessionId }: { sessionId: string }) {
  const state = useSessionCurrentStep(sessionId);
  return (
    <div>
      <span>{state.status}</span>
      {state.status === "success" ? <span>{state.currentStep.code}</span> : null}
    </div>
  );
}

beforeEach(() => vi.clearAllMocks());

describe("useSessionCurrentStep", () => {
  it("owns one cancellable aggregate GET for stable route identity", async () => {
    vi.mocked(getSessionDetail).mockResolvedValue(detail("INITIAL_EVIDENCE"));
    const view = render(<Harness sessionId={sessionA} />);
    await screen.findByText("INITIAL_EVIDENCE");
    expect(getSessionDetail).toHaveBeenCalledWith(sessionA, expect.any(AbortSignal));
    view.rerender(<Harness sessionId={sessionA} />);
    expect(getSessionDetail).toHaveBeenCalledTimes(1);
  });

  it.each([
    [new AuthenticationError(401, "AUTHENTICATION_REQUIRED", "raw"), "authentication-required"],
    [new ApiError(500, "INTERNAL_ERROR", "raw"), "unavailable"],
    [new Error("INVALID_CURRENT_STEP_CONTRACT"), "unavailable"],
  ])("maps aggregate failure safely", async (error, expected) => {
    vi.mocked(getSessionDetail).mockRejectedValue(error);
    render(<Harness sessionId={sessionA} />);
    await waitFor(() => expect(screen.getByText(expected)).toBeInTheDocument());
    expect(screen.queryByText("raw")).toBeNull();
  });

  it("aborts A, clears synchronously, and ignores stale A success", async () => {
    const a = deferred<SessionDetailAggregate>();
    const b = deferred<SessionDetailAggregate>();
    let aSignal: AbortSignal | undefined;
    vi.mocked(getSessionDetail).mockImplementation((id, signal) => {
      if (id === sessionA) { aSignal = signal; return a.promise; }
      return b.promise;
    });
    const view = render(<Harness sessionId={sessionA} />);
    view.rerender(<Harness sessionId={sessionB} />);
    expect(screen.getByText("loading")).toBeInTheDocument();
    expect(aSignal?.aborted).toBe(true);

    await act(async () => {
      a.resolve(detail("INITIAL_EVIDENCE"));
      await Promise.resolve();
    });
    expect(screen.queryByText("INITIAL_EVIDENCE")).toBeNull();

    await act(async () => b.resolve(detail("INITIAL_ANALYSIS")));
    expect(screen.getByText("INITIAL_ANALYSIS")).toBeInTheDocument();

    expect(screen.getByText("INITIAL_ANALYSIS")).toBeInTheDocument();
  });

  it("ignores stale A failure while B remains authoritative", async () => {
    const a = deferred<SessionDetailAggregate>();
    const b = deferred<SessionDetailAggregate>();
    vi.mocked(getSessionDetail).mockImplementation((id) =>
      id === sessionA ? a.promise : b.promise,
    );
    const view = render(<Harness sessionId={sessionA} />);
    view.rerender(<Harness sessionId={sessionB} />);
    await act(async () => {
      a.reject(new Error("stale failure"));
      await Promise.resolve();
    });
    expect(screen.getByText("loading")).toBeInTheDocument();
    expect(screen.queryByText("unavailable")).toBeNull();
    await act(async () => b.resolve(detail("INITIAL_ANALYSIS")));
    expect(screen.getByText("INITIAL_ANALYSIS")).toBeInTheDocument();
  });

  it("aborts on unmount without a state update", async () => {
    const pending = deferred<SessionDetailAggregate>();
    let signal: AbortSignal | undefined;
    vi.mocked(getSessionDetail).mockImplementation((_id, nextSignal) => {
      signal = nextSignal;
      return pending.promise;
    });
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const view = render(<Harness sessionId={sessionA} />);
    view.unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => pending.resolve(detail("INITIAL_EVIDENCE")));
    expect(consoleError).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });

  it("contains no polling, mutation, storage, selected-session, or availability coupling", () => {
    const source = readFileSync(
      path.join(process.cwd(), "src/features/sessions/use-session-current-step.ts"),
      "utf8",
    );
    expect(source).not.toMatch(
      /setInterval|setTimeout|POST|PATCH|DELETE|localStorage|sessionStorage|selectedSession|getAvailableActions|available-actions/,
    );
  });
});
