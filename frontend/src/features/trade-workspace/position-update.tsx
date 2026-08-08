"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  closePosition,
  readPositionUpdates,
  submitPositionUpdateAnalysis,
  uploadPositionUpdateInput,
} from "./api";
import type {
  CloseResponse,
  ObservationPeriod,
  PositionDetail,
  PositionUpdateResult,
  PositionUpdatesRead,
  RequestStatus,
  SessionStatus,
} from "./types";
import { safeErrorMessage } from "./safe-error";
import { ClosePositionForm } from "./components/close-position-form";
import { PositionUpdateFeedback } from "./components/position-update-feedback";
import { PositionUpdateForm } from "./components/position-update-form";

const POLL_INTERVAL_MS = 4000;
const MAX_POLL_ATTEMPTS = 60;

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
    <section aria-label="Hasil Position Update" className="grid gap-[var(--space-4)]">
      <h3 className="sr-only">Hasil Position Update</h3>
      {resultSections.map(([key, label]) => {
        const val = result[key];
        if (val === undefined) return null;
        return (<div key={key} className="contents">
          <article key={key} className="rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-elevated-background)] p-4">
            <h4 className="text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-strong)]">{label}</h4>
            <p className="mt-2 whitespace-pre-wrap text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">
              {displayValue(val)}
            </p>
          </article>
          {key === "orderbook_assessment" && result.broker_flow_analysis && (
            <article className="rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-elevated-background)] p-4">
              <h4 className="text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-strong)]">Analisa Broker Flow</h4>
              <p className="mt-2 text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-strong)]">{result.broker_flow_analysis.assessment}</p>
              <p className="mt-1 whitespace-pre-wrap text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{result.broker_flow_analysis.analysis}</p>
            </article>
          )}
        </div>);
      })}
    </section>
  );
}

export function CloseResultSummaryView({ closure }: { closure: CloseResponse }) {
  return (
    <section aria-label="Hasil Penutupan Posisi (CLOSE)" className="space-y-3 rounded-[var(--radius-large)] border border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] p-[var(--space-card)] shadow-[var(--elevation-low)]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border-default)] pb-3">
        <h3 className="font-semibold text-[var(--color-text-strong)]">Ringkasan Penutupan Posisi (CLOSE)</h3>
        <span className="rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-muted)] px-3 py-1 text-[var(--text-size-status)] font-semibold text-[var(--color-text-default)]">
          CLOSED
        </span>
      </div>
      <dl className="grid gap-3 text-[var(--text-size-compact-body)] sm:grid-cols-2">
        <div>
          <dt className="text-[var(--color-text-muted)]">Harga penutupan</dt>
          <dd className="font-medium">{closure.close_price}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Waktu penutupan</dt>
          <dd className="font-medium">{closure.close_timestamp}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Alasan penutupan</dt>
          <dd className="font-medium">{closure.close_reason}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Realized PnL</dt>
          <dd className="font-semibold text-[var(--color-text-strong)]">
            {closure.realized_profit_loss}
          </dd>
        </div>
      </dl>
      {closure.note && (
        <p className="border-t border-[var(--color-border-default)] pt-2 text-[var(--text-size-label)] text-[var(--color-text-default)]">
          Catatan: {closure.note}
        </p>
      )}
    </section>
  );
}

