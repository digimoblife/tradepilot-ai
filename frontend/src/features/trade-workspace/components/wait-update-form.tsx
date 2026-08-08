import type { FormEvent } from "react";
import type { ObservationPeriod } from "../types";

export function WaitUpdateForm({
  file,
  brokerFlowFile,
  currentPrice,
  period,
  timestamp,
  periods,
  busy,
  onFileChange,
  onBrokerFlowFileChange,
  onCurrentPriceChange,
  onPeriodChange,
  onTimestampChange,
  onSubmit,
}: {
  file: File | null;
  brokerFlowFile: File | null;
  currentPrice: string;
  period: ObservationPeriod | "";
  timestamp: string;
  periods: Array<{ value: ObservationPeriod; label: string }>;
  busy: boolean;
  onFileChange: (file: File | null) => void;
  onBrokerFlowFileChange: (file: File | null) => void;
  onCurrentPriceChange: (value: string) => void;
  onPeriodChange: (value: ObservationPeriod | "") => void;
  onTimestampChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return <form onSubmit={onSubmit} aria-label="WAIT Update" className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-border-strong)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)]">
    <h3 className="text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">WAIT Update</h3>
    <p className="mt-[var(--space-1)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-muted)]">Unggah orderbook, tambahkan Broker Flow 1D bila tersedia, dan masukkan fakta observasi Anda.</p>
    <fieldset className="mt-[var(--space-4)] grid min-w-0 gap-[var(--space-field)] sm:grid-cols-2">
      <legend className="sr-only">WAIT Update</legend>
      <label className="block min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)] sm:col-span-2" htmlFor="wait-orderbook">Orderbook<input id="wait-orderbook" type="file" accept="image/*" required onChange={(event) => onFileChange(event.target.files?.[0] ?? null)} className="mt-[var(--space-2)] block min-h-11 w-full min-w-0 max-w-full text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] file:mr-[var(--space-2)] file:min-h-11 file:rounded-[var(--radius-compact)] file:border-0 file:bg-[var(--color-surface-muted)] file:px-[var(--space-3)] file:font-semibold file:text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" />{file && <span className="mt-[var(--space-1)] block min-w-0 break-words text-[var(--text-size-label)] font-normal text-[var(--color-text-muted)]">{file.name}</span>}</label>
      <label className="block min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)] sm:col-span-2" htmlFor="wait-broker-flow">Broker Flow — 1D (Optional)<input id="wait-broker-flow" type="file" accept="image/*" onChange={(event) => onBrokerFlowFileChange(event.target.files?.[0] ?? null)} className="mt-[var(--space-2)] block min-h-11 w-full min-w-0 max-w-full text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] file:mr-[var(--space-2)] file:min-h-11 file:rounded-[var(--radius-compact)] file:border-0 file:bg-[var(--color-surface-muted)] file:px-[var(--space-3)] file:font-semibold file:text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" />{brokerFlowFile && <span className="mt-[var(--space-1)] block min-w-0 break-words text-[var(--text-size-label)] font-normal text-[var(--color-text-muted)]">{brokerFlowFile.name}</span>}</label>
      <label className="block min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="wait-current-price">Harga saat ini<input id="wait-current-price" required inputMode="decimal" value={currentPrice} onChange={(event) => onCurrentPriceChange(event.target.value)} className="mt-[var(--space-2)] block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" /></label>
      <label className="block min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]" htmlFor="wait-observation-period">Periode observasi<select id="wait-observation-period" required value={period} onChange={(event) => onPeriodChange(event.target.value as ObservationPeriod | "")} className="mt-[var(--space-2)] block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]"><option value="">Pilih periode</option>{periods.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
      <label className="block min-w-0 text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)] sm:col-span-2" htmlFor="wait-observation-timestamp">Waktu observasi<input id="wait-observation-timestamp" type="datetime-local" required value={timestamp} onChange={(event) => onTimestampChange(event.target.value)} className="mt-[var(--space-2)] block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-normal text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" /></label>
    </fieldset>
    <button type="submit" disabled={busy} aria-busy={busy} className="mt-[var(--space-4)] min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-status-information)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{busy ? "Mengunggah…" : "Terima Input WAIT Update"}</button>
  </form>;
}
