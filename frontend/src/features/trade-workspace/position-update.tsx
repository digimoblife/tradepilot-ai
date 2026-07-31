"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  readPositionUpdates,
  submitPositionUpdateAnalysis,
  uploadPositionUpdateInput,
} from "./api";
import type {
  ObservationPeriod,
  PositionDetail,
  PositionUpdateInputResponse,
  PositionUpdateItem,
  PositionUpdateResult,
  PositionUpdatesRead,
  RequestStatus,
  SessionStatus,
} from "./types";

const POLL_INTERVAL_MS = 4000;
const MAX_POLL_ATTEMPTS = 60;

const periods: Array<{ value: ObservationPeriod; label: string }> = [
  { value: "MORNING", label: "Pagi" },
  { value: "MIDDAY", label: "Siang" },
  { value: "AFTERNOON", label: "Sore" },
];

const resultSections: Array<[keyof PositionUpdateResult, string]> = [
  ["update_summary", "Ringkasan Update"],
  ["current_price", "Harga Saat Ini"],
  ["position_condition", "Kondisi Posisi Saat Ini"],
  ["orderbook_assessment", "Analisis Orderbook"],
  ["change_from_previous_analysis", "Perubahan Dibanding Analisis Sebelumnya"],
  ["target_realism", "Realisme Target"],
  ["downside_risk", "Risiko Penurunan"],
  ["target_probability", "Probabilitas Target"],
  ["trading_plan", "Trading Plan"],
  ["monitoring_points", "Poin Pemantauan"],
  ["warnings", "Peringatan Khusus"],
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
  return "Permintaan Position Update tidak dapat diproses. Silakan coba lagi.";
}

function isTerminal(status: RequestStatus): boolean {
  return status === "COMPLETED" || status === "FAILED";
}

export function PositionUpdateResultView({ result }: { result: PositionUpdateResult }) {
  return (
    <section aria-label="Hasil Position Update" className="space-y-3">
      <h3 className="sr-only">Hasil Position Update</h3>
      {resultSections.map(([key, label]) => {
        const val = result[key];
        if (val === undefined) return null;
        return (
          <article key={key} className="rounded-xl border border-zinc-200 bg-white p-4">
            <h4 className="font-semibold">{label}</h4>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-zinc-700">
              {displayValue(val)}
            </p>
          </article>
        );
      })}
    </section>
  );
}

export function PositionSummaryView({ position }: { position: PositionDetail }) {
  return (
    <section aria-label="Posisi terbuka" className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold text-emerald-950">Posisi OPEN</h3>
        <button
          type="button"
          aria-label="Tutup Posisi (CLOSE)"
          className="rounded-lg bg-zinc-800 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-zinc-700"
          onClick={() => {
            /* Phase 9 entry control boundary; non-operational in P8.5 */
          }}
        >
          Tutup Posisi (CLOSE)
        </button>
      </div>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-emerald-800">Status posisi</dt>
          <dd className="font-medium">{position.status}</dd>
        </div>
        <div>
          <dt className="text-emerald-800">Harga entry</dt>
          <dd className="font-medium">{position.entry_price}</dd>
        </div>
        <div>
          <dt className="text-emerald-800">Waktu entry</dt>
          <dd className="font-medium">{position.entry_timestamp}</dd>
        </div>
        <div>
          <dt className="text-emerald-800">Kuantitas</dt>
          <dd className="font-medium">{position.quantity}</dd>
        </div>
        <div>
          <dt className="text-emerald-800">Stop loss</dt>
          <dd className="font-medium">{position.stop_loss}</dd>
        </div>
        <div>
          <dt className="text-emerald-800">Target price</dt>
          <dd className="font-medium">{position.target_price}</dd>
        </div>
      </dl>
      {position.note && (
        <p className="mt-3 text-xs text-emerald-900 border-t border-emerald-200 pt-2">
          Catatan: {position.note}
        </p>
      )}
    </section>
  );
}

