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

interface PriceLevel {
  price: number;
  label: string;
  summary: string;
}

interface Comparison {
  comparison_available: boolean;
  previous_analysis_id: string | null;
  previous_analysis_type: string | null;
  previous_analysis_timestamp: string | null;
  previous_update_period: string | null;
  summary: string;
}

interface RemainingPositionAssessment {
  entry_price: number;
  current_price: number;
  original_quantity: number;
  exited_quantity: number;
  remaining_quantity: number;
  active_stop_loss: number | null;
  active_target: number | null;
  realized_profit_loss: number;
  unrealized_profit_loss: number | null;
  unrealized_return_percentage: number | null;
  total_trade_profit_loss: number | null;
  total_trade_return_percentage: number | null;
  distance_to_stop_percentage: number | null;
  distance_to_target_percentage: number | null;
  health: string;
  summary: string;
}

interface ThesisAssessment {
  status: string;
  remains_valid: boolean;
  summary: string;
  strengthening_evidence: string[];
  weakening_evidence: string[];
  partial_exit_effect: string;
  invalidation_condition: string;
  invalidation_price: number | null;
  invalidation_triggered: boolean;
}

interface RemainingTargetAssessment {
  current_target: number | null;
  still_realistic: boolean | null;
  realism: string;
  target_probability: number | null;
  distance_to_target_percentage: number | null;
  primary_obstacle: string | null;
  required_condition: string | null;
  revised_target_proposed: boolean;
  proposed_target: number | null;
  summary: string;
}

interface StopLossAssessment {
  current_stop_loss: number | null;
  still_appropriate: boolean | null;
  distance_to_stop_percentage: number | null;
  move_to_break_even_possible: boolean | null;
  profit_protection_possible: boolean | null;
  revised_stop_proposed: boolean;
  proposed_stop_loss: number | null;
  risk_if_unchanged: string;
  summary: string;
}

interface TradingPlan {
  current_action: string;
  action_rationale: string;
  plan_for_remaining_position: string;
  hold_condition: string | null;
  protect_profit_condition: string | null;
  second_partial_exit_condition: string | null;
  full_exit_condition: string;
  levels_to_monitor: PriceLevel[];
  requires_user_confirmation: boolean;
}

interface AiAssessment {
  bias: string;
  confidence: number | null;
  bullish_probability: number | null;
  remaining_target_probability: number | null;
  downside_probability: number | null;
  full_exit_probability: number | null;
  risk_level: string;
  remaining_position_worth_holding: boolean;
  summary: string;
}

interface PartialExitReviewPayload {
  metadata: Record<string, unknown>;
  update_period: string;
  comparison: Comparison;
  evidence_summary: Record<string, unknown>;
  market_snapshot: Record<string, unknown>;
  partial_exit_confirmation: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  orderbook_analysis: Record<string, unknown>;
  chart_update: Record<string, unknown>;
  remaining_position_assessment: RemainingPositionAssessment;
  thesis_assessment: ThesisAssessment;
  remaining_target_assessment: RemainingTargetAssessment;
  stop_loss_assessment: StopLossAssessment;
  trading_plan: TradingPlan;
  ai_assessment: AiAssessment;
  changes_from_previous: unknown[];
  warnings_and_missing_information: {
    missing_information: string[];
    warnings: string[];
  };
}

// ---------------------------------------------------------------------------
// Local label maps
// ---------------------------------------------------------------------------

const EXIT_REASON_LABEL: Record<string, string> = {
  PARTIAL_TAKE_PROFIT: "Partial Take Profit",
  RISK_REDUCTION: "Pengurangan Risiko",
  RESISTANCE_REACHED: "Resistance Tercapai",
  MOMENTUM_WEAKENING: "Momentum Melemah",
  USER_DECISION: "Keputusan User",
  OTHER: "Lainnya",
};

const PARTIAL_EXIT_EFFECT_LABEL: Record<string, string> = {
  RISK_SIGNIFICANTLY_REDUCED: "Risiko Berkurang Signifikan",
  RISK_REDUCED: "Risiko Berkurang",
  NEUTRAL: "Netral",
  REMAINING_POSITION_STILL_HIGH_RISK: "Sisa Posisi Masih Berisiko Tinggi",
  UNKNOWN: "Tidak Diketahui",
};

const TARGET_REALISM_LABEL: Record<string, string> = {
  REALISTIC: "Realistis",
  POSSIBLE_BUT_CHALLENGING: "Mungkin tetapi Menantang",
  UNLIKELY: "Tidak Mungkin",
  NO_LONGER_REALISTIC: "Tidak Lagi Realistis",
  UNCERTAIN: "Tidak Pasti",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type LoadState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string; retry: () => void }
  | { status: "loaded"; payload: PartialExitReviewPayload };

