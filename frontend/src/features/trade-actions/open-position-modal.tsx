"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { openPosition } from "@/lib/api/trade-actions";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateIdempotencyKey(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function toApiNumber(value: string): string {
  const cleaned = value.replace(/[^0-9.,-]/g, "").replace(/,/g, ".");
  return cleaned;
}

function nowISO(): string {
  return new Date().toISOString();
}

// ---------------------------------------------------------------------------
// Proposal loader
// ---------------------------------------------------------------------------

interface ProposalData {
  entryPrice: string;
  stopLoss: string;
  target: string;
}

async function loadProposal(sessionId: string, signal: AbortSignal): Promise<ProposalData | null> {
  try {
    const list = await listAnalyses(sessionId, {
      analysis_type: "WATCHING_UPDATE",
    });
    if (signal.aborted) return null;

    const accepted = list.analyses
      .filter((a) => a.acceptance_status === "ACCEPTED")
      .sort(
        (a, b) =>
          new Date(b.accepted_at ?? b.created_at).getTime() -
          new Date(a.accepted_at ?? a.created_at).getTime(),
      );

    if (accepted.length === 0) return null;

    const detail = await getAnalysis(accepted[0].id);
    if (signal.aborted || !detail.payload) return null;

    const p = detail.payload as Record<string, unknown>;
    const ea = p.entry_assessment as Record<string, unknown> | undefined;
    const pl = p.price_levels as Record<string, unknown> | undefined;
    const proposedStop = pl?.proposed_stop_loss as Record<string, unknown> | undefined;
    const proposedTarget = pl?.proposed_target as Record<string, unknown> | undefined;

    const entryPrice = String(
      (ea?.proposed_entry_price as number) ??
        (ea?.reference_entry_price as number) ??
        (ea?.current_price as number) ??
        "",
    );

    return {
      entryPrice,
      stopLoss: proposedStop?.price != null ? String(proposedStop.price) : "",
      target: proposedTarget?.price != null ? String(proposedTarget.price) : "",
    };
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

interface FormErrors {
  entryPrice?: string;
  quantity?: string;
  executedAt?: string;
  stopLoss?: string;
  target?: string;
}

function validateForm(
  entryPrice: string,
  quantity: string,
  executedAt: string,
  stopLoss: string,
  target: string,
): FormErrors {
  const errors: FormErrors = {};
  const ep = parseFloat(toApiNumber(entryPrice));
  const qty = parseFloat(toApiNumber(quantity));
  const sl = stopLoss ? parseFloat(toApiNumber(stopLoss)) : NaN;
  const tg = target ? parseFloat(toApiNumber(target)) : NaN;

  if (!entryPrice.trim() || isNaN(ep) || ep <= 0) {
    errors.entryPrice = "Harga entry harus lebih besar dari 0.";
  }
  if (!quantity.trim() || isNaN(qty) || qty <= 0) {
    errors.quantity = "Quantity harus lebih besar dari 0.";
  }
  if (!executedAt.trim()) {
    errors.executedAt = "Waktu eksekusi wajib diisi.";
  }
  if (stopLoss.trim() && (isNaN(sl) || sl <= 0)) {
    errors.stopLoss = "Stop loss harus lebih besar dari 0.";
  }
  if (target.trim() && (isNaN(tg) || tg <= 0)) {
    errors.target = "Target harus lebih besar dari 0.";
  }

  return errors;
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

interface Props {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function OpenPositionModal({ sessionId, isOpen, onClose, onSuccess }: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <OpenPositionForm key={sessionId} sessionId={sessionId} onClose={onClose} onSuccess={onSuccess} />
      </div>
    </div>
  );
}

// Inner form component — remounts on each open via key to get fresh state
function OpenPositionForm({ sessionId, onClose, onSuccess }: { sessionId: string; onClose: () => void; onSuccess: () => void }) {
  const [proposalState, setProposalState] = useState<{ loading: boolean; loaded: boolean; data: ProposalData | null }>({ loading: true, loaded: false, data: null });
  const [entryPrice, setEntryPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [executedAt, setExecutedAt] = useState(nowISO().slice(0, 16));
  const [stopLoss, setStopLoss] = useState("");
  const [target, setTarget] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitState, setSubmitState] = useState<"idle" | "pending" | "success" | { type: "error"; message: string }>("idle");
  const cancelledRef = useRef(false);

  // Load proposal once on mount
  useEffect(() => {
    cancelledRef.current = false;
    const ctrl = new AbortController();

    loadProposal(sessionId, ctrl.signal)
      .then((data) => {
        if (ctrl.signal.aborted) return;
        setProposalState({ loading: false, loaded: true, data });
        if (data) {
          setEntryPrice(data.entryPrice);
          setStopLoss(data.stopLoss);
          setTarget(data.target);
        }
      })
      .catch(() => {
        if (!ctrl.signal.aborted) {
          setProposalState({ loading: false, loaded: true, data: null });
        }
      });

    return () => {
      ctrl.abort();
      cancelledRef.current = true;
    };
  }, [sessionId]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      const validationErrors = validateForm(entryPrice, quantity, executedAt, stopLoss, target);
      setErrors(validationErrors);
      if (Object.keys(validationErrors).length > 0) return;

      setSubmitState("pending");

      try {
        await openPosition({
          session_id: sessionId,
          idempotency_key: generateIdempotencyKey(),
          entry_price: toApiNumber(entryPrice),
          quantity: toApiNumber(quantity),
          executed_at: executedAt,
          stop_loss: stopLoss.trim() ? toApiNumber(stopLoss) : null,
          target: target.trim() ? toApiNumber(target) : null,
          note: note.trim() || null,
        });

        if (cancelledRef.current) return;
        onSuccess();
        onClose();
      } catch (e: unknown) {
        if (cancelledRef.current) return;
        if (e instanceof AuthenticationError) {
          setSubmitState({ type: "error", message: "Silakan masuk terlebih dahulu." });
        } else if (e instanceof ApiError) {
          setSubmitState({ type: "error", message: e.message });
        } else {
          setSubmitState({ type: "error", message: "Gagal membuka posisi. Silakan coba lagi." });
        }
      }
    },
    [sessionId, entryPrice, quantity, executedAt, stopLoss, target, note, onSuccess, onClose],
  );

  const submitError = submitState && typeof submitState === "object" && "type" in submitState && submitState.type === "error"
    ? submitState.message
    : null;

  return (
    <><div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-800">Buka Posisi</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={submitState === "pending"}
            className="text-zinc-400 hover:text-zinc-600 focus:outline-none"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {proposalState.loading && (
          <p className="mb-4 text-sm text-zinc-400">Memuat usulan AI…</p>
        )}

        {proposalState.loaded && proposalState.data && (
          <div className="mb-4 rounded border border-blue-100 bg-blue-50 p-2 text-xs text-blue-700">
            Nilai di bawah diisi berdasarkan usulan AI. Anda dapat mengubahnya sebelum mengonfirmasi.
          </div>
        )}

        {proposalState.loaded && !proposalState.data && (
          <div className="mb-4 rounded border border-zinc-200 bg-zinc-50 p-2 text-xs text-zinc-500">
            Tidak ada usulan AI tersedia. Isi nilai secara manual.
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-700">
              Harga Entry <span className="text-red-500">*</span>
              {proposalState.data?.entryPrice && <span className="ml-1 text-xs text-blue-500">(Usulan AI: {proposalState.data.entryPrice})</span>}
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={entryPrice}
              onChange={(e) => setEntryPrice(e.target.value)}
              className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.entryPrice ? "border-red-300" : "border-zinc-300"}`}
              placeholder="2800"
            />
            {errors.entryPrice && <p className="mt-1 text-xs text-red-600">{errors.entryPrice}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-700">
              Quantity <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.quantity ? "border-red-300" : "border-zinc-300"}`}
              placeholder="100"
            />
            {errors.quantity && <p className="mt-1 text-xs text-red-600">{errors.quantity}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-700">
              Waktu Eksekusi <span className="text-red-500">*</span>
            </label>
            <input
              type="datetime-local"
              value={executedAt}
              onChange={(e) => setExecutedAt(e.target.value)}
              className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.executedAt ? "border-red-300" : "border-zinc-300"}`}
            />
            {errors.executedAt && <p className="mt-1 text-xs text-red-600">{errors.executedAt}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-700">
              Stop Loss
              {proposalState.data?.stopLoss && <span className="ml-1 text-xs text-blue-500">(Usulan AI: {proposalState.data.stopLoss})</span>}
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
              className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.stopLoss ? "border-red-300" : "border-zinc-300"}`}
              placeholder="2700"
            />
            {errors.stopLoss && <p className="mt-1 text-xs text-red-600">{errors.stopLoss}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-700">
              Target
              {proposalState.data?.target && <span className="ml-1 text-xs text-blue-500">(Usulan AI: {proposalState.data.target})</span>}
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.target ? "border-red-300" : "border-zinc-300"}`}
              placeholder="2900"
            />
            {errors.target && <p className="mt-1 text-xs text-red-600">{errors.target}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-700">Catatan</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Catatan opsional"
            />
          </div>

          {submitError && (
            <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">
              {submitError}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={submitState === "pending"}
              className="rounded border border-zinc-300 px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-50 focus:outline-none focus:ring-2 focus:ring-zinc-500 disabled:opacity-50"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={submitState === "pending"}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {submitState === "pending" ? "Memproses…" : "Konfirmasi Buka Posisi"}
            </button>
          </div>
        </form>
      </>
    );
  }
