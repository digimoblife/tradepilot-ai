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

interface PositionAssessment {
  summary: string;
  entry_price: number | null;
  current_price: number | null;
  remaining_quantity: number | null;
  active_stop_loss: number | null;
  active_target: number | null;
  unrealized_profit_loss: number | null;
  unrealized_return_percentage: number | null;
  distance_to_stop_percentage: number | null;
  distance_to_target_percentage: number | null;
  holding_duration_days: number | null;
  health: string;
}

interface ThesisAssessment {
  summary: string;
  status: string;
  remains_valid: boolean;
  strengthening_evidence: string[];
  weakening_evidence: string[];
  invalidation_condition: string;
  invalidation_price: number | null;
  invalidation_triggered: boolean;
}

interface TargetAssessment {
  distance_to_target_percentage: number | null;
  summary: string;
  target_price: number | null;
  still_realistic: boolean;
  realism: string;
  target_probability: number | null;
  primary_obstacle: string | null;
  required_condition: string | null;
  revised_target_proposed: boolean;
  proposed_target: number | null;
}

interface StopLossAssessment {
  distance_to_stop_percentage: number | null;
  summary: string;
  stop_loss_price: number | null;
  still_appropriate: boolean;
  approached: boolean;
  triggered: boolean;
  risk_if_unchanged: string | null;
  revised_stop_proposed: boolean;
  proposed_stop_loss: number | null;
}

interface TradingPlan {
  current_action: string;
  action_rationale: string;
  plan_for_next_session: string | null;
  hold_condition: string | null;
  reduce_risk_condition: string | null;
  exit_condition: string | null;
  add_position_condition: string | null;
  levels_to_monitor: string[];
  requires_user_confirmation: boolean;
}

interface AiAssessment {
  target_probability: number | null;
  summary: string;
  bias: string;
  confidence: number | null;
  bullish_probability: number | null;
  downside_probability: number | null;
  risk_level: string;
}

interface OpenPositionUpdatePayload {
  metadata: Record<string, unknown>;
  update_period: string;
  comparison: Comparison;
  evidence_summary: Record<string, unknown>;
  market_snapshot: Record<string, unknown>;
  today_summary: Record<string, unknown>;
  orderbook_analysis: Record<string, unknown>;
  chart_update: Record<string, unknown>;
  position_assessment: PositionAssessment;
  thesis_assessment: ThesisAssessment;
  target_assessment: TargetAssessment;
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
// Component
// ---------------------------------------------------------------------------

type LoadState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string; retry: () => void }
  | { status: "loaded"; payload: OpenPositionUpdatePayload };

interface Props {
  sessionId: string;
  onEmpty?: () => void;
  onLoaded?: () => void;
}

