"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { formatSessionDetailTimestamp } from "@/features/sessions/session-detail-header";
import { archiveSessionV2, restoreSessionV2 } from "@/features/trade-workspace/api";
import type {
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

export function ArchiveActionButton({
  sessionId,
  ticker,
  isArchiveEligible,
  onSuccess,
}: {
  sessionId: string;
  ticker?: string;
  isArchiveEligible: boolean;
  onSuccess?: () => void;
}) {
  const router = useRouter();
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorFeedback, setErrorFeedback] = useState<string | null>(null);
  const submitInFlightRef = useRef(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  if (!isArchiveEligible) {
    return null;
  }

  const handleConfirm = async () => {
    if (submitInFlightRef.current) return;
    submitInFlightRef.current = true;
    setIsSubmitting(true);
    setErrorFeedback(null);

    try {
      await archiveSessionV2(sessionId);
      if (onSuccess) {
        onSuccess();
      }
      router.push("/sessions/archived");
    } catch (err: unknown) {
      submitInFlightRef.current = false;
      setIsSubmitting(false);
      const message = err instanceof Error ? err.message : "Gagal mengarsipkan sesi.";
      setErrorFeedback(message);
    }
  };

  const handleCancel = () => {
    if (isSubmitting) return;
    setShowConfirm(false);
    setErrorFeedback(null);
    setTimeout(() => {
      triggerRef.current?.focus();
    }, 0);
  };

  if (showConfirm) {
    return (
      <div className="w-full rounded-[var(--radius-medium)] border border-[var(--color-border-default)] bg-[var(--color-surface-muted)] p-4 sm:ml-auto sm:max-w-md space-y-3">
        <h3 className="text-sm font-bold text-[var(--color-text-strong)]">
          Arsipkan Sesi{ticker ? ` ${ticker}` : ""}?
        </h3>
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
          Sesi{ticker ? ` ${ticker}` : ""} akan dipindahkan dari daftar Sesi ke Sesi Diarsipkan. Data, analisis, dan riwayat sesi tetap tersimpan, dan sesi dapat dikembalikan ke daftar selesai nanti.
        </p>
        {errorFeedback ? (
          <p className="text-xs font-semibold text-[var(--color-status-error)]" role="alert">
            {errorFeedback}
          </p>
        ) : null}
        <div className="flex items-center gap-2 pt-1">
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="inline-flex min-h-9 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-3 text-xs font-semibold text-[var(--color-text-inverse)] hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? "Mengarsipkan…" : "Arsipkan Sesi"}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={isSubmitting}
            className="inline-flex min-h-9 items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 text-xs font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] disabled:opacity-50"
          >
            Batal
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      ref={triggerRef}
      type="button"
      onClick={() => setShowConfirm(true)}
      className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-4 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] sm:ml-auto sm:w-auto"
    >
      Arsipkan Sesi
    </button>
  );
}

export function RestoreActionButton({
  sessionId,
  ticker,
  isArchived,
  onSuccess,
}: {
  sessionId: string;
  ticker?: string;
  isArchived: boolean;
  onSuccess?: () => void;
}) {
  const router = useRouter();
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorFeedback, setErrorFeedback] = useState<string | null>(null);
  const submitInFlightRef = useRef(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  if (!isArchived) {
    return null;
  }

  const handleConfirm = async () => {
    if (submitInFlightRef.current) return;
    submitInFlightRef.current = true;
    setIsSubmitting(true);
    setErrorFeedback(null);

    try {
      await restoreSessionV2(sessionId);
      if (onSuccess) {
        onSuccess();
      }
      router.push("/sessions");
    } catch (err: unknown) {
      submitInFlightRef.current = false;
      setIsSubmitting(false);
      const message = err instanceof Error ? err.message : "Sesi tidak dapat dikembalikan ke daftar. Coba lagi.";
      setErrorFeedback(message);
    }
  };

  const handleCancel = () => {
    if (isSubmitting) return;
    setShowConfirm(false);
    setErrorFeedback(null);
    setTimeout(() => {
      triggerRef.current?.focus();
    }, 0);
  };

  if (showConfirm) {
    return (
      <div className="w-full rounded-[var(--radius-medium)] border border-[var(--color-border-default)] bg-[var(--color-surface-muted)] p-4 sm:ml-auto sm:max-w-md space-y-3">
        <h3 className="text-sm font-bold text-[var(--color-text-strong)]">
          Kembalikan sesi ini ke daftar?
        </h3>
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
          Sesi{ticker ? ` ${ticker}` : ""} akan dikembalikan ke bagian Selesai pada daftar Sesi. Status selesai, data, analisis, dan riwayat tetap sama. Trading tidak akan dibuka kembali.
        </p>
        {errorFeedback ? (
          <p className="text-xs font-semibold text-[var(--color-status-error)]" role="alert">
            {errorFeedback}
          </p>
        ) : null}
        <div className="flex items-center gap-2 pt-1">
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="inline-flex min-h-9 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-3 text-xs font-semibold text-[var(--color-text-inverse)] hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? "Mengembalikan…" : "Kembalikan ke Daftar"}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={isSubmitting}
            className="inline-flex min-h-9 items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 text-xs font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] disabled:opacity-50"
          >
            Batal
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      ref={triggerRef}
      type="button"
      onClick={() => setShowConfirm(true)}
      className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:ml-auto sm:w-auto"
    >
      Kembalikan ke Daftar
    </button>
  );
}

export function SessionTerminalSummary({
  sessionId,
  detail,
  onArchiveSuccess,
  onRestoreSuccess,
}: {
  sessionId: string;
  detail: SessionDetailAggregate;
  onArchiveSuccess?: () => void;
  onRestoreSuccess?: () => void;
}) {
  const status = detail.session.status;
  const isClosed = status === "CLOSED";
  const isClosedSkipped = status === "CLOSED_SKIPPED";

  if (!isClosed && !isClosedSkipped) {
    return null;
  }

  const isArchived = Boolean(detail.session.archived_at);
  const isArchiveEligible = !isArchived;

  const analysisHref = `/sessions/${encodeURIComponent(sessionId)}/analysis`;
  const historyHref = `/sessions/${encodeURIComponent(sessionId)}/history`;

  const position = detail.position as SessionSummaryPosition | null;
  const closure = detail.closure as SessionSummaryClosure | null;
  const skipDecision = detail.decisions.find((d) => d.decision === "SKIP");

  return (
    <section className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8 sm:px-6 sm:pb-10 lg:px-8">
      <div className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6 space-y-6">
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-[var(--color-text-strong)]">
                {isClosed ? "Sesi Selesai" : "Sesi Dilewati"}
              </h2>
              {isArchived ? (
                <span className="inline-flex items-center rounded-full border border-[var(--color-border-default)] bg-[var(--color-surface-muted)] px-2.5 py-0.5 text-xs font-semibold text-[var(--color-text-muted)]">
                  Diarsipkan
                </span>
              ) : null}
            </div>
            <p className="mt-1 break-words text-sm text-[var(--color-text-muted)]">
              {isClosed
                ? "Posisi telah ditutup dan sesi ini sekarang hanya dapat dibaca."
                : "Sesi diakhiri melalui keputusan SKIP dan sekarang hanya dapat dibaca."}
            </p>
          </div>
        </div>

        {isClosed ? (
          <dl className="grid min-w-0 gap-4 border-t border-[var(--color-border-default)] pt-5 sm:grid-cols-2 lg:grid-cols-3">
            <Fact label="Status Posisi">Ditutup</Fact>
            {closure?.close_price !== null && closure?.close_price !== undefined ? (
              <Fact label="Harga Penutupan">{formatNumber(closure.close_price)}</Fact>
            ) : null}
            {closure?.close_timestamp ? (
              <Fact label="Waktu Ditutup">
                <Timestamp value={closure.close_timestamp} />
              </Fact>
            ) : null}
            {closure?.close_reason ? (
              <Fact label="Alasan Penutupan">{closure.close_reason}</Fact>
            ) : null}
            {closure?.note ? <Fact label="Catatan Penutupan">{closure.note}</Fact> : null}
            {position?.entry_price !== null && position?.entry_price !== undefined ? (
              <Fact label="Harga Masuk">{formatNumber(position.entry_price)}</Fact>
            ) : null}
            {position?.quantity !== null && position?.quantity !== undefined ? (
              <Fact label="Jumlah">{formatNumber(position.quantity)}</Fact>
            ) : null}
            {position?.stop_loss !== null && position?.stop_loss !== undefined ? (
              <Fact label="Stop Loss">{formatNumber(position.stop_loss)}</Fact>
            ) : null}
            {position?.target_price !== null && position?.target_price !== undefined ? (
              <Fact label="Target Profit">{formatNumber(position.target_price)}</Fact>
            ) : null}
            {position?.entry_timestamp ? (
              <Fact label="Waktu Masuk">
                <Timestamp value={position.entry_timestamp} />
              </Fact>
            ) : null}
          </dl>
        ) : (
          <dl className="grid min-w-0 gap-4 border-t border-[var(--color-border-default)] pt-5 sm:grid-cols-2">
            <Fact label="Keputusan">SKIP</Fact>
            {skipDecision?.reason ? (
              <Fact label="Alasan Skip">
                {SKIP_REASON_LABELS[skipDecision.reason as SkipReason] ?? skipDecision.reason}
              </Fact>
            ) : null}
            {skipDecision?.created_at ? (
              <Fact label="Waktu Keputusan">
                <Timestamp value={skipDecision.created_at} />
              </Fact>
            ) : null}
            {skipDecision?.note ? <Fact label="Catatan Skip">{skipDecision.note}</Fact> : null}
          </dl>
        )}

        <div className="flex min-w-0 flex-wrap items-center gap-3 border-t border-[var(--color-border-default)] pt-4">
          <Link
            href={analysisHref}
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
          >
            Lihat Analisis
          </Link>
          <Link
            href={historyHref}
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
          >
            Lihat Riwayat
          </Link>
          {isArchiveEligible ? (
            <ArchiveActionButton
              sessionId={sessionId}
              ticker={detail.session.ticker}
              isArchiveEligible={isArchiveEligible}
              onSuccess={onArchiveSuccess}
            />
          ) : (
            <RestoreActionButton
              sessionId={sessionId}
              ticker={detail.session.ticker}
              isArchived={isArchived}
              onSuccess={onRestoreSuccess}
            />
          )}
        </div>
      </div>
    </section>
  );
}
