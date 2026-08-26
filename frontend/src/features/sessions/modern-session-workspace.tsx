"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  analyzeSession,
  buyDecision,
  getSessionWorkspaceData,
  skipDecision,
  waitDecision,
} from "@/features/trade-workspace/api";
import type { SkipReason, TradeSession } from "@/features/trade-workspace/types";

type ActionType = "BUY" | "WAIT" | "SKIP";

export function ModernSessionWorkspace({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<TradeSession | null>(null);
  const [analysis, setAnalysis] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Modal states
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [showSkipModal, setShowSkipModal] = useState(false);
  const [buyPrice, setBuyPrice] = useState("");
  const [buyLots, setBuyLots] = useState("10");
  const [submittingAction, setSubmittingAction] = useState(false);

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setEvaluating(true);
    else setLoading(true);
    setError(null);

    try {
      if (isRefresh) {
        const freshAnalysis = await analyzeSession(sessionId);
        setAnalysis(freshAnalysis);
        const data = await getSessionWorkspaceData(sessionId);
        setSession(data.session);
      } else {
        const data = await getSessionWorkspaceData(sessionId);
        setSession(data.session);
        setAnalysis(data.analysis);
      }
    } catch (err: any) {
      setError(err?.message || "Gagal memuat data workspace sesi.");
    } finally {
      setLoading(false);
      setEvaluating(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  const handleBuy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;
    setSubmittingAction(true);
    setError(null);
    try {
      const price = buyPrice || String(analysis?.key_levels?.current_price || "0");
      const target = String(analysis?.key_levels?.target_price_1 || "0");
      const sl = String(analysis?.key_levels?.stop_loss || "0");

      await buyDecision(session.id, {
        entry_price: price,
        entry_timestamp: new Date().toISOString(),
        quantity: buyLots,
        stop_loss: sl,
        target_price: target,
        note: `BUY dieksekusi pada harga Rp ${price} (${buyLots} lot)`,
      });

      setShowBuyModal(false);
      setActionSuccess(`Posisi BUY berhasil dicatat untuk ${session.ticker} sebanyak ${buyLots} lot!`);
      loadData(false);
    } catch (err: any) {
      setError(err?.message || "Gagal mencatat keputusan BUY.");
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleWait = async () => {
    if (!session) return;
    setSubmittingAction(true);
    setError(null);
    try {
      await waitDecision(session.id);
      setActionSuccess(`Status sesi ${session.ticker} berhasil diubah ke WAITING (Pantau Setup).`);
      loadData(false);
    } catch (err: any) {
      setError(err?.message || "Gagal mencatat keputusan WAIT.");
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleSkip = async (reason: SkipReason) => {
    if (!session) return;
    setSubmittingAction(true);
    setError(null);
    try {
      await skipDecision(session.id, {
        reason,
        note: `Setup ${session.ticker} dilewati (${reason}).`,
      });
      setShowSkipModal(false);
      setActionSuccess(`Sesi ${session.ticker} berhasil di-SKIP dan ditutup.`);
      loadData(false);
    } catch (err: any) {
      setError(err?.message || "Gagal mencatat keputusan SKIP.");
    } finally {
      setSubmittingAction(false);
    }
  };

  if (loading) {
    return (
      <main className="mx-auto min-w-0 w-full max-w-[var(--layout-application-max)] px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-[var(--color-action-primary)] border-t-transparent mb-4" />
          <h2 className="text-xl font-bold text-[var(--color-text-strong)]">Mempersiapkan Workspace AI…</h2>
          <p role="status" className="text-sm text-[var(--color-text-muted)] mt-1">
            Memuat konteks sesi…
          </p>
        </div>
      </main>
    );
  }

  const snapshot = analysis?.market_evidence;
  const quote = snapshot?.quote;
  const orderbook = snapshot?.orderbook;
  const foreignFlow = snapshot?.foreign_flow;
  const brokerFlow = snapshot?.broker_flow;
  const keyLevels = analysis?.key_levels;
  const reasoning = analysis?.reasoning;
  const action: ActionType = analysis?.action || "WAIT";

  const actionColors: Record<ActionType, { badge: string; border: string; bg: string; text: string }> = {
    BUY: {
      badge: "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
      border: "border-emerald-500/40",
      bg: "bg-emerald-500/5",
      text: "text-emerald-600 dark:text-emerald-400",
    },
    WAIT: {
      badge: "bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30",
      border: "border-amber-500/40",
      bg: "bg-amber-500/5",
      text: "text-amber-600 dark:text-amber-400",
    },
    SKIP: {
      badge: "bg-rose-500/20 text-rose-600 dark:text-rose-400 border-rose-500/30",
      border: "border-rose-500/40",
      bg: "bg-rose-500/5",
      text: "text-rose-600 dark:text-rose-400",
    },
  };

  const currentTheme = actionColors[action] || actionColors.WAIT;

  return (
    <main className="mx-auto min-w-0 w-full max-w-[var(--layout-application-max)] px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Top Nav & Breadcrumbs */}
      <div className="flex items-center justify-between">
        <Link
          href="/sessions"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--color-action-primary)] hover:underline"
        >
          ← Kembali ke Daftar Sesi
        </Link>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-surface-muted)] px-3 py-1 text-xs font-semibold text-[var(--color-text-muted)] border border-[var(--color-border-subtle)]">
            🎯 {analysis?.trading_style || "Swing Trade"}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-surface-muted)] px-3 py-1 text-xs font-bold text-[var(--color-text-strong)] border border-[var(--color-border-subtle)]">
            STATUS: {session?.status || "ANALYZED"}
          </span>
        </div>
      </div>

      {/* Notifications */}
      {actionSuccess ? (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-600 dark:text-emerald-400 font-semibold">
          ✓ {actionSuccess}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-600 dark:text-rose-400 font-semibold">
          ⚠️ {error}
        </div>
      ) : null}

      {/* Header Card */}
      <section className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 sm:p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-extrabold text-[var(--color-text-strong)] tracking-tight">
                {session?.ticker || "EMITEN"}
              </h1>
              <span className={`rounded-md border px-2.5 py-0.5 text-xs font-bold uppercase ${currentTheme.badge}`}>
                REKOMENDASI: {action}
              </span>
            </div>
            <p className="text-sm text-[var(--color-text-muted)] mt-1">
              {session?.company_name || "Perusahaan Tercatat di BEI (IDX)"} • Sesi ID: {sessionId.slice(0, 8)}
            </p>
          </div>

          <button
            type="button"
            onClick={() => loadData(true)}
            disabled={evaluating}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 py-2 text-sm font-bold text-[var(--color-text-strong)] shadow-sm hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
          >
            {evaluating ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-action-primary)] border-t-transparent" />
                Mengevaluasi Ulang…
              </>
            ) : (
              <>⚡ Refresh Data & Re-Evaluasi</>
            )}
          </button>
        </div>
      </section>

      {/* 4-Card ZAPI Live Evidence Grid */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {/* Metric 1: Harga Terkini */}
        <div className="rounded-[var(--radius-large)] border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-sm">
          <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase">Harga Terkini</span>
          <p className="mt-1 text-2xl font-black text-[var(--color-text-strong)]">
            Rp {quote?.last_price ? Number(quote.last_price).toLocaleString("id-ID") : "-"}
          </p>
          <div className="mt-1 flex items-center gap-1.5 text-xs">
            <span
              className={`font-bold ${
                (quote?.change_percent ?? 0) >= 0
                  ? "text-[var(--color-status-success)]"
                  : "text-[var(--color-status-danger)]"
              }`}
            >
              {(quote?.change_percent ?? 0) >= 0 ? "+" : ""}
              {(quote?.change_percent ?? 0).toFixed(2)}%
            </span>
            <span className="text-[var(--color-text-muted)]">(Hari Ini)</span>
          </div>
        </div>

        {/* Metric 2: Orderbook Depth */}
        <div className="rounded-[var(--radius-large)] border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-sm">
          <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase">Orderbook Depth</span>
          <p className="mt-1 text-2xl font-black text-[var(--color-text-strong)]">
            {orderbook?.bid_ask_ratio ? Number(orderbook.bid_ask_ratio).toFixed(2) : "1.00"}x
          </p>
          <p className="mt-1 text-xs text-[var(--color-text-muted)]">
            Spread: Rp {orderbook?.spread ? Number(orderbook.spread).toLocaleString("id-ID") : "0"}
          </p>
        </div>

        {/* Metric 3: Foreign Flow */}
        <div className="rounded-[var(--radius-large)] border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-sm">
          <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase">Foreign Flow</span>
          <p
            className={`mt-1 text-lg sm:text-xl font-black uppercase truncate ${
              foreignFlow?.foreign_status === "ACCUMULATION" || foreignFlow?.foreign_status === "BIG_ACCUMULATION"
                ? "text-[var(--color-status-success)]"
                : foreignFlow?.foreign_status === "DISTRIBUTION"
                  ? "text-[var(--color-status-danger)]"
                  : "text-[var(--color-text-strong)]"
            }`}
          >
            {foreignFlow?.foreign_status || "NEUTRAL"}
          </p>
          <p className="mt-1 text-xs text-[var(--color-text-muted)] truncate">
            {foreignFlow?.monthly_1m?.net_shares
              ? `1M: ${(Number(foreignFlow.monthly_1m.net_shares) / 1_000_000).toFixed(1)}M lbr`
              : "Multi-Horizon Flow"}
          </p>
        </div>

        {/* Metric 4: Bandarmology */}
        <div className="rounded-[var(--radius-large)] border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-sm">
          <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase">Bandarmology</span>
          <p
            className={`mt-1 text-lg sm:text-xl font-black uppercase truncate ${
              brokerFlow?.bandar_status === "ACCUMULATION" || brokerFlow?.bandar_status === "BIG_ACCUMULATION"
                ? "text-[var(--color-status-success)]"
                : brokerFlow?.bandar_status === "DISTRIBUTION"
                  ? "text-[var(--color-status-danger)]"
                  : "text-[var(--color-text-strong)]"
            }`}
          >
            {brokerFlow?.bandar_status || "NEUTRAL"}
          </p>
          <p className="mt-1 text-xs text-[var(--color-text-muted)] truncate">
            Top3: {brokerFlow?.top3_buyer_concentration_percent ? `${brokerFlow.top3_buyer_concentration_percent}%` : "Konsentrasi 1D"}
          </p>
        </div>
      </section>

      {/* Hero AI Recommendation & Key Levels */}
      <section className={`rounded-[var(--radius-large)] border ${currentTheme.border} ${currentTheme.bg} p-5 sm:p-6 shadow-sm space-y-6`}>
        {/* Recommendation Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-border-subtle)] pb-4">
          <div>
            <span className="text-xs font-bold tracking-wider text-[var(--color-text-muted)] uppercase">
              REKOMENDASI TRADING AI (GEMINI ENGINE)
            </span>
            <div className="mt-1 flex items-center gap-3">
              <span className={`text-3xl font-black tracking-tight ${currentTheme.text}`}>
                {action === "BUY" ? "🚀 BUY (BELI)" : action === "WAIT" ? "⏳ WAIT (PANTAU)" : "⏭️ SKIP (LEWATI)"}
              </span>
              <span className="rounded-full bg-[var(--color-surface-standard)] px-3 py-1 text-xs font-bold text-[var(--color-text-strong)] border border-[var(--color-border-subtle)] shadow-xs">
                Kualitas: {analysis?.signal_quality || "HIGH"} • Akurasi: {Math.round((analysis?.confidence_score || 0.8) * 100)}%
              </span>
            </div>
          </div>
        </div>

        {/* 2x2 Key Price Grid */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
            <span className="text-xs font-semibold text-[var(--color-text-muted)]">🎯 AREA ENTRY (BELI)</span>
            <p className="mt-1 text-lg sm:text-xl font-bold text-[var(--color-text-strong)]">
              Rp {keyLevels?.entry_range?.[0]?.toLocaleString("id-ID") ?? "-"} - {keyLevels?.entry_range?.[1]?.toLocaleString("id-ID") ?? "-"}
            </p>
            <span className="text-xs text-[var(--color-text-muted)]">Optimal Buy Range</span>
          </div>

          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">🚀 TARGET PROFIT (TP)</span>
            <p className="mt-1 text-lg sm:text-xl font-bold text-emerald-600 dark:text-emerald-400">
              TP1: Rp {keyLevels?.target_price_1?.toLocaleString("id-ID") ?? "-"}
            </p>
            <span className="text-xs text-[var(--color-text-muted)]">
              TP2: Rp {keyLevels?.target_price_2?.toLocaleString("id-ID") ?? "-"}
            </span>
          </div>

          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
            <span className="text-xs font-semibold text-rose-600 dark:text-rose-400">🛑 STOP LOSS (SL)</span>
            <p className="mt-1 text-lg sm:text-xl font-bold text-rose-600 dark:text-rose-400">
              Rp {keyLevels?.stop_loss?.toLocaleString("id-ID") ?? "-"}
            </p>
            <span className="text-xs text-[var(--color-text-muted)]">
              Invalidasi: Rp {keyLevels?.invalidation_level?.toLocaleString("id-ID") ?? "-"}
            </span>
          </div>

          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
            <span className="text-xs font-semibold text-[var(--color-text-muted)]">⚖️ RISK / REWARD</span>
            <p className="mt-1 text-lg sm:text-xl font-bold text-[var(--color-text-strong)]">
              1 : {keyLevels?.risk_reward_ratio ?? "2.0"}
            </p>
            <span className="text-xs text-[var(--color-text-muted)]">
              ATR(14): Rp {keyLevels?.atr14 ?? "0"}
            </span>
          </div>
        </div>

        {/* AI Detailed Reasoning Thesis */}
        <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-5 space-y-4 shadow-xs">
          <div>
            <h3 className="text-sm font-bold text-[var(--color-text-strong)] uppercase tracking-wide">
              💡 Analisa Setup & Tesis AI:
            </h3>
            <p className="mt-1.5 text-sm text-[var(--color-text-default)] leading-relaxed">
              {reasoning?.thesis || "Analisa setup berbasis konfluensi teknikal dan flow pasar bursa."}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 pt-2 border-t border-[var(--color-border-subtle)]">
            <div>
              <h4 className="text-xs font-bold text-[var(--color-text-strong)]">📈 Analisa Teknikal:</h4>
              <p className="mt-1 text-xs text-[var(--color-text-muted)] leading-relaxed">
                {reasoning?.technical_analysis || "-"}
              </p>
            </div>
            <div>
              <h4 className="text-xs font-bold text-[var(--color-text-strong)]">🏦 Foreign Flow & Bandarmology:</h4>
              <p className="mt-1 text-xs text-[var(--color-text-muted)] leading-relaxed">
                {reasoning?.flow_analysis || "-"}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-[var(--color-border-subtle)]">
            <h4 className="text-xs font-bold text-rose-600 dark:text-rose-400">⚠️ Manajemen Risiko & Invalidasi:</h4>
            <p className="mt-1 text-xs text-[var(--color-text-muted)] leading-relaxed">
              {reasoning?.risk_factors || "-"}
            </p>
          </div>
        </div>
      </section>

      {/* Sticky Bottom Action Controls */}
      <section className="sticky bottom-4 z-20 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)]/95 backdrop-blur-md p-4 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-[var(--color-text-muted)]">
            <span className="font-semibold text-[var(--color-text-strong)]">Aksi Cepat:</span> Eksekusi atau pantau setup emiten ini
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={() => {
                setBuyPrice(String(keyLevels?.current_price || ""));
                setShowBuyModal(true);
              }}
              disabled={submittingAction}
              className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-emerald-600 px-6 text-sm font-bold text-white shadow-sm hover:bg-emerald-700 focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
            >
              🚀 BUY
            </button>

            <button
              type="button"
              onClick={handleWait}
              disabled={submittingAction}
              className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-amber-600 px-5 text-sm font-bold text-white shadow-sm hover:bg-amber-700 focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
            >
              ⏳ WAIT
            </button>

            <button
              type="button"
              onClick={() => setShowSkipModal(true)}
              disabled={submittingAction}
              className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/20 focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
            >
              ⏭️ SKIP
            </button>
          </div>
        </div>
      </section>

      {/* Buy Modal */}
      {showBuyModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-6 shadow-xl space-y-4">
            <h3 className="text-xl font-bold text-[var(--color-text-strong)]">
              🚀 Eksekusi Posisi BUY - {session?.ticker}
            </h3>
            <form onSubmit={handleBuy} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] uppercase">
                  Harga Beli (Rp)
                </label>
                <input
                  type="number"
                  value={buyPrice}
                  onChange={(e) => setBuyPrice(e.target.value)}
                  placeholder={String(keyLevels?.current_price || "0")}
                  required
                  className="mt-1 w-full rounded-md border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-base font-bold text-[var(--color-text-strong)]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] uppercase">
                  Jumlah Lot
                </label>
                <input
                  type="number"
                  value={buyLots}
                  onChange={(e) => setBuyLots(e.target.value)}
                  min="1"
                  required
                  className="mt-1 w-full rounded-md border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-base font-bold text-[var(--color-text-strong)]"
                />
              </div>

              <div className="rounded-lg bg-[var(--color-surface-muted)] p-3 text-xs text-[var(--color-text-muted)] space-y-1">
                <div className="flex justify-between">
                  <span>Take Profit 1:</span>
                  <span className="font-bold text-emerald-600">Rp {keyLevels?.target_price_1?.toLocaleString("id-ID")}</span>
                </div>
                <div className="flex justify-between">
                  <span>Stop Loss:</span>
                  <span className="font-bold text-rose-600">Rp {keyLevels?.stop_loss?.toLocaleString("id-ID")}</span>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowBuyModal(false)}
                  className="rounded-md border border-[var(--color-border-default)] px-4 py-2 text-sm font-semibold text-[var(--color-text-strong)]"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="rounded-md bg-emerald-600 px-6 py-2 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {submittingAction ? "Menyimpan…" : "Konfirmasi BUY"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {/* Skip Modal */}
      {showSkipModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-6 shadow-xl space-y-4">
            <h3 className="text-xl font-bold text-[var(--color-text-strong)]">
              ⏭️ Lewati Saham ({session?.ticker})
            </h3>
            <p className="text-xs text-[var(--color-text-muted)]">
              Pilih alasan utama mengapa setup ini dilewati untuk pencatatan trading journal:
            </p>

            <div className="grid gap-2">
              <button
                type="button"
                onClick={() => handleSkip("RISK_TOO_HIGH")}
                className="rounded-lg border border-[var(--color-border-default)] p-3 text-left text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)]"
              >
                🛑 Risiko Terlalu Tinggi / R:R Tidak Masuk
              </button>
              <button
                type="button"
                onClick={() => handleSkip("ORDERBOOK_WEAK")}
                className="rounded-lg border border-[var(--color-border-default)] p-3 text-left text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)]"
              >
                📉 Orderbook Lemah / Likuiditas Rendah
              </button>
              <button
                type="button"
                onClick={() => handleSkip("MARKET_CONDITION_UNFAVORABLE")}
                className="rounded-lg border border-[var(--color-border-default)] p-3 text-left text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)]"
              >
                🏦 Kondisi IHSG / Distribusi Asing Masif
              </button>
              <button
                type="button"
                onClick={() => handleSkip("SETUP_NOT_ATTRACTIVE")}
                className="rounded-lg border border-[var(--color-border-default)] p-3 text-left text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)]"
              >
                🔍 Setup Pola Tidak Menarik
              </button>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setShowSkipModal(false)}
                className="rounded-md border border-[var(--color-border-default)] px-4 py-2 text-sm font-semibold text-[var(--color-text-strong)]"
              >
                Batal
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
