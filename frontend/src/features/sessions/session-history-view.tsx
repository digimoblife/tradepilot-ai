"use client";

import Link from "next/link";
import { useMemo } from "react";

import { useRouteSession } from "@/features/sessions/use-route-session";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import { SessionDetailHeader, formatSessionDetailTimestamp } from "@/features/sessions/session-detail-header";
import { SessionNavigation } from "@/features/sessions/session-navigation";
import type {
  EvidenceFile,
  SessionDetailAggregate,
  SessionSummaryClosure,
  SessionSummaryPosition,
  SkipReason,
} from "@/features/trade-workspace/types";

const SKIP_REASON_LABELS: Record<string, string> = {
  RISK_TOO_HIGH: "Risiko Terlalu Tinggi",
  SETUP_NOT_ATTRACTIVE: "Setup Tidak Menarik",
  ORDERBOOK_WEAK: "Orderbook Lemah",
  MARKET_CONDITION_UNFAVORABLE: "Kondisi Pasar Tidak Mendukung",
  WAITING_TOO_LONG: "Waktu Tunggu Terlalu Lama",
  USER_DECISION: "Keputusan Pengguna",
  OTHER: "Lainnya",
};

export type HistoryEventType =
  | "SESSION_CREATED"
  | "INITIAL_EVIDENCE_UPLOADED"
  | "INITIAL_ANALYSIS_COMPLETED"
  | "WAIT_DECISION"
  | "WAIT_UPDATE_COMPLETED"
  | "BUY_DECISION"
  | "POSITION_CREATED"
  | "POSITION_UPDATE_COMPLETED"
  | "SKIP_DECISION"
  | "CLOSE_COMPLETED";

export interface HistoryEventItem {
  id: string;
  type: HistoryEventType;
  title: string;
  timestamp: string;
  priority: number;
  description?: string | null;
  facts?: Array<{ label: string; value: React.ReactNode }>;
  analysisLink?: boolean;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 10 }).format(value);
}

function Timestamp({ value }: { value: string }) {
  const formatted = formatSessionDetailTimestamp(value);
  return formatted ? <time dateTime={value}>{formatted}</time> : null;
}

