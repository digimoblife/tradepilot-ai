import type { FormEvent } from "react";
import type { SkipReason } from "../types";

export function SkipDecisionForm({
  skipReasons,
  skipReason,
  skipNote,
  busy,
  submitting,
  onReasonChange,
  onNoteChange,
  onSubmit,
}: {
  skipReasons: Array<{ value: SkipReason; label: string }>;
  skipReason: SkipReason | "";
  skipNote: string;
  busy: boolean;
  submitting: boolean;
  onReasonChange: (reason: SkipReason | "") => void;
  onNoteChange: (note: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return <form onSubmit={onSubmit} aria-label="Tutup tanpa posisi" className="min-w-0 space-y-[var(--space-field)] border-t border-[var(--color-border-default)] bg-[var(--color-surface-factual)] p-[var(--space-card)]">
    <h4 className="text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">Tutup tanpa posisi</h4>
    <label className="block min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="skip-reason">Alasan SKIP<select id="skip-reason" required value={skipReason} onChange={(event) => onReasonChange(event.target.value as SkipReason | "")} className="mt-[var(--space-2)] block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]"><option value="">Pilih alasan</option>{skipReasons.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label>
    <label className="block min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="skip-note">Catatan SKIP (opsional)<textarea id="skip-note" value={skipNote} onChange={(event) => onNoteChange(event.target.value)} className="mt-[var(--space-2)] block min-h-20 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" /></label>
    <button type="submit" disabled={busy} aria-busy={submitting} className="min-h-11 rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] bg-[var(--color-surface-action)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)] disabled:cursor-not-allowed disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{submitting ? "Menyimpan…" : "Konfirmasi SKIP"}</button>
  </form>;
}
