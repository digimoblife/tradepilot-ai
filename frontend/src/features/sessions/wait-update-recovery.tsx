"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { readWaitUpdateAnalysis, retryWaitUpdateAnalysis } from "@/features/trade-workspace/api";
import type { CurrentStep, WaitUpdateAnalysisRead } from "@/features/trade-workspace/types";

const POLL_MS = 5_000;

type PresentationState =
  | "IDLE"
  | "PROCESSING"
  | "FAILED_RETRY_AVAILABLE"
  | "FAILED_READ_ONLY"
  | "COMPLETED"
  | "UNAVAILABLE";

function presentationOf(
  request: WaitUpdateAnalysisRead,
  step: CurrentStep,
  candidateId: string | null,
): PresentationState {
  if (!candidateId || request.analysis_request_id !== candidateId || request.session_id === "") {
    return "UNAVAILABLE";
  }
  if (request.analysis_type !== "WAIT_UPDATE") return "UNAVAILABLE";
  if (request.request_status === "PENDING" || request.request_status === "PROCESSING") {
    return "PROCESSING";
  }
  if (request.request_status === "COMPLETED") return "COMPLETED";
  if (request.request_status === "FAILED") {
    const canRetry =
      step.workflow_actions.length === 1 &&
      step.workflow_actions[0] === "RETRY_WAIT_UPDATE" &&
      !step.read_only;
    return canRetry ? "FAILED_RETRY_AVAILABLE" : "FAILED_READ_ONLY";
  }
  return "UNAVAILABLE";
}

export function WaitUpdateRecovery({
  sessionId,
  step,
  refetch,
}: {
  sessionId: string;
  step: CurrentStep;
  refetch: () => Promise<unknown>;
}) {
  const [request, setRequest] = useState<WaitUpdateAnalysisRead | null>(null);
  const [readFailed, setReadFailed] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [recoveryNonce, setRecoveryNonce] = useState(0);

  const generation = useRef(0);
  const inFlight = useRef(false);
  const retryInFlight = useRef(false);
  const mounted = useRef(true);

  const active = step.active_request;
  const failed = step.failed_request;
  const candidate =
    active?.analysis_type === "WAIT_UPDATE"
      ? active
      : failed?.analysis_type === "WAIT_UPDATE"
        ? failed
        : null;
  const shouldRecover = candidate !== null;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (!shouldRecover) return;

    const current = ++generation.current;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      if (inFlight.current || current !== generation.current) return;
      inFlight.current = true;

      try {
        const next = await readWaitUpdateAnalysis(sessionId, controller.signal);
        if (current !== generation.current) return;

        if (
          next.session_id !== sessionId ||
          next.analysis_type !== "WAIT_UPDATE" ||
          next.analysis_request_id !== candidate?.id
        ) {
          setReadFailed(true);
          return;
        }

        setRequest(next);
        setReadFailed(false);

        if (next.request_status === "COMPLETED" || next.request_status === "FAILED") {
          await refetch();
          return;
        }
      } catch {
        if (current !== generation.current || controller.signal.aborted) return;
        setReadFailed(true);
        return;
      } finally {
        if (current === generation.current) {
          inFlight.current = false;
        }
      }

      if (current === generation.current && !controller.signal.aborted) {
        timer = setTimeout(() => void poll(), POLL_MS);
      }
    };

    void poll();

    return () => {
      generation.current += 1;
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [candidate?.id, recoveryNonce, refetch, sessionId, shouldRecover]);

  const state = request
    ? presentationOf(request, step, candidate?.id ?? null)
    : shouldRecover
      ? "PROCESSING"
      : "IDLE";

  const handleRetry = async () => {
    if (retryInFlight.current || state !== "FAILED_RETRY_AVAILABLE") return;
    retryInFlight.current = true;
    setRetrying(true);
    const current = generation.current;

    try {
      await retryWaitUpdateAnalysis(sessionId);
      if (!mounted.current || current !== generation.current) return;

      await refetch();
      if (mounted.current && current === generation.current) {
        setRequest(null);
        setRecoveryNonce((val) => val + 1);
      }
    } catch {
      if (mounted.current && current === generation.current) {
        setReadFailed(true);
      }
    } finally {
      if (mounted.current && current === generation.current) {
        retryInFlight.current = false;
        setRetrying(false);
      }
    }
  };

  const handleReload = async () => {
    const current = generation.current;
    try {
      await refetch();
      if (mounted.current && current === generation.current) {
        setReadFailed(false);
        setRecoveryNonce((val) => val + 1);
      }
    } catch {
      if (mounted.current && current === generation.current) {
        setReadFailed(true);
      }
    }
  };

  if (state === "IDLE") return null;

  if (readFailed) {
    return (
      <section
        aria-live="polite"
        className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8 sm:px-6 sm:pb-10 lg:px-8"
      >
        <div className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
          <h2 className="text-xl font-bold leading-[var(--text-line-heading)] text-[var(--color-status-danger)]">
            Status WAIT Update belum dapat dimuat
          </h2>
          <p className="mt-2 break-words text-sm text-[var(--color-text-default)]">
            Status WAIT Update belum dapat dimuat. Silakan periksa kembali.
          </p>
          <button
            type="button"
            onClick={() => void handleReload()}
            className="mt-4 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            Muat Ulang
          </button>
        </div>
      </section>
    );
  }

  if (state === "PROCESSING") {
    return (
      <section
        aria-live="polite"
        aria-busy="true"
        className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8 sm:px-6 sm:pb-10 lg:px-8"
      >
        <div className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-status-processing)] bg-[var(--color-status-processing-subtle)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
          <h2 className="text-xl font-bold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">
            WAIT Update sedang diproses
          </h2>
          <p className="mt-2 break-words text-sm text-[var(--color-text-default)]">
            Data terbaru sedang dianalisis. Hasilnya akan tersedia setelah proses selesai.
          </p>
          <p className="mt-2 break-words text-sm text-[var(--color-text-muted)]">
            Status akan diperbarui secara otomatis selama halaman ini terbuka.
          </p>
        </div>
      </section>
    );
  }

  if (state === "COMPLETED") {
    return (
      <section
        aria-live="polite"
        className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8 sm:px-6 sm:pb-10 lg:px-8"
      >
        <div className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-status-success)] bg-[var(--color-status-success-subtle)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
          <h2 className="text-xl font-bold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">
            WAIT Update selesai
          </h2>
          <p className="mt-2 break-words text-sm text-[var(--color-text-default)]">
            Hasil analisis terbaru sudah tersedia.
          </p>
          <Link
            href={`/sessions/${encodeURIComponent(sessionId)}/analysis`}
            className="mt-4 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            Lihat Hasil Analisis
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section
      aria-live="polite"
      className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8 sm:px-6 sm:pb-10 lg:px-8"
    >
      <div className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
        <h2 className="text-xl font-bold leading-[var(--text-line-heading)] text-[var(--color-status-danger)]">
          WAIT Update belum berhasil
        </h2>
        <p className="mt-2 break-words text-sm text-[var(--color-text-default)]">
          Analisis WAIT Update belum dapat diselesaikan.
        </p>

        {state === "FAILED_RETRY_AVAILABLE" ? (
          <button
            type="button"
            disabled={retrying}
            aria-busy={retrying}
            onClick={() => void handleRetry()}
            className="mt-4 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            {retrying ? "Mencoba lagi..." : "Coba Lagi"}
          </button>
        ) : null}
      </div>
    </section>
  );
}
