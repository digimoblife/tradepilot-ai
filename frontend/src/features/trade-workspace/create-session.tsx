"use client";
import { useState } from "react";
import { createSession } from "./api";
import type { TradeSession } from "./types";
import { ButtonSpinner } from "@/components/button-spinner";

export function CreateTradeSession({ onCreated }: { onCreated: (session: TradeSession) => void }) {
  const [ticker, setTicker] = useState(""); const [company, setCompany] = useState(""); const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null);
  async function submit(event: React.FormEvent) { event.preventDefault(); const t = ticker.trim(); const c = company.trim();
    if (!t || !c) { setError("Kode saham dan nama perusahaan wajib diisi."); return; }
    setBusy(true); setError(null); try { onCreated(await createSession({ ticker: t, company_name: c, note: note.trim() || null })); setTicker(""); setCompany(""); setNote(""); }
    catch (e) { setError(e instanceof Error ? e.message : "Sesi tidak dapat dibuat."); } finally { setBusy(false); }
  }
  return <form onSubmit={submit} className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)]" aria-label="Buat sesi trading">
    <h2 className="text-[var(--text-size-card-title)] font-semibold text-[var(--color-text-strong)]">Buat Sesi Baru</h2>
    <div className="mt-4 grid min-w-0 gap-4 sm:grid-cols-2">
      <label className="min-w-0 text-[var(--text-size-label)] font-medium text-[var(--color-text-strong)]">Kode Saham<input value={ticker} onChange={e => setTicker(e.target.value)} className="mt-1 block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]" /></label>
      <label className="min-w-0 text-[var(--text-size-label)] font-medium text-[var(--color-text-strong)]">Nama Perusahaan<input value={company} onChange={e => setCompany(e.target.value)} className="mt-1 block min-h-11 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]" /></label>
    </div>
    <label className="mt-4 block min-w-0 text-[var(--text-size-label)] font-medium text-[var(--color-text-strong)]">Catatan (opsional)<textarea value={note} onChange={e => setNote(e.target.value)} className="mt-1 block min-h-20 min-w-0 w-full rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]" /></label>
    {error && <p role="alert" className="mt-3 break-words text-[var(--text-size-compact-body)] text-[var(--color-status-danger)]">{error}</p>}
    <button type="submit" disabled={busy} className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-4 py-2 text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] hover:bg-[var(--color-action-primary-hover)] active:scale-[0.98] transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">
      {busy && <ButtonSpinner className="h-4 w-4" />}
      {busy ? "Menyimpan…" : "Buat Sesi"}
    </button>
  </form>;
}
