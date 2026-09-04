"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ButtonSpinner } from "@/components/button-spinner";
import {
  analyzeSession,
  archiveSessionV2,
  buyDecision,
  closePosition,
  getSessionWorkspaceData,
  restoreSessionV2,
  skipDecision,
  waitDecision,
} from "@/features/trade-workspace/api";
import type { SkipReason, TradeSession } from "@/features/trade-workspace/types";

type ActionType = "BUY" | "WAIT" | "SKIP" | "HOLD" | "TAKE_PROFIT" | "CUT_LOSS" | "TRAILING_STOP";

export function ModernSessionWorkspace({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<TradeSession | null>(null);
  const [analysis, setAnalysis] = useState<any | null>(null);
  const [position, setPosition] = useState<any | null>(null);
  const [closure, setClosure] = useState<any | null>(null);
  const [decision, setDecision] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Modal states
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [showSkipModal, setShowSkipModal] = useState(false);
  const [showCloseModal, setShowCloseModal] = useState(false);

  const [buyPrice, setBuyPrice] = useState("");
  const [buyLots, setBuyLots] = useState("10");

  const [closePrice, setClosePrice] = useState("");
  const [closeReason, setCloseReason] = useState("MANUAL");
  const [closeNote, setCloseNote] = useState("");

  const [submittingAction, setSubmittingAction] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [skipPendingReason, setSkipPendingReason] = useState<SkipReason | null>(null);

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setEvaluating(true);
    else setLoading(true);
    setError(null);

    try {
      if (isRefresh) {
        const freshAnalysis = await analyzeSession(sessionId);
        setAnalysis(freshAnalysis);
        const data: any = await getSessionWorkspaceData(sessionId, true);
        setSession(data.session);
        setPosition(data.position);
        setClosure(data.closure);
        setDecision(data.decision);
        setActionSuccess(`Data pasar & analisa AI ${data.session?.ticker || ""} berhasil diperbarui ke harga terkini!`);
      } else {
        const data: any = await getSessionWorkspaceData(sessionId, false);
        setSession(data.session);
        setAnalysis(data.analysis);
        setPosition(data.position);
        setClosure(data.closure);
        setDecision(data.decision);
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
      setActionSuccess(`Posisi BUY berhasil dibuka untuk ${session.ticker} sebanyak ${buyLots} lot! Mode Monitoring Aktif.`);
      loadData(false);
    } catch (err: any) {
      setError(err?.message || "Gagal mencatat keputusan BUY.");
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleClosePosition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;
    setSubmittingAction(true);
    setError(null);
    try {
      const p = closePrice || String(quote?.last_price || position?.entry_price || "0");
      await closePosition(session.id, {
        close_price: p,
        close_timestamp: new Date().toISOString(),
        close_reason: closeReason,
        note: closeNote || `Tutup posisi ${session.ticker} pada Rp ${p} (${closeReason})`,
      });

      setShowCloseModal(false);
      setActionSuccess(`Posisi ${session.ticker} berhasil ditutup!`);
      loadData(false);
    } catch (err: any) {
      setError(err?.message || "Gagal menutup posisi.");
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleWait = async () => {
    if (!session) return;
    setIsWaiting(true);
    setSubmittingAction(true);
    setError(null);
    try {
      await waitDecision(session.id);
      setActionSuccess(`Status sesi ${session.ticker} berhasil diubah ke WAITING (Pantau Setup).`);
      loadData(false);
    } catch (err: any) {
      setError(err?.message || "Gagal mencatat keputusan WAIT.");
    } finally {
      setIsWaiting(false);
      setSubmittingAction(false);
    }
  };

  const handleSkip = async (reason: SkipReason) => {
    if (!session) return;
    setSkipPendingReason(reason);
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
      setSkipPendingReason(null);
      setSubmittingAction(false);
    }
  };

  const handleArchive = async () => {
    if (!session) return;
    setIsArchiving(true);
    setSubmittingAction(true);
    setError(null);
    try {
      await archiveSessionV2(session.id);
      setActionSuccess(`Sesi ${session.ticker} berhasil diarsipkan ke halaman riwayat!`);
      loadData(false);
    } catch (err: any) {
      setError(err?.message || "Gagal mengarsipkan sesi.");
    } finally {
      setIsArchiving(false);
      setSubmittingAction(false);
    }
  };

  const handleRestore = async () => {
    if (!session) return;
    setIsRestoring(true);
    setSubmittingAction(true);
    setError(null);
    try {
      await restoreSessionV2(session.id);
      setActionSuccess(`Sesi ${session.ticker} berhasil dipulihkan dari arsip!`);
      loadData(false);
    } catch (err: any) {
      setError(err?.message || "Gagal memulihkan sesi dari arsip.");
    } finally {
      setIsRestoring(false);
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

  const currentPrice = Number(quote?.last_price || keyLevels?.current_price || 0);

  // Position PnL Calculations
  const entryPrice = position ? Number(position.entry_price) : 0;
  const quantityLots = position ? Number(position.quantity) : 0;
  const totalShares = quantityLots * 100;
  const capitalInvested = entryPrice * totalShares;
  const currentValue = currentPrice * totalShares;
  const floatingPnL = currentValue - capitalInvested;
  const floatingPnLPercent = capitalInvested > 0 ? (floatingPnL / capitalInvested) * 100 : 0;

  const isInTrade = session?.status === "OPEN_POSITION" || Boolean(position && position.status === "OPEN") || Boolean(analysis?.is_in_trade);

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
    HOLD: {
      badge: "bg-teal-500/20 text-teal-600 dark:text-teal-400 border-teal-500/30",
      border: "border-teal-500/40",
      bg: "bg-teal-500/5",
      text: "text-teal-600 dark:text-teal-400",
    },
    TAKE_PROFIT: {
      badge: "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 animate-pulse",
      border: "border-emerald-500/50",
      bg: "bg-emerald-500/10",
      text: "text-emerald-600 dark:text-emerald-400",
    },
    CUT_LOSS: {
      badge: "bg-rose-500/20 text-rose-600 dark:text-rose-400 border-rose-500/30 animate-pulse",
      border: "border-rose-500/50",
      bg: "bg-rose-500/10",
      text: "text-rose-600 dark:text-rose-400",
    },
    TRAILING_STOP: {
      badge: "bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30",
      border: "border-blue-500/40",
      bg: "bg-blue-500/5",
      text: "text-blue-600 dark:text-blue-400",
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
          {session?.archived_at ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-zinc-500/20 px-3 py-1 text-xs font-bold text-[var(--color-text-strong)] border border-zinc-500/30">
              📦 DIARSIPKAN
            </span>
          ) : null}
          <span
            className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-bold border ${
              session?.status === "OPEN_POSITION"
                ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/40"
                : session?.status === "CLOSED_SKIPPED" || session?.status === "CLOSED"
                  ? "bg-rose-500/10 text-rose-600 border-rose-500/30"
                  : session?.status === "WAITING"
                    ? "bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/40"
                    : "bg-[var(--color-surface-muted)] text-[var(--color-text-strong)] border-[var(--color-border-subtle)]"
            }`}
          >
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

      {/* ACTIVE POSITION CARD (IF STATUS === OPEN_POSITION) */}
      {session?.status === "OPEN_POSITION" && position ? (
        <section className="rounded-[var(--radius-large)] border-2 border-emerald-500/60 bg-emerald-500/10 p-5 sm:p-6 shadow-md space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-500/30 pb-3">
            <div className="flex items-center gap-2">
              <span className="text-xl">🚀</span>
              <h2 className="text-lg font-black text-emerald-700 dark:text-emerald-300">
                POSISI AKTIF TERBUKA (MONITORING)
              </h2>
            </div>
            <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">
              Dibuka: {position.entry_timestamp ? new Date(position.entry_timestamp).toLocaleTimeString("id-ID") : "-"}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-[var(--color-surface-standard)] p-3.5 shadow-xs border border-emerald-500/20">
              <span className="text-xs font-semibold text-[var(--color-text-muted)]">HARGA BELI (ENTRY)</span>
              <p className="mt-1 text-xl font-black text-[var(--color-text-strong)]">
                Rp {entryPrice.toLocaleString("id-ID")}
              </p>
              <span className="text-xs text-[var(--color-text-muted)]">
                {quantityLots} Lot ({totalShares.toLocaleString("id-ID")} lbr)
              </span>
            </div>

            <div className="rounded-lg bg-[var(--color-surface-standard)] p-3.5 shadow-xs border border-emerald-500/20">
              <span className="text-xs font-semibold text-[var(--color-text-muted)]">HARGA PASAR TERKINI</span>
              <p className="mt-1 text-xl font-black text-[var(--color-text-strong)]">
                Rp {currentPrice.toLocaleString("id-ID")}
              </p>
              <span className="text-xs text-[var(--color-text-muted)]">
                Modal: Rp {capitalInvested.toLocaleString("id-ID")}
              </span>
            </div>

            <div className="rounded-lg bg-[var(--color-surface-standard)] p-3.5 shadow-xs border border-emerald-500/20">
              <span className="text-xs font-semibold text-[var(--color-text-muted)]">FLOATING PnL</span>
              <p
                className={`mt-1 text-xl font-black ${
                  floatingPnL >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                }`}
              >
                {floatingPnL >= 0 ? "+" : ""}
                Rp {floatingPnL.toLocaleString("id-ID")}
              </p>
              <span
                className={`text-xs font-bold ${
                  floatingPnL >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                }`}
              >
                ({floatingPnLPercent >= 0 ? "+" : ""}
                {floatingPnLPercent.toFixed(2)}%)
              </span>
            </div>

            <div className="rounded-lg bg-[var(--color-surface-standard)] p-3.5 shadow-xs border border-emerald-500/20">
              <span className="text-xs font-semibold text-[var(--color-text-muted)]">DISIPLIN TARGET & SL</span>
              <p className="mt-1 text-sm font-bold text-emerald-600">
                TP1: Rp {position.target_price?.toLocaleString("id-ID") ?? keyLevels?.target_price_1?.toLocaleString("id-ID")}
              </p>
              <p className="text-sm font-bold text-rose-600">
                SL: Rp {position.stop_loss?.toLocaleString("id-ID") ?? keyLevels?.stop_loss?.toLocaleString("id-ID")}
              </p>
            </div>
          </div>
        </section>
      ) : null}

      {/* CLOSED / SKIPPED NOTICE (IF SESSION TERMINATED) */}
      {session?.status === "CLOSED" && closure ? (
        <section className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-muted)] p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-[var(--color-text-strong)]">✓ Ringkasan Penutupan Posisi</h3>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              Posisi ditutup pada harga <strong>Rp {closure.close_price?.toLocaleString("id-ID")}</strong> ({closure.close_reason}) dengan Realized PnL: <strong className={closure.realized_profit_loss >= 0 ? "text-emerald-600" : "text-rose-600"}>Rp {closure.realized_profit_loss?.toLocaleString("id-ID")}</strong>.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {session.archived_at ? (
              <span className="inline-flex items-center gap-1 rounded-md bg-zinc-500/20 px-3 py-1.5 text-xs font-bold text-[var(--color-text-strong)]">
                📦 Sudah Masuk Riwayat
              </span>
            ) : (
              <button
                type="button"
                onClick={handleArchive}
                disabled={submittingAction}
                className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-indigo-600 px-4 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {isArchiving ? (
                  <>
                    <ButtonSpinner className="h-3.5 w-3.5" />
                    <span>Mengarsipkan…</span>
                  </>
                ) : (
                  <>📦 Pindah ke Riwayat</>
                )}
              </button>
            )}
          </div>
        </section>
      ) : null}

      {session?.status === "CLOSED_SKIPPED" ? (
        <section className="rounded-[var(--radius-large)] border border-rose-500/30 bg-rose-500/5 p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-rose-600 dark:text-rose-400">🛑 Setup Saham Dilewati (SKIP)</h3>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              Setup emiten ini telah dilewati ({decision?.reason || "Risiko Tinggi"}) dan dicatat ke dalam journal trading.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {session.archived_at ? (
              <span className="inline-flex items-center gap-1 rounded-md bg-zinc-500/20 px-3 py-1.5 text-xs font-bold text-[var(--color-text-strong)]">
                📦 Sudah Masuk Riwayat
              </span>
            ) : (
              <button
                type="button"
                onClick={handleArchive}
                disabled={submittingAction}
                className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-indigo-600 px-4 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {isArchiving ? (
                  <>
                    <ButtonSpinner className="h-3.5 w-3.5" />
                    <span>Mengarsipkan…</span>
                  </>
                ) : (
                  <>📦 Pindah ke Riwayat</>
                )}
              </button>
            )}
          </div>
        </section>
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
                {isInTrade
                  ? action === "TAKE_PROFIT"
                    ? "STATUS: TAKE PROFIT"
                    : action === "CUT_LOSS"
                      ? "STATUS: CUT LOSS ALERT"
                      : action === "TRAILING_STOP"
                        ? "STATUS: TRAILING STOP"
                        : "STATUS: HOLD"
                  : `REKOMENDASI: ${action}`}
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

      {/* Hero AI Recommendation / Position Monitoring & Key Levels */}
      <section className={`rounded-[var(--radius-large)] border ${currentTheme.border} ${currentTheme.bg} p-5 sm:p-6 shadow-sm space-y-6`}>
        {/* Recommendation Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-border-subtle)] pb-4">
          <div>
            <span className="text-xs font-bold tracking-wider text-[var(--color-text-muted)] uppercase">
              {isInTrade ? "PENGAWALAN POSISI TRADING AI (TRADE MANAGEMENT)" : "REKOMENDASI TRADING AI (GEMINI ENGINE)"}
            </span>
            <div className="mt-1 flex items-center gap-3">
              <span className={`text-3xl font-black tracking-tight ${currentTheme.text}`}>
                {isInTrade
                  ? action === "TAKE_PROFIT"
                    ? "🎯 TAKE PROFIT (CAPAI TARGET)"
                    : action === "CUT_LOSS"
                      ? "⚠️ CUT LOSS ALERT (WASPADA)"
                      : action === "TRAILING_STOP"
                        ? "🔒 TRAILING STOP (KUNCI PROFIT)"
                        : "🛡️ HOLD (KAWAL POSISI)"
                  : action === "BUY"
                    ? "🚀 BUY (BELI)"
                    : action === "WAIT"
                      ? "⏳ WAIT (PANTAU)"
                      : "⏭️ SKIP (LEWATI)"}
              </span>
              <span className="rounded-full bg-[var(--color-surface-standard)] px-3 py-1 text-xs font-bold text-[var(--color-text-strong)] border border-[var(--color-border-subtle)] shadow-xs">
                {isInTrade
                  ? `Floating: ${floatingPnLPercent >= 0 ? "+" : ""}${floatingPnLPercent.toFixed(2)}% • Modal: Rp ${entryPrice.toLocaleString("id-ID")}`
                  : `Kualitas: ${analysis?.signal_quality || "HIGH"} • Akurasi: ${Math.round((analysis?.confidence_score || 0.8) * 100)}%`}
              </span>
            </div>
          </div>
        </div>

        {/* 2x2 Key Price Grid */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {isInTrade ? (
            <>
              {/* In-Trade Card 1: Jarak Menuju TP1 */}
              <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
                <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">🎯 JARAK MENUJU TP1</span>
                <p className="mt-1 text-lg sm:text-xl font-bold text-emerald-600 dark:text-emerald-400">
                  {keyLevels?.distance_to_tp1 !== undefined && keyLevels.distance_to_tp1 <= 0 ? (
                    "✓ TP1 TERCAPAI"
                  ) : (
                    <>Rp +{(keyLevels?.distance_to_tp1 ?? Math.max(0, (keyLevels?.target_price_1 || 0) - currentPrice)).toLocaleString("id-ID")}</>
                  )}
                </p>
                <span className="text-xs text-[var(--color-text-muted)]">
                  {keyLevels?.distance_to_tp1_percent !== undefined
                    ? `${keyLevels.distance_to_tp1_percent > 0 ? "+" : ""}${keyLevels.distance_to_tp1_percent}% lagi ke TP1`
                    : `TP1: Rp ${(keyLevels?.target_price_1 || 0).toLocaleString("id-ID")}`}
                </span>
              </div>

              {/* In-Trade Card 2: Target Profit (TP) */}
              <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
                <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">🚀 TARGET PROFIT (TP)</span>
                <p className="mt-1 text-lg sm:text-xl font-bold text-emerald-600 dark:text-emerald-400">
                  TP1: Rp {(keyLevels?.target_price_1 || position?.target_price || 0).toLocaleString("id-ID")}
                </p>
                <span className="text-xs text-[var(--color-text-muted)]">
                  TP2: Rp {(keyLevels?.target_price_2 || 0).toLocaleString("id-ID")}
                </span>
              </div>

              {/* In-Trade Card 3: Jarak Menuju SL */}
              <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
                <span className="text-xs font-semibold text-rose-600 dark:text-rose-400">🛑 JARAK MENUJU SL</span>
                <p className="mt-1 text-lg sm:text-xl font-bold text-rose-600 dark:text-rose-400">
                  Rp -{Math.abs(keyLevels?.distance_to_sl ?? (currentPrice - (keyLevels?.stop_loss || position?.stop_loss || 0))).toLocaleString("id-ID")}
                </p>
                <span className="text-xs text-[var(--color-text-muted)]">
                  {keyLevels?.distance_to_sl_percent !== undefined
                    ? (keyLevels.distance_to_sl_percent >= 0 ? `${keyLevels.distance_to_sl_percent}% toleransi` : "⚠️ Jebol SL!")
                    : `SL: Rp ${(keyLevels?.stop_loss || position?.stop_loss || 0).toLocaleString("id-ID")}`}
                </span>
              </div>

              {/* In-Trade Card 4: Saran Trailing Stop */}
              <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
                <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">🔒 SARAN TRAILING STOP</span>
                <p className="mt-1 text-lg sm:text-xl font-bold text-blue-600 dark:text-blue-400">
                  Rp {(keyLevels?.trailing_stop || keyLevels?.stop_loss || position?.stop_loss || 0).toLocaleString("id-ID")}
                </p>
                <span className="text-xs text-[var(--color-text-muted)] truncate block">
                  {keyLevels?.trailing_stop_note || (floatingPnLPercent >= 2 ? "Kunci modal / BEP" : "Pertahankan Stop Loss")}
                </span>
              </div>
            </>
          ) : (
            <>
              {/* Pre-Trade Card 1: Area Entry */}
              <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
                <span className="text-xs font-semibold text-[var(--color-text-muted)]">🎯 AREA ENTRY (BELI)</span>
                <p className="mt-1 text-lg sm:text-xl font-bold text-[var(--color-text-strong)]">
                  Rp {keyLevels?.entry_range?.[0]?.toLocaleString("id-ID") ?? "-"} - {keyLevels?.entry_range?.[1]?.toLocaleString("id-ID") ?? "-"}
                </p>
                <span className="text-xs text-[var(--color-text-muted)]">Optimal Buy Range</span>
              </div>

              {/* Pre-Trade Card 2: Target Profit */}
              <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
                <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">🚀 TARGET PROFIT (TP)</span>
                <p className="mt-1 text-lg sm:text-xl font-bold text-emerald-600 dark:text-emerald-400">
                  TP1: Rp {keyLevels?.target_price_1?.toLocaleString("id-ID") ?? "-"}
                </p>
                <span className="text-xs text-[var(--color-text-muted)]">
                  TP2: Rp {keyLevels?.target_price_2?.toLocaleString("id-ID") ?? "-"}
                </span>
              </div>

              {/* Pre-Trade Card 3: Stop Loss */}
              <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
                <span className="text-xs font-semibold text-rose-600 dark:text-rose-400">🛑 STOP LOSS (SL)</span>
                <p className="mt-1 text-lg sm:text-xl font-bold text-rose-600 dark:text-rose-400">
                  Rp {keyLevels?.stop_loss?.toLocaleString("id-ID") ?? "-"}
                </p>
                <span className="text-xs text-[var(--color-text-muted)]">
                  Invalidasi: Rp {keyLevels?.invalidation_level?.toLocaleString("id-ID") ?? "-"}
                </span>
              </div>

              {/* Pre-Trade Card 4: Risk / Reward */}
              <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
                <span className="text-xs font-semibold text-[var(--color-text-muted)]">⚖️ RISK / REWARD</span>
                <p className="mt-1 text-lg sm:text-xl font-bold text-[var(--color-text-strong)]">
                  1 : {keyLevels?.risk_reward_ratio ?? "2.0"}
                </p>
                <span className="text-xs text-[var(--color-text-muted)]">
                  ATR(14): Rp {keyLevels?.atr14 ?? "0"}
                </span>
              </div>
            </>
          )}
        </div>

        {/* AI Detailed Reasoning Thesis */}
        <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-5 space-y-4 shadow-xs">
          <div>
            <h3 className="text-sm font-bold text-[var(--color-text-strong)] uppercase tracking-wide">
              {isInTrade ? "💡 Status Kesehatan Posisi:" : "💡 Analisa Setup & Rangkuman Cepat:"}
            </h3>
            <p className="mt-1.5 text-sm text-[var(--color-text-default)] leading-relaxed">
              {reasoning?.thesis || "Analisa setup berbasis konfluensi teknikal dan flow pasar bursa."}
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 pt-3 border-t border-[var(--color-border-subtle)]">
            <div>
              <h4 className="text-xs font-bold text-[var(--color-text-strong)]">
                {isInTrade ? "📈 Bacaan Grafik & Momentum:" : "📈 Bacaan Grafik Singkat:"}
              </h4>
              <p className="mt-1 text-xs text-[var(--color-text-muted)] leading-relaxed whitespace-pre-line">
                {reasoning?.technical_analysis || "-"}
              </p>
            </div>
            <div>
              <h4 className="text-xs font-bold text-[var(--color-text-strong)]">🏦 Aliran Duit Bandar & Asing:</h4>
              <p className="mt-1 text-xs text-[var(--color-text-muted)] leading-relaxed whitespace-pre-line">
                {reasoning?.flow_analysis || "-"}
              </p>
            </div>
          </div>

          {reasoning?.action_guidance || reasoning?.wait_guidance ? (
            <div className="pt-3 border-t border-[var(--color-border-subtle)]">
              <h4 className="text-xs font-bold text-[var(--color-text-strong)]">
                {isInTrade
                  ? "🛡️ PANDUAN PENGAWALAN POSISI (HOLD / TP / SL):"
                  : action === "WAIT"
                    ? "⏳ PANDUAN WAIT (Tunggu Apa & Sampai Kapan?):"
                    : action === "BUY"
                      ? "🚀 PANDUAN ENTRY (Beli di Mana & Target):"
                      : "⏭️ PANDUAN SKIP (Kenapa Dilewati?):"}
              </h4>
              <p className="mt-1 text-xs text-[var(--color-text-default)] leading-relaxed whitespace-pre-line">
                {reasoning?.action_guidance || reasoning?.wait_guidance}
              </p>
            </div>
          ) : null}

          <div className="pt-3 border-t border-[var(--color-border-subtle)]">
            <h4 className="text-xs font-bold text-rose-600 dark:text-rose-400">
              {isInTrade ? "⚠️ Batas Disiplin Risiko:" : "⚠️ Batas Aman:"}
            </h4>
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
            {session?.status === "OPEN_POSITION" ? (
              <span className="font-bold text-emerald-600 dark:text-emerald-400">
                🚀 Posisi Aktif Terbuka ({quantityLots} Lot @ Rp {entryPrice.toLocaleString("id-ID")})
              </span>
            ) : session?.status === "WAITING" ? (
              <span className="font-bold text-amber-600 dark:text-amber-400">
                ⏳ Menunggu Konfirmasi Setup (Status: WAITING)
              </span>
            ) : session?.status === "CLOSED_SKIPPED" ? (
              <span className="font-bold text-rose-600 dark:text-rose-400">
                🛑 Sesi telah di-SKIP / Ditutup.
              </span>
            ) : session?.status === "CLOSED" ? (
              <span className="font-bold text-[var(--color-text-strong)]">
                ✓ Posisi telah selesai / Ditutup.
              </span>
            ) : (
              <>
                <span className="font-semibold text-[var(--color-text-strong)]">Aksi Cepat:</span> Eksekusi atau pantau setup emiten ini
              </>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {session?.status === "OPEN_POSITION" ? (
              /* OPEN POSITION ACTIONS: REFRESH & CLOSE */
              <>
                <button
                  type="button"
                  onClick={() => loadData(true)}
                  disabled={evaluating}
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-bold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  {evaluating ? (
                    <>
                      <ButtonSpinner className="h-4 w-4" />
                      <span>Memperbarui…</span>
                    </>
                  ) : (
                    <>⚡ Update Posisi</>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setClosePrice(String(currentPrice || entryPrice));
                    setShowCloseModal(true);
                  }}
                  disabled={submittingAction}
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-rose-600 px-6 text-sm font-bold text-white shadow-sm hover:bg-rose-700 active:scale-[0.98] transition-all focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
                >
                  🚪 Tutup Posisi (CLOSE)
                </button>
              </>
            ) : session?.status === "WAITING" ? (
              /* WAITING ACTIONS: REFRESH, BUY NOW, SKIP */
              <>
                <button
                  type="button"
                  onClick={() => loadData(true)}
                  disabled={evaluating}
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-bold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  {evaluating ? (
                    <>
                      <ButtonSpinner className="h-4 w-4" />
                      <span>Memperbarui…</span>
                    </>
                  ) : (
                    <>⚡ Update Data</>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setBuyPrice(String(currentPrice || ""));
                    setShowBuyModal(true);
                  }}
                  disabled={submittingAction}
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-emerald-600 px-6 text-sm font-bold text-white shadow-sm hover:bg-emerald-700 active:scale-[0.98] transition-all focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
                >
                  🚀 BUY Sekarang
                </button>

                <button
                  type="button"
                  onClick={() => setShowSkipModal(true)}
                  disabled={submittingAction}
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/20 active:scale-[0.98] transition-all focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
                >
                  ⏭️ SKIP
                </button>
              </>
            ) : session?.status === "CLOSED_SKIPPED" || session?.status === "CLOSED" ? (
              /* TERMINAL ACTIONS: ARCHIVE & RE-EVALUATE */
              <>
                {session.archived_at ? (
                  <>
                    <Link
                      href="/sessions/archived"
                      className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-bold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] active:scale-[0.98] transition-all shadow-xs"
                    >
                      📂 Buka Riwayat
                    </Link>
                    <button
                      type="button"
                      onClick={handleRestore}
                      disabled={submittingAction}
                      className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 text-sm font-semibold text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)] active:scale-[0.98] transition-all disabled:opacity-50"
                    >
                      {isRestoring ? (
                        <>
                          <ButtonSpinner className="h-4 w-4" />
                          <span>Memulihkan…</span>
                        </>
                      ) : (
                        <>↩️ Batal Arsip</>
                      )}
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={handleArchive}
                    disabled={submittingAction}
                    className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-indigo-600 px-5 text-sm font-bold text-white shadow-sm hover:bg-indigo-700 active:scale-[0.98] transition-all focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
                  >
                    {isArchiving ? (
                      <>
                        <ButtonSpinner className="h-4 w-4" />
                        <span>Mengarsipkan…</span>
                      </>
                    ) : (
                      <>📦 Arsipkan ke Riwayat</>
                    )}
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => loadData(true)}
                  disabled={evaluating}
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-5 text-sm font-bold text-white shadow-sm hover:bg-[var(--color-action-primary-hover)] active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  {evaluating ? (
                    <>
                      <ButtonSpinner className="h-4 w-4" />
                      <span>Mengevaluasi…</span>
                    </>
                  ) : (
                    <>🔄 Re-Evaluasi Setup</>
                  )}
                </button>
              </>
            ) : (
              /* DRAFT / ANALYZED ACTIONS: BUY, WAIT, SKIP */
              <>
                <button
                  type="button"
                  onClick={() => {
                    setBuyPrice(String(currentPrice || ""));
                    setShowBuyModal(true);
                  }}
                  disabled={submittingAction}
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-emerald-600 px-6 text-sm font-bold text-white shadow-sm hover:bg-emerald-700 active:scale-[0.98] transition-all focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
                >
                  🚀 BUY
                </button>

                <button
                  type="button"
                  onClick={handleWait}
                  disabled={submittingAction}
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-amber-600 px-5 text-sm font-bold text-white shadow-sm hover:bg-amber-700 active:scale-[0.98] transition-all focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
                >
                  {isWaiting ? (
                    <>
                      <ButtonSpinner className="h-4 w-4" />
                      <span>Menyimpan WAIT…</span>
                    </>
                  ) : (
                    <>⏳ WAIT</>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setShowSkipModal(true)}
                  disabled={submittingAction}
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/20 active:scale-[0.98] transition-all focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
                >
                  ⏭️ SKIP
                </button>
              </>
            )}
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
                  placeholder={String(currentPrice || "0")}
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
                <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                  Total Nilai: Rp {(Number(buyPrice || currentPrice) * Number(buyLots || 0) * 100).toLocaleString("id-ID")}
                </p>
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
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-6 py-2 text-sm font-bold text-white hover:bg-emerald-700 active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  {submittingAction ? (
                    <>
                      <ButtonSpinner className="h-4 w-4" />
                      <span>Menyimpan…</span>
                    </>
                  ) : (
                    "Konfirmasi BUY"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {/* Close Position Modal */}
      {showCloseModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-6 shadow-xl space-y-4">
            <h3 className="text-xl font-bold text-[var(--color-text-strong)]">
              🚪 Tutup Posisi (Jual) - {session?.ticker}
            </h3>
            <form onSubmit={handleClosePosition} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] uppercase">
                  Harga Jual / Exit (Rp)
                </label>
                <input
                  type="number"
                  value={closePrice}
                  onChange={(e) => setClosePrice(e.target.value)}
                  placeholder={String(currentPrice || "0")}
                  required
                  className="mt-1 w-full rounded-md border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-base font-bold text-[var(--color-text-strong)]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] uppercase">
                  Alasan Penutupan Posisi
                </label>
                <select
                  value={closeReason}
                  onChange={(e) => setCloseReason(e.target.value)}
                  className="mt-1 w-full rounded-md border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-sm font-semibold text-[var(--color-text-strong)]"
                >
                  <option value="TARGET_HIT">🎯 Mencapai Target TP1 / TP2</option>
                  <option value="STOP_LOSS_HIT">🛑 Kena Stop Loss (SL)</option>
                  <option value="MANUAL">💼 Tutup Manual / Amankan Profit</option>
                  <option value="INVALIDATED">⚠️ Struktur Berubah (Invalidasi)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--color-text-muted)] uppercase">
                  Catatan Exit (Opsional)
                </label>
                <input
                  type="text"
                  value={closeNote}
                  onChange={(e) => setCloseNote(e.target.value)}
                  placeholder="Catatan evaluasi trading..."
                  className="mt-1 w-full rounded-md border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-sm text-[var(--color-text-default)]"
                />
              </div>

              <div className="rounded-lg bg-[var(--color-surface-muted)] p-3 text-xs text-[var(--color-text-muted)] space-y-1">
                <div className="flex justify-between">
                  <span>Harga Beli (Entry):</span>
                  <span className="font-bold text-[var(--color-text-strong)]">Rp {entryPrice.toLocaleString("id-ID")}</span>
                </div>
                <div className="flex justify-between">
                  <span>Estimasi Realized PnL:</span>
                  <span
                    className={`font-bold ${
                      (Number(closePrice || currentPrice) - entryPrice) >= 0 ? "text-emerald-600" : "text-rose-600"
                    }`}
                  >
                    {((Number(closePrice || currentPrice) - entryPrice) * totalShares) >= 0 ? "+" : ""}
                    Rp {((Number(closePrice || currentPrice) - entryPrice) * totalShares).toLocaleString("id-ID")}
                  </span>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCloseModal(false)}
                  className="rounded-md border border-[var(--color-border-default)] px-4 py-2 text-sm font-semibold text-[var(--color-text-strong)]"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-rose-600 px-6 py-2 text-sm font-bold text-white hover:bg-rose-700 active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  {submittingAction ? (
                    <>
                      <ButtonSpinner className="h-4 w-4" />
                      <span>Menutup Posisi…</span>
                    </>
                  ) : (
                    "Konfirmasi CLOSE"
                  )}
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
              {[
                { reason: "RISK_TOO_HIGH" as const, label: "🛑 Risiko Terlalu Tinggi / R:R Tidak Masuk" },
                { reason: "ORDERBOOK_WEAK" as const, label: "📉 Orderbook Lemah / Likuiditas Rendah" },
                { reason: "MARKET_CONDITION_UNFAVORABLE" as const, label: "🏦 Kondisi IHSG / Distribusi Asing Masif" },
                { reason: "SETUP_NOT_ATTRACTIVE" as const, label: "🔍 Setup Pola Tidak Menarik" },
              ].map(({ reason, label }) => (
                <button
                  key={reason}
                  type="button"
                  disabled={submittingAction}
                  onClick={() => handleSkip(reason)}
                  className="flex items-center justify-between rounded-lg border border-[var(--color-border-default)] p-3 text-left text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  <span>{label}</span>
                  {skipPendingReason === reason ? (
                    <ButtonSpinner className="h-4 w-4 text-rose-600" />
                  ) : null}
                </button>
              ))}
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
