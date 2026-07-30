"use client";
import type { TradeSession } from "./types";
export function TradeWorkspaceSessionList({ sessions, selectedId, onSelect }: { sessions: TradeSession[]; selectedId: string | null; onSelect: (id: string) => void }) {
  return <aside aria-label="Daftar sesi" className="rounded-xl border border-zinc-200 bg-white p-3 shadow-sm"><h2 className="px-2 pb-2 text-sm font-semibold">Sesi Saya</h2>{sessions.length === 0 ? <p className="px-2 text-sm text-zinc-500">Belum ada sesi.</p> : <div className="space-y-1">{sessions.map(s => <button key={s.id} onClick={() => onSelect(s.id)} className={`w-full rounded-lg p-3 text-left ${selectedId === s.id ? "bg-blue-50 ring-1 ring-blue-200" : "hover:bg-zinc-50"}`}><span className="block font-semibold">{s.ticker}</span><span className="block text-sm text-zinc-600">{s.company_name}</span><span className="mt-1 block text-xs text-zinc-500">{s.status}</span></button>)}</div>}</aside>;
}
