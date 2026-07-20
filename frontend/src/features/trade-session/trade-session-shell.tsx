"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getSession } from "@/lib/api/trade-sessions";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { TradeSessionDetail } from "@/types/trade-session";
import { SessionHeader } from "./session-header";
import { LifecycleStatus } from "./lifecycle-status";
import { CanonicalPositionSummary } from "./canonical-position-summary";
import { SectionPlaceholder } from "./section-placeholder";
import { actionLabel } from "./helpers";

interface Props {
  sessionId: string;
}

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: TradeSessionDetail };

export function TradeSessionShell({ sessionId }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState({ status: "loading" });
      try {
        const data = await getSession(sessionId);
        if (!cancelled) {
          setState({ status: "loaded", data });
        }
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof AuthenticationError) {
          setState({
            status: "error",
            message: "Silakan masuk terlebih dahulu untuk melihat sesi trading.",
          });
        } else if (e instanceof ApiError) {
          if (e.status === 404) {
            setState({ status: "error", message: "Sesi trading tidak ditemukan." });
          } else {
            setState({ status: "error", message: e.message });
          }
        } else {
          setState({ status: "error", message: "Terjadi kesalahan. Silakan coba lagi." });
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, [sessionId, retryKey]);

  if (state.status === "loading") {
    return (
      <p className="py-12 text-center text-zinc-500">Memuat sesi trading…</p>
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
        <div className="mt-4">
          <Link href="/sessions" className="text-sm text-blue-600 hover:underline">
            &larr; Kembali ke Daftar Sesi
          </Link>
        </div>
      </div>
    );
  }

  const { session, trade_state, allowed_actions } = state.data;

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <SessionHeader session={session} />
      <LifecycleStatus status={session.lifecycle_status} />
      <div className="mt-4">
        <CanonicalPositionSummary tradeState={trade_state} />
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <SectionPlaceholder title="Evidence" message="Evidence sesi akan ditampilkan di sini." />
        <SectionPlaceholder title="Analisis Terbaru" message="Belum ada analisis yang ditampilkan." />
        <SectionPlaceholder title="Rencana Trading" message="Belum tersedia." />
        <SectionPlaceholder title="Probabilitas" message="Belum tersedia." />
        <SectionPlaceholder title="Timeline" message="Riwayat sesi akan ditampilkan di sini." />
        <SectionPlaceholder title="Riwayat Analisis" message="Riwayat analisis akan ditampilkan di sini." />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <PendingActionsSection actions={allowed_actions} />
        <SectionPlaceholder title="Peringatan" message="Tidak ada peringatan." />
      </div>
    </div>
  );
}

function PendingActionsSection({ actions }: { actions: string[] }) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Tindakan Tersedia
      </h3>
      {actions.length === 0 ? (
        <p className="text-sm text-zinc-400">Tidak ada tindakan yang tersedia.</p>
      ) : (
        <ul className="space-y-1">
          {actions.map((a) => (
            <li key={a} className="text-sm text-zinc-700">
              {actionLabel(a)}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
