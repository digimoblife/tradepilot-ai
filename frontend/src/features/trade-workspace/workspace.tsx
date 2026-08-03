"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  buyDecision,
  getAvailableActions,
  getSessionDetail,
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
  SessionStatus,
  SkipReason,
  TradeSession,
  SessionDetailAggregate,
} from "./types";
import { InitialAnalysisResultView } from "./result";
import { WaitUpdatePanel } from "./wait-update";
import { PositionUpdatePanel } from "./position-update";
import { SessionTimeline } from "./timeline";
import { InitialEvidencePanel } from "./components/initial-evidence-panel";
import { AnalysisRequestFeedback } from "./components/analysis-request-feedback";
import { DecisionPanel } from "./components/decision-panel";
import type { BuyFormState } from "./components/buy-decision-form";

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

const statusLabels: Record<SessionStatus, string> = {
  DRAFT: "Draft", ANALYZING: "Menganalisis", ANALYZED: "Dianalisis", WAITING: "Menunggu",
  OPEN_POSITION: "Posisi Terbuka", CLOSED: "Ditutup", CLOSED_SKIPPED: "Ditutup (Skip)",
};

const statusToneClasses: Record<SessionStatus, string> = {
  DRAFT: "border-[var(--color-border-default)] bg-[var(--color-surface-muted)] text-[var(--color-text-strong)]",
  ANALYZING: "border-[var(--color-status-processing)] bg-[var(--color-status-processing-subtle)] text-[var(--color-text-strong)]",
  ANALYZED: "border-[var(--color-status-information)] bg-[var(--color-status-information-subtle)] text-[var(--color-text-strong)]",
  WAITING: "border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)] text-[var(--color-text-strong)]",
  OPEN_POSITION: "border-[var(--color-status-information)] bg-[var(--color-status-information-subtle)] text-[var(--color-text-strong)]",
  CLOSED: "border-[var(--color-border-default)] bg-[var(--color-surface-muted)] text-[var(--color-text-strong)]",
  CLOSED_SKIPPED: "border-[var(--color-border-default)] bg-[var(--color-surface-muted)] text-[var(--color-text-strong)]",
};

function formatTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function latestDecision(detail: SessionDetailAggregate): string {
  const latest = [...detail.decisions].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()).at(-1);
  return latest?.decision ?? "Belum ada keputusan";
}

