"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { listSessions } from "@/features/trade-workspace/api";
import type { TradeSessionListItem } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

export type SessionsListState =
  | { status: "loading" }
  | { status: "success"; sessions: TradeSessionListItem[] }
  | { status: "authentication-required" }
  | { status: "error" };

export function useSessionsList(): {
  state: SessionsListState;
  retry: () => void;
} {
  const requestGeneration = useRef(0);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<SessionsListState>({ status: "loading" });

  useEffect(() => {
    const generation = ++requestGeneration.current;
    const controller = new AbortController();

    async function load() {
      setState({ status: "loading" });

      try {
        const response = await listSessions(controller.signal);
        if (controller.signal.aborted || requestGeneration.current !== generation) return;

        setState({
          status: "success",
          sessions: response.sessions.filter(
            (session): session is TradeSessionListItem => session.archived_at === null,
          ),
        });
      } catch (error: unknown) {
        if (controller.signal.aborted || requestGeneration.current !== generation) return;

        if (
          error instanceof AuthenticationError ||
          (error instanceof ApiError && error.status === 401)
        ) {
          setState({ status: "authentication-required" });
        } else {
          setState({ status: "error" });
        }
      }
    }

    void load();

    return () => {
      controller.abort();
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((current) => current + 1);
  }, []);

  return { state, retry };
}
