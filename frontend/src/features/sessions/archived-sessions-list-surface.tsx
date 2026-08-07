"use client";

import Link from "next/link";

import { useArchivedSessionsList } from "./use-archived-sessions-list";
import type { SessionStatus, TradeSessionListItem } from "@/features/trade-workspace/types";

const TERMINAL_STATUS_PRESENTATIONS: Record<
  string,
  { label: string; badgeClassName: string }
> = {
  CLOSED: {
    label: "Selesai",
    badgeClassName:
      "border-[var(--color-status-success)] bg-[var(--color-status-success-subtle)] text-[var(--color-status-success)]",
  },
  CLOSED_SKIPPED: {
    label: "Dilewati",
    badgeClassName:
      "border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] text-[var(--color-text-default)]",
  },
};

const UNKNOWN_STATUS_PRESENTATION = {
  label: "Status tidak dikenali",
  badgeClassName:
    "border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] text-[var(--color-text-default)]",
};

const TIMESTAMP_FORMATTER = new Intl.DateTimeFormat("id-ID", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function formatTimestamp(value: string | null | undefined): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return TIMESTAMP_FORMATTER.format(parsed);
}

export function ArchivedSessionCard({ session }: { session: TradeSessionListItem }) {
  const statusInfo =
    TERMINAL_STATUS_PRESENTATIONS[session.status as SessionStatus] ?? UNKNOWN_STATUS_PRESENTATION;

  const detailHref = `/sessions/${encodeURIComponent(session.id)}`;
  const formattedArchivedAt = formatTimestamp(session.archived_at);
  const formattedClosedAt = formatTimestamp(session.closed_at);

  return (
    <article className="min-w-0 rounded-[var(--radius-medium)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-4 shadow-[var(--elevation-low)] sm:p-5">
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-base font-bold text-[var(--color-text-strong)]">
              {session.ticker}
            </h3>
            <span
              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusInfo.badgeClassName}`}
            >
              {statusInfo.label}
            </span>
          </div>
          <p className="break-words text-sm text-[var(--color-text-muted)]">
            {session.company_name}
          </p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1 text-xs text-[var(--color-text-muted)]">
            {formattedArchivedAt ? (
              <span>Diarsipkan: {formattedArchivedAt}</span>
            ) : null}
            {formattedClosedAt ? (
              <span>Waktu Ditutup: {formattedClosedAt}</span>
            ) : null}
          </div>
        </div>

        <div className="flex min-w-0 items-center gap-2 pt-2 sm:pt-0">
          <Link
            href={detailHref}
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
          >
            Lihat Sesi
          </Link>
        </div>
      </div>
    </article>
  );
}

export function ArchivedSessionsListSurface() {
  const { state, retry } = useArchivedSessionsList();

  return (
    <main className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-6 sm:px-6 sm:py-8 lg:px-8 space-y-6">
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-[var(--color-border-default)] pb-5">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-[var(--color-text-strong)]">Sesi Diarsipkan</h1>
          <p className="mt-1 break-words text-sm text-[var(--color-text-muted)]">
            Sesi trading yang telah selesai dan dipindahkan dari daftar Sesi.
          </p>
        </div>
        <Link
          href="/sessions"
          className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
        >
          Kembali ke Sesi
        </Link>
      </div>

      {state.status === "loading" ? (
        <p role="status" className="text-sm text-[var(--color-text-muted)]">
          Memuat sesi yang diarsipkan…
        </p>
      ) : state.status === "authentication-required" ? (
        <div role="alert" className="text-sm text-[var(--color-status-error)] space-y-3">
          <p>Sesi Anda telah berakhir. Silakan masuk kembali.</p>
          <Link
            href="/login?next=%2Fsessions%2Farchived"
            className="inline-flex min-h-11 items-center font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            Masuk kembali
          </Link>
        </div>
      ) : state.status === "error" ? (
        <div role="alert" className="text-sm text-[var(--color-status-error)] space-y-3">
          <p>Daftar sesi yang diarsipkan tidak dapat dimuat. Silakan coba lagi.</p>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={retry}
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-4 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              Coba lagi
            </button>
            <Link
              href="/sessions"
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)]"
            >
              Kembali ke Sesi
            </Link>
          </div>
        </div>
      ) : state.sessions.length === 0 ? (
        <div className="rounded-[var(--radius-medium)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-6 text-center space-y-3">
          <h2 className="text-base font-bold text-[var(--color-text-strong)]">
            Belum ada sesi yang diarsipkan
          </h2>
          <p className="text-sm text-[var(--color-text-muted)] max-w-md mx-auto">
            Sesi yang Anda arsipkan setelah selesai akan muncul di sini.
          </p>
          <div className="pt-2">
            <Link
              href="/sessions"
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)]"
            >
              Kembali ke Sesi
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {state.sessions.map((session) => (
            <ArchivedSessionCard key={session.id} session={session} />
          ))}
        </div>
      )}
    </main>
  );
}
