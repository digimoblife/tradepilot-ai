"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import type { AnalysisDetail, AnalysisSummary } from "@/types/analysis";
import type { InitialAnalysisPayload, InitialAnalysisV2Payload } from "./types";
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
  | { status: "loaded"; payload: InitialAnalysisPayload | InitialAnalysisV2Payload; detail: AnalysisDetail };

interface Props {
  sessionId: string;
  onEmpty?: () => void;
  onLoaded?: () => void;
  selectedAnalysis?: AnalysisSummary | null;
}

export function InitialAnalysisView({ sessionId, onEmpty, onLoaded, selectedAnalysis }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const cancelledRef = useRef(false);

  const load = useCallback(async function loadFn() {
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      let latest = selectedAnalysis ?? null;
      if (selectedAnalysis === undefined) {
        const list = await listAnalyses(sessionId, {
          analysis_type: "INITIAL_ANALYSIS",
        });
        if (cancelledRef.current) return;

        const accepted = list.analyses
          .filter((a) => a.acceptance_status === "ACCEPTED")
          .sort(
            (a, b) =>
              new Date(b.accepted_at ?? b.created_at).getTime() -
              new Date(a.accepted_at ?? a.created_at).getTime(),
          );
        latest = accepted[0] ?? null;
      }

      if (!latest) {
        if (!cancelledRef.current) setState({ status: "empty" });
        return;
      }

      const detail = await getAnalysis(latest.id);
      if (cancelledRef.current) return;

      if (!detail.payload) {
        if (!cancelledRef.current) setState({ status: "empty" });
        return;
      }

      if (!cancelledRef.current) {
        setState({
          status: "loaded",
          payload: detail.payload as unknown as InitialAnalysisPayload,
          detail,
        });
      }
    } catch (e: unknown) {
      if (cancelledRef.current) return;
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
  }, [selectedAnalysis, sessionId]);

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
  const rawPayload = payload as unknown as Record<string, unknown>;
  if (isInitialAnalysisV2(rawPayload)) {
    return <InitialAnalysisV2View payload={withV2Fallbacks(rawPayload)} detail={state.detail} />;
  }
  const p = withDisplayFallbacks(rawPayload);
  const extraTopLevelFields = additionalTopLevelFields(rawPayload);

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
      {extraTopLevelFields.length > 0 && (
        <AnalysisSection title="Detail tambahan">
          <div className="space-y-2 text-sm text-zinc-700">
            {extraTopLevelFields.map(([key, value]) => (
              <div key={key} className="rounded bg-zinc-50 px-3 py-2">
                <span className="font-medium text-zinc-500">{key}</span>
                <pre className="mt-1 whitespace-pre-wrap break-words text-xs text-zinc-700">
                  {formatUnknownValue(value)}
                </pre>
              </div>
            ))}
          </div>
        </AnalysisSection>
      )}

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

function InitialAnalysisV2View({
  payload,
  detail,
}: {
  payload: InitialAnalysisV2Payload;
  detail: AnalysisDetail;
}) {
  return (
    <div className="space-y-4">
      <AnalysisSection title="Keputusan">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <AnalysisValue
              label="Rekomendasi"
              value={enumLabel("recommended_action", payload.decision.recommendation)}
            />
            <AnalysisValue
              label="Bias"
              value={enumLabel("bias", payload.decision.bias)}
            />
            <AnalysisValue
              label="Keyakinan"
              value={percentage(payload.decision.confidence)}
            />
            <AnalysisValue
              label="Kualitas Setup"
              value={enumLabel("setup_quality", payload.decision.setup_quality)}
            />
            <AnalysisValue
              label="Tingkat Risiko"
              value={enumLabel("risk_level", payload.decision.risk_level)}
            />
          </div>
          <div className="text-sm">
            <span className="text-zinc-400">Ringkasan</span>
            <p className="mt-1 text-zinc-800">{payload.decision.summary}</p>
          </div>
        </div>
      </AnalysisSection>

      <AnalysisSection title="Rencana Trading">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <AnalysisValue label="Support" value={currency(payload.trade_plan.nearest_support)} />
          <AnalysisValue label="Resistance" value={currency(payload.trade_plan.nearest_resistance)} />
          <AnalysisValue label="Entry Bawah" value={currency(payload.trade_plan.entry_zone_low)} />
          <AnalysisValue label="Entry Atas" value={currency(payload.trade_plan.entry_zone_high)} />
          <AnalysisValue label="Chase Limit" value={currency(payload.trade_plan.chase_limit)} />
          <AnalysisValue label="Stop Loss" value={currency(payload.trade_plan.stop_loss)} />
          <AnalysisValue label="Target 1" value={currency(payload.trade_plan.target_1)} />
          <AnalysisValue label="Target 2" value={currency(payload.trade_plan.target_2)} />
          <AnalysisValue label="Invalidasi" value={currency(payload.trade_plan.invalidation)} />
          <AnalysisValue label="Risk/Reward" value={enumLabel("risk_reward", payload.trade_plan.risk_reward)} />
        </div>
        <p className="mt-3 text-xs italic text-zinc-400">
          Rekomendasi AI, bukan posisi, stop loss, atau target terkonfirmasi.
        </p>
      </AnalysisSection>

      <AnalysisSection title="Probabilitas">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Bullish" value={percentage(payload.probabilities.bullish)} />
          <AnalysisValue label="Target 1" value={percentage(payload.probabilities.target_1)} />
          <AnalysisValue label="Downside" value={percentage(payload.probabilities.downside)} />
        </div>
        <p className="mt-3 text-xs italic text-zinc-400">
          Estimasi AI, bukan kepastian.
        </p>
      </AnalysisSection>

      <AnalysisSection title="Alasan, Risiko, Monitoring">
        <div className="grid gap-3 md:grid-cols-3">
          <CompactList title="Alasan" items={payload.next_actions.reasons} />
          <CompactList title="Risiko" items={payload.next_actions.risks} tone="risk" />
          <CompactList title="Monitoring" items={payload.next_actions.monitoring} />
        </div>
      </AnalysisSection>

      <AnalysisSection title="Skenario">
        <div className="grid gap-3 md:grid-cols-3">
          <AnalysisValue label="Bullish" value={payload.scenarios.bullish} />
          <AnalysisValue label="Netral" value={payload.scenarios.neutral} />
          <AnalysisValue label="Bearish" value={payload.scenarios.bearish} />
        </div>
      </AnalysisSection>

      <AnalysisSection title="Fakta Pasar">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <AnalysisValue label="Open" value={currency(payload.market_facts.open)} />
          <AnalysisValue label="High" value={currency(payload.market_facts.high)} />
          <AnalysisValue label="Low" value={currency(payload.market_facts.low)} />
          <AnalysisValue label="Last/Close" value={currency(payload.market_facts.close_or_last)} />
          <AnalysisValue label="Average" value={currency(payload.market_facts.average)} />
          <AnalysisValue label="Best Bid" value={currency(payload.market_facts.best_bid)} />
          <AnalysisValue label="Best Offer" value={currency(payload.market_facts.best_offer)} />
          <AnalysisValue label="Foreign Net" value={currency(payload.market_facts.foreign_net)} />
        </div>
      </AnalysisSection>

      <AnalysisSection title="Temuan Evidence">
        <div className="space-y-2">
          <CompactDetails title="Orderbook" items={payload.evidence_findings.orderbook} />
          <CompactDetails title="Chart 3 Bulan" items={payload.evidence_findings.chart_3_month} />
          <CompactDetails title="Chart 6 Bulan" items={payload.evidence_findings.chart_6_month} />
          <CompactDetails title="Broker" items={payload.evidence_findings.broker_summary} />
          <CompactDetails title="Foreign Flow" items={payload.evidence_findings.foreign_flow} />
          <CompactDetails title="Keterbatasan" items={payload.evidence_findings.limitations} />
        </div>
      </AnalysisSection>

      <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3">
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-400">
          <span>Tipe: INITIAL_ANALYSIS</span>
          <span>Versi Skema: {payload.metadata.schema_version}</span>
          <span>Skema: {payload.metadata.schema_name}</span>
          <span>Prompt: {payload.metadata.prompt_version}</span>
          <span>Waktu Analisis: {formatTimestamp(payload.metadata.analysis_timestamp)}</span>
          <span>ID Analisis: {detail.id}</span>
        </div>
      </div>
    </div>
  );
}

function CompactList({
  title,
  items,
  tone = "default",
}: {
  title: string;
  items: string[];
  tone?: "default" | "risk";
}) {
  const textClass = tone === "risk" ? "text-amber-700" : "text-zinc-800";
  return (
    <div className="text-sm">
      <span className="text-zinc-400">{title}</span>
      {items.length === 0 ? (
        <p className="mt-1 text-zinc-400">Tidak tersedia</p>
      ) : (
        <ul className={`mt-1 list-inside list-disc ${textClass}`}>
          {items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CompactDetails({ title, items }: { title: string; items: string[] }) {
  return (
    <details className="rounded border border-zinc-100 bg-zinc-50 px-3 py-2">
      <summary className="cursor-pointer text-sm font-medium text-zinc-600">
        {title}
      </summary>
      <CompactList title="" items={items} />
    </details>
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

const DISPLAY_FALLBACK = "Tidak tersedia";
const KNOWN_TOP_LEVEL_KEYS = new Set([
  "metadata",
  "evidence_summary",
  "market_snapshot",
  "executive_summary",
  "orderbook_analysis",
  "chart_3_month_analysis",
  "chart_6_month_analysis",
  "combined_chart_analysis",
  "price_levels",
  "entry_plan",
  "stop_loss_plan",
  "target_plan",
  "initial_thesis",
  "trading_plan",
  "ai_assessment",
  "warnings_and_missing_information",
  "decision",
  "market_facts",
  "evidence_findings",
  "trade_plan",
  "probabilities",
  "scenarios",
  "next_actions",
]);

function isInitialAnalysisV2(raw: Record<string, unknown>): boolean {
  const metadata = asRecord(raw.metadata);
  return (
    metadata.schema_name === "initial_analysis_v2" ||
    metadata.schema_version === "2.0.0" ||
    ("decision" in raw && "trade_plan" in raw && "next_actions" in raw)
  );
}

function withV2Fallbacks(raw: Record<string, unknown>): InitialAnalysisV2Payload {
  const metadata = asRecord(raw.metadata);
  const decision = asRecord(raw.decision);
  const marketFacts = asRecord(raw.market_facts);
  const evidenceFindings = asRecord(raw.evidence_findings);
  const tradePlan = asRecord(raw.trade_plan);
  const probabilities = asRecord(raw.probabilities);
  const scenarios = asRecord(raw.scenarios);
  const nextActions = asRecord(raw.next_actions);

  return {
    metadata: {
      session_id: asString(metadata.session_id),
      ticker: asString(metadata.ticker),
      analysis_timestamp: asNullableString(metadata.analysis_timestamp),
      schema_name: asString(metadata.schema_name),
      schema_version: asString(metadata.schema_version),
      prompt_version: asString(metadata.prompt_version),
    },
    decision: {
      recommendation: asString(decision.recommendation),
      bias: asString(decision.bias),
      confidence: asNumber(decision.confidence),
      setup_quality: asString(decision.setup_quality),
      risk_level: asString(decision.risk_level),
      summary: asString(decision.summary),
    },
    market_facts: {
      open: asNumber(marketFacts.open),
      high: asNumber(marketFacts.high),
      low: asNumber(marketFacts.low),
      close_or_last: asNumber(marketFacts.close_or_last),
      average: asNumber(marketFacts.average),
      best_bid: asNumber(marketFacts.best_bid),
      best_offer: asNumber(marketFacts.best_offer),
      foreign_net: asNumber(marketFacts.foreign_net),
    },
    evidence_findings: {
      orderbook: asStringArray(evidenceFindings.orderbook),
      chart_3_month: asStringArray(evidenceFindings.chart_3_month),
      chart_6_month: asStringArray(evidenceFindings.chart_6_month),
      broker_summary: asStringArray(evidenceFindings.broker_summary),
      foreign_flow: asStringArray(evidenceFindings.foreign_flow),
      limitations: asStringArray(evidenceFindings.limitations),
    },
    trade_plan: {
      nearest_support: asNumber(tradePlan.nearest_support),
      nearest_resistance: asNumber(tradePlan.nearest_resistance),
      entry_zone_low: asNumber(tradePlan.entry_zone_low),
      entry_zone_high: asNumber(tradePlan.entry_zone_high),
      chase_limit: asNumber(tradePlan.chase_limit),
      stop_loss: asNumber(tradePlan.stop_loss),
      target_1: asNumber(tradePlan.target_1),
      target_2: asNumber(tradePlan.target_2),
      invalidation: asNumber(tradePlan.invalidation),
      risk_reward: asString(tradePlan.risk_reward),
    },
    probabilities: {
      bullish: asNumber(probabilities.bullish),
      target_1: asNumber(probabilities.target_1),
      downside: asNumber(probabilities.downside),
    },
    scenarios: {
      bullish: asString(scenarios.bullish),
      neutral: asString(scenarios.neutral),
      bearish: asString(scenarios.bearish),
    },
    next_actions: {
      reasons: asStringArray(nextActions.reasons),
      risks: asStringArray(nextActions.risks),
      monitoring: asStringArray(nextActions.monitoring),
    },
  };
}

function withDisplayFallbacks(raw: Record<string, unknown>): InitialAnalysisPayload {
  const metadata = asRecord(raw.metadata);
  const schema = asRecord(metadata.schema);
  const executiveSummary = asRecord(raw.executive_summary);
  const orderbookAnalysis = asRecord(raw.orderbook_analysis);
  const chart3 = asRecord(raw.chart_3_month_analysis);
  const chart6 = asRecord(raw.chart_6_month_analysis);
  const combinedChart = asRecord(raw.combined_chart_analysis);
  const priceLevels = asRecord(raw.price_levels);
  const entryPlan = asRecord(raw.entry_plan);
  const stopLossPlan = asRecord(raw.stop_loss_plan);
  const targetPlan = asRecord(raw.target_plan);
  const initialThesis = asRecord(raw.initial_thesis);
  const tradingPlan = asRecord(raw.trading_plan);
  const aiAssessment = asRecord(raw.ai_assessment);
  const warningsInfo = asRecord(raw.warnings_and_missing_information);

  return {
    metadata: {
      analysis_id: asString(metadata.analysis_id),
      session_id: asString(metadata.session_id),
      analysis_type: asString(metadata.analysis_type),
      ticker: asString(metadata.ticker),
      company_name: asString(metadata.company_name),
      analysis_timestamp: asString(metadata.analysis_timestamp),
      language: asString(metadata.language),
      schema: {
        schema_name: asString(schema.schema_name),
        schema_version: asString(schema.schema_version),
      },
      prompt_version: asString(metadata.prompt_version),
      provider: asString(metadata.provider),
      model: asString(metadata.model),
    },
    evidence_summary: asRecord(raw.evidence_summary),
    market_snapshot: asRecord(raw.market_snapshot),
    executive_summary: {
      headline: asString(executiveSummary.headline),
      main_opportunity: asString(executiveSummary.main_opportunity),
      main_risk: asString(executiveSummary.main_risk),
      setup_status: asString(executiveSummary.setup_status),
      recommended_action: asString(executiveSummary.recommended_action),
      summary: asString(executiveSummary.summary),
    },
    orderbook_analysis: {
      market_timestamp: asString(orderbookAnalysis.market_timestamp),
      available: asBoolean(orderbookAnalysis.available),
      buyer_strength: asString(orderbookAnalysis.buyer_strength),
      seller_pressure: asString(orderbookAnalysis.seller_pressure),
      best_bid: asNumber(orderbookAnalysis.best_bid),
      best_offer: asNumber(orderbookAnalysis.best_offer),
      bid_support: asPriceLevel(orderbookAnalysis.bid_support),
      offer_resistance: asPriceLevel(orderbookAnalysis.offer_resistance),
      positive_signals: asStringArray(orderbookAnalysis.positive_signals),
      buyer_observations: asStringArray(orderbookAnalysis.buyer_observations),
      risk_signals: asStringArray(orderbookAnalysis.risk_signals),
      seller_observations: asStringArray(orderbookAnalysis.seller_observations),
      supports_entry: asBoolean(orderbookAnalysis.supports_entry),
      conclusion: asString(orderbookAnalysis.conclusion),
      limitations: asStringArray(orderbookAnalysis.limitations),
    },
    chart_3_month_analysis: chartFallback(chart3),
    chart_6_month_analysis: chartFallback(chart6),
    combined_chart_analysis: {
      multi_timeframe_alignment: asString(combinedChart.multi_timeframe_alignment),
      short_term_trend: asString(combinedChart.short_term_trend),
      dominant_structure: asString(combinedChart.dominant_structure),
      setup_supported: asBoolean(combinedChart.setup_supported),
      medium_term_trend: asString(combinedChart.medium_term_trend),
      main_confirmation: asString(combinedChart.main_confirmation),
      main_conflict: asString(combinedChart.main_conflict),
      conclusion: asString(combinedChart.conclusion),
    },
    price_levels: {
      entry_reference: asPriceLevel(priceLevels.entry_reference),
      invalidation_level: asPriceLevel(priceLevels.invalidation_level),
      stop_loss_level: asPriceLevel(priceLevels.stop_loss_level),
      target_level: asPriceLevel(priceLevels.target_level),
      summary: asString(priceLevels.summary),
      supports: asPriceLevelArray(priceLevels.supports),
      resistances: asPriceLevelArray(priceLevels.resistances),
    },
    entry_plan: {
      entry_recommended: asBoolean(entryPlan.entry_recommended),
      entry_type: asString(entryPlan.entry_type),
      entry_price: asNumber(entryPlan.entry_price),
      confirmation_required: asBoolean(entryPlan.confirmation_required),
      confirmation_condition: asString(entryPlan.confirmation_condition),
      chase_risk: asString(entryPlan.chase_risk),
      maximum_acceptable_entry: asNumber(entryPlan.maximum_acceptable_entry),
      cancel_entry_condition: asString(entryPlan.cancel_entry_condition),
      entry_zone_low: asNumber(entryPlan.entry_zone_low),
      entry_zone_high: asNumber(entryPlan.entry_zone_high),
      summary: asString(entryPlan.summary),
    },
    stop_loss_plan: {
      stop_loss_recommended: asBoolean(stopLossPlan.stop_loss_recommended),
      stop_loss_price: asNumber(stopLossPlan.stop_loss_price),
      risk_from_reference_entry_percentage: asNumber(stopLossPlan.risk_from_reference_entry_percentage),
      invalidation_condition: asString(stopLossPlan.invalidation_condition),
      reason: asString(stopLossPlan.reason),
      maximum_risk_respected: asBoolean(stopLossPlan.maximum_risk_respected),
      summary: asString(stopLossPlan.summary),
    },
    target_plan: {
      target_recommended: asBoolean(targetPlan.target_recommended),
      target_price: asNumber(targetPlan.target_price),
      reward_from_reference_entry_percentage: asNumber(targetPlan.reward_from_reference_entry_percentage),
      target_basis: asString(targetPlan.target_basis),
      primary_obstacle: asString(targetPlan.primary_obstacle),
      required_condition: asString(targetPlan.required_condition),
      risk_reward_ratio: asNumber(targetPlan.risk_reward_ratio),
      summary: asString(targetPlan.summary),
    },
    initial_thesis: {
      status: asString(initialThesis.status),
      setup_reason: asString(initialThesis.setup_reason),
      supporting_factors: asStringArray(initialThesis.supporting_factors),
      risk_factors: asStringArray(initialThesis.risk_factors),
      support_condition: asString(initialThesis.support_condition),
      invalidation_price: asNumber(initialThesis.invalidation_price),
      expected_holding_period: asString(initialThesis.expected_holding_period),
      review_conditions: asStringArray(initialThesis.review_conditions),
      invalidation_condition: asString(initialThesis.invalidation_condition),
      summary: asString(initialThesis.summary),
    },
    trading_plan: {
      current_action: asString(tradingPlan.current_action),
      action_rationale: asString(tradingPlan.action_rationale),
      entry_condition: asString(tradingPlan.entry_condition),
      post_entry_hold_condition: asString(tradingPlan.post_entry_hold_condition),
      post_entry_exit_condition: asString(tradingPlan.post_entry_exit_condition),
      wait_condition: asString(tradingPlan.wait_condition),
      next_checkpoint: asString(tradingPlan.next_checkpoint),
      cancel_setup_condition: asString(tradingPlan.cancel_setup_condition),
      levels_to_monitor: asStringArray(tradingPlan.levels_to_monitor),
      requires_user_confirmation: asBoolean(tradingPlan.requires_user_confirmation),
    },
    ai_assessment: {
      setup_quality: asString(aiAssessment.setup_quality),
      setup_valid: asBoolean(aiAssessment.setup_valid),
      bias: asString(aiAssessment.bias),
      confidence: asNumber(aiAssessment.confidence),
      bullish_probability: asNumber(aiAssessment.bullish_probability),
      target_probability: asNumber(aiAssessment.target_probability),
      downside_probability: asNumber(aiAssessment.downside_probability),
      risk_level: asString(aiAssessment.risk_level),
      summary: asString(aiAssessment.summary),
    },
    warnings_and_missing_information: {
      missing_information: asStringArray(warningsInfo.missing_information),
      warnings: asStringArray(warningsInfo.warnings),
    },
  } as InitialAnalysisPayload;
}

function chartFallback(chart: Record<string, unknown>) {
  return {
    available: asBoolean(chart.available),
    timeframe: asString(chart.timeframe),
    chart_timestamp: asString(chart.chart_timestamp),
    momentum: asString(chart.momentum),
    volume_condition: asString(chart.volume_condition),
    breakout_status: asString(chart.breakout_status),
    breakdown_status: asString(chart.breakdown_status),
    positive_signals: asStringArray(chart.positive_signals),
    risk_signals: asStringArray(chart.risk_signals),
    trend: asString(chart.trend),
    structure_status: asString(chart.structure_status),
    nearest_support: asPriceLevel(chart.nearest_support),
    nearest_resistance: asPriceLevel(chart.nearest_resistance),
    conclusion: asString(chart.conclusion),
    supports_setup: asBoolean(chart.supports_setup),
    limitations: asStringArray(chart.limitations),
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function asString(value: unknown): string {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return DISPLAY_FALLBACK;
}

function asNullableString(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value;
  return null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
}

function asPriceLevel(value: unknown) {
  const record = asRecord(value);
  const price = asNumber(record.price);
  if (price === null && !record.summary && !record.label) return null;
  return {
    price,
    label: asString(record.label),
    summary: asString(record.summary),
  };
}

function asPriceLevelArray(value: unknown) {
  return Array.isArray(value)
    ? value.map(asPriceLevel).filter((item): item is NonNullable<ReturnType<typeof asPriceLevel>> => item !== null)
    : [];
}

function additionalTopLevelFields(raw: Record<string, unknown>): [string, unknown][] {
  return Object.entries(raw).filter(([key]) => !KNOWN_TOP_LEVEL_KEYS.has(key));
}

function formatUnknownValue(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2) ?? DISPLAY_FALLBACK;
  } catch {
    return DISPLAY_FALLBACK;
  }
}
