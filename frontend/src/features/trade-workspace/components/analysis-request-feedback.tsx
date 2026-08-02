import type { InitialAnalysisRead } from "../types";
import { safeErrorMessage } from "../safe-error";

export function AnalysisRequestFeedback({
  analysis,
  complete,
  failed,
  busy,
  onRetry,
}: {
  analysis: InitialAnalysisRead | null;
  complete: boolean;
  failed: boolean;
  busy: boolean;
  onRetry: () => void;
}) {
  if (analysis && !complete && !failed) {
    return <p aria-live="polite" aria-busy="true" className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-status-processing)] bg-[var(--color-status-processing-subtle)] p-[var(--space-card)] text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-strong)]">Analisis sedang diproses. Silakan tunggu.</p>;
  }

  if (!failed) return null;

  return <section role="alert" aria-label="Initial Analysis gagal diproses" className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-[var(--space-card)]">
    <h3 className="break-words text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">Initial Analysis gagal diproses</h3>
    <p className="mt-[var(--space-2)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{safeErrorMessage(analysis?.error_message, "initial")}</p>
    <button type="button" disabled={busy} onClick={onRetry} className="mt-[var(--space-4)] min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-status-danger)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-danger)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{busy ? "Mencoba…" : "Coba Lagi"}</button>
  </section>;
}
