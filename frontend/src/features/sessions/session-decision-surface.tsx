"use client";

import { useEffect, useRef, useState } from "react";

import { buyDecision, skipDecision, waitDecision } from "@/features/trade-workspace/api";
import type { CurrentStep, SkipReason } from "@/features/trade-workspace/types";

type DecisionChoice = "BUY" | "WAIT" | "SKIP" | null;

export const SKIP_REASON_OPTIONS: ReadonlyArray<{ value: SkipReason; label: string }> = [
  { value: "RISK_TOO_HIGH", label: "Risiko Terlalu Tinggi" },
  { value: "SETUP_NOT_ATTRACTIVE", label: "Setup Tidak Menarik" },
  { value: "ORDERBOOK_WEAK", label: "Orderbook Lemah" },
  { value: "MARKET_CONDITION_UNFAVORABLE", label: "Kondisi Pasar Tidak Mendukung" },
  { value: "WAITING_TOO_LONG", label: "Waktu Tunggu Terlalu Lama" },
  { value: "USER_DECISION", label: "Keputusan Pengguna" },
  { value: "OTHER", label: "Lainnya" },
];

export function SessionDecisionSurface({
  sessionId,
  step,
  refetch,
}: {
  sessionId: string;
  step: CurrentStep;
  refetch: () => Promise<unknown>;
}) {
  const actions = step.workflow_actions;
  const isAvailable =
    step.mode === "ACTIONABLE" &&
    !step.read_only &&
    (actions.includes("BUY") || actions.includes("WAIT") || actions.includes("SKIP"));

  const generationRef = useRef(0);
  const submittingRef = useRef(false);

  const [selectedChoice, setSelectedChoice] = useState<DecisionChoice>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorFeedback, setErrorFeedback] = useState<string | null>(null);

  const [buyFields, setBuyFields] = useState({
    entryPrice: "",
    entryTimestamp: "",
    quantity: "",
    stopLoss: "",
    targetPrice: "",
    note: "",
  });

  const [skipReason, setSkipReason] = useState<SkipReason>("RISK_TOO_HIGH");
  const [skipNote, setSkipNote] = useState("");
  const [showSkipConfirm, setShowSkipConfirm] = useState(false);

  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    generationRef.current += 1;
    submittingRef.current = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelectedChoice(null);
    setIsSubmitting(false);
    setErrorFeedback(null);
    setValidationError(null);
    setShowSkipConfirm(false);
    setBuyFields({
      entryPrice: "",
      entryTimestamp: "",
      quantity: "",
      stopLoss: "",
      targetPrice: "",
      note: "",
    });
    setSkipReason("RISK_TOO_HIGH");
    setSkipNote("");
  }, [sessionId]);

  const handleSelectChoice = (choice: DecisionChoice) => {
    if (isSubmitting) return;
    setSelectedChoice(choice);
    setErrorFeedback(null);
    setValidationError(null);
    setShowSkipConfirm(false);
  };

  const handleBuySubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isSubmitting || submittingRef.current) return;

    const price = Number.parseFloat(buyFields.entryPrice);
    const qty = Number.parseFloat(buyFields.quantity);
    const sl = Number.parseFloat(buyFields.stopLoss);
    const tp = Number.parseFloat(buyFields.targetPrice);

    if (
      !buyFields.entryPrice ||
      Number.isNaN(price) ||
      price <= 0 ||
      !buyFields.quantity ||
      Number.isNaN(qty) ||
      qty <= 0 ||
      !buyFields.stopLoss ||
      Number.isNaN(sl) ||
      sl <= 0 ||
      !buyFields.targetPrice ||
      Number.isNaN(tp) ||
      tp <= 0
    ) {
      setValidationError("Semua nilai harga dan jumlah harus berupa angka positif.");
      return;
    }

    if (!buyFields.entryTimestamp || buyFields.entryTimestamp.trim().length === 0) {
      setValidationError("Waktu masuk harus diisi.");
      return;
    }

    setValidationError(null);
    setErrorFeedback(null);
    setIsSubmitting(true);
    submittingRef.current = true;
    const currentGen = ++generationRef.current;

    let formattedTimestamp = buyFields.entryTimestamp;
    try {
      const parsedDate = new Date(buyFields.entryTimestamp);
      if (!Number.isNaN(parsedDate.getTime())) {
        formattedTimestamp = parsedDate.toISOString();
      }
    } catch {
      // Use raw timestamp
    }

    try {
      await buyDecision(sessionId, {
        entry_price: buyFields.entryPrice,
        entry_timestamp: formattedTimestamp,
        quantity: buyFields.quantity,
        stop_loss: buyFields.stopLoss,
        target_price: buyFields.targetPrice,
        note: buyFields.note.trim() ? buyFields.note.trim() : null,
      });

      if (currentGen !== generationRef.current) return;
      await refetch();
      if (currentGen !== generationRef.current) return;
      setSelectedChoice(null);
    } catch {
      if (currentGen === generationRef.current) {
        setErrorFeedback(
          "Keputusan belum dapat disimpan. Periksa kembali data yang dimasukkan lalu coba lagi.",
        );
      }
    } finally {
      if (currentGen === generationRef.current) {
        setIsSubmitting(false);
        submittingRef.current = false;
      }
    }
  };

  const handleWaitSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isSubmitting || submittingRef.current) return;

    setValidationError(null);
    setErrorFeedback(null);
    setIsSubmitting(true);
    submittingRef.current = true;
    const currentGen = ++generationRef.current;

    try {
      await waitDecision(sessionId);
      if (currentGen !== generationRef.current) return;
      await refetch();
      if (currentGen !== generationRef.current) return;
      setSelectedChoice(null);
    } catch {
      if (currentGen === generationRef.current) {
        setErrorFeedback(
          "Keputusan belum dapat disimpan. Periksa kembali data yang dimasukkan lalu coba lagi.",
        );
      }
    } finally {
      if (currentGen === generationRef.current) {
        setIsSubmitting(false);
        submittingRef.current = false;
      }
    }
  };

  const handleSkipSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isSubmitting || submittingRef.current) return;

    if (!skipReason) {
      setValidationError("Pilih alasan lewati sesi.");
      return;
    }

    if (!showSkipConfirm) {
      setValidationError(null);
      setErrorFeedback(null);
      setShowSkipConfirm(true);
      return;
    }

    setValidationError(null);
    setErrorFeedback(null);
    setIsSubmitting(true);
    submittingRef.current = true;
    const currentGen = ++generationRef.current;

    try {
      await skipDecision(sessionId, {
        reason: skipReason,
        note: skipNote.trim() ? skipNote.trim() : null,
      });
      if (currentGen !== generationRef.current) return;
      await refetch();
      if (currentGen !== generationRef.current) return;
      setSelectedChoice(null);
      setShowSkipConfirm(false);
    } catch {
      if (currentGen === generationRef.current) {
        setErrorFeedback(
          "Keputusan belum dapat disimpan. Periksa kembali data yang dimasukkan lalu coba lagi.",
        );
      }
    } finally {
      if (currentGen === generationRef.current) {
        setIsSubmitting(false);
        submittingRef.current = false;
      }
    }
  };

  if (!isAvailable) return null;

  return (
    <section
      aria-labelledby="decision-surface-title"
      className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8 sm:px-6 sm:pb-10 lg:px-8"
    >
      <div className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
        <h2
          id="decision-surface-title"
          className="text-xl font-bold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]"
        >
          Pilih Keputusan Sesi
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text-muted)]">
          Tentukan langkah selanjutnya untuk sesi ini: BUY (buka posisi), WAIT (tunggu orderbook berikutnya), atau SKIP (lewati sesi).
        </p>

        <div className="mt-5 grid min-w-0 gap-3 sm:grid-cols-3">
          {actions.includes("BUY") ? (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => handleSelectChoice(selectedChoice === "BUY" ? null : "BUY")}
              aria-pressed={selectedChoice === "BUY"}
              className={`flex min-h-11 min-w-0 items-center justify-center rounded-[var(--radius-compact)] border px-4 font-semibold outline-offset-2 focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] ${
                selectedChoice === "BUY"
                  ? "border-[var(--color-status-success)] bg-[var(--color-status-success-subtle)] font-bold text-[var(--color-status-success)]"
                  : "border-[var(--color-border-default)] bg-[var(--color-surface-standard)] text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)]"
              }`}
            >
              Beli (BUY)
            </button>
          ) : null}

          {actions.includes("WAIT") ? (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => handleSelectChoice(selectedChoice === "WAIT" ? null : "WAIT")}
              aria-pressed={selectedChoice === "WAIT"}
              className={`flex min-h-11 min-w-0 items-center justify-center rounded-[var(--radius-compact)] border px-4 font-semibold outline-offset-2 focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] ${
                selectedChoice === "WAIT"
                  ? "border-[var(--color-status-information)] bg-[var(--color-status-information-subtle)] font-bold text-[var(--color-status-information)]"
                  : "border-[var(--color-border-default)] bg-[var(--color-surface-standard)] text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)]"
              }`}
            >
              Tunggu (WAIT)
            </button>
          ) : null}

          {actions.includes("SKIP") ? (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => handleSelectChoice(selectedChoice === "SKIP" ? null : "SKIP")}
              aria-pressed={selectedChoice === "SKIP"}
              className={`flex min-h-11 min-w-0 items-center justify-center rounded-[var(--radius-compact)] border px-4 font-semibold outline-offset-2 focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] ${
                selectedChoice === "SKIP"
                  ? "border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] font-bold text-[var(--color-status-warning)]"
                  : "border-[var(--color-border-default)] bg-[var(--color-surface-standard)] text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)]"
              }`}
            >
              Lewati (SKIP)
            </button>
          ) : null}
        </div>

        {validationError ? (
          <p id="decision-validation-error" role="alert" className="mt-4 break-words text-sm font-medium text-[var(--color-status-danger)]">
            {validationError}
          </p>
        ) : null}

        {errorFeedback ? (
          <div role="alert" className="mt-4 rounded-[var(--radius-compact)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-3 text-sm text-[var(--color-status-danger)]">
            <p className="font-bold">Keputusan belum dapat disimpan</p>
            <p className="mt-1">{errorFeedback}</p>
          </div>
        ) : null}

        {selectedChoice === "BUY" ? (
          <form noValidate onSubmit={handleBuySubmit} className="mt-6 min-w-0 space-y-4 border-t border-[var(--color-border-default)] pt-5">
            <h3 className="text-base font-bold text-[var(--color-text-strong)]">Formulir Keputusan BUY</h3>
            <div className="grid min-w-0 gap-4 sm:grid-cols-2">
              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                Harga Masuk (Entry Price) *
                <input
                  type="number"
                  inputMode="decimal"
                  step="any"
                  min="0"
                  required
                  disabled={isSubmitting}
                  value={buyFields.entryPrice}
                  onChange={(e) => setBuyFields({ ...buyFields, entryPrice: e.target.value })}
                  placeholder="cth. 5000"
                  className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                />
              </label>

              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                Waktu Masuk *
                <input
                  type="datetime-local"
                  required
                  disabled={isSubmitting}
                  value={buyFields.entryTimestamp}
                  onChange={(e) => setBuyFields({ ...buyFields, entryTimestamp: e.target.value })}
                  className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                />
              </label>

              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                Jumlah Saham (Quantity) *
                <input
                  type="number"
                  inputMode="numeric"
                  step="any"
                  min="0"
                  required
                  disabled={isSubmitting}
                  value={buyFields.quantity}
                  onChange={(e) => setBuyFields({ ...buyFields, quantity: e.target.value })}
                  placeholder="cth. 100"
                  className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                />
              </label>

              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                Stop Loss *
                <input
                  type="number"
                  inputMode="decimal"
                  step="any"
                  min="0"
                  required
                  disabled={isSubmitting}
                  value={buyFields.stopLoss}
                  onChange={(e) => setBuyFields({ ...buyFields, stopLoss: e.target.value })}
                  placeholder="cth. 4800"
                  className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                />
              </label>

              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)] sm:col-span-2">
                Target Profit *
                <input
                  type="number"
                  inputMode="decimal"
                  step="any"
                  min="0"
                  required
                  disabled={isSubmitting}
                  value={buyFields.targetPrice}
                  onChange={(e) => setBuyFields({ ...buyFields, targetPrice: e.target.value })}
                  placeholder="cth. 5500"
                  className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                />
              </label>
            </div>

            <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
              Catatan (Opsional)
              <textarea
                rows={2}
                disabled={isSubmitting}
                value={buyFields.note}
                onChange={(e) => setBuyFields({ ...buyFields, note: e.target.value })}
                placeholder="Catatan tambahan mengenai pembelian..."
                className="mt-1 block w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
              />
            </label>

            <div className="flex min-w-0 flex-col gap-3 pt-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => setSelectedChoice(null)}
                className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
                className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-6 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
              >
                {isSubmitting ? "Mengirim..." : "Kirim Keputusan BUY"}
              </button>
            </div>
          </form>
        ) : null}

        {selectedChoice === "WAIT" ? (
          <form noValidate onSubmit={handleWaitSubmit} className="mt-6 min-w-0 space-y-4 border-t border-[var(--color-border-default)] pt-5">
            <h3 className="text-base font-bold text-[var(--color-text-strong)]">Konfirmasi Keputusan WAIT</h3>
            <p className="text-sm text-[var(--color-text-default)]">
              Keputusan WAIT akan mengubah status sesi menjadi Menunggu (WAITING). Anda dapat memperbarui orderbook di kemudian hari.
            </p>

            <div className="flex min-w-0 flex-col gap-3 pt-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => setSelectedChoice(null)}
                className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
                className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-6 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
              >
                {isSubmitting ? "Menyimpan WAIT..." : "Kirim Keputusan WAIT"}
              </button>
            </div>
          </form>
        ) : null}

        {selectedChoice === "SKIP" ? (
          <form noValidate onSubmit={handleSkipSubmit} className="mt-6 min-w-0 space-y-4 border-t border-[var(--color-border-default)] pt-5">
            <h3 className="text-base font-bold text-[var(--color-text-strong)]">Formulir Keputusan SKIP</h3>

            {showSkipConfirm ? (
              <div role="alert" className="rounded-[var(--radius-compact)] border border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] p-3 text-sm text-[var(--color-status-warning)]">
                <p className="font-bold">Konfirmasi Lewati Sesi</p>
                <p className="mt-1">
                  Sesi ini akan ditutup secara permanen tanpa membuka posisi (status CLOSED_SKIPPED). Apakah Anda yakin?
                </p>
              </div>
            ) : null}

            <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
              Alasan Lewati Sesi (SKIP) *
              <select
                required
                disabled={isSubmitting || showSkipConfirm}
                value={skipReason}
                onChange={(e) => {
                  setSkipReason(e.target.value as SkipReason);
                  setShowSkipConfirm(false);
                }}
                className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                {SKIP_REASON_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
              Catatan (Opsional)
              <textarea
                rows={2}
                disabled={isSubmitting || showSkipConfirm}
                value={skipNote}
                onChange={(e) => setSkipNote(e.target.value)}
                placeholder="Catatan tambahan mengenai keputusan lewati sesi..."
                className="mt-1 block w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
              />
            </label>

            <div className="flex min-w-0 flex-col gap-3 pt-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => {
                  setShowSkipConfirm(false);
                  setSelectedChoice(null);
                }}
                className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
                className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-6 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
              >
                {isSubmitting
                  ? "Menyimpan SKIP..."
                  : showSkipConfirm
                    ? "Konfirmasi Lewati Sesi"
                    : "Kirim Keputusan SKIP"}
              </button>
            </div>
          </form>
        ) : null}
      </div>
    </section>
  );
}
