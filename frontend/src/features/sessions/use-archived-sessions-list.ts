"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { listArchivedSessions } from "@/features/trade-workspace/api";
import type { TradeSessionListItem } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

export type ArchivedSessionsListState =
  | { status: "loading" }
  | { status: "success"; sessions: TradeSessionListItem[] }
  | { status: "authentication-required" }
  | { status: "error" };

export function useArchivedSessionsList(): {
  state: ArchivedSessionsListState;
  retry: () => void;
} {
  const requestGeneration = useRef(0);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ArchivedSessionsListState>({ status: "loading" });

  useEffect(() => {
    const generation = ++requestGeneration.current;
    const controller = new AbortController();

    async function load() {
      setState({ status: "loading" });

      try {
        const response = await listArchivedSessions(controller.signal);
        if (controller.signal.aborted || requestGeneration.current !== generation) return;

        setState({
          status: "success",
          sessions: response.sessions.map((session) => ({
            ...session,
            archived_at: session.archived_at ?? null,
          })),
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
    setAttempt((prev) => prev + 1);
  }, []);

  return { state, retry };
}