export function PositionUpdatePanel({
  sessionId,
  sessionStatus,
  initialPosition,
}: {
  sessionId: string;
  sessionStatus: SessionStatus;
  initialPosition?: PositionDetail | null;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [currentPrice, setCurrentPrice] = useState("");
  const [period, setPeriod] = useState<ObservationPeriod | "">("");
  const [timestamp, setTimestamp] = useState("");
  const [note, setNote] = useState("");
  const [readData, setReadData] = useState<PositionUpdatesRead | null>(null);
  const [busy, setBusy] = useState<"submit" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  useEffect(() => {
    let cancelled = false;
    if (sessionStatus !== "OPEN_POSITION") return;
    Promise.resolve(readPositionUpdates(sessionId))
      .then((data) => {
        if (!cancelled && data) setReadData(data);
      })
      .catch(() => {
        // Position update read fallback
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, sessionStatus]);

  const latestUpdate = readData?.updates && readData.updates.length > 0
    ? readData.updates[readData.updates.length - 1]
    : null;
  const isProcessing = latestUpdate && (latestUpdate.request_status === "PENDING" || latestUpdate.request_status === "PROCESSING");

  useEffect(() => {
    if (!isProcessing) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;

    const poll = async () => {
      if (cancelled || inFlight.current) return;
      inFlight.current = true;
      attempts += 1;
      try {
        const next = await Promise.resolve(readPositionUpdates(sessionId));
        if (cancelled) return;
        setReadData(next);
        const last = next.updates && next.updates.length > 0 ? next.updates[next.updates.length - 1] : null;
        if (last && isTerminal(last.request_status)) {
          // Finished processing
        } else if (attempts < MAX_POLL_ATTEMPTS) {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        } else {
          setError("Analisis masih diproses. Silakan buka kembali sesi ini nanti.");
        }
      } catch {
        if (!cancelled && attempts < MAX_POLL_ATTEMPTS) {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        } else if (!cancelled) {
          setError("Status Position Update belum dapat dimuat.");
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
  }, [isProcessing, sessionId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file || !currentPrice.trim() || !period || !timestamp) {
      setError("Orderbook, harga saat ini, periode observasi, dan waktu observasi wajib diisi.");
      return;
    }
    setBusy("submit");
    setError(null);
    try {
      const isoTimestamp = new Date(timestamp).toISOString();
      await uploadPositionUpdateInput(sessionId, {
        orderbook: file,
        current_price: currentPrice.trim(),
        observation_period: period,
        observation_timestamp: isoTimestamp,
      });
      await submitPositionUpdateAnalysis(sessionId);
      const nextRead = await readPositionUpdates(sessionId);
      setReadData(nextRead);
      setFile(null);
      setCurrentPrice("");
      setPeriod("");
      setTimestamp("");
      setNote("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : safeError());
    } finally {
      setBusy(null);
    }
  }

  const effectivePosition = readData?.position ?? initialPosition ?? null;
  const updates = readData?.updates ?? [];

  return (
    <section aria-label="Position Update Workspace" className="space-y-4">
      {effectivePosition && <PositionSummaryView position={effectivePosition} />}

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      )}

      {isProcessing && (
        <p role="status" className="rounded-xl border bg-white p-5 text-sm text-zinc-700 shadow-sm">
          Position Update sedang diproses. Silakan tunggu.
        </p>
      )}

      {sessionStatus === "OPEN_POSITION" && (
        <form onSubmit={handleSubmit} className="rounded-xl border bg-white p-5 shadow-sm space-y-3">
          <h3 className="font-semibold">Position Update</h3>
          <p className="mt-1 text-sm text-zinc-500">
            Unggah satu orderbook screenshot dan masukkan observasi terbaru posisi Anda.
          </p>
          <div className="space-y-3 pt-2">
            <label className="block text-sm font-medium" htmlFor="position-orderbook">
              Orderbook screenshot
              <input
                id="position-orderbook"
                type="file"
                accept="image/*"
                required
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="mt-1 block w-full text-sm"
              />
            </label>

            <label className="block text-sm font-medium" htmlFor="position-current-price">
              Harga saat ini
              <input
                id="position-current-price"
                required
                inputMode="decimal"
                value={currentPrice}
                onChange={(event) => setCurrentPrice(event.target.value)}
                className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2"
              />
            </label>

            <label className="block text-sm font-medium" htmlFor="position-observation-period">
              Periode observasi
              <select
                id="position-observation-period"
                required
                value={period}
                onChange={(event) => setPeriod(event.target.value as ObservationPeriod)}
                className="mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2"
              >
                <option value="">Pilih periode</option>
                {periods.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm font-medium" htmlFor="position-observation-timestamp">
              Waktu observasi
              <input
                id="position-observation-timestamp"
                type="datetime-local"
                required
                value={timestamp}
                onChange={(event) => setTimestamp(event.target.value)}
                className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2"
              />
            </label>

            <label className="block text-sm font-medium" htmlFor="position-note">
              Catatan opsional
              <textarea
                id="position-note"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                className="mt-1 block min-h-20 w-full rounded-lg border border-zinc-300 px-3 py-2"
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={busy !== null}
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy === "submit" ? "Mengirim…" : "Kirim Position Update"}
          </button>
        </form>
      )}

      {updates.length > 0 && (
        <section aria-label="Riwayat Position Update" className="space-y-4 pt-2">
          <h3 className="font-semibold text-lg">Riwayat Position Update</h3>
          {updates.map((item, idx) => (
            <article key={item.analysis_request_id || idx} className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 pb-3">
                <div>
                  <span className="text-xs font-semibold text-zinc-500 uppercase">
                    Update #{idx + 1} · {item.observation_period ?? "—"}
                  </span>
                  <h4 className="font-medium text-sm">
                    Harga: {item.current_price ?? "—"}
                  </h4>
                </div>
                <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-semibold">
                  {item.request_status}
                </span>
              </div>

              {item.observation_timestamp && (
                <p className="text-xs text-zinc-500">
                  Waktu observasi: {item.observation_timestamp}
                </p>
              )}

              {item.request_status === "FAILED" && (
                <div className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
                  <p className="font-medium">Analisis Position Update gagal diproses.</p>
                  {item.error_message && <p className="mt-1 text-xs">{item.error_message}</p>}
                </div>
              )}

              {item.request_status === "COMPLETED" && item.processed_response && (
                <PositionUpdateResultView result={item.processed_response} />
              )}
            </article>
          ))}
        </section>
      )}
    </section>
  );
}
