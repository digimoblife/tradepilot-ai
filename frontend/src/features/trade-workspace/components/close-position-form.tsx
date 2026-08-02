import type { FormEvent } from "react";

export function ClosePositionForm({ closePrice, closeTimestamp, closeReason, closeNote, busy, onSubmit, onPriceChange, onTimestampChange, onReasonChange, onNoteChange, onCancel }: {
  closePrice: string; closeTimestamp: string; closeReason: string; closeNote: string; busy: boolean; onSubmit: (event: FormEvent) => void;
  onPriceChange: (value: string) => void; onTimestampChange: (value: string) => void; onReasonChange: (value: string) => void; onNoteChange: (value: string) => void; onCancel: () => void;
}) {
  return (
    <form onSubmit={onSubmit} className="overflow-hidden rounded-[var(--radius-large)] border border-[var(--color-status-warning)] bg-[var(--color-surface-factual)] shadow-[var(--elevation-low)]">
      <div className="border-b border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] px-[var(--space-card)] py-[var(--space-5)]">
        <p className="text-[var(--text-size-label)] font-semibold uppercase tracking-[0.08em] text-[var(--color-status-warning)]">Manual action</p>
        <h3 className="mt-1 text-[var(--text-size-section-title)] font-semibold text-[var(--color-text-strong)]">Konfirmasi Tutup Posisi (CLOSE)</h3>
        <p className="mt-2 text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-muted)]">Masukkan data penutupan posisi Anda untuk mengakhiri posisi ini secara manual.</p>
      </div>
      <div className="grid gap-[var(--space-5)] px-[var(--space-card)] py-[var(--space-6)] md:grid-cols-2">
        <label className="block text-[var(--text-size-label)] font-medium" htmlFor="close-price">Harga penutupan<input id="close-price" required inputMode="decimal" value={closePrice} onChange={(e) => onPriceChange(e.target.value)} className="mt-2 block w-full rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] px-3 py-2.5 outline-none focus:border-[var(--color-status-warning)]" /></label>
        <label className="block text-[var(--text-size-label)] font-medium" htmlFor="close-timestamp">Waktu penutupan<input id="close-timestamp" type="datetime-local" required value={closeTimestamp} onChange={(e) => onTimestampChange(e.target.value)} className="mt-2 block w-full rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] px-3 py-2.5 outline-none focus:border-[var(--color-status-warning)]" /></label>
        <label className="block text-[var(--text-size-label)] font-medium md:col-span-2" htmlFor="close-reason">Alasan penutupan<input id="close-reason" required value={closeReason} onChange={(e) => onReasonChange(e.target.value)} className="mt-2 block w-full rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] px-3 py-2.5 outline-none focus:border-[var(--color-status-warning)]" /></label>
        <label className="block text-[var(--text-size-label)] font-medium md:col-span-2" htmlFor="close-note">Catatan (opsional)<textarea id="close-note" value={closeNote} onChange={(e) => onNoteChange(e.target.value)} className="mt-2 block min-h-24 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] px-3 py-2.5 outline-none focus:border-[var(--color-status-warning)]" /></label>
      </div>
      <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--color-border-default)] bg-[var(--color-elevated-background)] px-[var(--space-card)] py-[var(--space-4)]">
        <button type="button" disabled={busy} onClick={onCancel} className="rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] px-4 py-2.5 text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-default)] disabled:opacity-50">Batal</button>
        <button type="submit" disabled={busy} className="rounded-[var(--radius-compact)] bg-[var(--color-text-strong)] px-4 py-2.5 text-[var(--text-size-compact-body)] font-semibold text-white disabled:opacity-50">{busy ? "Menyimpan…" : "Konfirmasi Tutup Posisi"}</button>
      </div>
    </form>
  );
}
