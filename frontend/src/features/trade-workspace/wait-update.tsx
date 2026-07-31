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
    <section aria-label="Hasil WAIT Update" className="space-y-3">
      <h3 className="sr-only">Hasil WAIT Update</h3>
      {resultSections.map(([key, label]) => (
        <article key={key} className="rounded-xl border border-zinc-200 bg-white p-4">
          <h3 className="font-semibold">{label}</h3>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-zinc-700">
            {displayValue(result[key])}
          </p>
        </article>
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

  useEffect(() => {
    if (!analysis || isTerminal(analysis.request_status)) return;
    if (analysis.request_status !== "PENDING" && analysis.request_status !== "PROCESSING") return;
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

    timer = setTimeout(poll, 0);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [analysis, onFinished, sessionId]);

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

  const requestStatus = analysis?.request_status;
  const effectiveSessionStatus = analysis?.session_status ?? sessionStatus;
  const retryEligible =
    analysis !== null &&
    (analysis.request_status === "FAILED" || analysis.request_status === "PENDING") &&
    effectiveSessionStatus === "WAITING";
  const processing = requestStatus === "PENDING" || requestStatus === "PROCESSING";

  return (
    <section aria-label="WAIT Update" className="space-y-4">
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {processing && (
        <p role="status" className="rounded-xl border bg-white p-5 text-sm text-zinc-700">
          WAIT Update sedang diproses. Silakan tunggu.
        </p>
      )}
      {analysis?.request_status === "COMPLETED" && analysis.processed_response && (
        <WaitUpdateResultView result={analysis.processed_response} />
      )}
      {analysis?.request_status === "FAILED" && (
        <section className="rounded-xl border border-red-200 bg-red-50 p-5">
          <h3 className="font-semibold text-red-900">WAIT Update gagal diproses</h3>
          <p className="mt-2 text-sm text-red-800">Analisis WAIT Update tidak selesai.</p>
          {analysis.error_code && <p className="mt-1 text-xs text-red-700">Kode: {analysis.error_code}</p>}
          {analysis.error_message && <p className="mt-1 text-sm text-red-800">{analysis.error_message}</p>}
          {retryEligible && <button type="button" disabled={busy !== null} onClick={retry} className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy === "retry" ? "Mencoba…" : "Coba Lagi"}</button>}
        </section>
      )}
      {analysis?.request_status === "PENDING" && effectiveSessionStatus === "WAITING" && (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-5">
          <h3 className="font-semibold text-amber-950">WAIT Update menunggu pemulihan antrean</h3>
          <p className="mt-2 text-sm text-amber-900">Permintaan belum masuk ke antrean pemrosesan.</p>
          {retryEligible && <button type="button" disabled={busy !== null} onClick={retry} className="mt-4 rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy === "retry" ? "Mencoba…" : "Coba Lagi"}</button>}
        </section>
      )}
      {sessionStatus === "WAITING" && !processing && !uploaded && (
        <form onSubmit={upload} className="rounded-xl border bg-white p-5 shadow-sm">
          <h3 className="font-semibold">WAIT Update</h3>
          <p className="mt-1 text-sm text-zinc-500">Unggah satu orderbook dan masukkan fakta observasi Anda.</p>
          <div className="mt-4 space-y-3">
            <label className="block text-sm font-medium" htmlFor="wait-orderbook">Orderbook<input id="wait-orderbook" type="file" accept="image/*" required onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="mt-1 block w-full text-sm" /></label>
            <label className="block text-sm font-medium" htmlFor="wait-current-price">Harga saat ini<input id="wait-current-price" required inputMode="decimal" value={currentPrice} onChange={(event) => setCurrentPrice(event.target.value)} className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2" /></label>
            <label className="block text-sm font-medium" htmlFor="wait-observation-period">Periode observasi<select id="wait-observation-period" required value={period} onChange={(event) => setPeriod(event.target.value as ObservationPeriod)} className="mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2"><option value="">Pilih periode</option>{periods.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label className="block text-sm font-medium" htmlFor="wait-observation-timestamp">Waktu observasi<input id="wait-observation-timestamp" type="datetime-local" required value={timestamp} onChange={(event) => setTimestamp(event.target.value)} className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2" /></label>
          </div>
          <button type="submit" disabled={busy !== null} className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy === "upload" ? "Mengunggah…" : "Terima Input WAIT Update"}</button>
        </form>
      )}
      {uploaded && !processing && (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
          <h3 className="font-semibold text-emerald-950">Input WAIT Update diterima</h3>
          <p className="mt-2 text-sm text-emerald-900">{uploaded.original_filename} · {uploaded.current_price} · {uploaded.observation_period}</p>
          <button type="button" disabled={busy !== null} onClick={submitAnalysis} className="mt-4 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy === "submit" ? "Mengirim…" : "Minta WAIT Update Analysis"}</button>
        </section>
      )}
    </section>
  );
}
