"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { AnalysisSection } from "./analysis-section";
import { AnalysisValue } from "./analysis-value";
import {
  enumLabel,
  percentage,
  currency,
  displayBool,
} from "./helpers";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TimelineEvent {
  timestamp: string;
  event_type: string;
  price: number | null;
  quantity: number | null;
  related_analysis_id: string | null;
  summary: string;
}

interface FinalThesisEvaluation {
  original_thesis: string;
  final_thesis_status: string;
  outcome: string;
  thesis_was_correct: boolean | null;
  entry_reason_remained_valid: boolean | null;
  invalidation_condition_respected: boolean | null;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  summary: string;
}

interface Mistake {
  category: string;
  severity: string;
  description: string;
  impact: string;
  how_to_avoid: string;
}

interface Lesson {
  category: string;
  lesson: string;
  evidence: string;
  future_rule: string;
}

interface FinalAiEvaluation {
  trade_grade: string;
  process_score: number;
  thesis_score: number;
  execution_score: number;
  risk_management_score: number;
  result_score: number;
  good_trade: boolean;
  result_aligned_with_process: boolean | null;
  summary: string;
}

interface JournalSummary {
  title: string;
  setup_summary: string;
  entry_summary: string;
  management_summary: string;
  exit_summary: string;
  result_summary: string;
  main_lesson: string;
  one_sentence_review: string;
  tags: string[];
}

interface ClosingAnalysisPayload {
  metadata: Record<string, unknown>;
  evidence_summary: Record<string, unknown>;
  closing_confirmation: Record<string, unknown>;
  trade_result: Record<string, unknown>;
  trade_timeline: Record<string, unknown>;
  final_thesis_evaluation: FinalThesisEvaluation;
  plan_execution_evaluation: Record<string, unknown>;
  risk_management_evaluation: Record<string, unknown>;
  what_worked: string[];
  what_did_not_work: string[];
  avoidable_mistakes: Mistake[];
  lessons_learned: Lesson[];
  future_improvements: string[];
  final_ai_evaluation: FinalAiEvaluation;
  journal_summary: JournalSummary;
  warnings_and_missing_information: {
    missing_information: string[];
    warnings: string[];
  };
}

// ---------------------------------------------------------------------------
// Local label maps
// ---------------------------------------------------------------------------

const CLOSING_REASON_LABEL: Record<string, string> = {
  TAKE_PROFIT: "Take Profit",
  STOP_LOSS: "Stop Loss",
  THESIS_INVALIDATED: "Thesis Tidak Valid",
  MANUAL_EXIT: "Exit Manual",
  RISK_REDUCTION: "Pengurangan Risiko",
  TIME_EXIT: "Exit Berdasarkan Waktu",
  OTHER: "Lainnya",
};

const THESIS_OUTCOME_LABEL: Record<string, string> = {
  FULLY_CONFIRMED: "Terkonfirmasi Penuh",
  PARTIALLY_CONFIRMED: "Terkonfirmasi Sebagian",
  CORRECT_BUT_POORLY_EXECUTED: "Benar tetapi Eksekusi Kurang",
  INVALIDATED_AFTER_PROGRESS: "Invalidasi Setelah Progress",
  INVALIDATED_EARLY: "Invalidasi Awal",
  INCORRECT: "Tidak Benar",
  INCONCLUSIVE: "Tidak Meyakinkan",
};

const EXECUTION_QUALITY_LABEL: Record<string, string> = {
  EXCELLENT: "Sangat Baik",
  GOOD: "Baik",
  FAIR: "Cukup",
  POOR: "Kurang",
  VERY_POOR: "Sangat Kurang",
  NOT_APPLICABLE: "Tidak Relevan",
  UNKNOWN: "Tidak Diketahui",
};

const TRADE_OUTCOME_LABEL: Record<string, string> = {
  LARGE_PROFIT: "Profit Besar",
  PROFIT: "Profit",
  SMALL_PROFIT: "Profit Kecil",
  BREAK_EVEN: "Impas",
  SMALL_LOSS: "Rugi Kecil",
  LOSS: "Rugi",
  LARGE_LOSS: "Rugi Besar",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type LoadState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string; retry: () => void }
  | { status: "loaded"; payload: ClosingAnalysisPayload };

interface Props {
  sessionId: string;
  onEmpty?: () => void;
  onLoaded?: () => void;
}

