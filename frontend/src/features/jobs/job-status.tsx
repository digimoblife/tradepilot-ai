"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { getJobStatus } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { AnalysisJobStatus } from "@/types/analysis-job";

const POLL_INTERVAL_MS = 3000;

const STATUS_LABEL: Record<string, string> = {
  PENDING: "Dalam Antrian",
  BUILDING_CONTEXT: "Membangun Konteks",
  CALLING_PROVIDER: "Menghubungi AI Provider",
  VALIDATING: "Memvalidasi Hasil",
  REPAIRING: "Memperbaiki Hasil",
  FALLBACK: "Mencoba Provider Cadangan",
  COMPLETED: "Selesai",
  FAILED: "Gagal",
};

const STATUS_STEPS: Record<string, number> = {
  PENDING: 1,
  BUILDING_CONTEXT: 2,
  CALLING_PROVIDER: 3,
  VALIDATING: 4,
  REPAIRING: 5,
  FALLBACK: 6,
  COMPLETED: 7,
  FAILED: 7,
};

const MAX_STEPS = 7;

function isTerminal(status: string): boolean {
  return status === "COMPLETED" || status === "FAILED";
}

interface Props {
  jobId: string;
  sessionId: string;
  onCompleted?: (analysisId: string) => void;
  onFailed?: () => void;
  onClear?: () => void;
}

export function JobStatus({ jobId, sessionId, onCompleted, onFailed, onClear }: Props) {
  const [status, setStatus] = useState<AnalysisJobStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelledRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statusRef = useRef<AnalysisJobStatus | null>(null);
  const pollRef = useRef<() => void>(() => {});

  const poll = useCallback(async () => {
    if (cancelledRef.current) return;
    try {
      const result = await getJobStatus(jobId);
      if (cancelledRef.current) return;
      setStatus(result);
      statusRef.current = result;
      setLoading(false);
      setError(null);

      if (isTerminal(result.status)) {
        if (result.status === "COMPLETED" && result.analysis_id) {
          onCompleted?.(result.analysis_id);
        }
        if (result.status === "FAILED") {
          onFailed?.();
        }
        return;
      }

      timerRef.current = setTimeout(() => pollRef.current(), POLL_INTERVAL_MS);
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      setLoading(false);
      if (e instanceof AuthenticationError) {
        setError("Silakan masuk terlebih dahulu.");
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Gagal memuat status job.");
      }
      timerRef.current = setTimeout(() => pollRef.current(), POLL_INTERVAL_MS);
    }
  }, [jobId, onCompleted, onFailed]);

  // Keep pollRef updated
  useEffect(() => { pollRef.current = poll; }, [poll]);

  useEffect(() => {
    cancelledRef.current = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setError(null);
    poll();

    return () => {
      cancelledRef.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [poll]);

  if (!status && loading) {
    return (
      <section className="rounded-lg border border-blue-100 bg-blue-50 p-4">
        <p className="text-sm text-blue-700">Memuat status job…</p>
      </section>
    );
  }

  if (error && !status) {
    return (
      <section className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">{error}</p>
      </section>
    );
  }

  if (!status) return null;

  const label = STATUS_LABEL[status.status] ?? status.status;
  const step = STATUS_STEPS[status.status] ?? 0;
  const progressPct = MAX_STEPS > 0 ? Math.round((step / MAX_STEPS) * 100) : 0;
  const terminal = isTerminal(status.status);
  const failed = status.status === "FAILED";

  return (
    <section className={`rounded-lg border p-4 ${failed ? "border-red-200 bg-red-50" : terminal ? "border-green-200 bg-green-50" : "border-blue-100 bg-blue-50"}`}>
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <p className={`text-sm font-medium ${failed ? "text-red-800" : terminal ? "text-green-800" : "text-blue-800"}`}>
            {label}
          </p>
          {!terminal && (
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-blue-200">
              <div
                className="h-full rounded-full bg-blue-600 transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          )}
          {status.attempt_count > 0 && (
            <p className="mt-1 text-xs text-zinc-500">
              Attempt: {status.attempt_count}/{status.max_attempts}
            </p>
          )}
          {failed && status.last_error_message && (
            <p className="mt-1 text-xs text-red-700">{status.last_error_message}</p>
          )}
          {terminal && onClear && (
            <button
              type="button"
              onClick={onClear}
              className="mt-2 text-xs text-zinc-500 underline hover:text-zinc-700 focus:outline-none"
            >
              Tutup
            </button>
          )}
        </div>
        {!terminal && (
          <div className="ml-3 h-5 w-5 animate-spin rounded-full border-2 border-blue-300 border-t-blue-600" />
        )}
      </div>
    </section>
  );
}
