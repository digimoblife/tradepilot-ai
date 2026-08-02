import type { FormEvent } from "react";

export type BuyFormState = {
  entry_price: string;
  entry_timestamp: string;
  quantity: string;
  stop_loss: string;
  target_price: string;
  note: string;
};

export function BuyDecisionForm({
  buyForm,
  busy,
  submitting,
  onChange,
  onSubmit,
}: {
  buyForm: BuyFormState;
  busy: boolean;
  submitting: boolean;
  onChange: (field: keyof BuyFormState, value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return <form onSubmit={onSubmit} aria-label="Konfirmasi posisi BUY" className="min-w-0 space-y-[var(--space-4)] border-t border-[var(--color-border-default)] bg-[var(--color-surface-factual)] p-[var(--space-card)]">
    <h4 className="text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">Konfirmasi posisi BUY</h4>
    <div className="grid min-w-0 gap-[var(--space-field)] sm:grid-cols-2">
      <label className="min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="buy-entry-price">Harga entry<input id="buy-entry-price" required inputMode="decimal" value={buyForm.entry_price} onChange={(event) => onChange("entry_price", event.target.value)} className="mt-[var(--space-2)] block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" /></label>
      <label className="min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="buy-entry-timestamp">Waktu entry<input id="buy-entry-timestamp" required type="text" placeholder="2026-07-30T09:15:00Z" value={buyForm.entry_timestamp} onChange={(event) => onChange("entry_timestamp", event.target.value)} className="mt-[var(--space-2)] block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" /></label>
      <label className="min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="buy-quantity">Kuantitas<input id="buy-quantity" required inputMode="decimal" value={buyForm.quantity} onChange={(event) => onChange("quantity", event.target.value)} className="mt-[var(--space-2)] block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" /></label>
      <label className="min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="buy-stop-loss">Stop loss<input id="buy-stop-loss" required inputMode="decimal" value={buyForm.stop_loss} onChange={(event) => onChange("stop_loss", event.target.value)} className="mt-[var(--space-2)] block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" /></label>
      <label className="min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="buy-target-price">Target price<input id="buy-target-price" required inputMode="decimal" value={buyForm.target_price} onChange={(event) => onChange("target_price", event.target.value)} className="mt-[var(--space-2)] block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" /></label>
    </div>
    <label className="block min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="buy-note">Catatan BUY (opsional)<textarea id="buy-note" value={buyForm.note} onChange={(event) => onChange("note", event.target.value)} className="mt-[var(--space-2)] block min-h-20 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" /></label>
    <button type="submit" disabled={busy} aria-busy={submitting} className="min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-status-information)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{submitting ? "Menyimpan…" : "Konfirmasi BUY"}</button>
  </form>;
}
