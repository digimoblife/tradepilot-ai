"use client";

import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import { getSession } from "@/lib/api/trade-sessions";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { TradeSessionDetail } from "@/types/trade-session";
import { SessionHeader } from "./session-header";
import { LifecycleStatus } from "./lifecycle-status";
import { CanonicalPositionSummary } from "./canonical-position-summary";
import { EvidenceSection } from "@/features/evidence/evidence-section";
import { InitialAnalysisView } from "@/features/analysis/initial-analysis-view";
import { WatchingUpdateView } from "@/features/analysis/watching-update-view";
import { OpenPositionUpdateView } from "@/features/analysis/open-position-update-view";
import { PartialExitReviewView } from "@/features/analysis/partial-exit-review-view";
import { ClosingAnalysisView } from "@/features/analysis/closing-analysis-view";
import { SectionPlaceholder } from "./section-placeholder";
import { AnalysisHistory } from "@/features/analysis/history/analysis-history";
import { OpenPositionModal } from "@/features/trade-actions/open-position-modal";
import { StopLossModal } from "@/features/trade-actions/stop-loss-modal";
import { TargetModal } from "@/features/trade-actions/target-modal";
import { PartialExitModal } from "@/features/trade-actions/partial-exit-modal";
import { actionLabel } from "./helpers";

interface Props {
  sessionId: string;
}

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: TradeSessionDetail };

export function TradeSessionShell({ sessionId }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [retryKey, setRetryKey] = useState(0);
  const [actionModal, setActionModal] = useState<string | null>(null);

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

  const handleActionSuccess = useCallback(() => {
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
        <AnalysisSwitcher sessionId={sessionId} />
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <SectionPlaceholder title="Timeline" message="Riwayat sesi akan ditampilkan di sini." />
        <AnalysisHistory sessionId={sessionId} />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <PendingActionsSection
          actions={allowed_actions}
          onActionClick={setActionModal}
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
    </div>
  );
}

function PendingActionsSection({ actions, onActionClick }: { actions: string[]; onActionClick?: (action: string) => void }) {
  const interactive = new Set(["OPEN_POSITION", "CONFIRM_STOP", "CHANGE_STOP", "CONFIRM_TARGET", "CHANGE_TARGET", "PARTIAL_EXIT"]);
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
              {interactive.has(a) ? (
                <button
                  type="button"
                  onClick={() => onActionClick?.(a)}
                  className="w-full rounded px-2 py-1 text-left text-sm text-blue-600 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                >
                  {actionLabel(a)}
                </button>
              ) : (
                <span className="text-sm text-zinc-700">{actionLabel(a)}</span>
              )}
            </li>
          ))}
        </ul>
      )}
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
function AnalysisSwitcher({ sessionId }: { sessionId: string }) {
  const [show, setShow] = useState<"ca" | "per" | "opu" | "wu" | "ia" | null>(null);

  return (
    <>
      {show !== "per" && show !== "opu" && show !== "wu" && show !== "ia" && (
        <ClosingAnalysisView
          sessionId={sessionId}
          onEmpty={() => setShow("per")}
          onLoaded={() => setShow("ca")}
        />
      )}
      {show === "per" && (
        <PartialExitReviewView
          sessionId={sessionId}
          onEmpty={() => setShow("opu")}
          onLoaded={() => setShow("per")}
        />
      )}
      {show === "opu" && (
        <OpenPositionUpdateView
          sessionId={sessionId}
          onEmpty={() => setShow("wu")}
          onLoaded={() => setShow("opu")}
        />
      )}
      {show === "wu" && (
        <WatchingUpdateView
          sessionId={sessionId}
          onEmpty={() => setShow("ia")}
          onLoaded={() => setShow("wu")}
        />
      )}
      {show === "ia" && <InitialAnalysisView sessionId={sessionId} />}
      {show === null && (
        <section className="rounded-lg border border-zinc-200 bg-white p-4">
          <p className="text-sm text-zinc-500">Memuat closing analysis…</p>
        </section>
      )}
    </>
  );
}
