"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  readWaitUpdateAnalysis,
  retryWaitUpdateAnalysis,
  submitWaitUpdateAnalysis,
  uploadWaitUpdateInput,
} from "./api";
import type {
  ObservationPeriod,
  RequestStatus,
  SessionStatus,
  WaitUpdateAnalysisRead,
  WaitUpdateInputResponse,
  WaitUpdateResult,
} from "./types";
import { WaitUpdateForm } from "./components/wait-update-form";
import { WaitUpdateFeedback } from "./components/wait-update-feedback";

const POLL_INTERVAL_MS = 4000;
const MAX_POLL_ATTEMPTS = 60;

const periods: Array<{ value: ObservationPeriod; label: string }> = [
  { value: "MORNING", label: "Pagi" },
  { value: "MIDDAY", label: "Siang" },
  { value: "AFTERNOON", label: "Sore" },
];

const resultSections: Array<[keyof WaitUpdateResult, string]> = [
  ["update_summary", "Ringkasan Update"],
  ["current_price", "Harga Saat Ini"],
  ["orderbook_assessment", "Analisis Orderbook"],
  ["change_from_previous_analysis", "Perubahan Dibanding Analisis Sebelumnya"],
  ["current_entry_condition", "Kondisi Entry Saat Ini"],
  ["key_risks", "Risiko Utama"],
  ["upside_probability", "Peluang Kenaikan"],
  ["downside_probability", "Peluang Penurunan"],
  ["recommended_action", "Rekomendasi BUY, WAIT, atau SKIP"],
  ["next_plan", "Trading Plan Berikutnya"],
  ["conclusion", "Kesimpulan AI"],
];

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map((item) => displayValue(item)).join(" • ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function safeError(): string {
  return "Permintaan WAIT Update tidak dapat diproses. Silakan coba lagi.";
}

function isTerminal(status: RequestStatus): boolean {
  return status === "COMPLETED" || status === "FAILED";
}

export function WaitUpdateResultView({ result }: { result: WaitUpdateResult }) {
  return (
    <section aria-label="Hasil WAIT Update" className="min-w-0 max-w-[var(--layout-text-readable)] space-y-[var(--space-3)] rounded-[var(--radius-standard)] border border-[var(--color-status-information)] bg-[var(--color-surface-advisory)] p-[var(--space-card)]">
      <h3 className="sr-only">Hasil WAIT Update</h3>
      {resultSections.map(([key, label]) => (
        <div key={key} className="contents">
        <article className="min-w-0 border-b border-[var(--color-border-default)] pb-[var(--space-3)] last:border-b-0 last:pb-0">
          <h3 className="break-words text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]">{label}</h3>
          <p className="mt-[var(--space-2)] break-words whitespace-pre-wrap text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">
            {displayValue(result[key])}
          </p>
        </article>
        {key === "orderbook_assessment" && result.broker_flow_analysis && (
          <article className="min-w-0 border-b border-[var(--color-border-default)] pb-[var(--space-3)] last:border-b-0 last:pb-0">
            <h3 className="break-words text-[var(--text-size-label)] font-semibold leading-[var(--text-line-body)] text-[var(--color-text-strong)]">Analisa Broker Flow</h3>
            <p className="mt-[var(--space-2)] break-words text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-strong)]">{result.broker_flow_analysis.assessment}</p>
            <p className="mt-[var(--space-1)] break-words whitespace-pre-wrap text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{result.broker_flow_analysis.analysis}</p>
          </article>
        )}
        </div>
      ))}
    </section>
  );
}

