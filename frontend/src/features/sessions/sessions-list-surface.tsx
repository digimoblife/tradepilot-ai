"use client";

import Link from "next/link";

import { groupSessions } from "./session-grouping";
import { SessionListCard } from "./session-list-card";
import { useSessionsList } from "./use-sessions-list";

export function SessionsListSurface() {
  const { state, retry } = useSessionsList();

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
      <div className="mt-6 text-sm text-[var(--color-text-muted)]">
        <p>Belum ada sesi perdagangan.</p>
        <Link
          href="/sessions/new"
          className="mt-3 inline-flex min-h-11 items-center font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          Buat sesi baru
        </Link>
      </div>
    );
  }

  const grouped = groupSessions(state.sessions);

  return (
    <div className="mt-6 min-w-0 space-y-[var(--space-8)]">
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
