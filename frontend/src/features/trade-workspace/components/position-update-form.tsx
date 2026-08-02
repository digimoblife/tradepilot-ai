import type { ChangeEvent, FormEvent } from "react";
import type { ObservationPeriod } from "../types";

const periods: Array<{ value: ObservationPeriod; label: string }> = [
  { value: "MORNING", label: "Pagi" },
  { value: "MIDDAY", label: "Siang" },
  { value: "AFTERNOON", label: "Sore" },
];

export function PositionUpdateForm({
  currentPrice,
  period,
  timestamp,
  note,
  busy,
  onSubmit,
  onFileChange,
  onCurrentPriceChange,
  onPeriodChange,
  onTimestampChange,
  onNoteChange,
}: {
  currentPrice: string;
  period: ObservationPeriod | "";
  timestamp: string;
  note: string;
  busy: boolean;
  onSubmit: (event: FormEvent) => void;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onCurrentPriceChange: (value: string) => void;
  onPeriodChange: (value: ObservationPeriod | "") => void;
  onTimestampChange: (value: string) => void;
  onNoteChange: (value: string) => void;
}) {
  return (
    <form onSubmit={onSubmit} className="overflow-hidden rounded-[var(--radius-large)] border border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] shadow-[var(--elevation-low)]">
      <div className="border-b border-[var(--color-border-default)] bg-[var(--color-elevated-background)] px-[var(--space-card)] py-[var(--space-5)]">
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-[var(--text-size-section-title)] font-semibold text-[var(--color-text-strong)]">Position Update</h3>
        </div>
        <p className="mt-2 max-w-2xl text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-muted)]">Unggah satu orderbook screenshot dan masukkan observasi terbaru posisi Anda.</p>
      </div>
      <div className="grid gap-[var(--space-5)] px-[var(--space-card)] py-[var(--space-6)] md:grid-cols-2">
        <label className="block text-[var(--text-size-label)] font-medium text-[var(--color-text-default)] md:col-span-2" htmlFor="position-orderbook">
          Orderbook screenshot
          <input id="position-orderbook" type="file" accept="image/*" required onChange={onFileChange} className="mt-2 block min-h-11 w-full max-w-full min-w-0 text-[var(--text-size-compact-body)] text-[var(--color-text-default)] file:mr-3 file:min-h-11 file:rounded-[var(--radius-compact)] file:border-0 file:bg-[var(--color-surface-muted)] file:px-3 file:py-2 file:font-semibold file:text-[var(--color-text-default)]" />
        </label>
        <label className="block text-[var(--text-size-label)] font-medium" htmlFor="position-current-price">
          Harga saat ini
          <input id="position-current-price" required inputMode="decimal" value={currentPrice} onChange={(event) => onCurrentPriceChange(event.target.value)} className="mt-2 block w-full rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] px-3 py-2.5 text-[var(--color-text-strong)] outline-none transition focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent-subtle)]" />
        </label>
        <label className="block text-[var(--text-size-label)] font-medium" htmlFor="position-observation-period">
          Periode observasi
          <select id="position-observation-period" required value={period} onChange={(event) => onPeriodChange(event.target.value as ObservationPeriod | "")} className="mt-2 block w-full rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] px-3 py-2.5 text-[var(--color-text-strong)] outline-none focus:border-[var(--color-accent)]">
            <option value="">Pilih periode</option>
            {periods.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
        <label className="block text-[var(--text-size-label)] font-medium" htmlFor="position-observation-timestamp">
          Waktu observasi
          <input id="position-observation-timestamp" type="datetime-local" required value={timestamp} onChange={(event) => onTimestampChange(event.target.value)} className="mt-2 block w-full rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] px-3 py-2.5 text-[var(--color-text-strong)] outline-none focus:border-[var(--color-accent)]" />
        </label>
        <label className="block text-[var(--text-size-label)] font-medium" htmlFor="position-note">
          Catatan opsional
          <textarea id="position-note" value={note} onChange={(event) => onNoteChange(event.target.value)} className="mt-2 block min-h-24 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] px-3 py-2.5 text-[var(--color-text-strong)] outline-none focus:border-[var(--color-accent)] md:min-h-11" />
        </label>
      </div>
      <div className="flex min-w-0 flex-col gap-3 border-t border-[var(--color-border-default)] bg-[var(--color-elevated-background)] px-[var(--space-card)] py-[var(--space-4)] sm:flex-row sm:items-center sm:justify-end">
        <button type="submit" disabled={busy} className="min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] bg-[var(--color-accent)] px-4 py-2.5 text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] shadow-[var(--elevation-low)] transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto">
          {busy ? "Mengirim…" : "Kirim Position Update"}
        </button>
      </div>
    </form>
  );
}
