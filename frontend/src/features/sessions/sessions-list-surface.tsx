"use client";

import { useState } from "react";
import Link from "next/link";
import { ButtonSpinner } from "@/components/button-spinner";

import { groupSessions } from "./session-grouping";
import { SessionListCard } from "./session-list-card";
import { useSessionsList } from "./use-sessions-list";

export function SessionsListSurface() {
  const { state, retry } = useSessionsList();
  const [isCreating, setIsCreating] = useState(false);

  if (state.status === "loading") {
    return (
      <p role="status" className="mt-6 text-sm text-[var(--color-text-muted)]">
        Memuat sesi perdagangan…
      </p>
    );
  }

  if (state.status === "authentication-required") {
    return (
      <div role="alert" className="mt-6 text-sm text-[var(--color-status-danger)]">
        <p>Sesi Anda telah berakhir. Silakan masuk kembali.</p>
        <Link
          href="/login?next=%2Fsessions"
          className="mt-3 inline-flex min-h-11 items-center font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          Masuk kembali
        </Link>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div role="alert" className="mt-6 text-sm text-[var(--color-status-danger)]">
        <p>Daftar sesi tidak dapat dimuat. Silakan coba lagi.</p>
        <button
          type="button"
          onClick={retry}
          className="mt-3 min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-4 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          Coba lagi
        </button>
      </div>
    );
  }

  if (state.sessions.length === 0) {
    return (
      <div className="mt-8 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-8 text-center shadow-[var(--elevation-low)] sm:p-12">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-blue-600 text-2xl font-bold">
          📊
        </div>
        <h3 className="mt-4 text-lg font-bold text-[var(--color-text-strong)]">
          Belum ada sesi perdagangan.
        </h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-[var(--color-text-muted)]">
          Mulai analisis saham baru Anda dengan mengunggah bukti orderbook dan grafik teknikal untuk evaluasi berbasis AI.
        </p>
        <div className="mt-6">
          <Link
            href="/sessions/new"
            onClick={() => setIsCreating(true)}
            aria-busy={isCreating}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-standard)] bg-[var(--color-action-primary)] px-6 text-sm font-semibold text-[var(--color-text-inverse)] shadow-xs transition-all hover:bg-[var(--color-action-primary-hover)] active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            {isCreating && <ButtonSpinner className="h-4 w-4" />}
            {isCreating ? "Membuka Form…" : "Buat Sesi Baru"}
          </Link>
        </div>
      </div>
    );
  }

  const grouped = groupSessions(state.sessions);

  return (
    <div className="mt-6 min-w-0 space-y-[var(--space-6)]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Link
          href="/sessions/new"
          onClick={() => setIsCreating(true)}
          aria-busy={isCreating}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-standard)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] shadow-xs transition-all hover:bg-[var(--color-action-primary-hover)] active:scale-[0.98] hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          {isCreating && <ButtonSpinner className="h-4 w-4" />}
          {isCreating ? "Membuka Form…" : "Buat Sesi Baru"}
        </Link>
      </div>

      {grouped.invalidSessions.length > 0 ? (
        <p role="alert" className="text-sm text-[var(--color-status-danger)]">
          Sebagian sesi tidak dapat ditampilkan karena status tidak dikenali.
        </p>
      ) : null}

      {grouped.groups
        .filter((group) => group.sessions.length > 0)
        .map((group) => {
          const headingId = `sessions-group-${group.key}`;
          return (
            <section key={group.key} aria-labelledby={headingId} className="min-w-0">
              <h2
                id={headingId}
                className="break-words text-[var(--text-size-section-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]"
              >
                {group.label}
              </h2>
              <ul
                aria-label={`Daftar sesi: ${group.label}`}
                className="mt-[var(--space-3)] space-y-[var(--space-3)]"
              >
                {group.sessions.map((session) => (
                  <li key={session.id} className="min-w-0">
                    <SessionListCard session={session} />
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
    </div>
  );
}
