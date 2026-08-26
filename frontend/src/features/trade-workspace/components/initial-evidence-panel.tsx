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
  sessionId,
  ticker,
}: {
  files: EvidenceFiles;
  knownEvidence: EvidenceFile[];
  busy: boolean;
  onFileSelected: (key: EvidenceKey, file: File) => void;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
  onRequestAnalysis: () => void;
  sessionId?: string;
  ticker?: string;
}) {
  const allFilesSelected = requiredEvidence.every(([key]) => Boolean(files[key]));

  if (knownEvidence.length > 0) {
    return (
      <section
        aria-label="Evidence siap"
        className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-status-success)] bg-[var(--color-surface-factual)] p-[var(--space-card)]"
      >
        <h3 className="text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">
          Evidence siap
        </h3>
        <p className="mt-[var(--space-1)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">
          {knownEvidence.length} file diterima.
        </p>
        <button
          type="button"
          disabled={busy}
          onClick={onRequestAnalysis}
          className="mt-[var(--space-4)] min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] transition-colors hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]"
        >
          {busy ? "Mengirim…" : "Minta Initial Analysis"}
        </button>
      </section>
    );
  }

  return (
    <div className="space-y-4">
      {/* 1-Click Automated ZAPI Option */}
      <div className="rounded-[var(--radius-standard)] border border-primary/40 bg-primary/5 p-[var(--space-card)] shadow-[var(--elevation-low)]">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-md bg-primary/20 px-2 py-0.5 text-xs font-bold text-primary">
            ⚡ REKOMENDASI (1-CLICK)
          </span>
        </div>
        <h3 className="mt-2 text-[var(--text-size-card-title)] font-semibold text-[var(--color-text-strong)]">
          Ambil Bukti Pasar Otomatis (ZAPI: Pluang, IDX, Stockbit)
        </h3>
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">
          Sistem akan secara instan mengunduh harga real-time, kedalaman orderbook, riwayat 130 candle bursa, Foreign Flow, dan konsentrasi broker 1D tanpa perlu upload screenshot manual.
        </p>
        <button
          type="button"
          disabled={busy}
          onClick={onRequestAnalysis}
          className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--color-action-primary-hover)] disabled:opacity-50"
        >
          {busy ? "Memproses Data Pasar…" : "⚡ Ambil Bukti Otomatis & Analisa Sekarang"}
        </button>
      </div>

      {/* Manual Upload Fallback Accordion */}
      <details className="rounded-[var(--radius-standard)] border border-[var(--color-border-strong)] bg-[var(--color-surface-standard)] p-[var(--space-card)]">
        <summary className="cursor-pointer text-xs font-semibold text-muted-foreground hover:text-foreground">
          Atau unggah screenshot manual (Opsi Cadangan)
        </summary>
        <form onSubmit={onUpload} className="mt-4">
          <h3 className="text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">
            Evidence Initial Analysis
          </h3>
          <p className="mt-[var(--space-1)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-muted)]">
            Unggah tepat empat gambar: order book, grafik 3 bulan, grafik 6 bulan, dan Foreign Flow 1W.
          </p>
          <fieldset className="mt-[var(--space-4)] grid min-w-0 gap-[var(--space-field)]">
            <legend className="sr-only">Evidence fields</legend>
            {requiredEvidence.map(([key, label]) => {
              const file = files[key];
              const inputId = `initial-evidence-${key}`;
              return (
                <div key={key} className="min-w-0 space-y-[var(--space-2)]">
                  <label
                    htmlFor={inputId}
                    className="block break-words text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]"
                  >
                    {label}
                  </label>
                  <input
                    id={inputId}
                    type="file"
                    accept="image/*"
                    required
                    onChange={(event) => {
                      const selectedFile = event.target.files?.[0];
                      if (selectedFile) onFileSelected(key, selectedFile);
                    }}
                    className="block min-h-11 w-full min-w-0 max-w-full text-[var(--text-size-compact-body)] text-[var(--color-text-default)] file:mr-[var(--space-2)] file:min-h-11 file:rounded-[var(--radius-compact)] file:border-0 file:bg-[var(--color-surface-muted)] file:px-[var(--space-3)] file:font-semibold file:text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-action-primary)]"
                  />
                  {file && (
                    <p className="min-w-0 break-words text-[var(--text-size-label)] leading-[var(--text-line-body)] text-[var(--color-text-muted)]">
                      {file.name}
                    </p>
                  )}
                </div>
              );
            })}
          </fieldset>
          <button
            type="submit"
            disabled={busy || !allFilesSelected}
            className="mt-[var(--space-4)] min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] transition-colors hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]"
          >
            {busy ? "Mengunggah…" : "Unggah Evidence"}
          </button>
        </form>
      </details>
    </div>
  );
}