export function buildSessionHistoryEvents(detail: SessionDetailAggregate): HistoryEventItem[] {
  const events: HistoryEventItem[] = [];
  const sessionId = detail.session.id;

  // 1. Session Created
  if (detail.session.created_at) {
    events.push({
      id: `session-created-${sessionId}`,
      type: "SESSION_CREATED",
      title: "Sesi Dibuat",
      timestamp: detail.session.created_at,
      priority: 10,
      description: detail.session.initial_note ? `Catatan awal: ${detail.session.initial_note}` : null,
    });
  }

  // 2. Initial Evidence Uploaded
  if (detail.initial_evidence && detail.initial_evidence.length > 0) {
    const earliestEvidence = (detail.initial_evidence as unknown as EvidenceFile[]).reduce((prev, curr) => {
      return prev.uploaded_at < curr.uploaded_at ? prev : curr;
    });
    const evidenceNames = (detail.initial_evidence as unknown as EvidenceFile[])
      .map((e) => e.original_filename)
      .filter(Boolean)
      .join(", ");

    events.push({
      id: `initial-evidence-${sessionId}`,
      type: "INITIAL_EVIDENCE_UPLOADED",
      title: "Bukti Awal Diunggah",
      timestamp: earliestEvidence.uploaded_at,
      priority: 20,
      description: evidenceNames ? `Berkas: ${evidenceNames}` : null,
      facts: [
        { label: "Jumlah Berkas", value: `${detail.initial_evidence.length} berkas` },
      ],
    });
  }

  // 3. Initial Analysis Completed
  const initialAnalysis = detail.initial_analysis as Record<string, unknown> | null;
  if (initialAnalysis && initialAnalysis.status === "COMPLETED" && typeof initialAnalysis.completed_at === "string") {
    events.push({
      id: `initial-analysis-${initialAnalysis.request_id || sessionId}`,
      type: "INITIAL_ANALYSIS_COMPLETED",
      title: "Analisis Awal Selesai",
      timestamp: initialAnalysis.completed_at,
      priority: 30,
      analysisLink: true,
    });
  }

  // 4. Decisions (WAIT, BUY, SKIP)
  if (detail.decisions) {
    detail.decisions.forEach((dec) => {
      if (dec.decision === "WAIT") {
        events.push({
          id: `decision-wait-${dec.decision_id || dec.created_at}`,
          type: "WAIT_DECISION",
          title: "Keputusan WAIT",
          timestamp: dec.created_at,
          priority: 40,
          description: dec.note ? `Catatan: ${dec.note}` : null,
        });
      } else if (dec.decision === "BUY") {
        events.push({
          id: `decision-buy-${dec.decision_id || dec.created_at}`,
          type: "BUY_DECISION",
          title: "Keputusan BUY",
          timestamp: dec.created_at,
          priority: 40,
          description: dec.note ? `Catatan: ${dec.note}` : null,
        });
      } else if (dec.decision === "SKIP") {
        const reasonLabel = dec.reason ? (SKIP_REASON_LABELS[dec.reason as SkipReason] ?? dec.reason) : null;
        events.push({
          id: `decision-skip-${dec.decision_id || dec.created_at}`,
          type: "SKIP_DECISION",
          title: "Keputusan SKIP",
          timestamp: dec.created_at,
          priority: 40,
          description: dec.note ? `Catatan: ${dec.note}` : null,
          facts: reasonLabel ? [{ label: "Alasan Skip", value: reasonLabel }] : undefined,
        });
      }
    });
  }

  // 5. WAIT Updates
  if (detail.wait_updates) {
    detail.wait_updates.forEach((updateRecord) => {
      const update = updateRecord as Record<string, unknown>;
      if (update.status === "COMPLETED" && typeof update.completed_at === "string") {
        const obsPeriod = typeof update.observation_period === "string" ? update.observation_period : null;
        events.push({
          id: `wait-update-${update.request_id || update.completed_at}`,
          type: "WAIT_UPDATE_COMPLETED",
          title: "WAIT Update Selesai",
          timestamp: update.completed_at,
          priority: 45,
          analysisLink: true,
          facts: obsPeriod ? [{ label: "Periode Pengamatan", value: obsPeriod }] : undefined,
        });
      }
    });
  }

  // 6. Position Created
  const position = detail.position as SessionSummaryPosition | null;
  if (position) {
    const posTimestamp = position.entry_timestamp || detail.session.created_at;
    const posFacts: Array<{ label: string; value: React.ReactNode }> = [];
    if (position.entry_price !== null && position.entry_price !== undefined) {
      posFacts.push({ label: "Harga Masuk", value: formatNumber(position.entry_price) });
    }
    if (position.quantity !== null && position.quantity !== undefined) {
      posFacts.push({ label: "Jumlah", value: formatNumber(position.quantity) });
    }
    if (position.stop_loss !== null && position.stop_loss !== undefined) {
      posFacts.push({ label: "Stop Loss", value: formatNumber(position.stop_loss) });
    }
    if (position.target_price !== null && position.target_price !== undefined) {
      posFacts.push({ label: "Target Profit", value: formatNumber(position.target_price) });
    }

    events.push({
      id: `position-created-${sessionId}`,
      type: "POSITION_CREATED",
      title: "Posisi Dibuka",
      timestamp: posTimestamp,
      priority: 50,
      description: position.note ? `Catatan: ${position.note}` : null,
      facts: posFacts.length > 0 ? posFacts : undefined,
    });
  }

  // 7. Position Updates
  if (detail.position_updates) {
    detail.position_updates.forEach((updateRecord) => {
      const update = updateRecord as Record<string, unknown>;
      if (update.status === "COMPLETED" && typeof update.completed_at === "string") {
        const obsPeriod = typeof update.observation_period === "string" ? update.observation_period : null;
        events.push({
          id: `position-update-${update.request_id || update.completed_at}`,
          type: "POSITION_UPDATE_COMPLETED",
          title: "Position Update Selesai",
          timestamp: update.completed_at,
          priority: 60,
          analysisLink: true,
          facts: obsPeriod ? [{ label: "Periode Pengamatan", value: obsPeriod }] : undefined,
        });
      }
    });
  }

  // 8. Close Completed
  const closure = detail.closure as SessionSummaryClosure | null;
  if (closure) {
    const closeTimestamp = closure.close_timestamp || detail.session.closed_at || detail.session.updated_at;
    const closeFacts: Array<{ label: string; value: React.ReactNode }> = [];
    if (closure.close_price !== null && closure.close_price !== undefined) {
      closeFacts.push({ label: "Harga Penutupan", value: formatNumber(closure.close_price) });
    }
    if (closure.close_reason) {
      closeFacts.push({ label: "Alasan Penutupan", value: closure.close_reason });
    }

    events.push({
      id: `closure-${sessionId}`,
      type: "CLOSE_COMPLETED",
      title: "Posisi Ditutup",
      timestamp: closeTimestamp,
      priority: 70,
      description: closure.note ? `Catatan: ${closure.note}` : null,
      facts: closeFacts.length > 0 ? closeFacts : undefined,
    });
  }

  // Chronological ascending sort: oldest first, newest last
  // Tie-breaking: timestamp ascending, priority ascending, id ascending
  events.sort((a, b) => {
    const timeA = new Date(a.timestamp).getTime();
    const timeB = new Date(b.timestamp).getTime();
    if (timeA !== timeB) {
      return timeA - timeB;
    }
    if (a.priority !== b.priority) {
      return a.priority - b.priority;
    }
    return a.id.localeCompare(b.id);
  });

  return events;
}