export function OpenPositionUpdateView({ sessionId, onEmpty, onLoaded }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const cancelledRef = useRef(false);

  const load = useCallback(async function loadFn() {
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      const list = await listAnalyses(sessionId, {
        analysis_type: "OPEN_POSITION_UPDATE",
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
          payload: detail.payload as unknown as OpenPositionUpdatePayload,
        });
      }
    } catch (e: unknown) {
      if (cancelledRef.current) return;
      if (e instanceof AuthenticationError) {
        setState({
          status: "error",
          message: "Silakan masuk terlebih dahulu untuk melihat pembaruan posisi.",
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
          message: "Gagal memuat pembaruan posisi. Silakan coba lagi.",
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
        <p className="text-sm text-zinc-500">Memuat pembaruan posisi…</p>
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
  const ts = p.today_summary as Record<string, unknown>;
  const ms = p.market_snapshot as Record<string, unknown>;
  const ob = p.orderbook_analysis as Record<string, unknown>;

  // -----------------------------------------------------------------------
  // 1. Ringkasan Hari Ini
  // -----------------------------------------------------------------------
  const marketSection = (
    <AnalysisSection title="Ringkasan Hari Ini">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Open" value={ts.open as number | null} />
          <AnalysisValue label="High" value={ts.high as number | null} />
          <AnalysisValue label="Low" value={ts.low as number | null} />
          <AnalysisValue label="Last / Close" value={ts.last_or_close as number | null} />
          <AnalysisValue label="Rata-rata" value={ts.average as number | null} />
          <AnalysisValue label="Perubahan (%)" value={percentage(ts.change_percentage as number | null)} />
        </div>
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{String(ts.summary ?? ms.summary ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 2. Yang Terlihat dari Orderbook
  // -----------------------------------------------------------------------
  const orderbookSection = (
    <AnalysisSection title="Yang Terlihat dari Orderbook">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Kekuatan Buyer" value={enumLabel("buyer_strength", ob.buyer_strength as string | null)} />
          <AnalysisValue label="Tekanan Seller" value={enumLabel("seller_pressure", ob.seller_pressure as string | null)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Best Bid" value={ob.best_bid as number | null} />
          <AnalysisValue label="Best Offer" value={ob.best_offer as number | null} />
        </div>
        <AnalysisValue label="Observasi Spread" value={ob.spread_observation as string | null} />
        {!!ob.bid_support && (
          <div className="text-sm">
            <span className="text-zinc-400">Support Bid</span>
            <p className="text-zinc-800">
              {(ob.bid_support as PriceLevel).price as number} — {(ob.bid_support as PriceLevel).summary as string}
            </p>
          </div>
        )}
        {!!ob.offer_resistance && (
          <div className="text-sm">
            <span className="text-zinc-400">Resistance Offer</span>
            <p className="text-zinc-800">
              {(ob.offer_resistance as PriceLevel).price as number} — {(ob.offer_resistance as PriceLevel).summary as string}
            </p>
          </div>
        )}
        {((ob.buyer_observations as string[]) ?? []).length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Observasi Buyer</span>
            <ul className="mt-1 list-inside list-disc text-zinc-800">
              {(ob.buyer_observations as string[]).map((o: string, i: number) => <li key={i}>{o}</li>)}
            </ul>
          </div>
        )}
        {((ob.seller_observations as string[]) ?? []).length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Observasi Seller</span>
            <ul className="mt-1 list-inside list-disc text-zinc-800">
              {(ob.seller_observations as string[]).map((o: string, i: number) => <li key={i}>{o}</li>)}
            </ul>
          </div>
        )}
        <AnalysisValue label="Mendukung Posisi" value={displayBool(ob.supports_position as boolean | null)} />
        <div className="text-sm">
          <span className="text-zinc-400">Kesimpulan</span>
          <p className="mt-1 text-zinc-800">{String(ob.conclusion ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 3. Kondisi Posisi Saat Ini
  // -----------------------------------------------------------------------
  const positionSection = (
    <AnalysisSection title="Kondisi Posisi Saat Ini">
      <div className="space-y-3">
        <p className="text-xs italic text-zinc-400">
          Penilaian AI terhadap posisi terkonfirmasi.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Kesehatan Posisi" value={enumLabel("setup_status", p.position_assessment.health)} />
          <AnalysisValue label="Harga Saat Ini" value={currency(p.position_assessment.current_price)} />
          <AnalysisValue label="Harga Entry" value={currency(p.position_assessment.entry_price)} />
          <AnalysisValue label="Unrealized P&L" value={currency(p.position_assessment.unrealized_profit_loss)} />
          <AnalysisValue label="Unrealized Return" value={percentage(p.position_assessment.unrealized_return_percentage)} />
          <AnalysisValue label="Durasi (hari)" value={p.position_assessment.holding_duration_days} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Jarak ke Stop" value={percentage(p.position_assessment.distance_to_stop_percentage)} />
          <AnalysisValue label="Jarak ke Target" value={percentage(p.position_assessment.distance_to_target_percentage)} />
        </div>
        <AnalysisValue label="Ringkasan" value={p.position_assessment.summary} />

        <AnalysisValue label="Status Thesis" value={enumLabel("setup_status", p.thesis_assessment.status)} />
        <AnalysisValue label="Thesis Masih Valid" value={displayBool(p.thesis_assessment.remains_valid)} />
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan Thesis</span>
          <p className="mt-1 text-zinc-800">{p.thesis_assessment.summary}</p>
        </div>
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
  // 4. Apakah Target Profit Masih Realistis?
  // -----------------------------------------------------------------------
  const targetSection = (
    <AnalysisSection title="Apakah Target Profit Masih Realistis?">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-2">
          <AnalysisValue label="Target Aktif" value={currency(p.target_assessment.target_price)} />
          <AnalysisValue label="Target Masih Realistis" value={displayBool(p.target_assessment.still_realistic)} />
        </div>
        <AnalysisValue label="Probabilitas Target" value={percentage(p.target_assessment.target_probability)} />
        <AnalysisValue label="Jarak ke Target" value={percentage(p.target_assessment.distance_to_target_percentage)} />
        <AnalysisValue label="Hambatan Utama" value={p.target_assessment.primary_obstacle ?? "—"} />
        <AnalysisValue label="Kondisi yang Diperlukan" value={p.target_assessment.required_condition ?? "—"} />
        <AnalysisValue label="Realisme" value={enumLabel("setup_status", p.target_assessment.realism)} />
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.target_assessment.summary}</p>
        </div>

        {p.target_assessment.revised_target_proposed && p.target_assessment.proposed_target != null && (
          <div className="rounded border border-amber-200 bg-amber-50 p-2 text-sm">
            <span className="font-medium text-amber-700">Usulan Target Baru: </span>
            {currency(p.target_assessment.proposed_target)}
            <p className="mt-1 text-xs italic text-zinc-500">Usulan AI — belum terkonfirmasi.</p>
          </div>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 5. Status Stop Loss
  // -----------------------------------------------------------------------
  const stopSection = (
    <AnalysisSection title="Status Stop Loss">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-2">
          <AnalysisValue label="Stop Loss Aktif" value={currency(p.stop_loss_assessment.stop_loss_price)} />
          <AnalysisValue label="Masih Tepat" value={displayBool(p.stop_loss_assessment.still_appropriate)} />
        </div>
        <AnalysisValue label="Jarak ke Stop" value={percentage(p.stop_loss_assessment.distance_to_stop_percentage)} />
        <AnalysisValue label="Stop Mendekat" value={displayBool(p.stop_loss_assessment.approached)} />
        <AnalysisValue label="Stop Tersentuh" value={displayBool(p.stop_loss_assessment.triggered)} />
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
  // 6. Trading Plan Selanjutnya
  // -----------------------------------------------------------------------
  const planSection = (
    <AnalysisSection title="Trading Plan Selanjutnya">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Tindakan" value={enumLabel("recommended_action", p.trading_plan.current_action)} />
          <AnalysisValue label="Konfirmasi Diperlukan" value={displayBool(p.trading_plan.requires_user_confirmation)} />
        </div>
        <AnalysisValue label="Alasan" value={p.trading_plan.action_rationale} />
        <AnalysisValue label="Kondisi Hold" value={p.trading_plan.hold_condition ?? "—"} />
        <AnalysisValue label="Kondisi Kurangi Risiko" value={p.trading_plan.reduce_risk_condition ?? "—"} />
        <AnalysisValue label="Kondisi Exit" value={p.trading_plan.exit_condition ?? "—"} />
        <AnalysisValue label="Rencana Sesi Berikutnya" value={p.trading_plan.plan_for_next_session ?? "—"} />
        {p.trading_plan.add_position_condition && (
          <AnalysisValue label="Syarat Tambah Posisi" value={p.trading_plan.add_position_condition} />
        )}
        {p.trading_plan.levels_to_monitor.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Level yang Dipantau</span>
            <ul className="mt-1 list-inside list-disc text-zinc-800">
              {p.trading_plan.levels_to_monitor.map((l, i) => <li key={i}>{l}</li>)}
            </ul>
          </div>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 7. Penilaian AI Saat Ini
  // -----------------------------------------------------------------------
  const aiSection = (
    <AnalysisSection title="Penilaian AI Saat Ini">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Bias" value={enumLabel("bias", p.ai_assessment.bias)} />
          <AnalysisValue label="Keyakinan" value={percentage(p.ai_assessment.confidence)} />
          <AnalysisValue label="Tingkat Risiko" value={enumLabel("risk_level", p.ai_assessment.risk_level)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Probabilitas Bullish" value={percentage(p.ai_assessment.bullish_probability)} />
          <AnalysisValue label="Probabilitas Downside" value={percentage(p.ai_assessment.downside_probability)} />
        </div>
        <AnalysisValue label="Probabilitas Target" value={percentage(p.ai_assessment.target_probability)} />
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
  // 8. Perubahan Material
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
  // 9. Peringatan
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
      {orderbookSection}
      {positionSection}
      {targetSection}
      {stopSection}
      {planSection}
      {aiSection}
      {changesSection}
      {warningsSection}
    </div>
  );
}
