"use client";

import { useEffect, useState } from "react";
import { listEvidence } from "@/lib/api/evidence";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { EvidenceItem } from "@/types/evidence";
import { EvidenceUploadForm } from "./evidence-upload-form";
import { EvidenceCard } from "./evidence-card";
import { getRequiredTypesStatus } from "./helpers";

interface Props {
  sessionId: string;
}

export function EvidenceSection({ sessionId }: Props) {
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await listEvidence(sessionId);
        if (!cancelled) {
          setItems(res.evidence);
          setLoading(false);
        }
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof AuthenticationError) {
          setError("Silakan masuk terlebih dahulu.");
        } else if (e instanceof ApiError) {
          setError(e.message);
        } else {
          setError("Terjadi kesalahan.");
        }
        setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [sessionId, refreshKey]);

  const reqStatus = getRequiredTypesStatus(items);

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">Evidence</h3>

      <div className="mb-4 space-y-1">
        <p className="text-xs font-medium text-zinc-600">Bukti awal yang diperlukan:</p>
        {reqStatus.map((r) => (
          <div key={r.type} className="flex items-center gap-2 text-sm">
            <span className={r.active ? "text-green-600" : "text-zinc-400"}>
              {r.active ? "✓" : "○"}
            </span>
            <span className={r.active ? "text-zinc-800" : "text-zinc-500"}>{r.label}</span>
          </div>
        ))}
      </div>

      <div className="mb-4">
        <p className="mb-2 text-xs font-medium text-zinc-600">Update Orderbook Terbaru</p>
        <p className="mb-2 text-xs text-zinc-400">
          Unggah screenshot orderbook terbaru tanpa perlu mengunggah ulang chart.
        </p>
        <EvidenceUploadForm sessionId={sessionId} evidenceList={items} onUploaded={() => setRefreshKey((k) => k + 1)} />
      </div>

      <hr className="my-4 border-zinc-200" />

      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700">
          Unggah Bukti Lainnya
        </summary>
        <div className="mt-3">
          <EvidenceUploadForm sessionId={sessionId} evidenceList={items} onUploaded={() => setRefreshKey((k) => k + 1)} />
        </div>
      </details>

      <hr className="my-4 border-zinc-200" />

      {loading ? (
        <p className="text-sm text-zinc-400">Memuat bukti…</p>
      ) : error ? (
        <p className="text-sm text-red-600" role="alert">{error}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-zinc-400">Belum ada bukti yang diunggah.</p>
      ) : (
        <div className="space-y-3">
          {items.map((ev) => <EvidenceCard key={ev.id} item={ev} />)}
        </div>
      )}
    </section>
  );
}
