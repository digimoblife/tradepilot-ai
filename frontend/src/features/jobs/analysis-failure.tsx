"use client";

import { useState, useCallback, useRef } from "react";
import { retryJob } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { AnalysisJobStatus } from "@/types/analysis-job";

const ERROR_SUMMARY: Record<string, string> = {
  PROVIDER_ERROR: "AI Provider mengalami kendala saat memproses permintaan.",
  PROVIDER_TIMEOUT: "AI Provider tidak merespons tepat waktu.",
  PROVIDER_RATE_LIMIT: "Batas permintaan AI Provider tercapai. Tunggu beberapa saat.",
  PROVIDER_REFUSED: "AI Provider menolak permintaan. Coba lagi nanti.",
  PROVIDER_CONTENT_FILTERED: "Respons AI mengandung konten yang tidak sesuai.",
  PARSING_ERROR: "Gagal membaca respons dari AI Provider.",
  SCHEMA_VALIDATION_ERROR: "Hasil analisis tidak sesuai format yang diharapkan.",
  DOMAIN_VALIDATION_ERROR: "Hasil analisis mengandung nilai yang tidak valid.",
  STATE_CONSISTENCY_ERROR: "Hasil analisis tidak konsisten dengan data posisi.",
  LIFECYCLE_ERROR: "Analisis tidak sesuai dengan tahapan sesi saat ini.",
  INTERNAL_ERROR: "Terjadi kesalahan internal sistem. Silakan coba lagi.",
};

const ERROR_CATEGORY_LABEL: Record<string, string> = {
  PROVIDER_ERROR: "Kesalahan Provider",
  PROVIDER_TIMEOUT: "Waktu Habis",
  PROVIDER_RATE_LIMIT: "Batas Permintaan",
  PROVIDER_REFUSED: "Permintaan Ditolak",
  PROVIDER_CONTENT_FILTERED: "Konten Difilter",
  PARSING_ERROR: "Kesalahan Parsing",
  SCHEMA_VALIDATION_ERROR: "Validasi Skema",
  DOMAIN_VALIDATION_ERROR: "Validasi Data",
  STATE_CONSISTENCY_ERROR: "Konsistensi Data",
  LIFECYCLE_ERROR: "Kesalahan Lifecycle",
  INTERNAL_ERROR: "Kesalahan Internal",
};

function errorCategoryLabel(code: string | null): string {
  return ERROR_CATEGORY_LABEL[code ?? ""] ?? "Kesalahan Lainnya";
}

function errorSummary(code: string | null, message: string | null): string {
  if (code && ERROR_SUMMARY[code]) return ERROR_SUMMARY[code];
  if (message) {
    const safe = message.length > 120 ? message.slice(0, 120) + "…" : message;
    return safe;
  }
  return "Terjadi kesalahan yang tidak diketahui.";
}

function canRetry(status: AnalysisJobStatus): boolean {
  return status.attempt_count < status.max_attempts;
}

interface Props {
  jobStatus: AnalysisJobStatus;
  sessionId: string;
  onRetry?: (jobId: string) => void;
  onClear?: () => void;
}

export function AnalysisFailure({ jobStatus, sessionId, onRetry, onClear }: Props) {
  const [retryState, setRetryState] = useState<"idle" | "pending" | { type: "error"; message: string }>("idle");
  const cancelledRef = useRef(false);

  const summary = errorSummary(jobStatus.last_error_code, jobStatus.last_error_message);
  const category = errorCategoryLabel(jobStatus.last_error_code);
  const retryAllowed = canRetry(jobStatus);

  const handleRetry = useCallback(async () => {
    if (retryState === "pending") return;
    setRetryState("pending");
    try {
      await retryJob(jobStatus.job_id);
      if (cancelledRef.current) return;
      setRetryState("idle");
      onRetry?.(jobStatus.job_id);
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      if (e instanceof AuthenticationError) {
        setRetryState({ type: "error", message: "Silakan masuk terlebih dahulu." });
      } else if (e instanceof ApiError) {
        setRetryState({ type: "error", message: e.message });
      } else {
        setRetryState({ type: "error", message: "Gagal mengirim ulang analisis." });
      }
    }
  }, [jobStatus.job_id, retryState, onRetry]);

  const retryError = typeof retryState === "object" && "type" in retryState ? retryState.message : null;

  return (
    <div className="space-y-3">
      <div>
        <p className="text-sm font-medium text-red-800">Analisis Gagal</p>
        <p className="mt-1 text-xs text-red-600">{category}</p>
        <p className="mt-1 text-sm text-red-700">{summary}</p>
      </div>

      {jobStatus.last_error_code && (
        <details className="text-xs text-zinc-500">
          <summary className="cursor-pointer hover:text-zinc-700">Detail teknis</summary>
          <p className="mt-1">Kode: {jobStatus.last_error_code}</p>
          {jobStatus.last_error_message && (
            <p className="mt-0.5">Pesan: {jobStatus.last_error_message}</p>
          )}
          <p className="mt-0.5">Attempt: {jobStatus.attempt_count}/{jobStatus.max_attempts}</p>
        </details>
      )}

      {retryError && (
        <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">
          {retryError}
        </div>
      )}

      <div className="flex gap-2">
        {retryAllowed && (
          <button
            type="button"
            onClick={handleRetry}
            disabled={retryState === "pending"}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {retryState === "pending" ? "Mengirim ulang…" : "Coba Lagi"}
          </button>
        )}
        {onClear && (
          <button
            type="button"
            onClick={onClear}
            disabled={retryState === "pending"}
            className="rounded border border-zinc-300 px-4 py-1.5 text-sm text-zinc-700 hover:bg-zinc-50 focus:outline-none focus:ring-2 focus:ring-zinc-500 disabled:opacity-50"
          >
            Tutup
          </button>
        )}
      </div>
    </div>
  );
}
