import Link from "next/link";

import type {
  SessionStatus,
  TradeSessionListItem,
} from "@/features/trade-workspace/types";

type StatusPresentation = {
  label: string;
  nextStage: string;
  badgeClassName: string;
};

export const SESSION_STATUS_PRESENTATIONS = {
  DRAFT: {
    label: "Sesi Baru",
    nextStage: "Mulai atau lanjutkan Bukti Awal.",
    badgeClassName:
      "border-[var(--color-border-default)] bg-[var(--color-surface-muted)] text-[var(--color-text-default)]",
  },
  ANALYZING: {
    label: "Sedang Diproses",
    nextStage: "Analisis Awal sedang diproses. Tunggu hingga proses selesai.",
    badgeClassName:
      "border-[var(--color-status-processing)] bg-[var(--color-status-processing-subtle)] text-[var(--color-status-processing)]",
  },
  ANALYZED: {
    label: "Menunggu Keputusan",
    nextStage: "Tinjau Analisis Awal, lalu pilih BUY, WAIT, atau SKIP.",
    badgeClassName:
      "border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] text-[var(--color-status-warning)]",
  },
  WAITING: {
    label: "Menunggu",
    nextStage: "Tinjau hasil terbaru atau kirim Pembaruan WAIT.",
    badgeClassName:
      "border-[var(--color-status-information)] bg-[var(--color-status-information-subtle)] text-[var(--color-status-information)]",
  },
  OPEN_POSITION: {
    label: "Posisi Terbuka",
    nextStage: "Pantau posisi, kirim Pembaruan Posisi, atau tutup sesi.",
    badgeClassName:
      "border-[var(--color-status-information)] bg-[var(--color-status-information-subtle)] text-[var(--color-status-information)]",
  },
  CLOSED: {
    label: "Selesai",
    nextStage: "Tinjau sesi perdagangan yang telah selesai.",
    badgeClassName:
      "border-[var(--color-status-success)] bg-[var(--color-status-success-subtle)] text-[var(--color-status-success)]",
  },
  CLOSED_SKIPPED: {
    label: "Dilewati",
    nextStage: "Tinjau sesi yang dilewati tanpa membuka posisi.",
    badgeClassName:
      "border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] text-[var(--color-text-default)]",
  },
} satisfies Record<SessionStatus, StatusPresentation>;

const UNKNOWN_STATUS_PRESENTATION: StatusPresentation = {
  label: "Status tidak dikenali",
  nextStage: "Buka sesi untuk meninjau status terbaru.",
  badgeClassName:
    "border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] text-[var(--color-text-default)]",
};

const UPDATED_AT_FORMATTER = new Intl.DateTimeFormat("id-ID", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function sessionStatusPresentation(status: string): StatusPresentation {
  return SESSION_STATUS_PRESENTATIONS[status as SessionStatus] ?? UNKNOWN_STATUS_PRESENTATION;
}

export function formatSessionUpdatedAt(value: string): string | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : UPDATED_AT_FORMATTER.format(date);
}

export function SessionListCard({ session }: { session: TradeSessionListItem }) {
  const status = sessionStatusPresentation(session.status);
  const updatedAt = formatSessionUpdatedAt(session.updated_at);

  return (
    <article className="group min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 shadow-xs transition-all duration-200 hover:border-blue-300 hover:shadow-md sm:p-6">
      <div className="grid min-w-0 gap-4 sm:grid-cols-[minmax(0,1fr)_auto]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <h3 className="break-all text-xl font-bold tracking-tight text-[var(--color-text-strong)] group-hover:text-[var(--color-action-primary)] transition-colors">
              {session.ticker}
            </h3>
            <span
              data-canonical-status={session.status}
              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold shadow-2xs ${status.badgeClassName}`}
            >
              {status.label}
            </span>
          </div>

          <p className="mt-1 [overflow-wrap:anywhere] text-sm font-medium text-[var(--color-text-muted)]">
            {session.company_name}
          </p>

          <div className="mt-4 rounded-[var(--radius-compact)] bg-[var(--color-surface-factual)] border border-[var(--color-border-default)] px-3.5 py-2.5">
            <p className="break-words text-xs leading-relaxed text-[var(--color-text-default)]">
              <span className="font-semibold text-[var(--color-text-strong)]">Tahap berikutnya: </span>
              {status.nextStage}
            </p>
          </div>
        </div>

        <div className="flex min-w-0 flex-col items-start gap-4 sm:items-end sm:justify-between sm:pl-4">
          <p className="max-w-full break-words text-xs text-[var(--color-text-muted)] sm:text-right">
            Diperbarui:{" "}
            {updatedAt ? (
              <time dateTime={session.updated_at} className="font-medium text-[var(--color-text-default)]">{updatedAt}</time>
            ) : (
              <span>waktu tidak tersedia</span>
            )}
          </p>
          <Link
            href={`/sessions/${session.id}`}
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-standard)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] shadow-xs transition-all hover:bg-[var(--color-action-primary-hover)] hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
          >
            Buka Sesi
          </Link>
        </div>
      </div>
    </article>
  );
}
