"use client";

import { useState, useCallback, useRef } from "react";
import { fullExit } from "@/lib/api/trade-actions";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { currency } from "@/features/analysis/helpers";
import type { FullExitRequest } from "@/types/trade-action";

function generateIdempotencyKey(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function toApiNumber(value: string): string {
  return value.replace(/[^0-9.,-]/g, "").replace(/,/g, ".");
}

function parseNum(value: string): number {
  const n = parseFloat(toApiNumber(value));
  return isNaN(n) ? 0 : n;
}

function formatSigned(value: number): string {
  const s = Math.abs(value).toLocaleString("id-ID");
  return value < 0 ? `-${s}` : s;
}

function nowISO(): string {
  return new Date().toISOString();
}

const CLOSING_REASON_LABEL: Record<string, string> = {
  TAKE_PROFIT: "Take Profit",
  STOP_LOSS: "Stop Loss",
  THESIS_INVALIDATED: "Thesis Tidak Valid",
  MANUAL_EXIT: "Exit Manual",
  RISK_REDUCTION: "Pengurangan Risiko",
  TIME_EXIT: "Exit Berdasarkan Waktu",
  OTHER: "Lainnya",
};

interface FormErrors {
  exitPrice?: string;
  executedAt?: string;
  closingReason?: string;
}

interface Props {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  remainingQuantity: string | null;
  entryPrice: string | null;
  activeStopLoss: string | null;
  activeTarget: string | null;
}

export function FullExitModal({ sessionId, isOpen, onClose, onSuccess, remainingQuantity, entryPrice, activeStopLoss, activeTarget }: Props) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <FullExitForm key={sessionId} sessionId={sessionId} onClose={onClose} onSuccess={onSuccess} remainingQuantity={remainingQuantity} entryPrice={entryPrice} activeStopLoss={activeStopLoss} activeTarget={activeTarget} />
      </div>
    </div>
  );
}

