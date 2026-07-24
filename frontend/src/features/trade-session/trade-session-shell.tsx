"use client";

import Link from "next/link";
import { useEffect, useState, useCallback, useRef } from "react";
import { archiveSession, getSession, markReady } from "@/lib/api/trade-sessions";
import { cancelSession } from "@/lib/api/trade-actions";
import { getTimeline } from "@/lib/api/timeline";
import { listAnalyses } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { TradeSessionDetail } from "@/types/trade-session";
import type { TimelineEvent } from "@/types/timeline";
import type { AnalysisSummary } from "@/types/analysis";
import { SessionHeader } from "./session-header";
import { LifecycleStatus } from "./lifecycle-status";
import { CanonicalPositionSummary } from "./canonical-position-summary";
import { EvidenceSection } from "@/features/evidence/evidence-section";
import { InitialAnalysisView } from "@/features/analysis/initial-analysis-view";
import { WatchingUpdateView } from "@/features/analysis/watching-update-view";
import { OpenPositionUpdateView } from "@/features/analysis/open-position-update-view";
import { PartialExitReviewView } from "@/features/analysis/partial-exit-review-view";
import { ClosingAnalysisView } from "@/features/analysis/closing-analysis-view";
import { AnalysisHistory } from "@/features/analysis/history/analysis-history";
import { OpenPositionModal } from "@/features/trade-actions/open-position-modal";
import { StopLossModal } from "@/features/trade-actions/stop-loss-modal";
import { TargetModal } from "@/features/trade-actions/target-modal";
import { PartialExitModal } from "@/features/trade-actions/partial-exit-modal";
import { FullExitModal } from "@/features/trade-actions/full-exit-modal";
import { RequestAnalysis } from "@/features/analysis/request-analysis";
import { JobStatus } from "@/features/jobs/job-status";
import { actionLabel } from "./helpers";

interface Props {
  sessionId: string;
}

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: TradeSessionDetail };

type LifecycleActionState =
  | { status: "idle"; error: string }
  | { status: "submitting"; action: string; error: string };

type AnalysisListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; analyses: AnalysisSummary[] };

const STORAGE_KEY = "tp-active-job";

interface ActiveJob {
  jobId: string;
  analysisType: string;
}

function loadActiveJob(): ActiveJob | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as ActiveJob;
  } catch { return null; }
}

function saveActiveJob(job: ActiveJob | null): void {
  if (typeof window === "undefined") return;
  try {
    if (job) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(job));
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch { /* ignore */ }
}

function makeIdempotencyKey(action: string, sessionId: string): string {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `ui_${action.toLowerCase()}_${sessionId}_${random}`;
}

function lifecycleErrorMessage(action: string, error: unknown): string {
  if (error instanceof AuthenticationError) {
    return "Silakan masuk terlebih dahulu untuk menjalankan tindakan ini.";
  }

  const prefix =
    action === "MARK_READY"
      ? "Belum bisa menandai sesi siap"
      : action === "CANCEL"
        ? "Belum bisa membatalkan sesi"
        : action === "ARCHIVE"
          ? "Belum bisa mengarsipkan sesi"
          : "Tindakan gagal";

  if (error instanceof ApiError) {
    return `${prefix}: ${error.message}`;
  }

  return `${prefix}. Silakan coba lagi.`;
}

