"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { listAnalyses, getAnalysis } from "@/lib/api/analyses";
import { ApiError, AuthenticationError } from "@/lib/api/errors";
import { AnalysisSection } from "./analysis-section";
import { AnalysisValue } from "./analysis-value";
import type { AnalysisSummary } from "@/types/analysis";
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

interface SetupAssessment {
  status: string;
  still_valid: boolean;
  original_thesis_summary: string;
  current_thesis_summary: string;
  strengthening_evidence: string[];
  weakening_evidence: string[];
  invalidation_condition: string;
  invalidation_price: number | null;
  invalidation_triggered: boolean;
  summary: string;
}

interface EntryAssessment {
  entry_confirmation_met: boolean;
  price_already_extended: boolean;
  chase_risk: string;
  maximum_acceptable_entry: number | null;
  revised_entry_proposed: boolean;
  proposed_entry_type: string | null;
  proposed_entry_price: number | null;
  proposed_entry_zone_low: number | null;
  proposed_entry_zone_high: number | null;
  entry_condition: string;
  wait_condition: string | null;
  cancel_entry_condition: string | null;
  reference_entry_type: string | null;
  reference_entry_price: number | null;
  reference_entry_zone_low: number | null;
  reference_entry_zone_high: number | null;
  entry_still_attractive: boolean | null;
  current_price: number | null;
  summary: string;
}

interface PriceLevels {
  reference_entry: PriceLevel | null;
  maximum_acceptable_entry: PriceLevel | null;
  invalidation_level: PriceLevel | null;
  proposed_stop_loss: PriceLevel | null;
  proposed_target: PriceLevel | null;
  summary: string;
  supports: PriceLevel[];
  resistances: PriceLevel[];
}

interface TradingPlan {
  current_action: string;
  wait_condition: string | null;
  action_rationale: string;
  entry_condition: string | null;
  do_not_chase_condition: string | null;
  next_checkpoint: string | null;
  cancel_setup_condition: string | null;
  levels_to_monitor: string[];
  requires_user_confirmation: boolean;
}

interface AiAssessment {
  entry_probability: number | null;
  bias: string;
  confidence: number | null;
  setup_quality: string;
  setup_valid: boolean;
  bullish_probability: number | null;
  target_probability: number | null;
  downside_probability: number | null;
  risk_level: string;
  summary: string;
}

interface WatchingUpdatePayload {
  metadata: Record<string, unknown>;
  update_period: string;
  comparison: Comparison;
  evidence_summary: Record<string, unknown>;
  market_snapshot: Record<string, unknown>;
  today_summary: Record<string, unknown>;
  orderbook_analysis: Record<string, unknown>;
  chart_update: Record<string, unknown>;
  setup_assessment: SetupAssessment;
  entry_assessment: EntryAssessment;
  price_levels: PriceLevels;
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
  | { status: "loaded"; payload: WatchingUpdatePayload };

interface Props {
  sessionId: string;
  onEmpty?: () => void;
  onLoaded?: () => void;
  selectedAnalysis?: AnalysisSummary | null;
}

export function WatchingUpdateView({ sessionId, onEmpty, onLoaded, selectedAnalysis }: Props) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const cancelledRef = useRef(false);