export function WaitUpdatePanel({
  sessionId,
  sessionStatus,
  onProcessing,
  onFinished,
}: {
  sessionId: string;
  sessionStatus: SessionStatus;
  onProcessing: () => void;
  onFinished: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [brokerFlowFile, setBrokerFlowFile] = useState<File | null>(null);
  const [currentPrice, setCurrentPrice] = useState("");
  const [period, setPeriod] = useState<ObservationPeriod | "">("");
  const [timestamp, setTimestamp] = useState("");
  const [uploaded, setUploaded] = useState<WaitUpdateInputResponse | null>(null);
  const [analysis, setAnalysis] = useState<WaitUpdateAnalysisRead | null>(null);
  const [busy, setBusy] = useState<"upload" | "submit" | "retry" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  useEffect(() => {
    let cancelled = false;
    if (sessionStatus !== "WAITING") return;
    readWaitUpdateAnalysis(sessionId)
      .then((next) => {
        if (!cancelled) {
          setAnalysis(next);
          if (isTerminal(next.request_status)) onFinished();
        }
      })
      .catch(() => {
        // A WAITING session without a submitted update has no result to read yet.
      });
    return () => {
      cancelled = true;
    };
  }, [onFinished, sessionId, sessionStatus]);

  const requestStatus = analysis?.request_status;

  useEffect(() => {
    if (!requestStatus || isTerminal(requestStatus)) return;
    if (requestStatus !== "PENDING" && requestStatus !== "PROCESSING") return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;

    const poll = async () => {
      if (cancelled || inFlight.current) return;
      inFlight.current = true;
      attempts += 1;
      try {
        const next = await readWaitUpdateAnalysis(sessionId);
        if (cancelled) return;
        setAnalysis(next);
        if (isTerminal(next.request_status)) {
          onFinished();
        } else if (attempts < MAX_POLL_ATTEMPTS) {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        } else {
          setError("Analisis masih diproses. Silakan buka kembali sesi ini nanti.");
        }
      } catch {
        if (!cancelled && attempts < MAX_POLL_ATTEMPTS) {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        } else if (!cancelled) {
          setError("Status WAIT Update belum dapat dimuat.");
        }
      } finally {
        inFlight.current = false;
      }
    };

    timer = setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [requestStatus, onFinished, sessionId]);

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file || !currentPrice.trim() || !period || !timestamp) {
      setError("Orderbook, harga saat ini, periode, dan waktu observasi wajib diisi.");
      return;
    }
    setBusy("upload");
    setError(null);
    try {
      const next = await uploadWaitUpdateInput(sessionId, {
        orderbook: file,
        broker_flow_1d: brokerFlowFile,
        current_price: currentPrice.trim(),
        observation_period: period,
        observation_timestamp: new Date(timestamp).toISOString(),
      });
      setUploaded(next);
      setAnalysis(null);
    } catch {
      setError(safeError());
    } finally {
      setBusy(null);
    }
  }

  async function submitAnalysis() {
    if (!uploaded || busy) return;
    setBusy("submit");
    setError(null);
    try {
      const next = await submitWaitUpdateAnalysis(sessionId);
      setAnalysis({
        ...next,
        processed_response: null,
        error_code: null,
        error_message: null,
        started_at: null,
        completed_at: null,
        observation_period: next.observation_period,
      });
      onProcessing();
    } catch {
      setError(safeError());
    } finally {
      setBusy(null);
    }
  }

  async function retry() {
    if (!analysis || busy) return;
    setBusy("retry");
    setError(null);
    try {
      const next = await retryWaitUpdateAnalysis(sessionId);
      setAnalysis({
        ...next,
        processed_response: null,
        error_code: null,
        error_message: null,
        started_at: null,
        completed_at: null,
        observation_period: next.observation_period,
      });
      onProcessing();
    } catch {
      setError(safeError());
    } finally {
      setBusy(null);
    }
  }

  const effectiveSessionStatus = analysis?.session_status ?? sessionStatus;
  const retryEligible =
    analysis !== null &&
    (analysis.request_status === "FAILED" || analysis.request_status === "PENDING") &&
    effectiveSessionStatus === "WAITING";
  const processing = requestStatus === "PENDING" || requestStatus === "PROCESSING";

  return (
    <section aria-label="WAIT Update" className="space-y-4">
      <WaitUpdateFeedback error={error} processing={processing} requestStatus={requestStatus} effectiveSessionStatus={effectiveSessionStatus} retryEligible={retryEligible} busy={busy !== null} errorCode={analysis?.error_code} errorMessage={analysis?.error_message} onRetry={retry} />
      {analysis?.request_status === "COMPLETED" && analysis.processed_response && (
        <WaitUpdateResultView result={analysis.processed_response} />
      )}
      {sessionStatus === "WAITING" && !processing && !uploaded && <WaitUpdateForm file={file} brokerFlowFile={brokerFlowFile} currentPrice={currentPrice} period={period} timestamp={timestamp} periods={periods} busy={busy !== null} onFileChange={setFile} onBrokerFlowFileChange={setBrokerFlowFile} onCurrentPriceChange={setCurrentPrice} onPeriodChange={setPeriod} onTimestampChange={setTimestamp} onSubmit={upload} />}
      {uploaded && !processing && (
        <section className="min-w-0 rounded-[var(--radius-standard)] border border-[var(--color-status-success)] bg-[var(--color-surface-factual)] p-[var(--space-card)]">
          <h3 className="text-[var(--text-size-card-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]">Input WAIT Update diterima</h3>
          <p className="mt-[var(--space-2)] break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{uploaded.original_filename} · {uploaded.current_price} · {uploaded.observation_period}</p>
          <button type="button" disabled={busy !== null} aria-busy={busy === "submit"} onClick={submitAnalysis} className="mt-[var(--space-4)] min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-status-information)] px-[var(--space-4)] py-[var(--space-2)] text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-status-information)] disabled:cursor-not-allowed disabled:border disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-surface-muted)] disabled:text-[var(--color-text-muted)]">{busy === "submit" ? "Mengirim…" : "Minta WAIT Update Analysis"}</button>
        </section>
      )}
    </section>
  );
}