export function PositionSummaryView({
  position,
  onOpenCloseForm,
  showCloseButton = true,
}: {
  position: PositionDetail;
  onOpenCloseForm?: () => void;
  showCloseButton?: boolean;
}) {
  const isOpen = position.status === "OPEN";
  return (
    <section aria-label="Posisi terbuka" className="rounded-[var(--radius-large)] border border-[var(--color-accent)] bg-[var(--color-accent-subtle)] p-[var(--space-card)] shadow-[var(--elevation-low)]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold text-[var(--color-text-strong)]">
          {isOpen ? "Posisi OPEN" : "Posisi CLOSED"}
        </h3>
        {showCloseButton && isOpen && (
          <button
            type="button"
            aria-label="Tutup Posisi (CLOSE)"
            className="rounded-[var(--radius-compact)] bg-[var(--color-text-strong)] px-3.5 py-1.5 text-[var(--text-size-status)] font-semibold text-white shadow-[var(--elevation-low)] hover:opacity-90"
            onClick={() => onOpenCloseForm?.()}
          >
            Tutup Posisi (CLOSE)
          </button>
        )}
      </div>
      <dl className="mt-4 grid gap-3 text-[var(--text-size-compact-body)] sm:grid-cols-2">
        <div>
          <dt className="text-[var(--color-text-muted)]">Status posisi</dt>
          <dd className="font-medium">{position.status}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Harga entry</dt>
          <dd className="font-medium">{position.entry_price}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Waktu entry</dt>
          <dd className="font-medium">{position.entry_timestamp}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Kuantitas</dt>
          <dd className="font-medium">{position.quantity}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Stop loss</dt>
          <dd className="font-medium">{position.stop_loss}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Target price</dt>
          <dd className="font-medium">{position.target_price}</dd>
        </div>
      </dl>
      {position.note && (
        <p className="mt-4 border-t border-[var(--color-accent)] pt-2 text-[var(--text-size-label)] text-[var(--color-text-default)]">
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
  onClosed,
}: {
  sessionId: string;
  sessionStatus: SessionStatus;
  initialPosition?: PositionDetail | null;
  onClosed?: () => void | Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [brokerFlowFile, setBrokerFlowFile] = useState<File | null>(null);
  const [currentPrice, setCurrentPrice] = useState("");
  const [period, setPeriod] = useState<ObservationPeriod | "">("");
  const [timestamp, setTimestamp] = useState("");
  const [note, setNote] = useState("");

  // CLOSE flow states
  const [showCloseForm, setShowCloseForm] = useState(false);
  const [closePrice, setClosePrice] = useState("");
  const [closeTimestamp, setCloseTimestamp] = useState("");
  const [closeReason, setCloseReason] = useState("");
  const [closeNote, setCloseNote] = useState("");
  const [closeResult, setCloseResult] = useState<CloseResponse | null>(null);
  const [closeSuccessMsg, setCloseSuccessMsg] = useState<string | null>(null);

  const [readData, setReadData] = useState<PositionUpdatesRead | null>(null);
  const [busy, setBusy] = useState<"submit" | "close" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const effectiveSessionStatus: SessionStatus = closeResult ? "CLOSED" : sessionStatus;

  useEffect(() => {
    let cancelled = false;
    if (effectiveSessionStatus !== "OPEN_POSITION" && effectiveSessionStatus !== "CLOSED") return;
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
  }, [sessionId, effectiveSessionStatus]);

  const latestUpdate = readData?.updates && readData.updates.length > 0
    ? readData.updates[readData.updates.length - 1]
    : null;
  const isProcessing = effectiveSessionStatus === "OPEN_POSITION" && latestUpdate && (latestUpdate.request_status === "PENDING" || latestUpdate.request_status === "PROCESSING");

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
        broker_flow_1d: brokerFlowFile,
        current_price: currentPrice.trim(),
        observation_period: period,
        observation_timestamp: isoTimestamp,
      });
      await submitPositionUpdateAnalysis(sessionId);
      const nextRead = await Promise.resolve(readPositionUpdates(sessionId));
      setReadData(nextRead);
      setFile(null);
      setBrokerFlowFile(null);
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

  async function handleCloseSubmit(event: FormEvent) {
    event.preventDefault();
    if (!closePrice.trim() || !closeTimestamp || !closeReason.trim()) {
      setError("Harga penutupan, waktu penutupan, dan alasan penutupan wajib diisi.");
      return;
    }
    const numericPrice = Number(closePrice.trim());
    if (isNaN(numericPrice) || numericPrice <= 0) {
      setError("Harga penutupan harus bernilai positif.");
      return;
    }

    setBusy("close");
    setError(null);
    try {
      const isoTimestamp = new Date(closeTimestamp).toISOString();
      const result = await closePosition(sessionId, {
        close_price: closePrice.trim(),
        close_timestamp: isoTimestamp,
        close_reason: closeReason.trim(),
        note: closeNote.trim() || null,
      });
      setCloseResult(result);
      setCloseSuccessMsg("Posisi berhasil ditutup.");
      setShowCloseForm(false);
      try {
        await onClosed?.();
      } catch {
        // Refresh failure does not revert a successful CLOSE
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : safeError());
    } finally {
      setBusy(null);
    }
  }

  let effectivePosition = readData?.position ?? initialPosition ?? null;
  if (closeResult && effectivePosition) {
    effectivePosition = { ...effectivePosition, status: "CLOSED" };
  }
  const updates = readData?.updates ?? [];

  return (
    <section aria-label="Position Update Workspace" className="space-y-[var(--space-5)]">
      {effectivePosition && (
        <PositionSummaryView
          position={effectivePosition}
          showCloseButton={effectiveSessionStatus === "OPEN_POSITION" && !closeResult}
          onOpenCloseForm={() => setShowCloseForm((prev) => !prev)}
        />
      )}

      {error && <PositionUpdateFeedback kind="error">{error}</PositionUpdateFeedback>}

      {closeSuccessMsg && <PositionUpdateFeedback kind="success">{closeSuccessMsg}</PositionUpdateFeedback>}

      {closeResult && <CloseResultSummaryView closure={closeResult} />}

      {showCloseForm && effectiveSessionStatus === "OPEN_POSITION" && !closeResult && (
        <ClosePositionForm
          closePrice={closePrice}
          closeTimestamp={closeTimestamp}
          closeReason={closeReason}
          closeNote={closeNote}
          busy={busy !== null}
          onSubmit={handleCloseSubmit}
          onPriceChange={setClosePrice}
          onTimestampChange={setCloseTimestamp}
          onReasonChange={setCloseReason}
          onNoteChange={setCloseNote}
          onCancel={() => setShowCloseForm(false)}
        />
      )}

      {isProcessing && (
        <PositionUpdateFeedback kind="processing">Position Update sedang diproses. Silakan tunggu.</PositionUpdateFeedback>
      )}

      {effectiveSessionStatus === "OPEN_POSITION" && !closeResult && (
        <PositionUpdateForm
          currentPrice={currentPrice}
          period={period}
          timestamp={timestamp}
          note={note}
          busy={busy !== null}
          brokerFlowFile={brokerFlowFile}
          onSubmit={handleSubmit}
          onFileChange={(event) => setFile(event.target.files?.[0] ?? null)}
          onBrokerFlowFileChange={(event) => setBrokerFlowFile(event.target.files?.[0] ?? null)}
          onCurrentPriceChange={setCurrentPrice}
          onPeriodChange={setPeriod}
          onTimestampChange={setTimestamp}
          onNoteChange={setNote}
        />
      )}

      {updates.length > 0 && (
        <section aria-label="Riwayat Position Update" className="space-y-[var(--space-4)] border-t border-[var(--color-border-default)] pt-[var(--space-6)]">
          <div>
            <h3 className="mt-1 text-[var(--text-size-section-title)] font-semibold text-[var(--color-text-strong)]">Riwayat Position Update</h3>
          </div>
          {updates.map((item, idx) => (
            <article key={item.analysis_request_id || idx} className="space-y-3 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-factual)] p-[var(--space-card)] shadow-[var(--elevation-low)]">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border-default)] pb-3">
                <div>
                  <span className="text-[var(--text-size-status)] font-semibold uppercase tracking-[0.06em] text-[var(--color-text-muted)]">
                    {item.observation_period ?? "—"}
                  </span>
                  <h4 className="text-[var(--text-size-compact-body)] font-semibold text-[var(--color-text-strong)]">
                    Harga: {item.current_price ?? "—"}
                  </h4>
                </div>
                <span className="rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-elevated-background)] px-2.5 py-1 text-[var(--text-size-status)] font-semibold text-[var(--color-text-default)]">
                  {item.request_status}
                </span>
              </div>

              {item.observation_timestamp && (
                <p className="text-[var(--text-size-label)] text-[var(--color-text-muted)]">
                  Waktu observasi: {item.observation_timestamp}
                </p>
              )}

              {item.request_status === "FAILED" && (
                <div className="rounded-[var(--radius-compact)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-3 text-[var(--text-size-compact-body)] text-[var(--color-text-default)]">
                  <p className="font-medium">Analisis Position Update gagal diproses.</p>
                  <p className="mt-1 text-[var(--text-size-label)]">{safeErrorMessage(item.error_message, "position")}</p>
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