function FullExitForm({ sessionId, onClose, onSuccess, remainingQuantity, entryPrice, activeStopLoss, activeTarget }: { sessionId: string; onClose: () => void; onSuccess: () => void; remainingQuantity: string | null; entryPrice: string | null; activeStopLoss: string | null; activeTarget: string | null }) {
  const rq = remainingQuantity ? parseFloat(remainingQuantity) : 0;
  const epCanonical = entryPrice ? parseFloat(entryPrice) : 0;

  const [exitPrice, setExitPrice] = useState("");
  const [executedAt, setExecutedAt] = useState(nowISO().slice(0, 16));
  const [closingReason, setClosingReason] = useState("");
  const [fees, setFees] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitState, setSubmitState] = useState<"idle" | "pending" | { type: "error"; message: string }>("idle");
  const cancelledRef = useRef(false);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    const fieldErrors: FormErrors = {};
    const ep = parseFloat(toApiNumber(exitPrice));
    if (!exitPrice.trim() || isNaN(ep) || ep <= 0) fieldErrors.exitPrice = "Harga exit harus lebih besar dari 0.";
    if (!executedAt.trim()) fieldErrors.executedAt = "Waktu eksekusi wajib diisi.";
    if (!closingReason.trim()) fieldErrors.closingReason = "Alasan penutupan wajib diisi.";

    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) return;

    setSubmitState("pending");

    try {
      const data: FullExitRequest = {
        session_id: sessionId,
        idempotency_key: generateIdempotencyKey(),
        exit_price: toApiNumber(exitPrice),
        exit_quantity: String(rq),
        executed_at: executedAt,
        closing_reason: closingReason,
        fees: fees.trim() ? toApiNumber(fees) : null,
        note: note.trim() || null,
      };
      await fullExit(data);
      if (cancelledRef.current) return;
      onSuccess();
      onClose();
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      if (e instanceof AuthenticationError) setSubmitState({ type: "error", message: "Silakan masuk terlebih dahulu." });
      else if (e instanceof ApiError) setSubmitState({ type: "error", message: e.message });
      else setSubmitState({ type: "error", message: "Gagal menutup posisi. Silakan coba lagi." });
    }
  }, [exitPrice, executedAt, closingReason, fees, note, rq, sessionId, onSuccess, onClose]);

  const submitError = typeof submitState === "object" && "type" in submitState ? submitState.message : null;

  return (
    <><div className="mb-4 flex items-center justify-between">
      <h2 className="text-lg font-semibold text-zinc-800">Tutup Posisi</h2>
      <button type="button" onClick={onClose} disabled={submitState === "pending"} className="text-zinc-400 hover:text-zinc-600 focus:outline-none">
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div className="mb-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm">
      <p className="font-medium text-amber-800">Konfirmasi Penutupan Posisi</p>
      <p className="mt-1 text-amber-700">
        Seluruh posisi ({rq} unit) akan ditutup. Tindakan ini tidak dapat dibatalkan.
      </p>
    </div>

    <div className="mb-4 rounded border border-zinc-200 bg-zinc-50 p-2 text-xs text-zinc-600">
      {activeStopLoss && <p>Stop Loss Aktif: {currency(parseFloat(activeStopLoss))}</p>}
      {activeTarget && <p>Target Aktif: {currency(parseFloat(activeTarget))}</p>}
    </div>

    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-zinc-700">
          Harga Exit <span className="text-red-500">*</span>
        </label>
        <input type="text" inputMode="decimal" value={exitPrice}
          onChange={(e) => { setExitPrice(e.target.value); setErrors((p) => ({ ...p, exitPrice: undefined })); }}
          className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.exitPrice ? "border-red-300" : "border-zinc-300"}`}
          placeholder="2900" />
        {errors.exitPrice && <p className="mt-1 text-xs text-red-600">{errors.exitPrice}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-zinc-700">
          Waktu Eksekusi <span className="text-red-500">*</span>
        </label>
        <input type="datetime-local" value={executedAt}
          onChange={(e) => { setExecutedAt(e.target.value); setErrors((p) => ({ ...p, executedAt: undefined })); }}
          className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.executedAt ? "border-red-300" : "border-zinc-300"}`} />
        {errors.executedAt && <p className="mt-1 text-xs text-red-600">{errors.executedAt}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-zinc-700">
          Alasan Penutupan <span className="text-red-500">*</span>
        </label>
        <select value={closingReason}
          onChange={(e) => { setClosingReason(e.target.value); setErrors((p) => ({ ...p, closingReason: undefined })); }}
          className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.closingReason ? "border-red-300" : "border-zinc-300"}`}>
          <option value="">Pilih alasan…</option>
          {Object.entries(CLOSING_REASON_LABEL).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        {errors.closingReason && <p className="mt-1 text-xs text-red-600">{errors.closingReason}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-zinc-700">Biaya (opsional)</label>
        <input type="text" inputMode="decimal" value={fees}
          onChange={(e) => setFees(e.target.value)}
          className="mt-1 w-full rounded border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="0" />
      </div>

      {exitPrice.trim() && epCanonical > 0 && rq > 0 && (() => {
        const ep = parseNum(exitPrice);
        if (ep <= 0) return null;
        const grossProceeds = ep * rq;
        const grossPL = (ep - epCanonical) * rq;
        const feeVal = parseNum(fees);
        const netPL = grossPL - feeVal;
        const retPct = ((ep - epCanonical) / epCanonical) * 100;
        return (
          <div className="rounded border border-blue-100 bg-blue-50 p-3 text-sm">
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-blue-700">
              Estimasi Hasil
            </p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-blue-900">
              <span>Perkiraan Penerimaan:</span><span className="text-right font-medium">{formatSigned(grossProceeds)}</span>
              <span>Estimasi Gross P&amp;L:</span><span className={`text-right font-medium ${grossPL >= 0 ? "text-green-700" : "text-red-700"}`}>{formatSigned(grossPL)}</span>
              <span>Biaya:</span><span className="text-right font-medium">{feeVal > 0 ? formatSigned(feeVal) : "0"}</span>
              <span>Estimasi Net P&amp;L:</span><span className={`text-right font-medium ${netPL >= 0 ? "text-green-700" : "text-red-700"}`}>{formatSigned(netPL)}</span>
              <span>Estimasi Return:</span><span className={`text-right font-medium ${retPct >= 0 ? "text-green-700" : "text-red-700"}`}>{retPct.toFixed(2)}%</span>
            </div>
            <p className="mt-1.5 text-xs italic text-blue-500">
              Estimasi berdasarkan data tersedia. Hasil final dari backend bersifat authoritative.
            </p>
          </div>
        );
      })()}

      <div>
        <label className="block text-sm font-medium text-zinc-700">Catatan</label>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2}
          className="mt-1 w-full rounded border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Catatan opsional" />
      </div>

      {submitError && <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">{submitError}</div>}

      <div className="flex justify-end gap-3">
        <button type="button" onClick={onClose} disabled={submitState === "pending"}
          className="rounded border border-zinc-300 px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-50 focus:outline-none focus:ring-2 focus:ring-zinc-500 disabled:opacity-50">Batal</button>
        <button type="submit" disabled={submitState === "pending"}
          className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50">
          {submitState === "pending" ? "Memproses…" : "Konfirmasi Tutup Posisi"}
        </button>
      </div>
    </form>
    </>
  );
}
