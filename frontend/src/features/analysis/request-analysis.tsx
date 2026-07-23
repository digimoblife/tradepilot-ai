"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { requestAnalysis } from "@/lib/api/analyses";
import { listEvidence } from "@/lib/api/evidence";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { getRequiredTypesStatus } from "@/features/evidence/helpers";
import type { AnalysisJobCreated } from "@/types/analysis-job";

const ANALYSIS_TYPE_LABEL: Record<string, string> = {
  INITIAL_ANALYSIS: "Analisis Awal",
  WATCHING_UPDATE: "Update Pemantauan",
  OPEN_POSITION_UPDATE: "Update Posisi Terbuka",
  PARTIAL_EXIT_REVIEW: "Review Partial Exit",
  CLOSING_ANALYSIS: "Closing Analysis",
};

interface Props {
  sessionId: string;
  analysisType: string;
  onSuccess?: (job: AnalysisJobCreated) => void;
  onClose?: () => void;
}

export function RequestAnalysis({ sessionId, analysisType, onSuccess, onClose }: Props) {
  const [evidenceItems, setEvidenceItems] = useState<ReturnType<typeof getRequiredTypesStatus>>([]);
  const [evidenceLoading, setEvidenceLoading] = useState(true);
  const [submitState, setSubmitState] = useState<"idle" | "pending" | { type: "error"; message: string }>("idle");
  const [jobResult, setJobResult] = useState<AnalysisJobCreated | null>(null);
  const cancelledRef = useRef(false);
  const submittingRef = useRef(false);

  const typeLabel = ANALYSIS_TYPE_LABEL[analysisType] ?? analysisType;

  // Load evidence to check requirements
  useEffect(() => {
    let cancelled = false;
    listEvidence(sessionId)
      .then((res) => {
        if (!cancelled) {
          setEvidenceItems(getRequiredTypesStatus(res.evidence));
          setEvidenceLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEvidenceItems([]);
          setEvidenceLoading(false);
        }
      });
    return () => { cancelled = true; cancelledRef.current = true; };
  }, [sessionId]);

  const allRequiredPresent = evidenceItems.length > 0 && evidenceItems.every((e) => e.active);
  const missingItems = evidenceItems.filter((e) => !e.active);

  const handleSubmit = useCallback(async () => {
    if (submittingRef.current || submitState === "pending") return;
    submittingRef.current = true;
    setSubmitState("pending");
    try {
      const job = await requestAnalysis(sessionId, { analysis_type: analysisType });
      if (cancelledRef.current) return;
      setJobResult(job);
      setSubmitState("idle");
      onSuccess?.(job);
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      if (e instanceof AuthenticationError) {
        setSubmitState({ type: "error", message: "Silakan masuk terlebih dahulu." });
      } else if (e instanceof ApiError) {
        if (e.status === 409) {
          setSubmitState({ type: "error", message: "Analisis sedang diproses. Tunggu hingga selesai." });
        } else {
          setSubmitState({ type: "error", message: `Gagal menjalankan ${typeLabel.toLowerCase()}: ${e.message}` });
        }
      } else {
        setSubmitState({ type: "error", message: "Gagal mengirim permintaan analisis. Silakan coba lagi." });
      }
    } finally {
      submittingRef.current = false;
    }
  }, [sessionId, analysisType, submitState, onSuccess, typeLabel]);

  const submitError = typeof submitState === "object" && "type" in submitState ? submitState.message : null;

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
          {typeLabel}
        </h3>
        {onClose && (
          <button type="button" onClick={onClose} className="text-zinc-400 hover:text-zinc-600 focus:outline-none">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {evidenceLoading && (
        <p className="mb-3 text-sm text-zinc-400">Memeriksa kelengkapan evidence…</p>
      )}

      {!evidenceLoading && evidenceItems.length > 0 && (
        <div className="mb-3 space-y-1">
          <p className="text-xs font-medium text-zinc-500">Evidence yang Diperlukan:</p>
          {evidenceItems.map((e) => (
            <div key={e.type} className="flex items-center gap-2 text-sm">
              <span className={e.active ? "text-green-600" : "text-red-500"}>
                {e.active ? "✓" : "✗"}
              </span>
              <span className={e.active ? "text-zinc-700" : "text-zinc-400"}>{e.label}</span>
            </div>
          ))}
        </div>
      )}

      {!evidenceLoading && missingItems.length > 0 && (
        <p className="mb-3 text-xs text-amber-600">
          Unggah evidence yang diperlukan sebelum menjalankan {typeLabel.toLowerCase()}.
        </p>
      )}

      {jobResult && (
        <div className="mb-3 rounded border border-green-200 bg-green-50 p-2 text-sm text-green-700">
          Permintaan {typeLabel.toLowerCase()} telah dikirim. Status: {jobResult.status}
        </div>
      )}

      {submitError && (
        <div className="mb-3 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700" role="alert">
          {submitError}
        </div>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={submitState === "pending" || !allRequiredPresent || !!jobResult}
        className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      >
        {submitState === "pending"
          ? "Mengirim…"
          : jobResult
            ? "Permintaan Terkirim"
            : `Jalankan ${typeLabel}`}
      </button>
    </section>
  );
}
