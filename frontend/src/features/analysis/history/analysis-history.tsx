"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { AnalysisSection } from "../analysis-section";
import { AnalysisValue } from "../analysis-value";
import { enumLabel, percentage, currency } from "../helpers";
import type { AnalysisSummary, AnalysisDetail } from "@/types/analysis";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ANALYSIS_TYPE_LABEL: Record<string, string> = {
  INITIAL_ANALYSIS: "Analisis Awal",
  WATCHING_UPDATE: "Update Pemantauan",
  OPEN_POSITION_UPDATE: "Update Posisi Terbuka",
  PARTIAL_EXIT_REVIEW: "Review Partial Exit",
  CLOSING_ANALYSIS: "Closing Analysis",
};

const UPDATE_PERIOD_LABEL: Record<string, string> = {
  MORNING: "Pagi",
  MIDDAY: "Siang",
  AFTERNOON: "Sore",
  CLOSING: "Penutupan",
  MARKET_CLOSE: "Penutupan Pasar",
  SPECIAL: "Khusus",
};

function updatePeriodLabel(value: string | null | undefined): string {
  if (!value) return "Tidak berlaku";
  return UPDATE_PERIOD_LABEL[value] ?? value;
}

function formatTimestamp(ts: string | null | undefined): string {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    return d.toLocaleString("id-ID", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

// ---------------------------------------------------------------------------
// Payload viewer — renders key fields per analysis type
// ---------------------------------------------------------------------------

function PeriodBadge({ value }: { value: string | null | undefined }) {
  return (
    <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
      {updatePeriodLabel(value)}
    </span>
  );
}

function ChangesList({ changes }: { changes: unknown[] }) {
  if (changes.length === 0) {
    return <p className="text-xs text-zinc-400">Tidak ada perubahan material.</p>;
  }
  return (
    <div className="text-sm">
      <span className="text-zinc-400">Perubahan Material</span>
      <ul className="mt-1 list-inside list-disc text-zinc-800">
        {changes.map((c, i) => {
          const item = c as Record<string, unknown>;
          return (
            <li key={i}>
              {String(item.category ?? "")}{item.explanation ? `: ${item.explanation}` : ""}
              {item.materiality ? ` (${item.materiality})` : ""}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function PayloadViewer({ payload, analysisType }: { payload: Record<string, unknown>; analysisType: string }) {
  const ms = payload.market_snapshot as Record<string, unknown> | undefined;
  const period = (payload.update_period as string) ?? (ms?.update_period as string) ?? null;
  const periodNode = <PeriodBadge value={period} />;
  switch (analysisType) {
    case "INITIAL_ANALYSIS":
      return <><div className="mb-2">{periodNode}</div><InitialAnalysisPayload p={payload} /></>;
    case "WATCHING_UPDATE":
      return <><div className="mb-2">{periodNode}</div><WatchingUpdatePayload p={payload} /></>;
    case "OPEN_POSITION_UPDATE":
      return <><div className="mb-2">{periodNode}</div><OpenPositionUpdatePayload p={payload} /></>;
    case "PARTIAL_EXIT_REVIEW":
      return <><div className="mb-2">{periodNode}</div><PartialExitReviewPayload p={payload} /></>;
    case "CLOSING_ANALYSIS":
      return <><div className="mb-2">{periodNode}</div><ClosingAnalysisPayload p={payload} /></>;
    default:
      return <p className="text-sm text-zinc-400">Tipe analisis tidak dikenal.</p>;
  }
}

function InitialAnalysisPayload({ p }: { p: Record<string, unknown> }) {
  const ms = p.market_snapshot as Record<string, unknown> | undefined;
  const es = p.executive_summary as Record<string, unknown> | undefined;
  const it = p.initial_thesis as Record<string, unknown> | undefined;
  return (
    <div className="space-y-3">
      {ms && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Open" value={ms.open as number | null} />
          <AnalysisValue label="High" value={ms.high as number | null} />
          <AnalysisValue label="Low" value={ms.low as number | null} />
          <AnalysisValue label="Last" value={ms.last as number | null} />
          <AnalysisValue label="Rata-rata" value={ms.average as number | null} />
          <AnalysisValue label="Perubahan" value={percentage(ms.change_percentage as number | null)} />
        </div>
      )}
      {es && (es.recommended_action as string | undefined) && (
        <AnalysisValue label="Rekomendasi" value={enumLabel("recommended_action", es.recommended_action as string | null)} />
      )}
      {it && (it.summary as string | undefined) && (
        <AnalysisValue label="Thesis" value={it.summary as string} />
      )}
    </div>
  );
}

function WatchingUpdatePayload({ p }: { p: Record<string, unknown> }) {
  const ms = p.market_snapshot as Record<string, unknown> | undefined;
  const tp = p.trading_plan as Record<string, unknown> | undefined;
  const comp = p.comparison as Record<string, unknown> | undefined;
  const changes = p.changes_from_previous as unknown[] | undefined;
  return (
    <div className="space-y-3">
      {ms && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Open" value={ms.open as number | null} />
          <AnalysisValue label="High" value={ms.high as number | null} />
          <AnalysisValue label="Low" value={ms.low as number | null} />
          <AnalysisValue label="Last" value={ms.last as number | null} />
          <AnalysisValue label="Rata-rata" value={ms.average as number | null} />
          <AnalysisValue label="Perubahan" value={percentage(ms.change_percentage as number | null)} />
        </div>
      )}
      {tp && (tp.current_action as string | undefined) && (
        <AnalysisValue label="Rekomendasi" value={enumLabel("recommended_action", tp.current_action as string | null)} />
      )}
      {comp && (comp.summary as string | undefined) && (
        <AnalysisValue label="Perbandingan" value={comp.summary as string} />
      )}
      {changes && <ChangesList changes={changes} />}
    </div>
  );
}

function OpenPositionUpdatePayload({ p }: { p: Record<string, unknown> }) {
  const ms = p.market_snapshot as Record<string, unknown> | undefined;
  const comp = p.comparison as Record<string, unknown> | undefined;
  const pa = p.position_assessment as Record<string, unknown> | undefined;
  const changes = p.changes_from_previous as unknown[] | undefined;
  return (
    <div className="space-y-3">
      {ms && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Open" value={ms.open as number | null} />
          <AnalysisValue label="High" value={ms.high as number | null} />
          <AnalysisValue label="Low" value={ms.low as number | null} />
          <AnalysisValue label="Last" value={ms.last as number | null} />
          <AnalysisValue label="Rata-rata" value={ms.average as number | null} />
          <AnalysisValue label="Perubahan" value={percentage(ms.change_percentage as number | null)} />
        </div>
      )}
      {!!(comp?.summary) && (
        <AnalysisValue label="Perbandingan" value={String(comp?.summary)} />
      )}
      {!!(pa?.summary) && (
        <AnalysisValue label="Penilaian Posisi" value={String(pa?.summary)} />
      )}
      {changes && <ChangesList changes={changes} />}
    </div>
  );
}

function PartialExitReviewPayload({ p }: { p: Record<string, unknown> }) {
  const pc = p.partial_exit_confirmation as Record<string, unknown> | undefined;
  const rs = p.result_summary as Record<string, unknown> | undefined;
  const rta = p.remaining_target_assessment as Record<string, unknown> | undefined;
  const comp = p.comparison as Record<string, unknown> | undefined;
  const changes = p.changes_from_previous as unknown[] | undefined;
  return (
    <div className="space-y-3">
      {pc && (
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Harga Exit" value={currency(pc.exit_price as number | null)} />
          <AnalysisValue label="Qty Terjual" value={pc.exited_quantity as number | null} />
        </div>
      )}
      {!!(rs?.summary) && (
        <AnalysisValue label="Hasil" value={String(rs?.summary)} />
      )}
      {!!(rta?.summary) && (
        <AnalysisValue label="Target Tersisa" value={String(rta?.summary)} />
      )}
      {!!(comp?.summary) && (
        <AnalysisValue label="Perbandingan" value={String(comp?.summary)} />
      )}
      {changes && <ChangesList changes={changes} />}
    </div>
  );
}

function ClosingAnalysisPayload({ p }: { p: Record<string, unknown> }) {
  const tr = p.trade_result as Record<string, unknown> | undefined;
  const fae = p.final_ai_evaluation as Record<string, unknown> | undefined;
  const js = p.journal_summary as Record<string, unknown> | undefined;
  return (
    <div className="space-y-3">
      {tr && (
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Gross P&L" value={currency(tr.gross_profit_loss as number | null)} />
          <AnalysisValue label="Return" value={percentage(tr.gross_return_percentage as number | null)} />
        </div>
      )}
      {!!(fae?.trade_grade) && (
        <AnalysisValue label="Grade" value={String(fae?.trade_grade)} />
      )}
      {!!(js?.one_sentence_review) && (
        <AnalysisValue label="Review" value={String(js?.one_sentence_review)} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// History item
// ---------------------------------------------------------------------------

interface HistoryItemProps {
  summary: AnalysisSummary;
  isOpen: boolean;
  onToggle: () => void;
  detail: AnalysisDetail | null;
  detailLoading: boolean;
  detailError: string | null;
}

function HistoryItem({ summary, isOpen, onToggle, detail, detailLoading, detailError }: HistoryItemProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white">
      <button
        type="button"
        data-testid={`history-item-${summary.id}`}
        onClick={onToggle}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-zinc-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-zinc-800">
              {ANALYSIS_TYPE_LABEL[summary.analysis_type] ?? summary.analysis_type}
            </span>
            {summary.acceptance_status === "ACCEPTED" && (
              <span className="shrink-0 rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700">
                Diterima
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-zinc-500">
            {formatTimestamp(summary.created_at)}
          </p>
        </div>
      </button>

      {isOpen && (
        <div className="border-t border-zinc-100 px-4 py-3">
          <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500">
            <span>Versi: {summary.prompt_version}</span>
            <span>Schema: {summary.schema_name} v{summary.schema_version}</span>
            {summary.accepted_at && <span>Diterima: {formatTimestamp(summary.accepted_at)}</span>}
          </div>

          {detailLoading && <p className="text-sm text-zinc-400">Memuat detail…</p>}

          {detailError && (
            <div className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">
              {detailError}
            </div>
          )}

          {detail && detail.payload && (
            <PayloadViewer payload={detail.payload} analysisType={summary.analysis_type} />
          )}

          {detail && !detail.payload && (
            <p className="text-sm text-zinc-400">Tidak ada data tersedia untuk analisis ini.</p>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

type LoadState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string; retry: () => void }
  | { status: "loaded"; analyses: AnalysisSummary[] };

interface Props {
  sessionId: string;
}

export function AnalysisHistory({ sessionId }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [openId, setOpenId] = useState<string | null>(null);
  const [detailMap, setDetailMap] = useState<Record<string, AnalysisDetail | "loading" | "error">>({});
  const cancelledRef = useRef(false);

  const load = useCallback(async function loadFn() {
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const result = await listAnalyses(sessionId);
      if (cancelledRef.current) return;

      const accepted = result.analyses
        .filter((a) => a.acceptance_status === "ACCEPTED")
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );

      if (accepted.length === 0) {
        if (!cancelledRef.current) setState({ status: "empty" });
        return;
      }

      if (!cancelledRef.current) {
        setState({ status: "loaded", analyses: accepted });
      }
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      if (e instanceof AuthenticationError) {
        setState({
          status: "error",
          message: "Silakan masuk terlebih dahulu untuk melihat riwayat analisis.",
          retry: loadFn,
        });
      } else if (e instanceof ApiError) {
        setState({
          status: "error",
          message: e.message,
          retry: loadFn,
        });
      } else {
        setState({
          status: "error",
          message: "Gagal memuat riwayat analisis. Silakan coba lagi.",
          retry: loadFn,
        });
      }
    }
  }, [sessionId]);

  useEffect(() => {
    cancelledRef.current = false;
    load();
    return () => { cancelledRef.current = true; };
  }, [load]);

  const handleToggle = useCallback((id: string) => {
    if (cancelledRef.current) return;
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);

    if (detailMap[id]) return;

    setDetailMap((prev) => {
      if (prev[id]) return prev;
      return { ...prev, [id]: "loading" as const };
    });

    getAnalysis(id)
      .then((detail) => {
        if (!cancelledRef.current) {
          setDetailMap((prev) => ({ ...prev, [id]: detail }));
        }
      })
      .catch(() => {
        if (!cancelledRef.current) {
          setDetailMap((prev) => ({ ...prev, [id]: "error" as const }));
        }
      });
  }, [openId, detailMap]);

  const currentDetail = openId ? detailMap[openId] : null;
  const detailLoading = currentDetail === "loading";
  const detailError = currentDetail === "error" ? "Gagal memuat detail analisis." : null;

  if (state.status === "loading") {
    return (
      <AnalysisSection title="Riwayat Analisis">
        <p className="text-sm text-zinc-500">Memuat riwayat analisis…</p>
      </AnalysisSection>
    );
  }

  if (state.status === "empty") {
    return (
      <AnalysisSection title="Riwayat Analisis">
        <p className="text-sm text-zinc-400">Belum ada analisis yang diterima.</p>
      </AnalysisSection>
    );
  }

  if (state.status === "error") {
    return (
      <AnalysisSection title="Riwayat Analisis">
        <p className="text-sm text-red-700">{state.message}</p>
        <button
          type="button"
          onClick={state.retry}
          className="mt-2 rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          Coba Lagi
        </button>
      </AnalysisSection>
    );
  }

  return (
    <AnalysisSection title="Riwayat Analisis">
      <div className="space-y-2">
        <p className="text-xs text-zinc-400">
          {state.analyses.length} analisis diterima. Klik untuk melihat detail.
        </p>
        {state.analyses.map((a) => (
          <HistoryItem
            key={a.id}
            summary={a}
            isOpen={openId === a.id}
            onToggle={() => handleToggle(a.id)}
            detail={currentDetail !== "loading" && currentDetail !== "error" && openId === a.id ? currentDetail as AnalysisDetail : null}
            detailLoading={detailLoading && openId === a.id}
            detailError={detailError && openId === a.id ? detailError : null}
          />
        ))}
      </div>
    </AnalysisSection>
  );
}
