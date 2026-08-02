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
    <main className="min-w-0 flex-1 bg-[var(--color-page-background)] text-[var(--color-text-default)]">
      <div className="mx-auto min-w-0 w-full max-w-[var(--layout-application-max)] px-[var(--layout-gutter-mobile)] py-[var(--space-8)] md:px-[var(--layout-gutter-tablet)] lg:px-[var(--layout-gutter-desktop)]">
        <header className="mb-[var(--space-section)] max-w-[var(--layout-text-readable)]">
          <h1 className="mt-[var(--space-2)] text-[var(--text-size-page-title)] font-bold leading-[var(--text-line-heading)] tracking-tight text-[var(--color-text-strong)]">
            Initial Analysis Workspace
          </h1>
          <p className="mt-[var(--space-2)] text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-muted)]">
            Kelola beberapa sesi secara terpisah dan minta analisis awal berbasis evidence.
          </p>
        </header>
        {error && (
          <p role="alert" className="mb-[var(--space-section)] text-[var(--text-size-compact-body)] text-[var(--color-status-danger)]">
            {error}
          </p>
        )}
        <div className="grid min-w-0 gap-[var(--space-section)] xl:grid-cols-[minmax(15rem,18rem)_minmax(0,1fr)] xl:items-start">
          <aside aria-labelledby="workspace-rail-heading" className="min-w-0 rounded-[var(--radius-large)] bg-[var(--color-surface-muted)] p-[var(--space-2)]">
            <h2 id="workspace-rail-heading" className="sr-only">Sesi dan pembuatan sesi</h2>
            <div className="space-y-[var(--space-4)]">
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
          </aside>
          <section aria-labelledby="active-session-heading" className="min-w-0">
            <h2 id="active-session-heading" className="sr-only">Sesi aktif</h2>
            {selected ? (
              <SessionWorkspace
                key={selected}
                sessionId={selected}
                knownEvidence={evidence[selected] ?? []}
                onEvidence={(files) => handleEvidence(selected, files)}
                onSessionStatusChange={handleStatusChange}
              />
            ) : (
              <section className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-8)] text-[var(--color-text-muted)] shadow-[var(--elevation-low)]">
                Pilih sesi atau buat sesi baru.
              </section>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
