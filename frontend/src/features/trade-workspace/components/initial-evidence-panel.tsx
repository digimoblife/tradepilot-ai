import type { FormEvent } from "react";
import type { EvidenceFile } from "../types";

type EvidenceKey = "orderbook" | "chart_3_month" | "chart_6_month" | "foreign_flow_1w";
type EvidenceFiles = Partial<Record<EvidenceKey, File>>;

const requiredEvidence: Array<[EvidenceKey, string]> = [
  ["orderbook", "Order Book"],
  ["chart_3_month", "Grafik 3 Bulan"],
  ["chart_6_month", "Grafik 6 Bulan"],
  ["foreign_flow_1w", "Foreign Flow — 1W"],
];

export function InitialEvidencePanel({
  files,
  knownEvidence,
  busy,
  onFileSelected,
  onUpload,
  onRequestAnalysis,
}: {
  files: EvidenceFiles;
  knownEvidence: EvidenceFile[];
  busy: boolean;
  onFileSelected: (key: EvidenceKey, file: File) => void;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
  onRequestAnalysis: () => void;
}) {
  const allFilesSelected = requiredEvidence.every(([key]) => Boolean(files[key]));

  if (knownEvidence.length > 0) {
    return <section aria-label="Evidence siap" className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-status-success)] bg-[var(--color-surface-factual)] p-[var(--space-card)]">
      <h3 className="text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">Evidence siap</h3>
      <p className="mt-[var(--space-1)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{knownEvidence.length} file diterima.</p>
      <button type="button" disabled={busy} onClick={onRequestAnalysis} className="mt-[var(--space-4)] min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-status-information)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{busy ? "Mengirim…" : "Minta Initial Analysis"}</button>
    </section>;
  }

  return <form onSubmit={onUpload} aria-label="Evidence Initial Analysis" className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-border-strong)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)]">
    <h3 className="text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">Evidence Initial Analysis</h3>
    <p className="mt-[var(--space-1)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-muted)]">Unggah tepat empat gambar: order book, grafik 3 bulan, grafik 6 bulan, dan Foreign Flow 1W.</p>
    <fieldset className="mt-[var(--space-4)] grid min-w-0 gap-[var(--space-field)]">
      <legend className="sr-only">Evidence fields</legend>
      {requiredEvidence.map(([key, label]) => {
        const file = files[key];
        const inputId = `initial-evidence-${key}`;
        return <div key={key} className="min-w-0 space-y-[var(--space-2)]">
          <label htmlFor={inputId} className="block break-words text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]">{label}</label>
          <input id={inputId} type="file" accept="image/*" required onChange={(event) => {
            const selectedFile = event.target.files?.[0];
            if (selectedFile) onFileSelected(key, selectedFile);
          }} className="block min-h-11 w-full min-w-0 max-w-full text-[var(--text-size-compact-body)] text-[var(--color-text-default)] file:mr-[var(--space-2)] file:min-h-11 file:rounded-[var(--radius-compact)] file:border-0 file:bg-[var(--color-surface-muted)] file:px-[var(--space-3)] file:font-semibold file:text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)]" />
          {file && <p className="min-w-0 break-words text-[var(--text-size-label)] leading-[var(--text-line-body)] text-[var(--color-text-muted)]">{file.name}</p>}
        </div>;
      })}
    </fieldset>
    <button type="submit" disabled={busy || !allFilesSelected} className="mt-[var(--space-4)] min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-status-information)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{busy ? "Mengunggah…" : "Unggah Evidence"}</button>
  </form>;
}
