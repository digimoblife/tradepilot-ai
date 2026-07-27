"use client";

import { useState } from "react";
import {
  ensureOpenPositionBatch,
  updateOpenPositionBatchSlot,
  confirmStop,
  confirmTarget,
} from "@/lib/api/trade-sessions";
import type { TradeState, EvidenceBatchSummary } from "@/types/trade-session";
import { ApiError } from "@/lib/api/errors";

interface OpenPositionPanelProps {
  sessionId: string;
  tradeState: TradeState;
  currentBatch?: EvidenceBatchSummary | null;
  allowedActions: string[];
  onRequestUpdate: () => void;
  onFullExit: () => void;
  onSuccess: () => void;
}

const SLOT_LABELS: Record<string, string> = {
  MORNING: "Pagi / Pembukaan",
  MIDDAY: "Siang / Jeda Pasar",
  CLOSE: "Sore / Penutupan",
  UNSPECIFIED: "Tidak Ditentukan",
};

export function OpenPositionPanel({
  sessionId,
  tradeState,
  currentBatch,
  allowedActions,
  onRequestUpdate,
  onFullExit,
  onSuccess,
}: OpenPositionPanelProps) {
  const [updatingSlot, setUpdatingSlot] = useState(false);
  const [showStopModal, setShowStopModal] = useState(false);
  const [showTargetModal, setShowTargetModal] = useState(false);
  const [stopPrice, setStopPrice] = useState(tradeState.active_stop_loss || "");
  const [targetPrice, setTargetPrice] = useState(tradeState.active_target || "");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const slot = currentBatch?.monitoring_slot || "UNSPECIFIED";

  async function handleSlotChange(newSlot: string) {
    if (!currentBatch || currentBatch.status !== "DRAFT") return;
    setUpdatingSlot(true);
    setError(null);
    try {
      await updateOpenPositionBatchSlot(sessionId, currentBatch.id, newSlot);
      onSuccess();
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Gagal memperbarui slot pemantauan.");
      }
    } finally {
      setUpdatingSlot(false);
    }
  }

  async function handleConfirmStop(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await confirmStop(sessionId, {
        price: parseFloat(stopPrice),
        idempotency_key: `stop_${sessionId}_${Date.now()}`,
        note: note || undefined,
      });
      setShowStopModal(false);
      onSuccess();
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Gagal mengonfirmasi stop loss.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirmTarget(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await confirmTarget(sessionId, {
        price: parseFloat(targetPrice),
        idempotency_key: `target_${sessionId}_${Date.now()}`,
        note: note || undefined,
      });
      setShowTargetModal(false);
      onSuccess();
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Gagal mengonfirmasi target.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/80 p-4 space-y-4 text-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700 pb-3">
        <h3 className="text-lg font-semibold text-emerald-400">Posisi Terbuka</h3>
        <div className="flex flex-wrap items-center gap-2">
          {allowedActions.includes("REQUEST_OPEN_POSITION_UPDATE") && (
            <button
              onClick={onRequestUpdate}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
            >
              Minta Update Posisi
            </button>
          )}
          {allowedActions.includes("CONFIRM_STOP") || allowedActions.includes("CHANGE_STOP") ? (
            <button
              onClick={() => setShowStopModal(true)}
              className="rounded bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-500 transition-colors"
            >
              Ubah Stop Loss
            </button>
          ) : null}
          {allowedActions.includes("CONFIRM_TARGET") || allowedActions.includes("CHANGE_TARGET") ? (
            <button
              onClick={() => setShowTargetModal(true)}
              className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 transition-colors"
            >
              Ubah Target
            </button>
          ) : null}
          {allowedActions.includes("FULL_EXIT") && (
            <button
              onClick={onFullExit}
              className="rounded bg-rose-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-500 transition-colors"
            >
              Jual
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded bg-rose-900/50 border border-rose-700 p-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      {/* Position Facts Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div className="rounded bg-slate-900/60 p-2.5">
          <div className="text-slate-400 text-xs">Harga Masuk</div>
          <div className="font-semibold text-slate-100">
            {tradeState.entry_price ? `Rp ${parseFloat(tradeState.entry_price).toLocaleString("id-ID")}` : "Tidak tersedia"}
          </div>
        </div>
        <div className="rounded bg-slate-900/60 p-2.5">
          <div className="text-slate-400 text-xs">Jumlah Lot/Saham</div>
          <div className="font-semibold text-slate-100">
            {tradeState.remaining_quantity ? parseFloat(tradeState.remaining_quantity).toLocaleString("id-ID") : "Tidak tersedia"}
          </div>
        </div>
        <div className="rounded bg-slate-900/60 p-2.5">
          <div className="text-slate-400 text-xs">Stop Loss Aktif</div>
          <div className="font-semibold text-rose-300">
            {tradeState.active_stop_loss ? `Rp ${parseFloat(tradeState.active_stop_loss).toLocaleString("id-ID")}` : "Belum ditentukan"}
          </div>
        </div>
        <div className="rounded bg-slate-900/60 p-2.5">
          <div className="text-slate-400 text-xs">Target Aktif</div>
          <div className="font-semibold text-emerald-300">
            {tradeState.active_target ? `Rp ${parseFloat(tradeState.active_target).toLocaleString("id-ID")}` : "Belum ditentukan"}
          </div>
        </div>
      </div>

      {/* Monitoring Slot Selector */}
      {currentBatch && currentBatch.status === "DRAFT" && (
        <div className="rounded border border-slate-700 bg-slate-900/40 p-3 space-y-2">
          <div className="text-xs font-medium text-slate-300">Slot Pemantauan Batch Ini:</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(SLOT_LABELS).map(([key, label]) => (
              <button
                key={key}
                disabled={updatingSlot}
                onClick={() => handleSlotChange(key)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                  slot === key
                    ? "bg-blue-600 text-white"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Stop Loss Modal */}
      {showStopModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <form onSubmit={handleConfirmStop} className="w-full max-w-md rounded-lg border border-slate-700 bg-slate-800 p-5 space-y-4">
            <h4 className="text-base font-semibold">Konfirmasi Stop Loss</h4>
            <div>
              <label className="block text-xs font-medium text-slate-400">Harga Stop Loss (Rp)</label>
              <input
                type="number"
                required
                value={stopPrice}
                onChange={(e) => setStopPrice(e.target.value)}
                className="mt-1 w-full rounded border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400">Catatan (Opsional)</label>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="mt-1 w-full rounded border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowStopModal(false)}
                className="rounded bg-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-600"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="rounded bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-500"
              >
                Simpan
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Target Modal */}
      {showTargetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <form onSubmit={handleConfirmTarget} className="w-full max-w-md rounded-lg border border-slate-700 bg-slate-800 p-5 space-y-4">
            <h4 className="text-base font-semibold">Konfirmasi Target</h4>
            <div>
              <label className="block text-xs font-medium text-slate-400">Harga Target (Rp)</label>
              <input
                type="number"
                required
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                className="mt-1 w-full rounded border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400">Catatan (Opsional)</label>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="mt-1 w-full rounded border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowTargetModal(false)}
                className="rounded bg-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-600"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500"
              >
                Simpan
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
