import Link from "next/link";

import { formatSessionDetailTimestamp } from "@/features/sessions/session-detail-header";
import type {
  AnalysisType,
  SessionActivityType,
  SessionDetailAggregate,
  SessionSummaryClosure,
  SessionSummaryPosition,
} from "@/features/trade-workspace/types";

const ANALYSIS_LABELS: Record<AnalysisType, string> = {
  INITIAL_ANALYSIS: "Analisis Awal",
  WAIT_UPDATE: "Analisis Pembaruan WAIT",
  POSITION_UPDATE: "Analisis Pembaruan Posisi",
};

const ACTIVITY_LABELS: Record<SessionActivityType, string> = {
  SESSION_CREATED: "Sesi dibuat",
  INITIAL_ANALYSIS_COMPLETED: "Analisis Awal selesai",
  WAIT_UPDATE_COMPLETED: "Analisis Pembaruan WAIT selesai",
  POSITION_UPDATE_COMPLETED: "Analisis Pembaruan Posisi selesai",
  BUY_CONFIRMED: "Keputusan BUY dikonfirmasi",
  WAIT_CONFIRMED: "Keputusan WAIT dikonfirmasi",
  SKIP_CONFIRMED: "Keputusan SKIP dikonfirmasi",
  SESSION_CLOSED: "Sesi ditutup",
  SESSION_ARCHIVED: "Sesi diarsipkan",
};

const POSITION_STATUS_LABELS: Record<string, string> = {
  OPEN: "Terbuka",
  CLOSED: "Ditutup",
};

function formatNumber(value: number): string {
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 10 }).format(value);
}

function Timestamp({ value }: { value: string }) {
  const formatted = formatSessionDetailTimestamp(value);
  return formatted ? <time dateTime={value}>{formatted}</time> : null;
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-semibold text-[var(--color-text-muted)]">{label}</dt>
      <dd className="mt-1 break-words text-sm text-[var(--color-text-default)]">{children}</dd>
    </div>
  );
}

export function SessionSummaryContent({
  sessionId,
  detail,
}: {
  sessionId: string;
  detail: SessionDetailAggregate;
}) {
  const analysisHref = `/sessions/${encodeURIComponent(sessionId)}/analysis`;
  const historyHref = `/sessions/${encodeURIComponent(sessionId)}/history`;
  const position = detail.position as SessionSummaryPosition | null;
  const hasPosition = detail.session.status !== "CLOSED_SKIPPED" && position !== null;
  const closure = hasPosition ? detail.closure as SessionSummaryClosure | null : null;

  return (
    <section className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-10 sm:px-6 lg:px-8">
      <div className="grid min-w-0 gap-4 lg:grid-cols-2 lg:gap-6">
        {detail.latest_analysis ? (
          <article className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
            <h2 className="text-lg font-bold text-[var(--color-text-strong)]">Analisis Terbaru</h2>
            <p className="mt-3 break-words text-sm text-[var(--color-text-default)]">
              {ANALYSIS_LABELS[detail.latest_analysis.analysis_type]}
            </p>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              <Timestamp value={detail.latest_analysis.completed_at} />
            </p>
            <p className="mt-3 break-words text-sm text-[var(--color-text-default)]">
              {detail.latest_analysis.has_result
                ? "Hasil analisis terbaru tersedia untuk ditinjau."
                : "Ketersediaan hasil analisis belum dapat dikonfirmasi."}
            </p>
            {detail.latest_analysis.has_result ? (
              <Link href={analysisHref} className="mt-4 inline-flex min-h-11 items-center font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]">
                Lihat Analisis
              </Link>
            ) : null}
          </article>
        ) : null}

        {hasPosition ? (
          <article className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
            <h2 className="text-lg font-bold text-[var(--color-text-strong)]">
              {closure ? "Posisi dan Penutupan" : "Ringkasan Posisi"}
            </h2>
            <dl className="mt-4 grid min-w-0 gap-4 sm:grid-cols-2">
              <Fact label="Status Posisi">{POSITION_STATUS_LABELS[position!.status] ?? "Status posisi tidak tersedia"}</Fact>
              {position!.entry_price !== null ? <Fact label="Harga Masuk">{formatNumber(position!.entry_price)}</Fact> : null}
              {position!.quantity !== null ? <Fact label="Jumlah">{formatNumber(position!.quantity)}</Fact> : null}
              {position!.stop_loss !== null ? <Fact label="Stop Loss">{formatNumber(position!.stop_loss)}</Fact> : null}
              {position!.target_price !== null ? <Fact label="Target Profit">{formatNumber(position!.target_price)}</Fact> : null}
              {position!.entry_timestamp ? <Fact label="Waktu Masuk"><Timestamp value={position!.entry_timestamp} /></Fact> : null}
              {position!.note ? <Fact label="Catatan Posisi">{position!.note}</Fact> : null}
              {closure?.close_price !== null && closure?.close_price !== undefined ? <Fact label="Harga Penutupan">{formatNumber(closure.close_price)}</Fact> : null}
              {closure?.close_timestamp ? <Fact label="Waktu Ditutup"><Timestamp value={closure.close_timestamp} /></Fact> : null}
              {closure?.close_reason ? <Fact label="Alasan Penutupan">{closure.close_reason}</Fact> : null}
              {closure?.note ? <Fact label="Catatan Penutupan">{closure.note}</Fact> : null}
            </dl>
          </article>
        ) : null}

        <article className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
          <h2 className="text-lg font-bold text-[var(--color-text-strong)]">Aktivitas Terbaru</h2>
          {detail.recent_activity.length ? (
            <ol className="mt-4 space-y-3">
              {detail.recent_activity.map((activity, index) => (
                <li key={`${activity.type}-${activity.occurred_at}-${index}`} className="min-w-0 border-b border-[var(--color-border-default)] pb-3 last:border-0 last:pb-0">
                  <p className="break-words text-sm font-semibold text-[var(--color-text-strong)]">{ACTIVITY_LABELS[activity.type]}</p>
                  <p className="mt-1 text-sm text-[var(--color-text-muted)]"><Timestamp value={activity.occurred_at} /></p>
                </li>
              ))}
            </ol>
          ) : null}
          <Link href={historyHref} className="mt-4 inline-flex min-h-11 items-center font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]">
            Lihat Riwayat
          </Link>
        </article>
      </div>
    </section>
  );
}
