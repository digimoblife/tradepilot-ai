"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { confirmTarget, changeTarget } from "@/lib/api/trade-actions";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { currency } from "@/features/analysis/helpers";

function generateIdempotencyKey(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function toApiNumber(value: string): string {
  return value.replace(/[^0-9.,-]/g, "").replace(/,/g, ".");
}

function nowISO(): string {
  return new Date().toISOString();
}

async function loadAIProposal(sessionId: string, signal: AbortSignal): Promise<string | null> {
  try {
    const list = await listAnalyses(sessionId, { analysis_type: "OPEN_POSITION_UPDATE" });
    if (signal.aborted) return null;
    const accepted = list.analyses
      .filter((a) => a.acceptance_status === "ACCEPTED")
      .sort((a, b) => new Date(b.accepted_at ?? b.created_at).getTime() - new Date(a.accepted_at ?? a.created_at).getTime());
    if (accepted.length === 0) return null;
    const detail = await getAnalysis(accepted[0].id);
    if (signal.aborted || !detail.payload) return null;
    const p = detail.payload as Record<string, unknown>;
    const ta = p.target_assessment as Record<string, unknown> | undefined;
    if (ta?.proposed_target != null) return String(ta.proposed_target);
    return null;
  } catch {
    return null;
  }
}

function validate(value: string): string | null {
  if (!value.trim()) return "Nilai target wajib diisi.";
  const num = parseFloat(toApiNumber(value));
  if (isNaN(num) || num <= 0) return "Target harus lebih besar dari 0.";
  return null;
}

interface Props {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  action: "CONFIRM_TARGET" | "CHANGE_TARGET";
  activeTarget: string | null;
}

export function TargetModal({ sessionId, isOpen, onClose, onSuccess, action, activeTarget }: Props) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <TargetForm key={sessionId + action} sessionId={sessionId} onClose={onClose} onSuccess={onSuccess} action={action} activeTarget={activeTarget} />
      </div>
    </div>
  );
}

function TargetForm({ sessionId, onClose, onSuccess, action, activeTarget }: { sessionId: string; onClose: () => void; onSuccess: () => void; action: "CONFIRM_TARGET" | "CHANGE_TARGET"; activeTarget: string | null }) {
  const [proposal, setProposal] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitState, setSubmitState] = useState<"idle" | "pending" | { type: "error"; message: string }>("idle");
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    const ctrl = new AbortController();
    loadAIProposal(sessionId, ctrl.signal).then((p) => {
      if (ctrl.signal.aborted) return;
      setProposal(p);
      setLoading(false);
      setValue(p ?? activeTarget ?? "");
    }).catch(() => {
      if (!ctrl.signal.aborted) {
        setLoading(false);
        setValue(activeTarget ?? "");
      }
    });
    return () => { ctrl.abort(); cancelledRef.current = true; };
  }, [sessionId, activeTarget]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate(value);
    if (err) { setError(err); return; }
    setError(null);
    setSubmitState("pending");
    try {
      const api = action === "CONFIRM_TARGET" ? confirmTarget : changeTarget;
      await api({ session_id: sessionId, idempotency_key: generateIdempotencyKey(), target: toApiNumber(value), confirmed_at: nowISO(), note: note.trim() || null });
      if (cancelledRef.current) return;
      onSuccess();
      onClose();
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      if (e instanceof AuthenticationError) setSubmitState({ type: "error", message: "Silakan masuk terlebih dahulu." });
      else if (e instanceof ApiError) setSubmitState({ type: "error", message: e.message });
      else setSubmitState({ type: "error", message: "Gagal memperbarui target. Silakan coba lagi." });
    }
  }, [value, note, sessionId, action, onSuccess, onClose]);

  const submitError = typeof submitState === "object" && "type" in submitState ? submitState.message : null;

  return (
    <><div className="mb-4 flex items-center justify-between">
      <h2 className="text-lg font-semibold text-zinc-800">
        {action === "CONFIRM_TARGET" ? "Konfirmasi Target" : "Ubah Target"}
      </h2>
      <button type="button" onClick={onClose} disabled={submitState === "pending"} className="text-zinc-400 hover:text-zinc-600 focus:outline-none">
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    {loading && <p className="mb-4 text-sm text-zinc-400">Memuat usulan AI…</p>}

    <div className="mb-4 space-y-1">
      <p className="text-sm text-zinc-500">
        <span className="font-medium text-zinc-700">Target Aktif: </span>
        {activeTarget ? currency(parseFloat(activeTarget)) : "—"}
      </p>
      {proposal != null && (
        <p className="text-sm text-blue-600">
          <span className="font-medium">Usulan AI: </span>
          {currency(parseFloat(proposal))}
        </p>
      )}
    </div>

    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-zinc-700">
          Nilai Target <span className="text-red-500">*</span>
        </label>
        <input
          type="text" inputMode="decimal"
          value={value}
          onChange={(e) => { setValue(e.target.value); setError(null); }}
          className={`mt-1 w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${error ? "border-red-300" : "border-zinc-300"}`}
          placeholder="3000"
        />
        {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
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
          {submitState === "pending" ? "Memproses…" : (action === "CONFIRM_TARGET" ? "Konfirmasi Target" : "Ubah Target")}
        </button>
      </div>
    </form>
    </>
  );
}
