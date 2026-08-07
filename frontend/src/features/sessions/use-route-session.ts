"use client";

import { useEffect, useRef, useState } from "react";

import { getSession } from "@/features/trade-workspace/api";
import type { TradeSession } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

export type RouteSessionState =
  | { status: "loading" }
  | { status: "success"; session: TradeSession }
  | { status: "not-found" }
  | { status: "authentication-required" }
  | { status: "error" };

type RequestedState = {
  sessionId: string;
  state: RouteSessionState;
};

const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isStructurallyValidSessionId(sessionId: string): boolean {
  return uuidPattern.test(sessionId);
}

export function useRouteSession(sessionId: string): RouteSessionState {
  const requestGeneration = useRef(0);
  const [requested, setRequested] = useState<RequestedState>({
    sessionId,
    state: { status: "loading" },
  });
  const isValid = isStructurallyValidSessionId(sessionId);

  useEffect(() => {
    if (!isValid) return;

    const generation = ++requestGeneration.current;
    const controller = new AbortController();

    async function load() {
      setRequested({ sessionId, state: { status: "loading" } });

      try {
        const session = await getSession(sessionId, controller.signal);
        if (!controller.signal.aborted && requestGeneration.current === generation) {
          setRequested({ sessionId, state: { status: "success", session } });
        }
      } catch (error: unknown) {
        if (controller.signal.aborted || requestGeneration.current !== generation) return;

        if (
          error instanceof AuthenticationError ||
          (error instanceof ApiError && error.status === 401)
        ) {
          setRequested({ sessionId, state: { status: "authentication-required" } });
        } else if (error instanceof ApiError && error.status === 404) {
          setRequested({ sessionId, state: { status: "not-found" } });
        } else {
          setRequested({ sessionId, state: { status: "error" } });
        }
      }
    }

    void load();

    return () => {
      controller.abort();
    };
  }, [isValid, sessionId]);

  if (!isValid) return { status: "not-found" };
  if (requested.sessionId !== sessionId) return { status: "loading" };
  return requested.state;
}
