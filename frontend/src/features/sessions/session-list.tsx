"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listSessions } from "@/lib/api/trade-sessions";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { TradeSessionSummary } from "@/types/trade-session";
import { SessionCard } from "./session-card";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string; isAuthError: boolean }
  | { status: "loaded"; sessions: TradeSessionSummary[] };

export function SessionList() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState({ status: "loading" });
      try {
        const result = await listSessions();
        if (!cancelled) {
          setState({ status: "loaded", sessions: result.sessions });
        }
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof AuthenticationError) {
          setState({
            status: "error",
            message: "Silakan masuk terlebih dahulu untuk melihat sesi trading.",
            isAuthError: true,
          });
        } else if (e instanceof ApiError) {
          setState({
            status: "error",
            message: e.message,
            isAuthError: false,
          });
        } else {
          setState({
            status: "error",
            message: "Terjadi kesalahan. Silakan coba lagi.",
            isAuthError: false,
          });
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [retryKey]);

  if (state.status === "loading") {
    return (
      <p className="py-12 text-center text-zinc-500">
        Memuat sesi trading…
      </p>
    );
  }

  if (state.status === "error") {
    return (
      <div className="py-12 text-center">
        <p className="text-zinc-600">{state.message}</p>
        <button
          type="button"
          onClick={() => setRetryKey((k) => k + 1)}
          className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Coba Lagi
        </button>
      </div>
    );
  }

  if (state.sessions.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-lg text-zinc-500">Belum ada sesi trading.</p>
        <Link
          href="/sessions/new"
          className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Buat Sesi Baru
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {state.sessions.map((s) => (
        <SessionCard key={s.id} session={s} />
      ))}
    </div>
  );
}
