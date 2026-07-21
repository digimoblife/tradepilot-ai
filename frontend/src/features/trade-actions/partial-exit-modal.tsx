"use client";

import { useState, useCallback, useRef } from "react";
import { partialExit } from "@/lib/api/trade-actions";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { PartialExitRequest } from "@/types/trade-action";

function generateIdempotencyKey(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function toApiNumber(value: string): string {
  return value.replace(/[^0-9.,-]/g, "").replace(/,/g, ".");
}

function nowISO(): string {
  return new Date().toISOString();
}

interface FormErrors {
  exitPrice?: string;
  exitQuantity?: string;
  executedAt?: string;
  reason?: string;
}

interface Props {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  remainingQuantity: string | null;
}

export function PartialExitModal({ sessionId, isOpen, onClose, onSuccess, remainingQuantity }: Props) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <PartialExitForm key={sessionId} sessionId={sessionId} onClose={onClose} onSuccess={onSuccess} remainingQuantity={remainingQuantity} />
      </div>
    </div>
  );
}

function PartialExitForm({ sessionId, onClose, onSuccess, remainingQuantity }: { sessionId: string; onClose: () => void; onSuccess: () => void; remainingQuantity: string | null }) {
  const rq = remainingQuantity ? parseFloat(remainingQuantity) : 0;

  const [exitPrice, setExitPrice] = useState("");
  const [exitQuantity, setExitQuantity] = useState("");
  const [executedAt, setExecutedAt] = useState(nowISO().slice(0, 16));
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitState, setSubmitState] = useState<"idle" | "pending" | { type: "error"; message: string }>("idle");
  const cancelledRef = useRef(false);

  const eq = exitQuantity.trim() ? parseFloat(toApiNumber(exitQuantity)) : 0;
  const remainingAfter = rq - eq;
  const showRemainingPreview = exitQuantity.trim() && !isNaN(eq) && eq > 0 && rq > 0;

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    const fieldErrors: FormErrors = {};
    const ep = parseFloat(toApiNumber(exitPrice));
    const eqv = parseFloat(toApiNumber(exitQuantity));
    if (!exitPrice.trim() || isNaN(ep) || ep <= 0) fieldErrors.exitPrice = "Harga exit harus lebih besar dari 0.";
    if (!exitQuantity.trim() || isNaN(eqv) || eqv <= 0) fieldErrors.exitQuantity = "Quantity harus lebih besar dari 0.";
    else if (rq > 0 && eqv >= rq) fieldErrors.exitQuantity = `Quantity harus kurang dari sisa posisi (${rq}). Gunakan Tutup Posisi untuk keluar penuh.`;
    if (!executedAt.trim()) fieldErrors.executedAt = "Waktu eksekusi wajib diisi.";
    if (!reason.trim()) fieldErrors.reason = "Alasan partial exit wajib diisi.";

    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) return;

    setSubmitState("pending");

    try {
      const data: PartialExitRequest = {
        session_id: sessionId,
        idempotency_key: generateIdempotencyKey(),
        exit_price: toApiNumber(exitPrice),
        exit_quantity: toApiNumber(exitQuantity),
        executed_at: executedAt,
        reason: reason.trim(),
        note: note.trim() || null,
      };
      await partialExit(data);
      if (cancelledRef.current) return;
      onSuccess();
      onClose();
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      if (e instanceof AuthenticationError) setSubmitState({ type: "error", message: "Silakan masuk terlebih dahulu." });
      else if (e instanceof ApiError) setSubmitState({ type: "error", message: e.message });
      else setSubmitState({ type: "error", message: "Gagal melakukan partial exit. Silakan coba lagi." });
    }
  }, [exitPrice, exitQuantity, executedAt, reason, note, rq, sessionId, onSuccess, onClose]);

  const submitError = typeof submitState === "object" && "type" in submitState ? submitState.message : null;

  return (
    <><div className="mb-4 flex items-center justify-between">
      <h2 className="text-lg font-semibold text-zinc-800">Partial Exit</h2>
      <button type="button" onClick={onClose} disabled={submitState === "pending"} className="text-zinc-400 hover:text-zinc-600 focus:outline-none">
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div className="mb-4 rounded border border-zinc-200 bg-zinc-50 p-2 text-sm">
      <span className="text-zinc-600">Sisa Posisi Saat Ini: </span>
      <span className="font-medium text-zinc-800">{rq}</span>
      {showRemainingPreview && (
        <span className="ml-2 text-zinc-500">
          → Sisa setelah exit: <span className="font-medium text-zinc-700">{remainingAfter > 0 ? remainingAfter : "—"}</span>
        </span>
      )}
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
          Quantity Dijual <span className="text-red-500">*</span>
        </label>
        <input type="text" inputMode="decimal" value={exitQuantity}
          onChange={(e) => { setExitQuantity(e.target.value); setErrors((p) => ({ ...p, exitQuantity: undefined })); }}
          className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.exitQuantity ? "border-red-300" : "border-zinc-300"}`}
          placeholder="30" />
        {errors.exitQuantity && <p className="mt-1 text-xs text-red-600">{errors.exitQuantity}</p>}
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
          Alasan <span className="text-red-500">*</span>
        </label>
        <select value={reason}
          onChange={(e) => { setReason(e.target.value); setErrors((p) => ({ ...p, reason: undefined })); }}
          className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.reason ? "border-red-300" : "border-zinc-300"}`}>
          <option value="">Pilih alasan…</option>
          <option value="PARTIAL_TAKE_PROFIT">Partial Take Profit</option>
          <option value="RISK_REDUCTION">Pengurangan Risiko</option>
          <option value="RESISTANCE_REACHED">Resistance Tercapai</option>
          <option value="MOMENTUM_WEAKENING">Momentum Melemah</option>
          <option value="USER_DECISION">Keputusan User</option>
          <option value="OTHER">Lainnya</option>
        </select>
        {errors.reason && <p className="mt-1 text-xs text-red-600">{errors.reason}</p>}
      </div>

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
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50">
          {submitState === "pending" ? "Memproses…" : "Konfirmasi Partial Exit"}
        </button>
      </div>
    </form>
    </>
  );
}