export function SessionWorkspace({
  sessionId,
  knownEvidence,
  onEvidence,
  onSessionStatusChange,
}: {
  sessionId: string;
  knownEvidence: EvidenceFile[];
  onEvidence: (files: EvidenceFile[]) => void;
  onSessionStatusChange?: (sessionId: string, status: SessionStatus) => void;
}) {
  const [session, setSession] = useState<TradeSession | null>(null);
  const [aggregate, setAggregate] = useState<SessionDetailAggregate | null>(null);
  const [aggregateError, setAggregateError] = useState<string | null>(null);
  const [aggregateLoading, setAggregateLoading] = useState(true);
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
    const aggregatePromise = typeof getSessionDetail === "function"
      ? getSessionDetail(sessionId)
      : Promise.resolve(null);
    const [nextSession, nextAvailability, nextAggregate] = await Promise.all([
      getSession(sessionId),
      getAvailableActions(sessionId),
      aggregatePromise,
    ]);
    setSession(nextSession);
    setAvailability(nextAvailability);
    if (nextAggregate) setAggregate(nextAggregate);
    setAggregateLoading(false);
    setAggregateError(null);
    onSessionStatusChange?.(sessionId, nextSession.status);
    if (nextSession.status !== "WAITING" && nextSession.status !== "ANALYZING") {
      setWaitPanelActive(false);
    }
  }, [sessionId, onSessionStatusChange]);

  const handleWaitProcessing = useCallback(() => {
    setWaitPanelActive(true);
    setSession((current) => (current ? { ...current, status: "ANALYZING" } : current));
    setAvailability((current) =>
      current ? { ...current, session_status: "ANALYZING", available_actions: [] } : current
    );
  }, []);

  useEffect(() => {
    let cancelled = false;
    setAggregate(null);
    setAggregateError(null);
    setAggregateLoading(true);
    if (typeof getSessionDetail === "function") {
      getSessionDetail(sessionId)
        .then((next) => { if (!cancelled) { setAggregate(next); setAggregateLoading(false); } })
        .catch(() => { if (!cancelled) { setAggregateError("Ringkasan sesi tidak dapat dimuat."); setAggregateLoading(false); } });
    }
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
          onSessionStatusChange?.(sessionId, next.session_status);
          if (["COMPLETED", "FAILED"].includes(next.request_status)) {
            refreshDecisionWorkspace().catch(() => {});
          } else {
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
  }, [requestStatus, sessionStatus, sessionId, refreshDecisionWorkspace]);

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
      onSessionStatusChange?.(sessionId, response.session_status);
      if (response.request_status === "COMPLETED") {
        const fullAnalysis = await readInitialAnalysis(sessionId).catch(() => null);
        if (fullAnalysis) {
          setAnalysis(fullAnalysis);
        }
        await refreshDecisionWorkspace().catch(() => {});
        return;
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

  const headerSession = aggregate?.session;
  const handleBuyChange = (field: keyof BuyFormState, value: string) => {
    setBuyForm((current) => ({ ...current, [field]: value }));
  };
  return <section className="min-w-0 space-y-[var(--space-section)]">
    <header aria-label="Ringkasan sesi" className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-strong)] bg-[var(--color-surface-factual)] p-[var(--space-card)] shadow-[var(--elevation-low)]">
      {!headerSession ? <p role={aggregateError ? "alert" : undefined} aria-live={aggregateError ? undefined : "polite"} className={aggregateError ? "text-red-700" : "text-zinc-500"}>{aggregateError ?? "Memuat ringkasan sesi…"}</p> : <>
        <div className="flex min-w-0 flex-col gap-[var(--space-4)] sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><p className="break-words text-[var(--text-size-ticker)] font-bold leading-[var(--text-line-compact)] tracking-[0.04em] text-[var(--color-text-strong)]">{headerSession.ticker}</p><h2 className="mt-[var(--space-1)] break-words text-[var(--text-size-section-title)] font-semibold leading-[var(--text-line-heading)] text-[var(--color-text-default)]">{headerSession.company_name}</h2></div><span className={`w-fit shrink-0 rounded-[var(--radius-compact)] border px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-size-status)] font-semibold leading-[var(--text-line-compact)] ${statusToneClasses[headerSession.status]}`}>{statusLabels[headerSession.status]}</span></div>
        <dl className="mt-[var(--space-6)] grid min-w-0 grid-cols-1 gap-x-[var(--space-6)] gap-y-[var(--space-4)] text-[var(--text-size-compact-body)] sm:grid-cols-2"><div className="min-w-0"><dt className="text-[var(--text-size-label)] font-medium text-[var(--color-text-muted)]">Status</dt><dd className="mt-[var(--space-1)] break-words font-semibold text-[var(--color-text-strong)]">{statusLabels[headerSession.status]}</dd></div><div className="min-w-0"><dt className="text-[var(--text-size-label)] font-medium text-[var(--color-text-muted)]">Keputusan Aktif</dt><dd className="mt-[var(--space-1)] break-words font-semibold text-[var(--color-text-strong)]">{latestDecision(aggregate)}</dd></div><div className="min-w-0"><dt className="text-[var(--text-size-label)] font-medium text-[var(--color-text-muted)]">Dibuat</dt><dd className="mt-[var(--space-1)] break-words text-[var(--color-text-default)]">{formatTime(headerSession.created_at)}</dd></div><div className="min-w-0"><dt className="text-[var(--text-size-label)] font-medium text-[var(--color-text-muted)]">Pembaruan Terakhir</dt><dd className="mt-[var(--space-1)] break-words text-[var(--color-text-default)]">{formatTime(headerSession.updated_at)}</dd></div><div className="min-w-0"><dt className="text-[var(--text-size-label)] font-medium text-[var(--color-text-muted)]">Ditutup</dt><dd className="mt-[var(--space-1)] break-words text-[var(--color-text-default)]">{formatTime(headerSession.closed_at)}</dd></div>{aggregate.position && <div className="min-w-0"><dt className="text-[var(--text-size-label)] font-medium text-[var(--color-text-muted)]">Status posisi</dt><dd className="mt-[var(--space-1)] break-words font-semibold text-[var(--color-text-strong)]">{String(aggregate.position.status ?? "—")}</dd></div>}</dl>
        {headerSession.initial_note && <section aria-label="Catatan" className="mt-[var(--space-6)] rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-elevated-background)] px-[var(--space-4)] py-[var(--space-3)]"><p className="whitespace-pre-wrap break-words text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{headerSession.initial_note}</p></section>}
      </>}
    </header>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
    <div className="space-y-[var(--space-section)]">
    {showDecisionPanel && <DecisionPanel actions={actions} decisionSubmitting={decisionSubmitting} decisionError={decisionError} decisionSuccess={decisionSuccess} buyForm={buyForm} skipReasons={skipReasons} skipReason={skipReason} skipNote={skipNote} onBuyChange={handleBuyChange} onBuySubmit={submitBuy} onWait={submitWait} onSkipReasonChange={setSkipReason} onSkipNoteChange={setSkipNote} onSkipSubmit={submitSkip} />}
    {!showDecisionPanel && decisionError && <p role="alert" className="break-words rounded-[var(--radius-compact)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-[var(--space-3)] text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{decisionError}</p>}
    {!showDecisionPanel && decisionSuccess && <p role="status" aria-live="polite" className="break-words rounded-[var(--radius-compact)] border border-[var(--color-status-success)] bg-[var(--color-surface-feedback)] p-[var(--space-3)] text-[var(--text-size-compact-body)] leading-[var(--text-line-body)] text-[var(--color-text-default)]">{decisionSuccess}</p>}
    {(waitPanelActive || session.status === "WAITING") && <WaitUpdatePanel key={`${sessionId}-${waitCycle}`} sessionId={sessionId} sessionStatus={session.status} onProcessing={handleWaitProcessing} onFinished={refreshDecisionWorkspace} />}
    {(session.status === "OPEN_POSITION" || session.status === "CLOSED") && <PositionUpdatePanel sessionId={sessionId} sessionStatus={session.status} onClosed={refreshDecisionWorkspace} initialPosition={buyResult ? { id: buyResult.position_id, session_id: sessionId, status: buyResult.position_status, entry_price: buyResult.entry_price, entry_timestamp: buyResult.entry_timestamp, quantity: buyResult.quantity, stop_loss: buyResult.stop_loss, target_price: buyResult.target_price, note: buyResult.note, created_at: buyResult.decision_at } : null} />}
    {!analysis && session.status === "DRAFT" && <InitialEvidencePanel files={files} knownEvidence={knownEvidence} busy={busy} onFileSelected={(key, file) => setFiles((current) => ({ ...current, [key]: file }))} onUpload={upload} onRequestAnalysis={submitAnalysis} />}
    <AnalysisRequestFeedback analysis={analysis} complete={complete} failed={failed} busy={busy} onRetry={retry} />
    </div>
    {completedResult && <div className="max-w-[var(--layout-text-readable)]"><InitialAnalysisResultView result={completedResult} /></div>}
    <div>
      <SessionTimeline aggregate={aggregate} loading={aggregateLoading} error={aggregateError} />
    </div>
  </section>;
}
