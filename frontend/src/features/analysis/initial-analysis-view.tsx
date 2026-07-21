"use client";

import { useEffect, useState, useCallback } from "react";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { AnalysisDetail } from "@/types/analysis";
import type { InitialAnalysisPayload } from "./types";
import { AnalysisSection } from "./analysis-section";
import { AnalysisValue } from "./analysis-value";
import {
  enumLabel,
  percentage,
  currency,
  displayBool,
} from "./helpers";

type LoadState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string; retry: () => void }
  | { status: "loaded"; payload: InitialAnalysisPayload; detail: AnalysisDetail };

interface Props {
  sessionId: string;
}

export function InitialAnalysisView({ sessionId }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async function loadFn() {
    setState({ status: "loading" });
    try {
      const list = await listAnalyses(sessionId, {
        analysis_type: "INITIAL_ANALYSIS",
      });

      const accepted = list.analyses
        .filter((a) => a.acceptance_status === "ACCEPTED")
        .sort(
          (a, b) =>
            new Date(b.accepted_at ?? b.created_at).getTime() -
            new Date(a.accepted_at ?? a.created_at).getTime(),
        );

      if (accepted.length === 0) {
        setState({ status: "empty" });
        return;
      }

      const latest = accepted[0];
      const detail = await getAnalysis(latest.id);

      if (!detail.payload) {
        setState({ status: "empty" });
        return;
      }

      setState({
        status: "loaded",
        payload: detail.payload as unknown as InitialAnalysisPayload,
        detail,
      });
    } catch (e: unknown) {
      if (e instanceof AuthenticationError) {
        setState({
          status: "error",
          message:
            "Silakan masuk terlebih dahulu untuk melihat analisis.",
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
          message:
            "Gagal memuat analisis. Silakan coba lagi.",
          retry: loadFn,
        });
      }
    }
  }, [sessionId]);

  useEffect(() => {
    load();
  }, [load]);

  if (state.status === "loading") {
    return (
      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <p className="text-sm text-zinc-500">Memuat analisis terbaru…</p>
      </section>
    );
  }

  if (state.status === "empty") {
    return (
      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <p className="text-sm text-zinc-400">
          Belum ada Initial Analysis yang diterima untuk sesi ini.
        </p>
      </section>
    );
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

  const { payload } = state;
  const p = payload;

  return (
    <div className="space-y-4">
      {/* Executive Summary */}
      <AnalysisSection title="Ringkasan Eksekutif">
        <div className="space-y-3">
          <AnalysisValue label="Judul" value={p.executive_summary.headline} />
          <AnalysisValue
            label="Status Setup"
            value={enumLabel("setup_status", p.executive_summary.setup_status)}
          />
          <AnalysisValue
            label="Tindakan yang Direkomendasikan"
            value={enumLabel(
              "recommended_action",
              p.executive_summary.recommended_action,
            )}
          />
          <AnalysisValue
            label="Peluang Utama"
            value={p.executive_summary.main_opportunity}
          />
          <AnalysisValue
            label="Risiko Utama"
            value={p.executive_summary.main_risk}
          />
          <div className="text-sm">
            <span className="text-zinc-400">Ringkasan</span>
            <p className="mt-1 text-zinc-800">
              {p.executive_summary.summary}
            </p>
          </div>
        </div>
      </AnalysisSection>

      {/* Orderbook Analysis */}
      <AnalysisSection title="Analisis Orderbook">
        <div className="space-y-3">
          <AnalysisValue
            label="Kekuatan Buyer"
            value={enumLabel("buyer_strength", p.orderbook_analysis.buyer_strength)}
          />
          <AnalysisValue
            label="Tekanan Seller"
            value={enumLabel("seller_pressure", p.orderbook_analysis.seller_pressure)}
          />
          <div className="grid grid-cols-2 gap-3">
            <AnalysisValue
              label="Best Bid"
              value={p.orderbook_analysis.best_bid}
            />
            <AnalysisValue
              label="Best Offer"
              value={p.orderbook_analysis.best_offer}
            />
          </div>
          {p.orderbook_analysis.bid_support && (
            <div className="text-sm">
              <span className="text-zinc-400">Support Bid</span>
              <p className="text-zinc-800">
                {p.orderbook_analysis.bid_support.price} —{" "}
                {p.orderbook_analysis.bid_support.summary}
              </p>
            </div>
          )}
          {p.orderbook_analysis.offer_resistance && (
            <div className="text-sm">
              <span className="text-zinc-400">Resistance Offer</span>
              <p className="text-zinc-800">
                {p.orderbook_analysis.offer_resistance.price} —{" "}
                {p.orderbook_analysis.offer_resistance.summary}
              </p>
            </div>
          )}
          {p.orderbook_analysis.buyer_observations.length > 0 && (
            <div className="text-sm">
              <span className="text-zinc-400">Observasi Buyer</span>
              <ul className="mt-1 list-inside list-disc text-zinc-800">
                {p.orderbook_analysis.buyer_observations.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            </div>
          )}
          {p.orderbook_analysis.seller_observations.length > 0 && (
            <div className="text-sm">
              <span className="text-zinc-400">Observasi Seller</span>
              <ul className="mt-1 list-inside list-disc text-zinc-800">
                {p.orderbook_analysis.seller_observations.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            </div>
          )}
          <AnalysisValue
            label="Mendukung Entry"
            value={displayBool(p.orderbook_analysis.supports_entry)}
          />
          <div className="text-sm">
            <span className="text-zinc-400">Kesimpulan</span>
            <p className="mt-1 text-zinc-800">
              {p.orderbook_analysis.conclusion}
            </p>
          </div>
          {p.orderbook_analysis.limitations.length > 0 && (
            <div className="text-sm">
              <span className="text-zinc-400">Keterbatasan</span>
              <ul className="mt-1 list-inside list-disc text-zinc-600">
                {p.orderbook_analysis.limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </AnalysisSection>

      {/* 3-Month Chart */}
      <AnalysisSection title="Analisis Chart 3 Bulan">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <AnalysisValue
              label="Tren"
              value={enumLabel("trend", p.chart_3_month_analysis.trend)}
            />
            <AnalysisValue
              label="Momentum"
              value={enumLabel("momentum", p.chart_3_month_analysis.momentum)}
            />
            <AnalysisValue
              label="Volume"
              value={enumLabel(
                "volume_condition",
                p.chart_3_month_analysis.volume_condition,
              )}
            />
            <AnalysisValue
              label="Struktur"
              value={enumLabel(
                "structure_status",
                p.chart_3_month_analysis.structure_status,
              )}
            />
          </div>
          {p.chart_3_month_analysis.nearest_support && (
            <div className="text-sm">
              <span className="text-zinc-400">Support Terdekat</span>
              <p className="text-zinc-800">
                {currency(p.chart_3_month_analysis.nearest_support.price)} —{" "}
                {p.chart_3_month_analysis.nearest_support.summary}
              </p>
            </div>
          )}
          {p.chart_3_month_analysis.nearest_resistance && (
            <div className="text-sm">
              <span className="text-zinc-400">Resistance Terdekat</span>
              <p className="text-zinc-800">
                {currency(p.chart_3_month_analysis.nearest_resistance.price)} —{" "}
                {p.chart_3_month_analysis.nearest_resistance.summary}
              </p>
            </div>
          )}
          <AnalysisValue
            label="Mendukung Setup"
            value={displayBool(p.chart_3_month_analysis.supports_setup)}
          />
          <div className="text-sm">
            <span className="text-zinc-400">Kesimpulan</span>
            <p className="mt-1 text-zinc-800">
              {p.chart_3_month_analysis.conclusion}
            </p>
          </div>
          {p.chart_3_month_analysis.limitations.length > 0 && (
            <div className="text-sm">
              <span className="text-zinc-400">Keterbatasan</span>
              <ul className="mt-1 list-inside list-disc text-zinc-600">
                {p.chart_3_month_analysis.limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </AnalysisSection>

      {/* 6-Month Chart */}
      <AnalysisSection title="Analisis Chart 6 Bulan">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <AnalysisValue
              label="Tren"
              value={enumLabel("trend", p.chart_6_month_analysis.trend)}
            />
            <AnalysisValue
              label="Momentum"
              value={enumLabel("momentum", p.chart_6_month_analysis.momentum)}
            />
            <AnalysisValue
              label="Volume"
              value={enumLabel(
                "volume_condition",
                p.chart_6_month_analysis.volume_condition,
              )}
            />
            <AnalysisValue
              label="Struktur"
              value={enumLabel(
                "structure_status",
                p.chart_6_month_analysis.structure_status,
              )}
            />
          </div>
          {p.chart_6_month_analysis.nearest_support && (
            <div className="text-sm">
              <span className="text-zinc-400">Support Terdekat</span>
              <p className="text-zinc-800">
                {currency(p.chart_6_month_analysis.nearest_support.price)} —{" "}
                {p.chart_6_month_analysis.nearest_support.summary}
              </p>
            </div>
          )}
          {p.chart_6_month_analysis.nearest_resistance && (
            <div className="text-sm">
              <span className="text-zinc-400">Resistance Terdekat</span>
              <p className="text-zinc-800">
                {currency(p.chart_6_month_analysis.nearest_resistance.price)} —{" "}
                {p.chart_6_month_analysis.nearest_resistance.summary}
              </p>
            </div>
          )}
          <div className="text-sm">
            <span className="text-zinc-400">Kesimpulan</span>
            <p className="mt-1 text-zinc-800">
              {p.chart_6_month_analysis.conclusion}
            </p>
          </div>
          {p.chart_6_month_analysis.limitations.length > 0 && (
            <div className="text-sm">
              <span className="text-zinc-400">Keterbatasan</span>
              <ul className="mt-1 list-inside list-disc text-zinc-600">
                {p.chart_6_month_analysis.limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </AnalysisSection>

      {/* Combined Chart Assessment */}
      <AnalysisSection title="Analisis Gabungan Chart">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <AnalysisValue
              label="Alignment"
              value={enumLabel(
                "multi_timeframe_alignment",
                p.combined_chart_analysis.multi_timeframe_alignment,
              )}
            />
            <AnalysisValue
              label="Tren Jangka Pendek"
              value={enumLabel(
                "short_term_trend",
                p.combined_chart_analysis.short_term_trend,
              )}
            />
            <AnalysisValue
              label="Tren Jangka Menengah"
              value={enumLabel(
                "medium_term_trend",
                p.combined_chart_analysis.medium_term_trend,
              )}
            />
            <AnalysisValue
              label="Struktur Dominan"
              value={enumLabel(
                "dominant_structure",
                p.combined_chart_analysis.dominant_structure,
              )}
            />
            <AnalysisValue
              label="Konfirmasi Utama"
              value={enumLabel(
                "main_confirmation",
                p.combined_chart_analysis.main_confirmation,
              )}
            />
            <AnalysisValue
              label="Konflik Utama"
              value={enumLabel(
                "main_conflict",
                p.combined_chart_analysis.main_conflict,
              )}
            />
          </div>
          <AnalysisValue
            label="Setup Didukung"
            value={displayBool(p.combined_chart_analysis.setup_supported)}
          />
          <div className="text-sm">
            <span className="text-zinc-400">Kesimpulan</span>
            <p className="mt-1 text-zinc-800">
              {p.combined_chart_analysis.conclusion}
            </p>
          </div>
        </div>
      </AnalysisSection>

      {/* Support dan Resistance */}
      <AnalysisSection title="Support dan Resistance">
        <div className="space-y-3">
          {p.price_levels.supports.length > 0 && (
            <div>
              <span className="text-xs font-medium uppercase tracking-wide text-green-600">
                Support
              </span>
              <ul className="mt-1 space-y-1">
                {p.price_levels.supports.map((s, i) => (
                  <li
                    key={i}
                    className="rounded bg-green-50 px-2 py-1 text-sm text-zinc-800"
                  >
                    {currency(s.price)} — {s.summary}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {p.price_levels.resistances.length > 0 && (
            <div>
              <span className="text-xs font-medium uppercase tracking-wide text-red-600">
                Resistance
              </span>
              <ul className="mt-1 space-y-1">
                {p.price_levels.resistances.map((r, i) => (
                  <li
                    key={i}
                    className="rounded bg-red-50 px-2 py-1 text-sm text-zinc-800"
                  >
                    {currency(r.price)} — {r.summary}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {p.price_levels.entry_reference && (
            <AnalysisValue
              label="Referensi Entry"
              value={`${currency(p.price_levels.entry_reference.price)} — ${p.price_levels.entry_reference.summary}`}
            />
          )}
          {p.price_levels.stop_loss_level && (
            <AnalysisValue
              label="Level Stop Loss"
              value={`${currency(p.price_levels.stop_loss_level.price)} — ${p.price_levels.stop_loss_level.summary}`}
            />
          )}
          {p.price_levels.target_level && (
            <AnalysisValue
              label="Level Target"
              value={`${currency(p.price_levels.target_level.price)} — ${p.price_levels.target_level.summary}`}
            />
          )}
          {p.price_levels.invalidation_level && (
            <AnalysisValue
              label="Level Invalidasi"
              value={`${currency(p.price_levels.invalidation_level.price)} — ${p.price_levels.invalidation_level.summary}`}
            />
          )}
        </div>
      </AnalysisSection>

      {/* Entry Plan — labelled as recommendation */}
      <AnalysisSection title="Rekomendasi Entry AI">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <AnalysisValue
              label="Entry Direkomendasikan"
              value={displayBool(p.entry_plan.entry_recommended)}
            />
            <AnalysisValue
              label="Tipe Entry"
              value={enumLabel("entry_type", p.entry_plan.entry_type)}
            />
            <AnalysisValue
              label="Konfirmasi Diperlukan"
              value={displayBool(p.entry_plan.confirmation_required)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-2">
            <AnalysisValue
              label="Zona Entry Bawah"
              value={currency(p.entry_plan.entry_zone_low)}
            />
            <AnalysisValue
              label="Zona Entry Atas"
              value={currency(p.entry_plan.entry_zone_high)}
            />
          </div>
          <AnalysisValue
            label="Max Acceptable Entry"
            value={currency(p.entry_plan.maximum_acceptable_entry)}
          />
          <AnalysisValue
            label="Risiko Kejar Harga"
            value={enumLabel("chase_risk", p.entry_plan.chase_risk)}
          />
          <AnalysisValue
            label="Kondisi Konfirmasi"
            value={p.entry_plan.confirmation_condition}
          />
          <AnalysisValue
            label="Batalkan Entry Jika"
            value={p.entry_plan.cancel_entry_condition}
          />
          <div className="text-sm">
            <span className="text-zinc-400">Ringkasan Rencana Entry</span>
            <p className="mt-1 text-zinc-800">{p.entry_plan.summary}</p>
          </div>
          <p className="text-xs italic text-zinc-400">
            Rekomendasi AI, bukan posisi terkonfirmasi.
          </p>
        </div>
      </AnalysisSection>

      {/* Stop Loss Plan — labelled as recommendation */}
      <AnalysisSection title="Rekomendasi Stop Loss">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <AnalysisValue
              label="SL Direkomendasikan"
              value={displayBool(p.stop_loss_plan.stop_loss_recommended)}
            />
            <AnalysisValue
              label="Harga Stop Loss"
              value={currency(p.stop_loss_plan.stop_loss_price)}
            />
            <AnalysisValue
              label="Risiko dari Entry (%)"
              value={percentage(
                p.stop_loss_plan.risk_from_reference_entry_percentage,
              )}
            />
          </div>
          <AnalysisValue
            label="Alasan"
            value={p.stop_loss_plan.reason}
          />
          <AnalysisValue
            label="Kondisi Invalidasi"
            value={p.stop_loss_plan.invalidation_condition}
          />
          <AnalysisValue
            label="Max Risk Dihormati"
            value={displayBool(p.stop_loss_plan.maximum_risk_respected)}
          />
          <div className="text-sm">
            <span className="text-zinc-400">Ringkasan</span>
            <p className="mt-1 text-zinc-800">{p.stop_loss_plan.summary}</p>
          </div>
          <p className="text-xs italic text-zinc-400">
            Rekomendasi AI, bukan stop loss terkonfirmasi.
          </p>
        </div>
      </AnalysisSection>

      {/* Target Plan — labelled as recommendation */}
      <AnalysisSection title="Rekomendasi Target">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <AnalysisValue
              label="Target Direkomendasikan"
              value={displayBool(p.target_plan.target_recommended)}
            />
            <AnalysisValue
              label="Harga Target"
              value={currency(p.target_plan.target_price)}
            />
            <AnalysisValue
              label="Risk/Reward"
              value={p.target_plan.risk_reward_ratio}
            />
          </div>
          <AnalysisValue
            label="Reward dari Entry (%)"
            value={percentage(
              p.target_plan.reward_from_reference_entry_percentage,
            )}
          />
          <AnalysisValue
            label="Dasar Target"
            value={p.target_plan.target_basis}
          />
          <AnalysisValue
            label="Hambatan Utama"
            value={p.target_plan.primary_obstacle}
          />
          <AnalysisValue
            label="Kondisi yang Diperlukan"
            value={p.target_plan.required_condition}
          />
          <div className="text-sm">
            <span className="text-zinc-400">Ringkasan</span>
            <p className="mt-1 text-zinc-800">{p.target_plan.summary}</p>
          </div>
          <p className="text-xs italic text-zinc-400">
            Rekomendasi AI, bukan target terkonfirmasi.
          </p>
        </div>
      </AnalysisSection>

      {/* Thesis */}
      <AnalysisSection title="Thesis Awal">
        <div className="space-y-3">
          <AnalysisValue
            label="Status Thesis"
            value={enumLabel("dominant_structure", p.initial_thesis.status)}
          />
          <AnalysisValue
            label="Alasan Setup"
            value={p.initial_thesis.setup_reason}
          />
          {p.initial_thesis.supporting_factors.length > 0 && (
            <div className="text-sm">
              <span className="text-zinc-400">Faktor Pendukung</span>
              <ul className="mt-1 list-inside list-disc text-zinc-800">
                {p.initial_thesis.supporting_factors.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
          {p.initial_thesis.risk_factors.length > 0 && (
            <div className="text-sm">
              <span className="text-zinc-400">Faktor Risiko</span>
              <ul className="mt-1 list-inside list-disc text-zinc-600">
                {p.initial_thesis.risk_factors.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
          <AnalysisValue
            label="Kondisi Support"
            value={p.initial_thesis.support_condition}
          />
          <AnalysisValue
            label="Harga Invalidasi"
            value={currency(p.initial_thesis.invalidation_price)}
          />
          <AnalysisValue
            label="Kondisi Invalidasi"
            value={p.initial_thesis.invalidation_condition}
          />
          <AnalysisValue
            label="Ekspektasi Holding Period"
            value={enumLabel(
              "expected_holding_period",
              p.initial_thesis.expected_holding_period,
            )}
          />
          {p.initial_thesis.review_conditions.length > 0 && (
            <div className="text-sm">
              <span className="text-zinc-400">Kondisi Review</span>
              <ul className="mt-1 list-inside list-disc text-zinc-800">
                {p.initial_thesis.review_conditions.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="text-sm">
            <span className="text-zinc-400">Ringkasan</span>
            <p className="mt-1 text-zinc-800">{p.initial_thesis.summary}</p>
          </div>
        </div>
      </AnalysisSection>

      {/* Trading Plan */}
      <AnalysisSection title="Rencana Trading">
        <div className="space-y-3">
          <AnalysisValue
            label="Tindakan Saat Ini"
            value={enumLabel(
              "recommended_action",
              p.trading_plan.current_action,
            )}
          />
          <AnalysisValue
            label="Alasan Tindakan"
            value={p.trading_plan.action_rationale}
          />
          <AnalysisValue
            label="Kondisi Entry"
            value={p.trading_plan.entry_condition}
          />
          <AnalysisValue
            label="Kondisi Hold Setelah Entry"
            value={p.trading_plan.post_entry_hold_condition}
          />
          <AnalysisValue
            label="Kondisi Exit Setelah Entry"
            value={p.trading_plan.post_entry_exit_condition}
          />
          <AnalysisValue
            label="Kondisi Tunggu"
            value={p.trading_plan.wait_condition}
          />
          <AnalysisValue
            label="Checkpoint Berikutnya"
            value={p.trading_plan.next_checkpoint}
          />
          <AnalysisValue
            label="Batalkan Setup Jika"
            value={p.trading_plan.cancel_setup_condition}
          />
          {p.trading_plan.levels_to_monitor.length > 0 && (
            <div className="text-sm">
              <span className="text-zinc-400">Level yang Dipantau</span>
              <ul className="mt-1 list-inside list-disc text-zinc-800">
                {p.trading_plan.levels_to_monitor.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          )}
          <AnalysisValue
            label="Memerlukan Konfirmasi Pengguna"
            value={displayBool(p.trading_plan.requires_user_confirmation)}
          />
        </div>
      </AnalysisSection>

      {/* Probability and Confidence */}
      <AnalysisSection title="Probabilitas dan Keyakinan">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <AnalysisValue
              label="Keyakinan"
              value={percentage(p.ai_assessment.confidence)}
            />
            <AnalysisValue
              label="Probabilitas Bullish"
              value={percentage(p.ai_assessment.bullish_probability)}
            />
            <AnalysisValue
              label="Probabilitas Target"
              value={percentage(p.ai_assessment.target_probability)}
            />
            <AnalysisValue
              label="Probabilitas Downside"
              value={percentage(p.ai_assessment.downside_probability)}
            />
          </div>
          <AnalysisValue
            label="Bias"
            value={enumLabel("bias", p.ai_assessment.bias)}
          />
          <AnalysisValue
            label="Kualitas Setup"
            value={enumLabel("setup_quality", p.ai_assessment.setup_quality)}
          />
          <AnalysisValue
            label="Setup Valid"
            value={displayBool(p.ai_assessment.setup_valid)}
          />
          <AnalysisValue
            label="Tingkat Risiko"
            value={enumLabel("risk_level", p.ai_assessment.risk_level)}
          />
          <div className="text-sm">
            <span className="text-zinc-400">Ringkasan</span>
            <p className="mt-1 text-zinc-800">{p.ai_assessment.summary}</p>
          </div>
          <p className="text-xs italic text-zinc-400">
            Estimasi AI, bukan kepastian.
          </p>
        </div>
      </AnalysisSection>

      {/* Warnings and Missing Information */}
      <AnalysisSection title="Peringatan dan Informasi yang Kurang">
        <div className="space-y-3">
          {p.warnings_and_missing_information.warnings.length === 0 &&
          p.warnings_and_missing_information.missing_information.length ===
            0 ? (
            <p className="text-sm text-zinc-400">
              Tidak ada peringatan tambahan.
            </p>
          ) : (
            <>
              {p.warnings_and_missing_information.warnings.length > 0 && (
                <div className="text-sm">
                  <span className="text-zinc-400">Peringatan</span>
                  <ul className="mt-1 list-inside list-disc text-amber-700">
                    {p.warnings_and_missing_information.warnings.map(
                      (w, i) => (
                        <li key={i}>{w}</li>
                      ),
                    )}
                  </ul>
                </div>
              )}
              {p.warnings_and_missing_information.missing_information
                .length > 0 && (
                <div className="text-sm">
                  <span className="text-zinc-400">
                    Informasi yang Tidak Tersedia
                  </span>
                  <ul className="mt-1 list-inside list-disc text-zinc-600">
                    {p.warnings_and_missing_information.missing_information.map(
                      (m, i) => (
                        <li key={i}>{m}</li>
                      ),
                    )}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </AnalysisSection>

      {/* Metadata — visually secondary */}
      <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3">
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-400">
          <span>
            Tipe: {p.metadata.analysis_type}
          </span>
          <span>
            Versi Skema: {p.metadata.schema.schema_version}
          </span>
          <span>
            Provider: {p.metadata.provider}
          </span>
          <span>
            Model: {p.metadata.model}
          </span>
          <span>
            Waktu Analisis:{" "}
            {formatTimestamp(p.metadata.analysis_timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
}

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("id-ID", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}