export function ClosingAnalysisView({ sessionId, onEmpty, onLoaded }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const cancelledRef = useRef(false);

  const load = useCallback(async function loadFn() {
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const list = await listAnalyses(sessionId, {
        analysis_type: "CLOSING_ANALYSIS",
      });
      if (cancelledRef.current) return;

      const accepted = list.analyses
        .filter((a) => a.acceptance_status === "ACCEPTED")
        .sort(
          (a, b) =>
            new Date(b.accepted_at ?? b.created_at).getTime() -
            new Date(a.accepted_at ?? a.created_at).getTime(),
        );

      if (accepted.length === 0) {
        if (!cancelledRef.current) setState({ status: "empty" });
        return;
      }

      const latest = accepted[0];
      const detail = await getAnalysis(latest.id);
      if (cancelledRef.current) return;

      if (!detail.payload) {
        if (!cancelledRef.current) setState({ status: "empty" });
        return;
      }

      if (!cancelledRef.current) {
        setState({
          status: "loaded",
          payload: detail.payload as unknown as ClosingAnalysisPayload,
        });
      }
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      if (e instanceof AuthenticationError) {
        setState({
          status: "error",
          message: "Silakan masuk terlebih dahulu untuk melihat closing analysis.",
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
          message: "Gagal memuat closing analysis. Silakan coba lagi.",
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

  useEffect(() => {
    if (state.status === "empty" && onEmpty) onEmpty();
    if (state.status === "loaded" && onLoaded) onLoaded();
  }, [state.status, onEmpty, onLoaded]);

  if (state.status === "loading") {
    return (
      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <p className="text-sm text-zinc-500">Memuat closing analysis…</p>
      </section>
    );
  }

  if (state.status === "empty") {
    return null;
  }

  if (state.status === "error") {
    return (
      <section className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">{state.message}</p>
        <button
          type="button"
          onClick={state.retry}
          className="mt-2 rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          Coba Lagi
        </button>
      </section>
    );
  }

  const p = state.payload;

  // Helper: access unknown fields
  const cc = p.closing_confirmation as Record<string, unknown>;
  const tr = p.trade_result as Record<string, unknown>;
  const tt = p.trade_timeline as Record<string, unknown>;
  const pee = p.plan_execution_evaluation as Record<string, unknown>;
  const rme = p.risk_management_evaluation as Record<string, unknown>;

  // -----------------------------------------------------------------------
  // 1. Ringkasan Penutupan
  // -----------------------------------------------------------------------
  const closingSection = (
    <AnalysisSection title="Ringkasan Penutupan">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Alasan Tutup" value={CLOSING_REASON_LABEL[String(cc.closing_reason ?? "")] ?? String(cc.closing_reason ?? "—")} />
          <AnalysisValue label="Waktu Tutup" value={String(cc.exit_timestamp ?? "—")} />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Harga Final Exit" value={currency(cc.final_exit_price as number | null)} />
          <AnalysisValue label="Qty Final Exit" value={cc.final_exit_quantity as number | null} />
          <AnalysisValue label="Rata-rata Exit" value={currency(cc.average_exit_price as number | null)} />
        </div>
        {(cc.user_note as string | null) && (
          <AnalysisValue label="Catatan User" value={String(cc.user_note)} />
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 2. Hasil Final Trade
  // -----------------------------------------------------------------------
  const resultSection = (
    <AnalysisSection title="Hasil Final Trade">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Hasil" value={TRADE_OUTCOME_LABEL[String(tr.outcome ?? "")] ?? String(tr.outcome ?? "—")} />
          <AnalysisValue label="Mata Uang" value={String(tr.currency ?? "—")} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Harga Entry" value={currency(tr.entry_price as number | null)} />
          <AnalysisValue label="Rata-rata Exit" value={currency(tr.average_exit_price as number | null)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Qty Awal" value={tr.original_quantity as number | null} />
          <AnalysisValue label="Jumlah Partial Exit" value={tr.partial_exit_count as number | null} />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Gross P&L" value={currency(tr.gross_profit_loss as number | null)} />
          <AnalysisValue label="Net P&L" value={currency(tr.net_profit_loss as number | null)} />
          <AnalysisValue label="Gross Return" value={percentage(tr.gross_return_percentage as number | null)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Net Return" value={percentage(tr.net_return_percentage as number | null)} />
          <AnalysisValue label="Max Profit Floating" value={percentage(tr.maximum_unrealized_profit_percentage as number | null)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Max Loss Floating" value={percentage(tr.maximum_unrealized_loss_percentage as number | null)} />
          <AnalysisValue label="Biaya" value={currency(tr.fees as number | null)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Durasi (kalender)" value={`${String(tr.holding_duration_calendar_days ?? "—")} hari`} />
          <AnalysisValue label="Durasi (trading)" value={`${String(tr.holding_duration_trading_days ?? "—")} hari`} />
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{String(tr.summary ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 3. Timeline Perjalanan Trade
  // -----------------------------------------------------------------------
  const events = (tt.events as TimelineEvent[]) ?? [];
  const timelineSection = (
    <AnalysisSection title="Timeline Perjalanan Trade">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Mulai Sesi" value={String(tt.session_started_at ?? "—")} />
          <AnalysisValue label="Posisi Dibuka" value={String(tt.position_opened_at ?? "—")} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Posisi Ditutup" value={String(tt.position_closed_at ?? "—")} />
          <AnalysisValue label="Jumlah Analisis" value={tt.analysis_count as number | null} />
        </div>
        {events.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Peristiwa</span>
            <ul className="mt-2 space-y-2">
              {events.map((ev, i) => (
                <li key={i} className="rounded border border-zinc-100 bg-zinc-50 p-2">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-xs text-zinc-500">{ev.timestamp}</span>
                    <span className="text-xs font-medium text-zinc-600">{ev.event_type}</span>
                  </div>
                  <p className="mt-1 text-zinc-800">{ev.summary}</p>
                  {(ev.price != null || ev.quantity != null) && (
                    <p className="mt-0.5 text-xs text-zinc-500">
                      {ev.price != null && `Harga: ${currency(ev.price)}`}
                      {ev.price != null && ev.quantity != null && " | "}
                      {ev.quantity != null && `Qty: ${ev.quantity}`}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan Perjalanan</span>
          <p className="mt-1 text-zinc-800">{String(tt.journey_summary ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 4. Evaluasi Thesis
  // -----------------------------------------------------------------------
  const thesisSection = (
    <AnalysisSection title="Evaluasi Thesis">
      <div className="space-y-3">
        <AnalysisValue label="Thesis Awal" value={p.final_thesis_evaluation.original_thesis} />
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Status Akhir" value={enumLabel("setup_status", p.final_thesis_evaluation.final_thesis_status)} />
          <AnalysisValue label="Hasil" value={THESIS_OUTCOME_LABEL[p.final_thesis_evaluation.outcome] ?? p.final_thesis_evaluation.outcome} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Thesis Benar" value={displayBool(p.final_thesis_evaluation.thesis_was_correct)} />
          <AnalysisValue label="Alasan Entry Tetap Valid" value={displayBool(p.final_thesis_evaluation.entry_reason_remained_valid)} />
        </div>
        <AnalysisValue label="Kondisi Invalidasi Dihormati" value={displayBool(p.final_thesis_evaluation.invalidation_condition_respected)} />
        {p.final_thesis_evaluation.supporting_evidence.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Bukti Pendukung</span>
            <ul className="mt-1 list-inside list-disc text-green-700">
              {p.final_thesis_evaluation.supporting_evidence.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </div>
        )}
        {p.final_thesis_evaluation.contradicting_evidence.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Bukti Kontradiksi</span>
            <ul className="mt-1 list-inside list-disc text-amber-700">
              {p.final_thesis_evaluation.contradicting_evidence.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </div>
        )}
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.final_thesis_evaluation.summary}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 5. Kualitas Eksekusi
  // -----------------------------------------------------------------------
  const executionSection = (
    <AnalysisSection title="Kualitas Eksekusi">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Keseluruhan" value={EXECUTION_QUALITY_LABEL[String(pee.overall_quality ?? "")] ?? String(pee.overall_quality ?? "—")} />
          <AnalysisValue label="Entry" value={EXECUTION_QUALITY_LABEL[String(pee.entry_quality ?? "")] ?? String(pee.entry_quality ?? "—")} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Manajemen Posisi" value={EXECUTION_QUALITY_LABEL[String(pee.position_management_quality ?? "")] ?? String(pee.position_management_quality ?? "—")} />
          <AnalysisValue label="Exit" value={EXECUTION_QUALITY_LABEL[String(pee.exit_quality ?? "")] ?? String(pee.exit_quality ?? "—")} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Rencana Entry Diikuti" value={displayBool(pee.entry_plan_followed as boolean | null)} />
          <AnalysisValue label="Rencana Stop Loss Diikuti" value={displayBool(pee.stop_loss_plan_followed as boolean | null)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Rencana Target Diikuti" value={displayBool(pee.target_plan_followed as boolean | null)} />
          <AnalysisValue label="Rencana Exit Diikuti" value={displayBool(pee.exit_plan_followed as boolean | null)} />
        </div>
        {(pee.positive_execution_points as string[] ?? []).length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Poin Positif</span>
            <ul className="mt-1 list-inside list-disc text-green-700">
              {(pee.positive_execution_points as string[]).map((pt, i) => <li key={i}>{pt}</li>)}
            </ul>
          </div>
        )}
        {(pee.execution_deviations as string[] ?? []).length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Penyimpangan</span>
            <ul className="mt-1 list-inside list-disc text-amber-700">
              {(pee.execution_deviations as string[]).map((d, i) => <li key={i}>{d}</li>)}
            </ul>
          </div>
        )}
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{String(pee.summary ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 6. Manajemen Risiko
  // -----------------------------------------------------------------------
  const riskSection = (
    <AnalysisSection title="Manajemen Risiko">
      <div className="space-y-3">
        <AnalysisValue label="Kualitas" value={EXECUTION_QUALITY_LABEL[String(rme.quality ?? "")] ?? String(rme.quality ?? "—")} />
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Risiko Awal" value={percentage(rme.initial_risk_percentage as number | null)} />
          <AnalysisValue label="Batas Rugi Dihormati" value={displayBool(rme.maximum_loss_limit_respected as boolean | null)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Stop Loss Digunakan" value={displayBool(rme.stop_loss_used as boolean | null)} />
          <AnalysisValue label="Stop Loss Dihormati" value={displayBool(rme.stop_loss_respected as boolean | null)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Profit Terlindungi" value={displayBool(rme.profit_protected as boolean | null)} />
          <AnalysisValue label="Partial Exit Digunakan" value={displayBool(rme.partial_exit_used as boolean | null)} />
        </div>
        <AnalysisValue label="Risiko Meningkat Tanpa Konfirmasi" value={displayBool(rme.risk_increased_without_confirmation as boolean | null)} />
        {(rme.strengths as string[] ?? []).length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Kekuatan</span>
            <ul className="mt-1 list-inside list-disc text-green-700">
              {(rme.strengths as string[]).map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </div>
        )}
        {(rme.weaknesses as string[] ?? []).length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Kelemahan</span>
            <ul className="mt-1 list-inside list-disc text-amber-700">
              {(rme.weaknesses as string[]).map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{String(rme.summary ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 7. Yang Berjalan Baik & Tidak Berjalan Baik
  // -----------------------------------------------------------------------
  const workedSection = (
    <AnalysisSection title="Yang Berjalan Baik & Tidak Berjalan Baik">
      <div className="space-y-3">
        {p.what_worked.length > 0 ? (
          <div className="text-sm">
            <span className="text-zinc-400">Berjalan Baik</span>
            <ul className="mt-1 list-inside list-disc text-green-700">
              {p.what_worked.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        ) : (
          <p className="text-xs text-zinc-400">Tidak ada data.</p>
        )}
        {p.what_did_not_work.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Tidak Berjalan Baik</span>
            <ul className="mt-1 list-inside list-disc text-amber-700">
              {p.what_did_not_work.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}
        {p.future_improvements.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Perbaikan ke Depan</span>
            <ul className="mt-1 list-inside list-disc text-blue-700">
              {p.future_improvements.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 8. Kesalahan yang Bisa Dihindari
  // -----------------------------------------------------------------------
  const mistakesSection = (
    <AnalysisSection title="Kesalahan yang Bisa Dihindari">
      <div className="space-y-3">
        {p.avoidable_mistakes.length === 0 ? (
          <p className="text-xs text-zinc-400">Tidak ada kesalahan yang teridentifikasi.</p>
        ) : (
          p.avoidable_mistakes.map((m, i) => (
            <div key={i} className="rounded border border-red-100 bg-red-50 p-2 text-sm">
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-medium text-red-800">{m.category}</span>
                <span className="text-xs text-red-600">{m.severity}</span>
              </div>
              <p className="mt-1 text-red-800">{m.description}</p>
              <p className="mt-0.5 text-xs text-red-600">Dampak: {m.impact}</p>
              <p className="mt-0.5 text-xs text-red-600">Cara menghindari: {m.how_to_avoid}</p>
            </div>
          ))
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 9. Pelajaran yang Dipetik
  // -----------------------------------------------------------------------
  const lessonsSection = (
    <AnalysisSection title="Pelajaran yang Dipetik">
      <div className="space-y-3">
        {p.lessons_learned.map((l, i) => (
          <div key={i} className="rounded border border-green-100 bg-green-50 p-2 text-sm">
            <span className="font-medium text-green-800">{l.category}</span>
            <p className="mt-1 text-green-800">{l.lesson}</p>
            <p className="mt-0.5 text-xs text-green-600">Bukti: {l.evidence}</p>
            <p className="mt-0.5 text-xs text-green-600">Aturan ke depan: {l.future_rule}</p>
          </div>
        ))}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 10. Penilaian Akhir AI
  // -----------------------------------------------------------------------
  const evaluationSection = (
    <AnalysisSection title="Penilaian Akhir AI">
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-100 text-2xl font-bold text-blue-700">
            {p.final_ai_evaluation.trade_grade}
          </div>
          <div className="text-sm">
            <AnalysisValue label="Good Trade" value={displayBool(p.final_ai_evaluation.good_trade)} />
            <AnalysisValue label="Hasil Selaras Proses" value={displayBool(p.final_ai_evaluation.result_aligned_with_process)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Proses" value={percentage(p.final_ai_evaluation.process_score)} />
          <AnalysisValue label="Thesis" value={percentage(p.final_ai_evaluation.thesis_score)} />
          <AnalysisValue label="Eksekusi" value={percentage(p.final_ai_evaluation.execution_score)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Manajemen Risiko" value={percentage(p.final_ai_evaluation.risk_management_score)} />
          <AnalysisValue label="Hasil" value={percentage(p.final_ai_evaluation.result_score)} />
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.final_ai_evaluation.summary}</p>
        </div>
        <p className="text-xs italic text-zinc-400">
          Estimasi AI, bukan kepastian.
        </p>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 11. Ringkasan Jurnal
  // -----------------------------------------------------------------------
  const journalSection = (
    <AnalysisSection title="Ringkasan Jurnal">
      <div className="space-y-3">
        <AnalysisValue label="Judul" value={p.journal_summary.title} />
        <div className="text-sm">
          <span className="text-zinc-400">Setup</span>
          <p className="mt-1 text-zinc-800">{p.journal_summary.setup_summary}</p>
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Entry</span>
          <p className="mt-1 text-zinc-800">{p.journal_summary.entry_summary}</p>
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Manajemen</span>
          <p className="mt-1 text-zinc-800">{p.journal_summary.management_summary}</p>
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Exit</span>
          <p className="mt-1 text-zinc-800">{p.journal_summary.exit_summary}</p>
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Hasil</span>
          <p className="mt-1 text-zinc-800">{p.journal_summary.result_summary}</p>
        </div>
        <AnalysisValue label="Pelajaran Utama" value={p.journal_summary.main_lesson} />
        <AnalysisValue label="Review Satu Kalimat" value={p.journal_summary.one_sentence_review} />
        {p.journal_summary.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {p.journal_summary.tags.map((t, i) => (
              <span key={i} className="rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 12. Peringatan
  // -----------------------------------------------------------------------
  const warningsSection = (
    <AnalysisSection title="Peringatan dan Informasi yang Kurang">
      <div className="space-y-3">
        {p.warnings_and_missing_information.warnings.length === 0 &&
        p.warnings_and_missing_information.missing_information.length === 0 ? (
          <p className="text-sm text-zinc-400">Tidak ada peringatan tambahan.</p>
        ) : (
          <>
            {p.warnings_and_missing_information.warnings.length > 0 && (
              <div className="text-sm">
                <span className="text-zinc-400">Peringatan</span>
                <ul className="mt-1 list-inside list-disc text-amber-700">
                  {p.warnings_and_missing_information.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}
            {p.warnings_and_missing_information.missing_information.length > 0 && (
              <div className="text-sm">
                <span className="text-zinc-400">Informasi Tidak Tersedia</span>
                <ul className="mt-1 list-inside list-disc text-zinc-600">
                  {p.warnings_and_missing_information.missing_information.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div className="space-y-4">
      {closingSection}
      {resultSection}
      {timelineSection}
      {thesisSection}
      {executionSection}
      {riskSection}
      {workedSection}
      {mistakesSection}
      {lessonsSection}
      {evaluationSection}
      {journalSection}
      {warningsSection}
    </div>
  );
}
