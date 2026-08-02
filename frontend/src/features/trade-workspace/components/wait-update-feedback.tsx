import type { RequestStatus } from "../types";
import { safeErrorMessage } from "../safe-error";

export function WaitUpdateFeedback({
  error,
  processing,
  requestStatus,
  effectiveSessionStatus,
  retryEligible,
  busy,
  errorCode,
  errorMessage,
  onRetry,
}: {
  error: string | null;
  processing: boolean;
  requestStatus: RequestStatus | undefined;
  effectiveSessionStatus: string;
  retryEligible: boolean;
  busy: boolean;
  errorCode: string | null | undefined;
  errorMessage: string | null | undefined;
  onRetry: () => void;
}) {
  return <>
    {error && <p role="alert" className="break-words rounded-[var(--radius-compact)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-[var(--space-3)] text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{error}</p>}
    {processing && <p role="status" aria-live="polite" aria-busy="true" className="break-words rounded-[var(--radius-standard)] border border-[var(--color-status-processing)] bg-[var(--color-status-processing-subtle)] p-[var(--space-card)] text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-strong)]">WAIT Update sedang diproses. Silakan tunggu.</p>}
    {requestStatus === "FAILED" && <section role="alert" aria-label="WAIT Update gagal diproses" className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-[var(--space-card)]">
      <h3 className="break-words text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">WAIT Update gagal diproses</h3>
      <p className="mt-[var(--space-2)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">Analisis WAIT Update tidak selesai.</p>
      {errorCode && <p className="mt-[var(--space-1)] break-words text-[var(--text-size-label)] leading-[var(--text-line-body)] text-[var(--color-text-muted)]">Kode: {errorCode}</p>}
      <p className="mt-[var(--space-1)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{safeErrorMessage(errorMessage, "wait")}</p>
      {retryEligible && <button type="button" disabled={busy} aria-busy={busy} onClick={onRetry} className="mt-[var(--space-4)] min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-status-danger)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-danger)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{busy ? "Mencoba…" : "Coba Lagi"}</button>}
    </section>}
    {requestStatus === "PENDING" && effectiveSessionStatus === "WAITING" && <section className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] p-[var(--space-card)]">
      <h3 className="break-words text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">WAIT Update menunggu pemulihan antrean</h3>
      <p className="mt-[var(--space-2)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">Permintaan belum masuk ke antrean pemrosesan.</p>
      {retryEligible && <button type="button" disabled={busy} aria-busy={busy} onClick={onRetry} className="mt-[var(--space-4)] min-h-11 rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] bg-[var(--color-surface-action)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)] disabled:cursor-not-allowed disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{busy ? "Mencoba…" : "Coba Lagi"}</button>}
    </section>}
  </>;
}
