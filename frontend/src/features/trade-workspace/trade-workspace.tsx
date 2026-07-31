"use client";

import { useCallback, useEffect, useState } from "react";
import { listSessions } from "./api";
import { CreateTradeSession } from "./create-session";
import { TradeWorkspaceSessionList } from "./session-list";
import { SessionWorkspace } from "./workspace";
import type { EvidenceFile, TradeSession } from "./types";

export function TradeWorkspace() {
  const [sessions, setSessions] = useState<TradeSession[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Record<string, EvidenceFile[]>>({});
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    listSessions()
      .then((r) => {
        setSessions(r.sessions);
        setSelected((x) => x ?? r.sessions[0]?.id ?? null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Sesi tidak dapat dimuat."));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleEvidence = useCallback((sessionId: string, files: EvidenceFile[]) => {
    setEvidence((x) => ({ ...x, [sessionId]: files }));
  }, []);

  const handleStatusChange = useCallback((sessionId: string, status: TradeSession["status"]) => {
    setSessions((current) =>
      current.map((s) => (s.id === sessionId ? { ...s, status } : s))
    );
  }, []);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Initial Analysis Workspace</h1>
        <p className="mt-1 text-zinc-600">
          Kelola beberapa sesi secara terpisah dan minta analisis awal berbasis evidence.
        </p>
      </div>
      {error && (
        <p role="alert" className="mb-4 text-red-700">
          {error}
        </p>
      )}
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <div className="space-y-4">
          <TradeWorkspaceSessionList
            sessions={sessions}
            selectedId={selected}
            onSelect={setSelected}
          />
          <CreateTradeSession
            onCreated={(s) => {
              setSessions((x) => [s, ...x]);
              setSelected(s.id);
            }}
          />
        </div>
        {selected ? (
          <SessionWorkspace
            key={selected}
            sessionId={selected}
            knownEvidence={evidence[selected] ?? []}
            onEvidence={(files) => handleEvidence(selected, files)}
            onSessionStatusChange={handleStatusChange}
          />
        ) : (
          <section className="rounded-xl border bg-white p-8 text-zinc-500">
            Pilih sesi atau buat sesi baru.
          </section>
        )}
      </div>
    </main>
  );
}