interface Props {
  sessionId: string;
  onEmpty?: () => void;
  onLoaded?: () => void;
}

export function PartialExitReviewView({ sessionId, onEmpty, onLoaded }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const cancelledRef = useRef(false);

  const load = useCallback(async function loadFn() {
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const list = await listAnalyses(sessionId, {
        analysis_type: "PARTIAL_EXIT_REVIEW",
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
          payload: detail.payload as unknown as PartialExitReviewPayload,
        });
      }
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      if (e instanceof AuthenticationError) {
        setState({
          status: "error",
          message: "Silakan masuk terlebih dahulu untuk melihat review partial exit.",
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
          message: "Gagal memuat review partial exit. Silakan coba lagi.",
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
        <p className="text-sm text-zinc-500">Memuat review partial exit…</p>
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

  // Helper: access unknown fields from Record<string, unknown>
  const ms = p.market_snapshot as Record<string, unknown>;
  const px = p.partial_exit_confirmation as Record<string, unknown>;
  const rs = p.result_summary as Record<string, unknown>;

  // -----------------------------------------------------------------------
  // 1. Ringkasan Hari Ini
  // -----------------------------------------------------------------------
  const marketSection = (
    <AnalysisSection title="Ringkasan Hari Ini">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Open" value={ms.open as number | null} />
          <AnalysisValue label="High" value={ms.high as number | null} />
          <AnalysisValue label="Low" value={ms.low as number | null} />
          <AnalysisValue label="Last / Close" value={ms.last as number | null} />
          <AnalysisValue label="Rata-rata" value={ms.average as number | null} />
          <AnalysisValue label="Perubahan (%)" value={percentage(ms.change_percentage as number | null)} />
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{String(ms.summary ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 2. Eksekusi Partial Exit
  // -----------------------------------------------------------------------
  const exitSection = (
    <AnalysisSection title="Eksekusi Partial Exit">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Harga Exit" value={currency(px.exit_price as number | null)} />
          <AnalysisValue label="Waktu Exit" value={String(px.exit_timestamp ?? "—")} />
          <AnalysisValue label="Qty Terjual" value={px.exited_quantity as number | null} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Sisa Qty" value={px.remaining_quantity as number | null} />
          <AnalysisValue
            label="Alasan Exit"
            value={EXIT_REASON_LABEL[String(px.exit_reason ?? "")] ?? String(px.exit_reason ?? "—")}
          />
        </div>
        {(px.user_note as string | null) && (
          <AnalysisValue label="Catatan User" value={String(px.user_note)} />
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 3. Ringkasan Hasil Realisasi
  // -----------------------------------------------------------------------
  const resultSection = (
    <AnalysisSection title="Ringkasan Hasil Realisasi">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Harga Entry" value={currency(rs.entry_price as number | null)} />
          <AnalysisValue label="Harga Exit" value={currency(rs.partial_exit_price as number | null)} />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Realized P&L" value={currency(rs.realized_profit_loss as number | null)} />
          <AnalysisValue label="Realized Return" value={percentage(rs.realized_return_percentage as number | null)} />
          <AnalysisValue label="Modal Kembali" value={percentage(rs.capital_recovered_percentage as number | null)} />
        </div>
        <AnalysisValue label="Risiko Berkurang" value={displayBool(rs.original_risk_reduced as boolean | null)} />
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{String(rs.summary ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 4. Kondisi Posisi Tersisa
  // -----------------------------------------------------------------------
  const positionSection = (
    <AnalysisSection title="Kondisi Posisi Tersisa">
      <div className="space-y-3">
        <p className="text-xs italic text-zinc-400">
          Penilaian terhadap sisa posisi setelah partial exit.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Kesehatan" value={enumLabel("setup_status", p.remaining_position_assessment.health)} />
          <AnalysisValue label="Harga Entry" value={currency(p.remaining_position_assessment.entry_price)} />
          <AnalysisValue label="Harga Saat Ini" value={currency(p.remaining_position_assessment.current_price)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Qty Awal" value={p.remaining_position_assessment.original_quantity} />
          <AnalysisValue label="Qty Terjual" value={p.remaining_position_assessment.exited_quantity} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Sisa Qty" value={p.remaining_position_assessment.remaining_quantity} />
          <AnalysisValue label="Stop Loss Aktif" value={currency(p.remaining_position_assessment.active_stop_loss)} />
        </div>
        <AnalysisValue label="Target Aktif" value={currency(p.remaining_position_assessment.active_target)} />
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Realized P&L" value={currency(p.remaining_position_assessment.realized_profit_loss)} />
          <AnalysisValue label="Unrealized P&L" value={currency(p.remaining_position_assessment.unrealized_profit_loss)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Total P&L Trade" value={currency(p.remaining_position_assessment.total_trade_profit_loss)} />
          <AnalysisValue label="Total Return" value={percentage(p.remaining_position_assessment.total_trade_return_percentage)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Jarak ke Stop" value={percentage(p.remaining_position_assessment.distance_to_stop_percentage)} />
          <AnalysisValue label="Jarak ke Target" value={percentage(p.remaining_position_assessment.distance_to_target_percentage)} />
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.remaining_position_assessment.summary}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 5. Penilaian Thesis
  // -----------------------------------------------------------------------
  const thesisSection = (
    <AnalysisSection title="Penilaian Thesis">
      <div className="space-y-3">
        <AnalysisValue label="Status" value={enumLabel("setup_status", p.thesis_assessment.status)} />
        <AnalysisValue label="Thesis Masih Valid" value={displayBool(p.thesis_assessment.remains_valid)} />
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.thesis_assessment.summary}</p>
        </div>
        <AnalysisValue
          label="Efek Partial Exit"
          value={PARTIAL_EXIT_EFFECT_LABEL[p.thesis_assessment.partial_exit_effect] ?? p.thesis_assessment.partial_exit_effect}
        />
        {p.thesis_assessment.strengthening_evidence.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Bukti Penguat</span>
            <ul className="mt-1 list-inside list-disc text-green-700">
              {p.thesis_assessment.strengthening_evidence.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </div>
        )}
        {p.thesis_assessment.weakening_evidence.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Bukti Pelemah</span>
            <ul className="mt-1 list-inside list-disc text-amber-700">
              {p.thesis_assessment.weakening_evidence.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </div>
        )}
        <AnalysisValue label="Kondisi Invalidasi" value={p.thesis_assessment.invalidation_condition} />
        <AnalysisValue label="Invalidasi Terpicu" value={displayBool(p.thesis_assessment.invalidation_triggered)} />
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 6. Apakah Target Masih Realistis?
  // -----------------------------------------------------------------------
  const targetSection = (
    <AnalysisSection title="Apakah Target Masih Realistis?">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Target Aktif" value={currency(p.remaining_target_assessment.current_target)} />
          <AnalysisValue label="Masih Realistis" value={displayBool(p.remaining_target_assessment.still_realistic)} />
        </div>
        <AnalysisValue label="Probabilitas Target" value={percentage(p.remaining_target_assessment.target_probability)} />
        <AnalysisValue label="Jarak ke Target" value={percentage(p.remaining_target_assessment.distance_to_target_percentage)} />
        <AnalysisValue label="Hambatan Utama" value={p.remaining_target_assessment.primary_obstacle ?? "—"} />
        <AnalysisValue label="Kondisi Diperlukan" value={p.remaining_target_assessment.required_condition ?? "—"} />
        <AnalysisValue
          label="Realisme"
          value={TARGET_REALISM_LABEL[p.remaining_target_assessment.realism] ?? p.remaining_target_assessment.realism}
        />
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.remaining_target_assessment.summary}</p>
        </div>

        {p.remaining_target_assessment.revised_target_proposed && p.remaining_target_assessment.proposed_target != null && (
          <div className="rounded border border-amber-200 bg-amber-50 p-2 text-sm">
            <span className="font-medium text-amber-700">Usulan Target Baru: </span>
            {currency(p.remaining_target_assessment.proposed_target)}
            <p className="mt-1 text-xs italic text-zinc-500">Usulan AI — belum terkonfirmasi.</p>
          </div>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 7. Status Stop Loss
  // -----------------------------------------------------------------------
  const stopSection = (
    <AnalysisSection title="Status Stop Loss">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Stop Loss Aktif" value={currency(p.stop_loss_assessment.current_stop_loss)} />
          <AnalysisValue label="Masih Tepat" value={displayBool(p.stop_loss_assessment.still_appropriate)} />
        </div>
        <AnalysisValue label="Jarak ke Stop" value={percentage(p.stop_loss_assessment.distance_to_stop_percentage)} />
        <AnalysisValue label="Break Even Memungkinkan" value={displayBool(p.stop_loss_assessment.move_to_break_even_possible)} />
        <AnalysisValue label="Proteksi Profit" value={displayBool(p.stop_loss_assessment.profit_protection_possible)} />
        <AnalysisValue label="Risiko Jika Tidak Diubah" value={enumLabel("chase_risk", p.stop_loss_assessment.risk_if_unchanged)} />
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.stop_loss_assessment.summary}</p>
        </div>

        {p.stop_loss_assessment.revised_stop_proposed && p.stop_loss_assessment.proposed_stop_loss != null && (
          <div className="rounded border border-amber-200 bg-amber-50 p-2 text-sm">
            <span className="font-medium text-amber-700">Usulan Stop Loss Baru: </span>
            {currency(p.stop_loss_assessment.proposed_stop_loss)}
            <p className="mt-1 text-xs italic text-zinc-500">Usulan AI — belum terkonfirmasi.</p>
          </div>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 8. Trading Plan Sisa Posisi
  // -----------------------------------------------------------------------
  const planSection = (
    <AnalysisSection title="Trading Plan Sisa Posisi">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Tindakan" value={enumLabel("recommended_action", p.trading_plan.current_action)} />
          <AnalysisValue label="Konfirmasi Diperlukan" value={displayBool(p.trading_plan.requires_user_confirmation)} />
        </div>
        <AnalysisValue label="Alasan" value={p.trading_plan.action_rationale} />
        <AnalysisValue label="Rencana Sisa Posisi" value={p.trading_plan.plan_for_remaining_position} />
        <AnalysisValue label="Kondisi Hold" value={p.trading_plan.hold_condition ?? "—"} />
        <AnalysisValue label="Proteksi Profit" value={p.trading_plan.protect_profit_condition ?? "—"} />
        <AnalysisValue label="Syarat Partial Exit Kedua" value={p.trading_plan.second_partial_exit_condition ?? "—"} />
        <AnalysisValue label="Syarat Full Exit" value={p.trading_plan.full_exit_condition} />
        {p.trading_plan.levels_to_monitor.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Level yang Dipantau</span>
            <ul className="mt-1 list-inside list-disc text-zinc-800">
              {p.trading_plan.levels_to_monitor.map((l, i) => (
                <li key={i}>
                  {l.price} — {l.label}{l.summary ? `: ${l.summary}` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 9. Penilaian AI
  // -----------------------------------------------------------------------
  const aiSection = (
    <AnalysisSection title="Penilaian AI">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Bias" value={enumLabel("bias", p.ai_assessment.bias)} />
          <AnalysisValue label="Keyakinan" value={percentage(p.ai_assessment.confidence)} />
          <AnalysisValue label="Tingkat Risiko" value={enumLabel("risk_level", p.ai_assessment.risk_level)} />
        </div>
        <AnalysisValue label="Layak Dipertahankan" value={displayBool(p.ai_assessment.remaining_position_worth_holding)} />
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Prob. Bullish" value={percentage(p.ai_assessment.bullish_probability)} />
          <AnalysisValue label="Prob. Downside" value={percentage(p.ai_assessment.downside_probability)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Prob. Target Tersisa" value={percentage(p.ai_assessment.remaining_target_probability)} />
          <AnalysisValue label="Prob. Full Exit" value={percentage(p.ai_assessment.full_exit_probability)} />
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.ai_assessment.summary}</p>
        </div>
        <p className="text-xs italic text-zinc-400">
          Estimasi AI, bukan kepastian.
        </p>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 10. Perubahan Material
  // -----------------------------------------------------------------------
  const changesSection = (
    <AnalysisSection title="Perubahan Material dari Update Sebelumnya">
      <div className="space-y-3">
        <AnalysisValue label="Perbandingan Tersedia" value={displayBool(p.comparison.comparison_available)} />
        {p.comparison.previous_analysis_type && (
          <AnalysisValue label="Analisis Sebelumnya" value={p.comparison.previous_analysis_type} />
        )}
        {p.comparison.previous_update_period && (
          <AnalysisValue label="Periode Sebelumnya" value={p.comparison.previous_update_period} />
        )}
        {p.changes_from_previous.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Perubahan</span>
            <ul className="mt-1 list-inside list-disc text-zinc-800">
              {p.changes_from_previous.map((c, i) => <li key={i}>{String(c)}</li>)}
            </ul>
          </div>
        )}
        {p.changes_from_previous.length === 0 && (
          <p className="text-xs text-zinc-400">Tidak ada perubahan material sejak update sebelumnya.</p>
        )}
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan Perbandingan</span>
          <p className="mt-1 text-zinc-800">{p.comparison.summary}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 11. Peringatan
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
      {marketSection}
      {exitSection}
      {resultSection}
      {positionSection}
      {thesisSection}
      {targetSection}
      {stopSection}
      {planSection}
      {aiSection}
      {changesSection}
      {warningsSection}
    </div>
  );
}
