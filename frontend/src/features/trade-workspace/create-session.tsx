"use client";
import { useState } from "react";
import { createSession } from "./api";
import type { TradeSession } from "./types";

export function CreateTradeSession({ onCreated }: { onCreated: (session: TradeSession) => void }) {
  const [ticker, setTicker] = useState(""); const [company, setCompany] = useState(""); const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null);
  async function submit(event: React.FormEvent) { event.preventDefault(); const t = ticker.trim(); const c = company.trim();
    if (!t || !c) { setError("Kode saham dan nama perusahaan wajib diisi."); return; }
    setBusy(true); setError(null); try { onCreated(await createSession({ ticker: t, company_name: c, note: note.trim() || null })); setTicker(""); setCompany(""); setNote(""); }
    catch (e) { setError(e instanceof Error ? e.message : "Sesi tidak dapat dibuat."); } finally { setBusy(false); }
  }
  return <form onSubmit={submit} className="min-w-0 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm" aria-label="Buat sesi trading">
    <h2 className="text-lg font-semibold">Buat Sesi Baru</h2>
    <div className="mt-4 grid min-w-0 gap-4 sm:grid-cols-2">
      <label className="min-w-0 text-sm font-medium">Kode Saham<input value={ticker} onChange={e => setTicker(e.target.value)} className="mt-1 block min-w-0 w-full rounded-lg border p-2" /></label>
      <label className="min-w-0 text-sm font-medium">Nama Perusahaan<input value={company} onChange={e => setCompany(e.target.value)} className="mt-1 block min-w-0 w-full rounded-lg border p-2" /></label>
    </div>
    <label className="mt-4 block min-w-0 text-sm font-medium">Catatan (opsional)<textarea value={note} onChange={e => setNote(e.target.value)} className="mt-1 block min-h-20 min-w-0 w-full rounded-lg border p-2" /></label>
    {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    <button disabled={busy} className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? "Menyimpan…" : "Buat Sesi"}</button>
  </form>;
}