  const load = useCallback(async function loadFn() {
    cancelledRef.current = false;
    setState({ status: "loading" });
    try {
      let latest = selectedAnalysis ?? null;
      if (selectedAnalysis === undefined) {
        const list = await listAnalyses(sessionId, {
          analysis_type: "WATCHING_UPDATE",
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
          payload: detail.payload as unknown as WatchingUpdatePayload,
        });
      }
    } catch (e: unknown) {
      if (e instanceof AuthenticationError) {
        setState({
          status: "error",
          message: "Silakan masuk terlebih dahulu untuk melihat pembaruan setup.",
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
          message: "Gagal memuat pembaruan setup. Silakan coba lagi.",
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
        <p className="text-sm text-zinc-500">Memuat pembaruan setup…</p>
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

  // -----------------------------------------------------------------------
  // 1. Current Setup Status
  // -----------------------------------------------------------------------
  const setupSection = (
    <AnalysisSection title="Status Setup Saat Ini">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-2">
          <AnalysisValue
            label="Status"
            value={enumLabel("setup_status", p.setup_assessment.status)}
          />
          <AnalysisValue
            label="Setup Valid"
            value={displayBool(p.setup_assessment.still_valid)}
          />
        </div>
        <AnalysisValue
          label="Ringkasan Thesis Awal"
          value={p.setup_assessment.original_thesis_summary}
        />
        <AnalysisValue
          label="Ringkasan Thesis Saat Ini"
          value={p.setup_assessment.current_thesis_summary}
        />
        {p.setup_assessment.strengthening_evidence.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Bukti Penguat</span>
            <ul className="mt-1 list-inside list-disc text-green-700">
              {p.setup_assessment.strengthening_evidence.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </div>
        )}
        {p.setup_assessment.weakening_evidence.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Bukti Pelemah</span>
            <ul className="mt-1 list-inside list-disc text-amber-700">
              {p.setup_assessment.weakening_evidence.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </div>
        )}
        <AnalysisValue
          label="Kondisi Invalidasi"
          value={p.setup_assessment.invalidation_condition}
        />
        <AnalysisValue
          label="Harga Invalidasi"
          value={currency(p.setup_assessment.invalidation_price)}
        />
        <AnalysisValue
          label="Invalidasi Terpicu"
          value={displayBool(p.setup_assessment.invalidation_triggered)}
        />
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.setup_assessment.summary}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 2. Comparison with Previous Analysis
  // -----------------------------------------------------------------------
  const comparisonSection = (
    <AnalysisSection title="Perbandingan dengan Analisis Sebelumnya">
      <div className="space-y-3">
        <AnalysisValue
          label="Analisis Sebelumnya"
          value={p.comparison.previous_analysis_type ?? "—"}
        />
        <AnalysisValue
          label="Periode Sebelumnya"
          value={p.comparison.previous_update_period ?? "—"}
        />
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan Perubahan</span>
          <p className="mt-1 text-zinc-800">{p.comparison.summary}</p>
        </div>
        {p.changes_from_previous.length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Perubahan Material</span>
            <ul className="mt-1 list-inside list-disc text-zinc-800">
              {p.changes_from_previous.map((c, i) => (
                <li key={i}>{String(c)}</li>
              ))}
            </ul>
          </div>
        )}
        {p.changes_from_previous.length === 0 && (
          <p className="text-xs text-zinc-400">
            Tidak ada perubahan material sejak analisis sebelumnya.
          </p>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 3. Entry Validity
  // -----------------------------------------------------------------------
  const entryValiditySection = (
    <AnalysisSection title="Validitas Entry">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue
            label="Entry Masih Menarik"
            value={displayBool(p.entry_assessment.entry_still_attractive)}
          />
          <AnalysisValue
            label="Konfirmasi Entry Terpenuhi"
            value={displayBool(p.entry_assessment.entry_confirmation_met)}
          />
          <AnalysisValue
            label="Harga Sudah Terlalu Jauh"
            value={displayBool(p.entry_assessment.price_already_extended)}
          />
        </div>
        <AnalysisValue
          label="Harga Saat Ini"
          value={currency(p.entry_assessment.current_price)}
        />
        <AnalysisValue
          label="Harga Referensi Entry"
          value={currency(p.entry_assessment.reference_entry_price)}
        />
        <AnalysisValue
          label="Zona Referensi Entry"
          value={
            p.entry_assessment.reference_entry_zone_low != null &&
            p.entry_assessment.reference_entry_zone_high != null
              ? `${currency(p.entry_assessment.reference_entry_zone_low)} – ${currency(p.entry_assessment.reference_entry_zone_high)}`
              : "—"
          }
        />
        <AnalysisValue
          label="Kondisi Entry"
          value={enumLabel("entry_condition", p.entry_assessment.entry_condition)}
        />
        <AnalysisValue
          label="Kondisi Tunggu"
          value={p.entry_assessment.wait_condition ?? "—"}
        />
        <AnalysisValue
          label="Batalkan Entry Jika"
          value={p.entry_assessment.cancel_entry_condition ?? "—"}
        />
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">{p.entry_assessment.summary}</p>
        </div>
        <p className="text-xs italic text-zinc-400">
          Usulan AI, belum menjadi posisi terkonfirmasi.
        </p>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 4. Confirmation Status
  // -----------------------------------------------------------------------
  const confirmationSection = (
    <AnalysisSection title="Status Konfirmasi Setup">
      <div className="space-y-3">
        <AnalysisValue
          label="Konfirmasi Entry Terpenuhi"
          value={displayBool(p.entry_assessment.entry_confirmation_met)}
        />
        <AnalysisValue
          label="Revisi Entry Diajukan"
          value={displayBool(p.entry_assessment.revised_entry_proposed)}
        />
        {p.entry_assessment.proposed_entry_type && (
          <AnalysisValue
            label="Tipe Entry Diusulkan"
            value={enumLabel("entry_type", p.entry_assessment.proposed_entry_type)}
          />
        )}
        {p.entry_assessment.proposed_entry_price != null && (
          <AnalysisValue
            label="Harga Entry Diusulkan"
            value={currency(p.entry_assessment.proposed_entry_price)}
          />
        )}
        {p.entry_assessment.proposed_entry_zone_low != null &&
          p.entry_assessment.proposed_entry_zone_high != null && (
            <AnalysisValue
              label="Zona Entry Diusulkan"
              value={`${currency(p.entry_assessment.proposed_entry_zone_low)} – ${currency(p.entry_assessment.proposed_entry_zone_high)}`}
            />
          )}
        <AnalysisValue
          label="Entry Confirmation Terlihat di Orderbook"
          value={displayBool(
            (p.orderbook_analysis as Record<string, unknown>)
              .entry_confirmation_visible as boolean | null | undefined,
          )}
        />
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 5. Chase Risk
  // -----------------------------------------------------------------------
  const chaseRiskSection = (
    <AnalysisSection title="Risiko Mengejar Harga">
      <div className="space-y-3">
        <AnalysisValue
          label="Risiko Kejar Harga"
          value={enumLabel("chase_risk", p.entry_assessment.chase_risk)}
        />
        <AnalysisValue
          label="Harga Sudah Terlalu Jauh"
          value={displayBool(p.entry_assessment.price_already_extended)}
        />
        <AnalysisValue
          label="Max Acceptable Entry"
          value={currency(p.entry_assessment.maximum_acceptable_entry)}
        />
        <AnalysisValue
          label="Harga Saat Ini"
          value={currency(p.entry_assessment.current_price)}
        />
        {p.trading_plan.do_not_chase_condition && (
          <AnalysisValue
            label="Jangan Kejar Jika"
            value={p.trading_plan.do_not_chase_condition}
          />
        )}
        <AnalysisValue
          label="Kondisi Tunggu"
          value={p.entry_assessment.wait_condition ?? "—"}
        />
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 6. Proposed Levels
  // -----------------------------------------------------------------------
  const proposedLevelsSection = (
    <AnalysisSection title="Level Harga yang Diusulkan">
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
        {p.price_levels.reference_entry && (
          <AnalysisValue
            label="Referensi Entry"
            value={`${currency(p.price_levels.reference_entry.price)} — ${p.price_levels.reference_entry.summary}`}
          />
        )}
        {p.price_levels.maximum_acceptable_entry && (
          <AnalysisValue
            label="Max Acceptable Entry"
            value={`${currency(p.price_levels.maximum_acceptable_entry.price)} — ${p.price_levels.maximum_acceptable_entry.summary}`}
          />
        )}
        {p.price_levels.proposed_stop_loss && (
          <AnalysisValue
            label="Stop Loss Diusulkan"
            value={`${currency(p.price_levels.proposed_stop_loss.price)} — ${p.price_levels.proposed_stop_loss.summary}`}
          />
        )}
        {p.price_levels.proposed_target && (
          <AnalysisValue
            label="Target Diusulkan"
            value={`${currency(p.price_levels.proposed_target.price)} — ${p.price_levels.proposed_target.summary}`}
          />
        )}
        {p.price_levels.invalidation_level && (
          <AnalysisValue
            label="Level Invalidasi"
            value={`${currency(p.price_levels.invalidation_level.price)} — ${p.price_levels.invalidation_level.summary}`}
          />
        )}
        <p className="text-xs italic text-zinc-400">
          Usulan AI, belum menjadi nilai terkonfirmasi.
        </p>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // 7. Recommended Action
  // -----------------------------------------------------------------------
  const recommendedActionSection = (
    <AnalysisSection title="Tindakan yang Direkomendasikan">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-2">
          <AnalysisValue
            label="Tindakan"
            value={enumLabel("recommended_action", p.trading_plan.current_action)}
          />
          <AnalysisValue
            label="Konfirmasi Pengguna Diperlukan"
            value={displayBool(p.trading_plan.requires_user_confirmation)}
          />
        </div>
        <AnalysisValue
          label="Alasan"
          value={p.trading_plan.action_rationale}
        />
        <AnalysisValue
          label="Kondisi Entry"
          value={p.trading_plan.entry_condition ?? "—"}
        />
        <AnalysisValue
          label="Kondisi Tunggu"
          value={p.trading_plan.wait_condition ?? "—"}
        />
        <AnalysisValue
          label="Batalkan Setup Jika"
          value={p.trading_plan.cancel_setup_condition ?? "—"}
        />
        <AnalysisValue
          label="Checkpoint Berikutnya"
          value={p.trading_plan.next_checkpoint ?? "—"}
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
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // AI Assessment / Probability & Confidence
  // -----------------------------------------------------------------------
  const probabilitySection = (
    <AnalysisSection title="Probabilitas dan Keyakinan">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue
            label="Keyakinan"
            value={percentage(p.ai_assessment.confidence)}
          />
          <AnalysisValue
            label="Probabilitas Entry"
            value={percentage(p.ai_assessment.entry_probability)}
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
  );

  // -----------------------------------------------------------------------
  // Market Snapshot / Today Summary
  // -----------------------------------------------------------------------
  const md = p.market_snapshot as Record<string, unknown>;
  const td = p.today_summary as Record<string, unknown>;
  const marketSection = (
    <AnalysisSection title="Ringkasan Pasar Hari Ini">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue label="Open" value={currency(md.open as number | null)} />
          <AnalysisValue label="High" value={currency(md.high as number | null)} />
          <AnalysisValue label="Low" value={currency(md.low as number | null)} />
          <AnalysisValue label="Last" value={currency(md.last as number | null)} />
          <AnalysisValue label="Rata-rata" value={currency(td.average as number | null)} />
          <AnalysisValue
            label="Perubahan (%)"
            value={percentage(td.change_percentage as number | null)}
          />
        </div>
        <AnalysisValue
          label="Posisi dalam Rentang Hari Ini"
          value={enumLabel(
            "setup_status",
            (td.position_in_daily_range as string) ?? null,
          )}
        />
        {td.distance_from_reference_entry_percentage != null && (
          <AnalysisValue
            label="Jarak dari Referensi Entry (%)"
            value={percentage(td.distance_from_reference_entry_percentage as number)}
          />
        )}
        <div className="text-sm">
          <span className="text-zinc-400">Ringkasan</span>
          <p className="mt-1 text-zinc-800">
            {String(td.summary ?? md.summary ?? "—")}
          </p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // Orderbook
  // -----------------------------------------------------------------------
  const ob = p.orderbook_analysis as Record<string, unknown>;
  const orderbookSection = (
    <AnalysisSection title="Orderbook">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-2">
          <AnalysisValue
            label="Kekuatan Buyer"
            value={enumLabel("buyer_strength", (ob.buyer_strength as string) ?? null)}
          />
          <AnalysisValue
            label="Tekanan Seller"
            value={enumLabel("seller_pressure", (ob.seller_pressure as string) ?? null)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <AnalysisValue label="Best Bid" value={ob.best_bid as number | null} />
          <AnalysisValue label="Best Offer" value={ob.best_offer as number | null} />
        </div>
        {!!ob.bid_support && (
          <div className="text-sm">
            <span className="text-zinc-400">Support Bid</span>
            <p className="text-zinc-800">
              {(ob.bid_support as PriceLevel).price as number} —{" "}
              {(ob.bid_support as PriceLevel).summary as string}
            </p>
          </div>
        )}
        {!!ob.offer_resistance && (
          <div className="text-sm">
            <span className="text-zinc-400">Resistance Offer</span>
            <p className="text-zinc-800">
              {(ob.offer_resistance as PriceLevel).price as number} —{" "}
              {(ob.offer_resistance as PriceLevel).summary as string}
            </p>
          </div>
        )}
        {((ob.buyer_observations as string[]) ?? []).length > 0 && (
          <div className="text-sm">
            <span className="text-zinc-400">Observasi Buyer</span>
            <ul className="mt-1 list-inside list-disc text-zinc-800">
              {(ob.buyer_observations as string[]).map((o: string, i: number) => (
                <li key={i}>{o}</li>
              ))}
            </ul>
          </div>
        )}
        <AnalysisValue
          label="Mendukung Entry"
          value={displayBool(ob.supports_entry as boolean | null)}
        />
        <div className="text-sm">
          <span className="text-zinc-400">Kesimpulan</span>
          <p className="mt-1 text-zinc-800">{String(ob.conclusion ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // Chart Update
  // -----------------------------------------------------------------------
  const cu = p.chart_update as Record<string, unknown>;
  const chartSection = (
    <AnalysisSection title="Pembaruan Chart">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <AnalysisValue
            label="Tren Jangka Pendek"
            value={enumLabel("short_term_trend", (cu.short_term_trend as string) ?? null)}
          />
          <AnalysisValue
            label="Tren Jangka Menengah"
            value={enumLabel("medium_term_trend", (cu.medium_term_trend as string) ?? null)}
          />
          <AnalysisValue
            label="Struktur"
            value={enumLabel("setup_status", (cu.structure_status as string) ?? null)}
          />
        </div>
        {!!cu.nearest_support && (
          <div className="text-sm">
            <span className="text-zinc-400">Support Terdekat</span>
            <p className="text-zinc-800">
              {(cu.nearest_support as PriceLevel).price as number} —{" "}
              {(cu.nearest_support as PriceLevel).summary as string}
            </p>
          </div>
        )}
        {!!cu.nearest_resistance && (
          <div className="text-sm">
            <span className="text-zinc-400">Resistance Terdekat</span>
            <p className="text-zinc-800">
              {(cu.nearest_resistance as PriceLevel).price as number} —{" "}
              {(cu.nearest_resistance as PriceLevel).summary as string}
            </p>
          </div>
        )}
        <div className="text-sm">
          <span className="text-zinc-400">Kesimpulan</span>
          <p className="mt-1 text-zinc-800">{String(cu.conclusion ?? "—")}</p>
        </div>
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // Warnings
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
                  {p.warnings_and_missing_information.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
            {p.warnings_and_missing_information.missing_information.length > 0 && (
              <div className="text-sm">
                <span className="text-zinc-400">Informasi yang Tidak Tersedia</span>
                <ul className="mt-1 list-inside list-disc text-zinc-600">
                  {p.warnings_and_missing_information.missing_information.map(
                    (m, i) => <li key={i}>{m}</li>,
                  )}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </AnalysisSection>
  );

  // -----------------------------------------------------------------------
  // Render all sections
  // -----------------------------------------------------------------------
  return (
    <div className="space-y-4">
      {setupSection}
      {comparisonSection}
      {entryValiditySection}
      {confirmationSection}
      {chaseRiskSection}
      {proposedLevelsSection}
      {recommendedActionSection}
      {probabilitySection}
      {marketSection}
      {orderbookSection}
      {chartSection}
      {warningsSection}
    </div>
  );
}
