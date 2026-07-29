"use client";

import { useEffect, useState } from "react";
import { listEvidence } from "@/lib/api/evidence";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { EvidenceItem } from "@/types/evidence";
import type { EvidenceBatchSummary } from "@/types/trade-session";
import { EvidenceUploadForm } from "./evidence-upload-form";
import { EvidenceCard } from "./evidence-card";
import { getRequiredTypesStatus } from "./helpers";

interface Props {
  sessionId: string;
  batches?: EvidenceBatchSummary[];
  currentBatch?: EvidenceBatchSummary | null;
}

export function EvidenceSection({ sessionId, batches = [], currentBatch = null }: Props) {
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

  const currentBatchItems = currentBatch
    ? items.filter((item) => item.evidence_batch_id === currentBatch.id)
    : items;
  const currentAnalysisType = currentBatch?.analysis_type ?? "INITIAL_ANALYSIS";
  const reqStatus = getRequiredTypesStatus(currentBatchItems, currentAnalysisType);
  const canMutateCurrentBatch = !currentBatch || currentBatch.status === "DRAFT";
  const disabledReason = currentBatch && currentBatch.status !== "DRAFT"
    ? `Batch ${currentBatch.sequence_number} berstatus ${currentBatch.status}. Bukti tidak dapat diubah.`
    : undefined;
  const knownBatchIds = new Set(batches.map((batch) => batch.id));
  const evidenceGroups = [
    ...batches.map((batch) => ({
      id: batch.id,
      title: `${batch.label ?? `Batch ${batch.sequence_number}`} · ${batch.status}`,
      items: items.filter((item) => item.evidence_batch_id === batch.id),
    })),
    {
      id: "legacy",
      title: "Legacy tanpa batch",
      items: items.filter((item) => !item.evidence_batch_id || !knownBatchIds.has(item.evidence_batch_id)),
    },
  ].filter((group) => group.items.length > 0);

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">Evidence</h3>

      {currentBatch && (
        <div className="mb-4 rounded border border-zinc-200 bg-zinc-50 px-3 py-2">
          <p className="text-xs font-medium text-zinc-600">Batch saat ini</p>
          <p className="text-sm text-zinc-800">
            {currentBatch.label ?? `Batch ${currentBatch.sequence_number}`} · {currentBatch.status}
          </p>
        </div>
      )}

      <div className="mb-4 space-y-1">
        <p className="text-xs font-medium text-zinc-600">Bukti yang diperlukan:</p>
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
        <EvidenceUploadForm
          sessionId={sessionId}
          evidenceList={currentBatchItems}
          batchId={currentBatch?.id}
          onUploaded={() => setRefreshKey((k) => k + 1)}
          disabled={!canMutateCurrentBatch}
          disabledReason={disabledReason}
        />
      </div>

      <hr className="my-4 border-zinc-200" />

      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700">
          Unggah Bukti Lainnya
        </summary>
        <div className="mt-3">
          <EvidenceUploadForm
            sessionId={sessionId}
            evidenceList={currentBatchItems}
            batchId={currentBatch?.id}
            onUploaded={() => setRefreshKey((k) => k + 1)}
            disabled={!canMutateCurrentBatch}
            disabledReason={disabledReason}
          />
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
        <div className="space-y-4">
          {evidenceGroups.map((group) => (
            <div key={group.id} className="space-y-3">
              <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                {group.title}
              </p>
              {group.items.map((ev) => <EvidenceCard key={ev.id} item={ev} />)}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
