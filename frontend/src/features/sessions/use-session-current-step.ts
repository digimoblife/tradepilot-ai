"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getSessionDetail } from "@/features/trade-workspace/api";
import type { CurrentStep, SessionDetailAggregate } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

export type SessionCurrentStepState =
  | { status: "loading" }
  | { status: "success"; currentStep: CurrentStep; detail: SessionDetailAggregate }
  | { status: "authentication-required" }
  | { status: "unavailable" };

export type SessionCurrentStepResult = SessionCurrentStepState & {
  refetch: () => Promise<SessionCurrentStepState>;
};

type RequestedState = { sessionId: string; state: SessionCurrentStepState };

export function useSessionCurrentStep(sessionId: string): SessionCurrentStepResult {
  const requestGeneration = useRef(0);
  const mounted = useRef(true);
  const controller = useRef<AbortController | null>(null);
  const [requested, setRequested] = useState<RequestedState>({
    sessionId,
    state: { status: "loading" },
  });

  const load = useCallback(async (requestedSessionId: string): Promise<SessionCurrentStepState> => {
    const generation = ++requestGeneration.current;
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    const loading: SessionCurrentStepState = { status: "loading" };

    if (mounted.current) setRequested({ sessionId: requestedSessionId, state: loading });

    try {
      const detail = await getSessionDetail(requestedSessionId, nextController.signal);
      const result: SessionCurrentStepState = {
        status: "success",
        currentStep: detail.current_step,
        detail,
      };
      if (!nextController.signal.aborted && mounted.current && requestGeneration.current === generation) {
        setRequested({ sessionId: requestedSessionId, state: result });
      }
      return result;
    } catch (error: unknown) {
      const isAuthenticationError =
        error instanceof AuthenticationError ||
        (error instanceof ApiError && error.status === 401);
      const result: SessionCurrentStepState = {
        status: isAuthenticationError ? "authentication-required" : "unavailable",
      };
      if (!nextController.signal.aborted && mounted.current && requestGeneration.current === generation) {
        setRequested({ sessionId: requestedSessionId, state: result });
      }
      return result;
    }
  }, []);

  useEffect(() => {
    // The route-owned canonical request intentionally starts on route identity changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(sessionId);
    return () => controller.current?.abort();
  }, [load, sessionId]);

  useEffect(() => () => {
    mounted.current = false;
    controller.current?.abort();
  }, []);

  const refetch = useCallback(() => load(sessionId), [load, sessionId]);
  const state = requested.sessionId === sessionId ? requested.state : { status: "loading" as const };

  return { ...state, refetch } as SessionCurrentStepResult;
}
