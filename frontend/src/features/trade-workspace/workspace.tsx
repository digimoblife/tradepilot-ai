"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  buyDecision,
  getAvailableActions,
  getSession,
  readInitialAnalysis,
  readInitialEvidence,
  retryInitialAnalysis,
  skipDecision,
  submitInitialAnalysis,
  uploadInitialEvidence,
  waitDecision,
} from "./api";
import type {
  BuyDecisionResult,
  DecisionAvailability,
  EvidenceFile,
  InitialAnalysisRead,
  SkipReason,
  TradeSession,
} from "./types";
import { InitialAnalysisResultView } from "./result";
import { WaitUpdatePanel } from "./wait-update";
import { PositionUpdatePanel } from "./position-update";

const skipReasons: Array<{ value: SkipReason; label: string }> = [

  { value: "RISK_TOO_HIGH", label: "Risiko terlalu tinggi" },
  { value: "SETUP_NOT_ATTRACTIVE", label: "Setup tidak menarik" },
  { value: "ORDERBOOK_WEAK", label: "Order book lemah" },
  { value: "MARKET_CONDITION_UNFAVORABLE", label: "Kondisi pasar tidak mendukung" },
  { value: "WAITING_TOO_LONG", label: "Menunggu terlalu lama" },
  { value: "USER_DECISION", label: "Keputusan pengguna" },
  { value: "OTHER", label: "Lainnya" },
];

