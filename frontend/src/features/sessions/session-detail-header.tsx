import Link from "next/link";

import type { SessionStatus, TradeSession } from "@/features/trade-workspace/types";

type StatusPresentation = {
  label: string;
  badgeClassName: string;
};

export const SESSION_DETAIL_STATUS_PRESENTATIONS = {
  DRAFT: {
    label: "Sesi Baru",
    badgeClassName:
      "border-[var(--color-border-default)] bg-[var(--color-surface-muted)] text-[var(--color-text-default)]",
  },
  ANALYZING: {
    label: "Sedang Diproses",
    badgeClassName:
      "border-[var(--color-status-processing)] bg-[var(--color-status-processing-subtle)] text-[var(--color-status-processing)]",
  },
  ANALYZED: {
    label: "Menunggu Keputusan",
    badgeClassName:
      "border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] text-[var(--color-status-warning)]",
  },
  WAITING: {
    label: "Menunggu",
    badgeClassName:
      "border-[var(--color-status-information)] bg-[var(--color-status-information-subtle)] text-[var(--color-status-information)]",
  },
  OPEN_POSITION: {
    label: "Posisi Terbuka",
    badgeClassName:
      "border-[var(--color-status-information)] bg-[var(--color-status-information-subtle)] text-[var(--color-status-information)]",
  },
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
} satisfies Record<SessionStatus, StatusPresentation>;

const UNKNOWN_STATUS_PRESENTATION: StatusPresentation = {
  label: "Status tidak dikenali",
  badgeClassName:
    "border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] text-[var(--color-text-default)]",
};

const SESSION_DETAIL_TIME_FORMATTER = new Intl.DateTimeFormat("id-ID", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const TERMINAL_STATUSES = new Set<string>(["CLOSED", "CLOSED_SKIPPED"]);

export function formatSessionDetailTimestamp(value: string): string | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : SESSION_DETAIL_TIME_FORMATTER.format(date);
}

function statusPresentation(status: string): StatusPresentation {
  return (
    SESSION_DETAIL_STATUS_PRESENTATIONS[status as SessionStatus] ??
    UNKNOWN_STATUS_PRESENTATION
  );
}

function Timestamp({ label, value }: { label: string; value: string }) {
  const formatted = formatSessionDetailTimestamp(value);

  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold text-[var(--color-text-muted)]">{label}</dt>
      <dd className="mt-1 [overflow-wrap:anywhere] text-sm text-[var(--color-text-default)]">
        {formatted ? <time dateTime={value}>{formatted}</time> : <span>waktu tidak tersedia</span>}
      </dd>
    </div>
  );
}

export function SessionDetailHeader({ session }: { session: TradeSession }) {
  const status = statusPresentation(session.status);
  const isKnownStatus = session.status in SESSION_DETAIL_STATUS_PRESENTATIONS;
  const isTerminal = TERMINAL_STATUSES.has(session.status);
  const archivedAt = session.archived_at ?? null;
  const hasConsistentArchiveState = archivedAt !== null && isTerminal;
  const hasInconsistentArchiveState = archivedAt !== null && !isTerminal;
  const formattedArchivedAt = archivedAt
    ? formatSessionDetailTimestamp(archivedAt)
    : null;
  const note = session.note?.trim() ? session.note : null;

  return (
    <section
      aria-labelledby="session-detail-title"
      className="mx-auto flex w-full max-w-[var(--layout-application-max)] min-w-0 flex-1 flex-col px-4 py-8 sm:px-6 sm:py-10 lg:px-8"
    >
      <nav aria-label="Navigasi sesi" className="min-w-0">
        <Link
          href={hasConsistentArchiveState ? "/sessions/archived" : "/sessions"}
          className="inline-flex min-h-11 max-w-full items-center [overflow-wrap:anywhere] text-sm font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          {hasConsistentArchiveState ? "Kembali ke Arsip" : "Kembali ke Sesi"}
        </Link>
      </nav>

      <header className="mt-4 min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
        <div className="grid min-w-0 gap-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
          <div className="min-w-0">
            <h1
              id="session-detail-title"
              className="break-all text-3xl font-bold leading-[var(--text-line-heading)] tracking-tight text-[var(--color-text-strong)]"
            >
              {session.ticker}
            </h1>
            <p className="mt-2 [overflow-wrap:anywhere] text-base text-[var(--color-text-muted)]">
              {session.company_name}
            </p>
          </div>

          <span
            data-canonical-status={isKnownStatus ? session.status : undefined}
            className={`inline-flex max-w-full justify-self-start rounded-full border px-3 py-1.5 text-sm font-semibold leading-[var(--text-line-compact)] sm:justify-self-end ${status.badgeClassName}`}
          >
            {status.label}
          </span>
        </div>

        <dl className="mt-6 grid min-w-0 gap-4 border-t border-[var(--color-border-default)] pt-5 sm:grid-cols-2">
          <Timestamp label="Dibuat" value={session.created_at} />
          <Timestamp label="Diperbarui" value={session.updated_at} />
        </dl>

        {session.status === "CLOSED" ? (
          <p className="mt-5 break-words rounded-[var(--radius-compact)] bg-[var(--color-status-success-subtle)] p-3 text-sm text-[var(--color-text-default)]">
            Sesi ini telah selesai dan tidak dapat dilanjutkan.
          </p>
        ) : null}

        {session.status === "CLOSED_SKIPPED" ? (
          <p className="mt-5 break-words rounded-[var(--radius-compact)] bg-[var(--color-surface-factual)] p-3 text-sm text-[var(--color-text-default)]">
            Sesi ini dilewati tanpa membuka posisi.
          </p>
        ) : null}

        {hasConsistentArchiveState ? (
          <aside
            aria-label="Konteks arsip"
            className="mt-5 min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] p-3 text-sm text-[var(--color-text-default)]"
          >
            <p className="break-words font-semibold">Sesi ini telah diarsipkan.</p>
            <p className="mt-1 break-words">
              Sesi ditampilkan sebagai konteks historis hanya-baca.
            </p>
            <p className="mt-2 [overflow-wrap:anywhere] text-xs text-[var(--color-text-muted)]">
              Diarsipkan: {" "}
              {formattedArchivedAt ? (
                <time dateTime={archivedAt}>{formattedArchivedAt}</time>
              ) : (
                <span>waktu tidak tersedia</span>
              )}
            </p>
          </aside>
        ) : null}

        {hasInconsistentArchiveState ? (
          <p
            role="alert"
            className="mt-5 break-words rounded-[var(--radius-compact)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-3 text-sm text-[var(--color-status-danger)]"
          >
            Data arsip sesi tidak konsisten. Konteks arsip tidak dapat ditampilkan.
          </p>
        ) : null}

        {note ? (
          <section aria-labelledby="initial-note-title" className="mt-6 min-w-0 border-t border-[var(--color-border-default)] pt-5">
            <h2
              id="initial-note-title"
              className="text-sm font-semibold text-[var(--color-text-strong)]"
            >
              Catatan Awal
            </h2>
            <p className="mt-2 whitespace-pre-wrap [overflow-wrap:anywhere] text-sm leading-[var(--text-line-body)] text-[var(--color-text-default)]">
              {note}
            </p>
          </section>
        ) : null}
      </header>
    </section>
  );
}