export function TradeSessionShell({ sessionId }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [analysisListState, setAnalysisListState] = useState<AnalysisListState>({ status: "loading" });
  const [retryKey, setRetryKey] = useState(0);
  const [actionModal, setActionModal] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<ActiveJob | null>(null);
  const [lifecycleAction, setLifecycleAction] = useState<LifecycleActionState>({
    status: "idle",
    error: "",
  });
  const lifecycleSubmittingRef = useRef(false);

  // Restore active job on mount
  useEffect(() => {
    const restored = loadActiveJob();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (restored) setActiveJob(restored);
  }, []);

  // Persist active job changes
  useEffect(() => {
    saveActiveJob(activeJob);
  }, [activeJob]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState({ status: "loading" });
      try {
        const data = await getSession(sessionId);
        if (!cancelled) {
          setState({ status: "loaded", data });
        }
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof AuthenticationError) {
          setState({
            status: "error",
            message: "Silakan masuk terlebih dahulu untuk melihat sesi trading.",
          });
        } else if (e instanceof ApiError) {
          if (e.status === 404) {
            setState({ status: "error", message: "Sesi trading tidak ditemukan." });
          } else {
            setState({ status: "error", message: e.message });
          }
        } else {
          setState({ status: "error", message: "Terjadi kesalahan. Silakan coba lagi." });
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, [sessionId, retryKey]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setAnalysisListState({ status: "loading" });
      try {
        const result = await listAnalyses(sessionId);
        if (!cancelled) {
          setAnalysisListState({ status: "loaded", analyses: result.analyses });
        }
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof AuthenticationError) {
          setAnalysisListState({
            status: "error",
            message: "Silakan masuk terlebih dahulu untuk melihat analisis.",
          });
        } else if (e instanceof ApiError) {
          setAnalysisListState({ status: "error", message: e.message });
        } else {
          setAnalysisListState({
            status: "error",
            message: "Gagal memuat analisis. Silakan coba lagi.",
          });
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, [sessionId, retryKey]);

  const handleActionSuccess = useCallback(() => {
    setRetryKey((k) => k + 1);
  }, []);

  const handleLifecycleAction = useCallback(async (action: string) => {
    if (lifecycleSubmittingRef.current) return;

    if (
      action === "CANCEL" &&
      !window.confirm("Batalkan sesi trading ini? Tindakan ini tidak dapat dibatalkan.")
    ) {
      return;
    }
    if (
      action === "ARCHIVE" &&
      !window.confirm("Arsipkan sesi trading ini? Sesi yang diarsipkan tidak lagi aktif.")
    ) {
      return;
    }

    lifecycleSubmittingRef.current = true;
    setLifecycleAction({ status: "submitting", action, error: "" });

    try {
      if (action === "MARK_READY") {
        await markReady(sessionId);
      } else if (action === "CANCEL") {
        await cancelSession({
          session_id: sessionId,
          idempotency_key: makeIdempotencyKey(action, sessionId),
          cancelled_at: new Date().toISOString(),
          reason: "USER_CANCELLED_SESSION",
        });
      } else if (action === "ARCHIVE") {
        await archiveSession(sessionId);
      }

      setLifecycleAction({ status: "idle", error: "" });
      handleActionSuccess();
    } catch (e: unknown) {
      setLifecycleAction({ status: "idle", error: lifecycleErrorMessage(action, e) });
    } finally {
      lifecycleSubmittingRef.current = false;
    }
  }, [handleActionSuccess, sessionId]);

  const handleJobCreated = useCallback((job: { job_id: string; analysis_type: string }) => {
    setActiveJob({ jobId: job.job_id, analysisType: job.analysis_type });
  }, []);

  const handleJobCompleted = useCallback(() => {
    setActiveJob(null);
    setRetryKey((k) => k + 1);
  }, []);

  const handleJobFailed = useCallback(() => {
    setRetryKey((k) => k + 1);
  }, []);

  if (state.status === "loading") {
    return (
      <p className="py-12 text-center text-zinc-500">Memuat sesi trading…</p>
    );
  }

  if (state.status === "error") {
    return (
      <div className="py-12 text-center">
        <p className="text-zinc-600">{state.message}</p>
        <button
          type="button"
          onClick={() => setRetryKey((k) => k + 1)}
          className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Coba Lagi
        </button>
        <div className="mt-4">
          <Link href="/sessions" className="text-sm text-blue-600 hover:underline">
            &larr; Kembali ke Daftar Sesi
          </Link>
        </div>
      </div>
    );
  }

  const { session, trade_state, allowed_actions } = state.data;
  const availableActions =
    session.lifecycle_status === "READY_FOR_ANALYSIS" &&
    !allowed_actions.includes("REQUEST_INITIAL_ANALYSIS")
      ? ["REQUEST_INITIAL_ANALYSIS", ...allowed_actions]
      : allowed_actions;

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <SessionHeader session={session} />
      <LifecycleStatus status={session.lifecycle_status} />
      <div className="mt-4">
        <CanonicalPositionSummary tradeState={trade_state} />
      </div>

      <div className="mt-6 space-y-4">
        <EvidenceSection sessionId={sessionId} />
      </div>

      <div className="mt-6">
        <AnalysisSwitcher
          analysisListState={analysisListState}
          onRetry={() => setRetryKey((k) => k + 1)}
          sessionId={sessionId}
        />
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <SessionTimeline sessionId={sessionId} refreshKey={retryKey} />
        <AnalysisHistory
          sessionId={sessionId}
          refreshKey={retryKey}
          analyses={analysisListState.status === "loaded" ? analysisListState.analyses : undefined}
          loading={analysisListState.status === "loading"}
          errorMessage={analysisListState.status === "error" ? analysisListState.message : null}
          onRetry={() => setRetryKey((k) => k + 1)}
        />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <PendingActionsSection
          actions={availableActions}
          onActionClick={setActionModal}
          onLifecycleAction={handleLifecycleAction}
          pendingAction={lifecycleAction.status === "submitting" ? lifecycleAction.action : null}
          error={lifecycleAction.error}
        />
      </div>

      {actionModal === "OPEN_POSITION" && (
        <OpenPositionModal
          sessionId={sessionId}
          isOpen={true}
          onClose={() => setActionModal(null)}
          onSuccess={handleActionSuccess}
        />
      )}
      {(actionModal === "CONFIRM_STOP" || actionModal === "CHANGE_STOP") && (
        <StopLossModal
          sessionId={sessionId}
          isOpen={true}
          onClose={() => setActionModal(null)}
          onSuccess={handleActionSuccess}
          action={actionModal}
          activeStopLoss={trade_state.active_stop_loss}
        />
      )}
      {(actionModal === "CONFIRM_TARGET" || actionModal === "CHANGE_TARGET") && (
        <TargetModal
          sessionId={sessionId}
          isOpen={true}
          onClose={() => setActionModal(null)}
          onSuccess={handleActionSuccess}
          action={actionModal}
          activeTarget={trade_state.active_target}
        />
      )}
      {actionModal === "PARTIAL_EXIT" && (
        <PartialExitModal
          sessionId={sessionId}
          isOpen={true}
          onClose={() => setActionModal(null)}
          onSuccess={handleActionSuccess}
          remainingQuantity={trade_state.remaining_quantity}
        />
      )}
      {actionModal === "FULL_EXIT" && (
        <FullExitModal
          sessionId={sessionId}
          isOpen={true}
          onClose={() => setActionModal(null)}
          onSuccess={handleActionSuccess}
          remainingQuantity={trade_state.remaining_quantity}
          entryPrice={trade_state.entry_price}
          activeStopLoss={trade_state.active_stop_loss}
          activeTarget={trade_state.active_target}
        />
      )}
      {actionModal?.startsWith("REQUEST_") && (
        <RequestAnalysis
          sessionId={sessionId}
          analysisType={actionModal.replace("REQUEST_", "")}
          onSuccess={(job) => { handleJobCreated(job); setActionModal(null); handleActionSuccess(); }}
          onClose={() => setActionModal(null)}
        />
      )}

      {activeJob && (
        <div className="mt-4">
          <JobStatus
            jobId={activeJob.jobId}
            sessionId={sessionId}
            onCompleted={handleJobCompleted}
            onFailed={handleJobFailed}
            onClear={handleJobCompleted}
            onRetry={handleJobCompleted}
          />
        </div>
      )}
    </div>
  );
}

type TimelineState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "loaded"; events: TimelineEvent[] };

function formatTimelineTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("id-ID", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function SessionTimeline({ sessionId, refreshKey }: { sessionId: string; refreshKey: number }) {
  const [state, setState] = useState<TimelineState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState({ status: "loading" });
      try {
        const result = await getTimeline(sessionId);
        if (cancelled) return;
        setState(
          result.events.length === 0
            ? { status: "empty" }
            : { status: "loaded", events: result.events },
        );
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof AuthenticationError) {
          setState({ status: "error", message: "Silakan masuk terlebih dahulu untuk melihat timeline." });
        } else if (e instanceof ApiError) {
          setState({ status: "error", message: e.message });
        } else {
          setState({ status: "error", message: "Gagal memuat timeline. Silakan coba lagi." });
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, [sessionId, refreshKey]);

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Timeline
      </h3>
      {state.status === "loading" && (
        <p className="text-sm text-zinc-500">Memuat timeline…</p>
      )}
      {state.status === "empty" && (
        <p className="text-sm text-zinc-400">Belum ada riwayat sesi.</p>
      )}
      {state.status === "error" && (
        <p className="text-sm text-red-700" role="alert">{state.message}</p>
      )}
      {state.status === "loaded" && (
        <ol className="space-y-2">
          {state.events.map((event) => (
            <li key={event.id} className="border-l-2 border-zinc-200 pl-3">
              <p className="text-sm font-medium text-zinc-800">
                {event.summary ?? event.event_type}
              </p>
              <p className="text-xs text-zinc-400">
                {formatTimelineTimestamp(event.occurred_at)}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function PendingActionsSection({
  actions,
  onActionClick,
  onLifecycleAction,
  pendingAction,
  error,
}: {
  actions: string[];
  onActionClick?: (action: string) => void;
  onLifecycleAction?: (action: string) => void;
  pendingAction?: string | null;
  error?: string;
}) {
  const interactive = new Set(["OPEN_POSITION", "CONFIRM_STOP", "CHANGE_STOP", "CONFIRM_TARGET", "CHANGE_TARGET", "PARTIAL_EXIT", "FULL_EXIT"]);
  const lifecycleActions = new Set(["MARK_READY", "CANCEL", "ARCHIVE"]);

  function isInteractive(action: string): boolean {
    if (interactive.has(action)) return true;
    if (lifecycleActions.has(action)) return true;
    if (action.startsWith("REQUEST_")) return true;
    return false;
  }

  function handleClick(action: string): void {
    if (lifecycleActions.has(action)) {
      onLifecycleAction?.(action);
      return;
    }
    onActionClick?.(action);
  }

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        Tindakan Tersedia
      </h3>
      {actions.length === 0 ? (
        <p className="text-sm text-zinc-400">Tidak ada tindakan yang tersedia.</p>
      ) : (
        <ul className="space-y-1">
          {actions.map((a) => (
            <li key={a}>
              {isInteractive(a) ? (
                <button
                  type="button"
                  onClick={() => handleClick(a)}
                  disabled={pendingAction !== null && pendingAction !== undefined}
                  className="w-full rounded px-2 py-1 text-left text-sm font-medium text-blue-600 transition hover:bg-blue-50 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 disabled:cursor-not-allowed disabled:text-zinc-400 disabled:hover:bg-transparent"
                >
                  {pendingAction === a ? "Memproses…" : actionLabel(a)}
                </button>
              ) : (
                <span className="text-sm text-zinc-700">{actionLabel(a)}</span>
              )}
            </li>
          ))}
        </ul>
      )}
      {error ? (
        <p className="mt-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert" aria-live="polite">
          {error}
        </p>
      ) : null}
    </section>
  );
}

/**
 * Analysis lifecycle precedence:
 * 1. ClosingAnalysisView (closed session final review)
 * 2. PartialExitReviewView (after partial exit)
 * 3. OpenPositionUpdateView (active position monitoring)
 * 4. WatchingUpdateView (pre-entry setup changes)
 * 5. InitialAnalysisView (initial setup)
 */
function AnalysisSwitcher({
  analysisListState,
  onRetry,
  sessionId,
}: {
  analysisListState: AnalysisListState;
  onRetry: () => void;
  sessionId: string;
}) {
  if (analysisListState.status === "loading") {
    return (
      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <p className="text-sm text-zinc-500">Memuat closing analysis…</p>
      </section>
    );
  }

  if (analysisListState.status === "error") {
    return (
      <section className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">{analysisListState.message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          Coba Lagi
        </button>
      </section>
    );
  }

  const selected = selectHighestPrecedenceAnalysis(analysisListState.analyses);

  return (
    <>
      {selected?.analysis_type === "CLOSING_ANALYSIS" && (
        <ClosingAnalysisView
          sessionId={sessionId}
          selectedAnalysis={selected}
        />
      )}
      {selected?.analysis_type === "PARTIAL_EXIT_REVIEW" && (
        <PartialExitReviewView
          sessionId={sessionId}
          selectedAnalysis={selected}
        />
      )}
      {selected?.analysis_type === "OPEN_POSITION_UPDATE" && (
        <OpenPositionUpdateView
          sessionId={sessionId}
          selectedAnalysis={selected}
        />
      )}
      {selected?.analysis_type === "WATCHING_UPDATE" && (
        <WatchingUpdateView
          sessionId={sessionId}
          selectedAnalysis={selected}
        />
      )}
      {(selected?.analysis_type === "INITIAL_ANALYSIS" || selected === null) && (
        <InitialAnalysisView sessionId={sessionId} selectedAnalysis={selected} />
      )}
    </>
  );
}

const ANALYSIS_PRECEDENCE = [
  "CLOSING_ANALYSIS",
  "PARTIAL_EXIT_REVIEW",
  "OPEN_POSITION_UPDATE",
  "WATCHING_UPDATE",
  "INITIAL_ANALYSIS",
] as const;

function selectHighestPrecedenceAnalysis(analyses: AnalysisSummary[]): AnalysisSummary | null {
  const accepted = analyses.filter((analysis) => analysis.acceptance_status === "ACCEPTED");

  for (const type of ANALYSIS_PRECEDENCE) {
    const match = accepted
      .filter((analysis) => analysis.analysis_type === type)
      .sort(
        (a, b) =>
          new Date(b.accepted_at ?? b.created_at).getTime() -
          new Date(a.accepted_at ?? a.created_at).getTime(),
      )[0];

    if (match) return match;
  }

  return null;
}