type DecisionForm = "WAIT" | "SKIP" | "BUY" | null;

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function SessionWorkspace({
  sessionId,
  knownEvidence,
  onEvidence,
}: {
  sessionId: string;
  knownEvidence: EvidenceFile[];
  onEvidence: (files: EvidenceFile[]) => void;
}) {
  const [session, setSession] = useState<TradeSession | null>(null);
  const [analysis, setAnalysis] = useState<InitialAnalysisRead | null>(null);
  const [availability, setAvailability] = useState<DecisionAvailability | null>(null);
  const [files, setFiles] = useState<Record<string, File>>({});
  const [busy, setBusy] = useState(false);
  const [decisionSubmitting, setDecisionSubmitting] = useState<DecisionForm>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [decisionSuccess, setDecisionSuccess] = useState<string | null>(null);
  const [buyResult, setBuyResult] = useState<BuyDecisionResult | null>(null);
  const [waitPanelActive, setWaitPanelActive] = useState(false);
  const [waitCycle, setWaitCycle] = useState(0);
  const [skipReason, setSkipReason] = useState<SkipReason | "">("");
  const [skipNote, setSkipNote] = useState("");
  const [buyForm, setBuyForm] = useState({
    entry_price: "",
    entry_timestamp: "",
    quantity: "",
    stop_loss: "",
    target_price: "",
    note: "",
  });
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);
  const onEvidenceRef = useRef(onEvidence);
  useEffect(() => {
    onEvidenceRef.current = onEvidence;
  });

  const refreshDecisionWorkspace = useCallback(async () => {
    const [nextSession, nextAvailability] = await Promise.all([
      getSession(sessionId),
      getAvailableActions(sessionId),
    ]);
    setSession(nextSession);
    setAvailability(nextAvailability);
    if (nextSession.status !== "WAITING" && nextSession.status !== "ANALYZING") {
      setWaitPanelActive(false);
    }
  }, [sessionId]);

  const handleWaitProcessing = useCallback(() => {
    setWaitPanelActive(true);
    setSession((current) => (current ? { ...current, status: "ANALYZING" } : current));
    setAvailability((current) =>
      current ? { ...current, session_status: "ANALYZING", available_actions: [] } : current
    );
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getSession(sessionId), getAvailableActions(sessionId)])
      .then(([nextSession, nextAvailability]) => {
        if (!cancelled) {
          setSession(nextSession);
          setAvailability(nextAvailability);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(errorText(reason, "Sesi tidak dapat dimuat."));
      });
    readInitialEvidence(sessionId)
      ?.then((evidenceRes) => {
        if (!cancelled && evidenceRes?.evidence?.length) {
          onEvidenceRef.current(evidenceRes.evidence);
        }
      })
      .catch(() => {
        // No initial evidence uploaded yet.
      });
    readInitialAnalysis(sessionId)
      ?.then((next) => {
        if (!cancelled) setAnalysis(next);
      })
      .catch(() => {
        // No initial analysis exists yet.
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const requestStatus = analysis?.request_status;
  const sessionStatus = session?.status;

  useEffect(() => {
    if (
      !requestStatus ||
      sessionStatus !== "ANALYZING" ||
      requestStatus === "COMPLETED" ||
      requestStatus === "FAILED"
    ) {
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      if (cancelled || inFlight.current) return;
      inFlight.current = true;
      try {
        const next = await readInitialAnalysis(sessionId);
        if (!cancelled) {
          setAnalysis(next);
          setSession((current) => (current ? { ...current, status: next.session_status } : current));
          if (!["COMPLETED", "FAILED"].includes(next.request_status)) {
            timer = setTimeout(poll, 5000);
          }
        }
      } catch {
        if (!cancelled) {
          timer = setTimeout(poll, 5000);
        }
      } finally {
        inFlight.current = false;
      }
    };
    timer = setTimeout(poll, 5000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [requestStatus, sessionStatus, sessionId]);

  async function upload(event: React.FormEvent) {
    event.preventDefault();
    if (!files.orderbook || !files.chart_3_month || !files.chart_6_month) {
      setError("Tiga file evidence wajib dipilih.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await uploadInitialEvidence(sessionId, files as {
        orderbook: File;
        chart_3_month: File;
        chart_6_month: File;
      });
      onEvidence(response.evidence);
    } catch (reason: unknown) {
      setError(errorText(reason, "Evidence tidak dapat diunggah."));
    } finally {
      setBusy(false);
    }
  }

  async function submitAnalysis() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await submitInitialAnalysis(sessionId);
      setSession((current) => (current ? { ...current, status: response.session_status } : current));
      if (response.request_status === "COMPLETED") {
        const fullAnalysis = await readInitialAnalysis(sessionId).catch(() => null);
        if (fullAnalysis) {
          setAnalysis(fullAnalysis);
          return;
        }
      }
      setAnalysis({
        ...response,
        processed_response: null,
        error_code: null,
        error_message: null,
        started_at: null,
        completed_at: null,
      });
    } catch (reason: unknown) {
      setError(errorText(reason, "Analisis tidak dapat diminta."));
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    setBusy(true);
    setError(null);
    try {
      const response = await retryInitialAnalysis(sessionId);
      setAnalysis({ ...response, processed_response: null, error_code: null, error_message: null, started_at: null, completed_at: null });
      setSession((current) => current ? { ...current, status: response.session_status } : current);
    } catch (reason: unknown) {
      setError(errorText(reason, "Analisis tidak dapat dicoba lagi."));
    } finally {
      setBusy(false);
    }
  }

  async function submitWait() {
    if (decisionSubmitting) return;
    setDecisionSubmitting("WAIT");
    setDecisionError(null);
    setDecisionSuccess(null);
    try {
      await waitDecision(sessionId);
      setWaitPanelActive(true);
      setWaitCycle((current) => current + 1);
      await refreshDecisionWorkspace();
      setDecisionSuccess("Keputusan WAIT tersimpan.");
    } catch (reason: unknown) {
      setDecisionError(errorText(reason, "Keputusan WAIT tidak dapat disimpan."));
    } finally {
      setDecisionSubmitting(null);
    }
  }

  async function submitSkip(event: React.FormEvent) {
    event.preventDefault();
    if (decisionSubmitting || !skipReason) {
      if (!skipReason) setDecisionError("Alasan SKIP wajib dipilih.");
      return;
    }
    setDecisionSubmitting("SKIP");
    setDecisionError(null);
    setDecisionSuccess(null);
    try {
      await skipDecision(sessionId, { reason: skipReason, note: skipNote || null });
      await refreshDecisionWorkspace();
      setDecisionSuccess("Sesi ditutup sebagai CLOSED_SKIPPED.");
    } catch (reason: unknown) {
      setDecisionError(errorText(reason, "Keputusan SKIP tidak dapat disimpan."));
    } finally {
      setDecisionSubmitting(null);
    }
  }

  async function submitBuy(event: React.FormEvent) {
    event.preventDefault();
    if (decisionSubmitting) return;
    const required = ["entry_price", "entry_timestamp", "quantity", "stop_loss", "target_price"] as const;
    if (required.some((field) => !buyForm[field].trim())) {
      setDecisionError("Semua fakta BUY wajib diisi.");
      return;
    }
    setDecisionSubmitting("BUY");
    setDecisionError(null);
    setDecisionSuccess(null);
    try {
      const result = await buyDecision(sessionId, {
        entry_price: buyForm.entry_price,
        entry_timestamp: buyForm.entry_timestamp,
        quantity: buyForm.quantity,
        stop_loss: buyForm.stop_loss,
        target_price: buyForm.target_price,
        note: buyForm.note || null,
      });
      setBuyResult(result);
      await refreshDecisionWorkspace();
      setDecisionSuccess("BUY tersimpan dan posisi OPEN dibuat.");
    } catch (reason: unknown) {
      setDecisionError(errorText(reason, "Keputusan BUY tidak dapat disimpan."));
    } finally {
      setDecisionSubmitting(null);
    }
  }

  if (!session) return <section className="rounded-xl border bg-white p-5">{error ? <p role="alert" className="text-red-700">{error}</p> : "Memuat sesi…"}</section>;
  const completedResult = analysis?.request_status === "COMPLETED" ? analysis.processed_response : null;
  const complete = completedResult !== null;
  const failed = analysis?.request_status === "FAILED" || (analysis?.request_status === "PENDING" && session.status === "DRAFT");
  const actions = availability?.available_actions ?? [];
  const showDecisionPanel = actions.some((action) => action === "BUY" || action === "WAIT" || action === "SKIP");

  return <section className="space-y-4">
    <header className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm text-zinc-500">{session.ticker}</p><h2 className="text-2xl font-bold">{session.company_name}</h2></div><span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-semibold">{session.status}</span></div>{session.note && <p className="mt-4 whitespace-pre-wrap text-sm text-zinc-600">{session.note}</p>}</header>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
    {decisionError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{decisionError}</p>}
    {decisionSuccess && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{decisionSuccess}</p>}
    {showDecisionPanel && <section aria-label="Keputusan sesi" className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <h3 className="font-semibold">Keputusan Anda</h3>
      <div className="mt-4 flex flex-wrap gap-2">
        {actions.includes("WAIT") && <button type="button" disabled={decisionSubmitting !== null} onClick={submitWait} className="rounded-lg border border-amber-300 px-4 py-2 text-sm font-medium text-amber-900 disabled:opacity-50">{decisionSubmitting === "WAIT" ? "Menyimpan…" : "WAIT"}</button>}
      </div>
      {actions.includes("SKIP") && <form onSubmit={submitSkip} className="mt-5 space-y-3 border-t border-zinc-100 pt-5"><h4 className="font-medium">Tutup tanpa posisi</h4><label className="block text-sm font-medium" htmlFor="skip-reason">Alasan SKIP<select id="skip-reason" required value={skipReason} onChange={(event) => setSkipReason(event.target.value as SkipReason | "")} className="mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2"><option value="">Pilih alasan</option>{skipReasons.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label><label className="block text-sm font-medium" htmlFor="skip-note">Catatan SKIP (opsional)<textarea id="skip-note" value={skipNote} onChange={(event) => setSkipNote(event.target.value)} className="mt-1 block min-h-20 w-full rounded-lg border border-zinc-300 px-3 py-2" /></label><button type="submit" disabled={decisionSubmitting !== null} className="rounded-lg bg-zinc-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{decisionSubmitting === "SKIP" ? "Menyimpan…" : "Konfirmasi SKIP"}</button></form>}
      {actions.includes("BUY") && <form onSubmit={submitBuy} className="mt-5 space-y-3 border-t border-zinc-100 pt-5"><h4 className="font-medium">Konfirmasi posisi BUY</h4><div className="grid gap-3 sm:grid-cols-2"><label className="block text-sm font-medium" htmlFor="buy-entry-price">Harga entry<input id="buy-entry-price" required inputMode="decimal" value={buyForm.entry_price} onChange={(event) => setBuyForm((current) => ({ ...current, entry_price: event.target.value }))} className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2" /></label><label className="block text-sm font-medium" htmlFor="buy-entry-timestamp">Waktu entry<input id="buy-entry-timestamp" required type="text" placeholder="2026-07-30T09:15:00Z" value={buyForm.entry_timestamp} onChange={(event) => setBuyForm((current) => ({ ...current, entry_timestamp: event.target.value }))} className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2" /></label><label className="block text-sm font-medium" htmlFor="buy-quantity">Kuantitas<input id="buy-quantity" required inputMode="decimal" value={buyForm.quantity} onChange={(event) => setBuyForm((current) => ({ ...current, quantity: event.target.value }))} className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2" /></label><label className="block text-sm font-medium" htmlFor="buy-stop-loss">Stop loss<input id="buy-stop-loss" required inputMode="decimal" value={buyForm.stop_loss} onChange={(event) => setBuyForm((current) => ({ ...current, stop_loss: event.target.value }))} className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2" /></label><label className="block text-sm font-medium" htmlFor="buy-target-price">Target price<input id="buy-target-price" required inputMode="decimal" value={buyForm.target_price} onChange={(event) => setBuyForm((current) => ({ ...current, target_price: event.target.value }))} className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2" /></label></div><label className="block text-sm font-medium" htmlFor="buy-note">Catatan BUY (opsional)<textarea id="buy-note" value={buyForm.note} onChange={(event) => setBuyForm((current) => ({ ...current, note: event.target.value }))} className="mt-1 block min-h-20 w-full rounded-lg border border-zinc-300 px-3 py-2" /></label><button type="submit" disabled={decisionSubmitting !== null} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{decisionSubmitting === "BUY" ? "Menyimpan…" : "Konfirmasi BUY"}</button></form>}
    </section>}
    {(waitPanelActive || session.status === "WAITING") && <WaitUpdatePanel key={`${sessionId}-${waitCycle}`} sessionId={sessionId} sessionStatus={session.status} onProcessing={handleWaitProcessing} onFinished={refreshDecisionWorkspace} />}
    {(session.status === "OPEN_POSITION" || session.status === "CLOSED") && <PositionUpdatePanel sessionId={sessionId} sessionStatus={session.status} initialPosition={buyResult ? { id: buyResult.position_id, session_id: sessionId, status: buyResult.position_status, entry_price: buyResult.entry_price, entry_timestamp: buyResult.entry_timestamp, quantity: buyResult.quantity, stop_loss: buyResult.stop_loss, target_price: buyResult.target_price, note: buyResult.note, created_at: buyResult.decision_at } : null} />}
    {!analysis && session.status === "DRAFT" && knownEvidence.length === 0 && <form onSubmit={upload} className="rounded-xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">Evidence Initial Analysis</h3><p className="mt-1 text-sm text-zinc-500">Unggah tepat tiga gambar: order book, grafik 3 bulan, dan grafik 6 bulan.</p><div className="mt-4 grid gap-3">{([['orderbook', 'Order Book'], ['chart_3_month', 'Grafik 3 Bulan'], ['chart_6_month', 'Grafik 6 Bulan']] as const).map(([key, label]) => <label key={key} className="text-sm font-medium">{label}<input type="file" accept="image/*" required onChange={(event) => { const file = event.target.files?.[0]; if (file) setFiles((current) => ({ ...current, [key]: file })); }} className="mt-1 block w-full text-sm" /></label>)}</div><button disabled={busy} className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? "Mengunggah…" : "Unggah Evidence"}</button></form>}
    {knownEvidence.length > 0 && session.status === "DRAFT" && !analysis && <section className="rounded-xl border bg-white p-5"><h3 className="font-semibold">Evidence siap</h3><p className="mt-1 text-sm text-zinc-600">{knownEvidence.length} file diterima.</p><button disabled={busy} onClick={submitAnalysis} className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? "Mengirim…" : "Minta Initial Analysis"}</button></section>}
    {analysis && !complete && !failed && <p className="rounded-xl border bg-white p-5 text-sm text-zinc-700">Analisis sedang diproses. Silakan tunggu.</p>}
    {failed && <section className="rounded-xl border border-red-200 bg-red-50 p-5"><h3 className="font-semibold text-red-900">Initial Analysis gagal diproses</h3><p className="mt-2 text-sm text-red-800">{analysis?.error_message || "Permintaan analisis belum masuk ke pemrosesan."}</p><button disabled={busy} onClick={retry} className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? "Mencoba…" : "Coba Lagi"}</button></section>}
    {completedResult && <InitialAnalysisResultView result={completedResult} />}
  </section>;
}