export function SessionHistoryView({ sessionId }: { sessionId: string }) {
  const routeState = useRouteSession(sessionId);
  const detailState = useSessionCurrentStep(sessionId);

  const events = useMemo(() => {
    if (detailState.status === "success") {
      return buildSessionHistoryEvents(detailState.detail);
    }
    return [];
  }, [detailState]);

  if (routeState.status === "loading" || detailState.status === "loading") {
    return (
      <section className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="sr-only">Riwayat Sesi</h1>
        <Link href={`/sessions/${encodeURIComponent(sessionId)}`} className="sr-only">
          Kembali
        </Link>
        <p role="status" className="text-sm text-[var(--color-text-muted)]">
          Memuat konteks sesi…
        </p>
      </section>
    );
  }

  if (routeState.status !== "success" || detailState.status !== "success") {
    return (
      <section className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-10 sm:px-6 lg:px-8">
        <div role="alert" className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-6 space-y-3">
          <h2 className="text-lg font-bold text-[var(--color-text-strong)]">
            Riwayat belum dapat dimuat
          </h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Riwayat sesi belum dapat dimuat. Silakan coba lagi.
          </p>
          <button
            type="button"
            onClick={() => void detailState.refetch()}
            className="mt-2 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            Muat Ulang
          </button>
        </div>
      </section>
    );
  }

  const isArchived = Boolean(routeState.session.archived_at || detailState.detail.session.archived_at);
  const backHref = `/sessions/${encodeURIComponent(sessionId)}`;
  const analysisHref = `/sessions/${encodeURIComponent(sessionId)}/analysis`;

  return (
    <>
      <SessionDetailHeader session={routeState.session} />
      <SessionNavigation sessionId={sessionId} />

      <main className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <div className="mx-auto max-w-3xl min-w-0 space-y-6">
          <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-[var(--color-text-strong)]">
                  Riwayat Sesi
                </h1>
                {isArchived ? (
                  <span className="inline-flex items-center rounded-full border border-[var(--color-border-default)] bg-[var(--color-surface-muted)] px-2.5 py-0.5 text-xs font-semibold text-[var(--color-text-muted)]">
                    Diarsipkan
                  </span>
                ) : null}
              </div>
              <p className="mt-1 break-words text-sm text-[var(--color-text-muted)]">
                Kronologi lengkap aktivitas dan peristiwa dalam sesi trading ini.
              </p>
            </div>
            <Link
              href={backHref}
              className="inline-flex min-h-11 items-center text-sm font-semibold text-[var(--color-action-primary)] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              ← Kembali ke Ringkasan
            </Link>
          </div>

          {events.length === 0 ? (
            <div className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-6 space-y-3 text-center">
              <h2 className="text-lg font-bold text-[var(--color-text-strong)]">
                Riwayat belum tersedia
              </h2>
              <p className="text-sm text-[var(--color-text-muted)]">
                Belum ada aktivitas yang tercatat untuk sesi ini.
              </p>
              <Link
                href={backHref}
                className="mt-4 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                Kembali ke Ringkasan
              </Link>
            </div>
          ) : (
            <ol className="relative min-w-0 space-y-6 border-l-2 border-[var(--color-border-default)] pl-4 sm:pl-6">
              {events.map((event) => (
                <li key={event.id} className="relative min-w-0 pl-2">
                  <span className="absolute -left-[25px] top-1.5 h-3 w-3 rounded-full border-2 border-[var(--color-surface-standard)] bg-[var(--color-action-primary)] sm:-left-[33px]" />
                  <article className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 shadow-[var(--elevation-low)] space-y-3">
                    <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
                      <h2 className="break-words text-base font-bold text-[var(--color-text-strong)]">
                        {event.title}
                      </h2>
                      <span className="text-xs text-[var(--color-text-muted)]">
                        <Timestamp value={event.timestamp} />
                      </span>
                    </div>

                    {event.description ? (
                      <p className="break-words text-sm text-[var(--color-text-default)]">
                        {event.description}
                      </p>
                    ) : null}

                    {event.facts && event.facts.length > 0 ? (
                      <dl className="grid min-w-0 gap-3 border-t border-[var(--color-border-default)] pt-3 sm:grid-cols-2">
                        {event.facts.map((fact, fIdx) => (
                          <div key={`${event.id}-fact-${fIdx}`} className="min-w-0">
                            <dt className="text-xs font-semibold text-[var(--color-text-muted)]">
                              {fact.label}
                            </dt>
                            <dd className="mt-0.5 break-words text-sm font-semibold text-[var(--color-text-strong)]">
                              {fact.value}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    ) : null}

                    {event.analysisLink ? (
                      <div className="pt-1">
                        <Link
                          href={analysisHref}
                          className="inline-flex min-h-11 items-center text-sm font-semibold text-[var(--color-action-primary)] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
                        >
                          Lihat Hasil Analisis →
                        </Link>
                      </div>
                    ) : null}
                  </article>
                </li>
              ))}
            </ol>
          )}
        </div>
      </main>
    </>
  );
}
