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
import { formatMiliar, formatShares, generateTelegramReport } from "./telegram-report";

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
  const [copiedTelegram, setCopiedTelegram] = useState(false);

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
      const msg = typeof err === "string" ? err : err?.message || "";
      if (/database|secret|internal|500/i.test(msg)) {
        setError("Konteks sesi tidak dapat dimuat.");
      } else {
        setError(msg || "Gagal memuat data workspace sesi.");
      }
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
        <h1 className="sr-only">Ringkasan Sesi</h1>
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

  if (error && !session) {
    return (
      <main className="mx-auto min-w-0 w-full max-w-[var(--layout-application-max)] px-4 py-8 sm:px-6 lg:px-8">
        <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-600 dark:text-rose-400 font-semibold">
          ⚠️ {error}
        </div>
      </main>
    );
  }

  const snapshot = analysis?.market_evidence;
  const quote = snapshot?.quote;
  const companyProfile = snapshot?.company_profile;
  const orderbook = snapshot?.orderbook;
  const foreignFlow = snapshot?.foreign_flow;
  const brokerFlow = snapshot?.broker_flow;
  const historical = snapshot?.historical_ohlcv;
  const tech = historical?.computed_technical;
  const marketContext = snapshot?.market_context;
  const keyLevels = analysis?.key_levels;
  const reasoning = analysis?.reasoning;
  const action: ActionType = analysis?.action || "WAIT";

  const handleCopyTelegram = () => {
    const text = generateTelegramReport({
      ticker: session?.ticker || quote?.symbol || "EMITEN",
      companyName: session?.company_name || quote?.company_name || "Perusahaan Tercatat di BEI (IDX)",
      analyzedAt: analysis?.analyzed_at,
      quote,
      profile: companyProfile,
      tech,
      brokerFlow,
      foreignFlow,
      orderbook,
      marketContext,
      keyLevels,
      reasoning,
      action,
      isInTrade,
    });
    navigator.clipboard.writeText(text);
    setCopiedTelegram(true);
    setTimeout(() => setCopiedTelegram(false), 3000);
  };

  const displayPe = companyProfile?.pe_ratio ?? quote?.pe_ratio;
  const displayEps = companyProfile?.eps_ttm ?? quote?.eps_ttm;
  const displayYield = companyProfile?.dividend_yield_percent ?? quote?.dividend_yield;
  const displayDps = companyProfile?.dividend_per_share ?? quote?.dps;
  const displayBeta = companyProfile?.beta ?? quote?.beta;
  const display1YReturn = companyProfile?.one_year_return_percent ?? quote?.one_year_return;
  const displayNextEarnings = companyProfile?.next_earnings_date || quote?.next_earnings_date;

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
      <h1 className="sr-only">Ringkasan Sesi</h1>
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

      {/* 📊 TRADEPILOT AI MARKET INTELLIGENCE Header */}
      <section className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-border-subtle)] pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center rounded-md bg-indigo-500/10 px-2.5 py-1 text-xs font-black tracking-wide text-indigo-600 dark:text-indigo-400 uppercase">
                📊 TRADEPILOT AI MARKET INTELLIGENCE
              </span>
              <span className="text-xs text-[var(--color-text-muted)]">
                Tanggal: {new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "long", year: "numeric" }).format(analysis?.analyzed_at ? new Date(analysis.analyzed_at) : new Date())}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 sm:gap-3">
              <h1 className="text-2xl sm:text-3xl font-black text-[var(--color-text-strong)] tracking-tight">
                ${session?.ticker || quote?.symbol || "EMITEN"}
              </h1>
              <span className="text-sm sm:text-base font-bold text-[var(--color-text-muted)]">
                ({session?.company_name || quote?.company_name || "Perusahaan Tercatat di BEI (IDX)"})
              </span>
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
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={handleCopyTelegram}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-compact)] border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-bold text-sky-600 dark:text-sky-400 shadow-xs hover:bg-sky-500/20 active:scale-[0.98] transition-all"
            >
              {copiedTelegram ? (
                <>
                  <span className="text-emerald-500 font-black">✓</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">Format Telegram Tersalin!</span>
                </>
              ) : (
                <>
                  <span>📋</span>
                  <span>Salin Format Telegram</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => loadData(true)}
              disabled={evaluating}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 py-2 text-sm font-bold text-[var(--color-text-strong)] shadow-xs hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] active:scale-[0.98] transition-all disabled:opacity-50"
            >
              {evaluating ? (
                <>
                  <ButtonSpinner className="h-4 w-4" />
                  <span>Mengevaluasi Ulang…</span>
                </>
              ) : (
                <>⚡ Refresh Data & Re-Evaluasi</>
              )}
            </button>
          </div>
        </div>
      </section>

      {/* 🏢 Modul 1: PROFIL & VALUASI EMITEN */}
      <section className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border-subtle)] pb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">🏢</span>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-strong)]">
              PROFIL & VALUASI EMITEN
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
            <span className="rounded-md bg-indigo-500/10 px-2.5 py-1 text-indigo-600 dark:text-indigo-400">
              Sektor: {companyProfile?.sector || quote?.sector || "IDX General"}
            </span>
            <span className="rounded-md bg-zinc-500/10 px-2.5 py-1 text-[var(--color-text-muted)]">
              Sub-sektor: {companyProfile?.sub_sector || quote?.industry || "Saham Terbuka"}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {/* Harga Saat Ini */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">Harga Saat Ini</span>
            <p className="mt-1 text-xl font-black text-[var(--color-text-strong)]">
              Rp {currentPrice.toLocaleString("id-ID")}
            </p>
            <span className={`text-xs font-bold ${(quote?.change_percent ?? 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
              {(quote?.change_percent ?? 0) >= 0 ? "+" : ""}{(quote?.change_percent ?? 0).toFixed(2)}% (Hari Ini)
            </span>
          </div>

          {/* P/E Ratio */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">P/E Ratio (TTM)</span>
            <p className="mt-1 text-xl font-black text-[var(--color-text-strong)]">
              {displayPe != null ? `${Number(displayPe).toFixed(2)}x` : "-"}
            </p>
            <span className="text-[11px] text-[var(--color-text-muted)] block truncate">
              {Number(displayPe) <= 12 ? "Valuasi atraktif" : "Valuasi wajar"}
            </span>
          </div>

          {/* EPS TTM */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">EPS (TTM)</span>
            <p className="mt-1 text-xl font-black text-[var(--color-text-strong)] truncate">
              {displayEps != null ? `Rp ${Number(displayEps).toFixed(2)}` : "-"}
            </p>
            <span className="text-[11px] text-[var(--color-text-muted)] block">Per lembar saham</span>
          </div>

          {/* Dividend Yield */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">Dividend Yield</span>
            <p className="mt-1 text-xl font-black text-emerald-600 dark:text-emerald-400">
              {displayYield != null ? `${Number(displayYield).toFixed(2)}%` : "-"}
            </p>
            <span className="text-[11px] text-[var(--color-text-muted)] block truncate">
              {displayDps != null ? `DPS Rp ${Number(displayDps).toFixed(1)}` : "Dividen teratur"}
            </span>
          </div>

          {/* Beta vs IHSG */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">Beta vs IHSG</span>
            <p className="mt-1 text-xl font-black text-[var(--color-text-strong)]">
              {displayBeta != null ? Number(displayBeta).toFixed(2) : "-"}
            </p>
            <span className="text-[11px] text-[var(--color-text-muted)] block truncate">
              {Number(displayBeta) < 0 ? "Defensif (Lawan Tren)" : Number(displayBeta) < 1 ? "Volatilitas rendah" : "Agresif"}
            </span>
          </div>

          {/* Momentum 1Y */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">Momentum 1 Thn</span>
            <p className={`mt-1 text-xl font-black ${Number(display1YReturn) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
              {display1YReturn != null ? `${Number(display1YReturn) >= 0 ? "+" : ""}${Number(display1YReturn).toFixed(2)}%` : "-"}
            </p>
            <span className="text-[11px] text-[var(--color-text-muted)] block">Performa tahunan</span>
          </div>
        </div>

        {displayNextEarnings && (
          <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 px-3.5 py-2 text-xs font-semibold text-amber-700 dark:text-amber-400 flex items-center gap-2">
            <span>📅 Katalis Rilis Lapkeu:</span>
            <span>{displayNextEarnings}</span>
          </div>
        )}
      </section>

      {/* 💰 Modul 2: ARUS DANA (BANDARMOLOGY & FOREIGN FLOW) */}
      <section className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 border-b border-[var(--color-border-subtle)] pb-3">
          <span className="text-lg">💰</span>
          <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-strong)]">
            ARUS DANA (BANDARMOLOGY & FOREIGN FLOW)
          </h2>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {/* Bandarmology Panel */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase text-[var(--color-text-muted)]">Status Bandar</span>
              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-0.5 text-xs font-extrabold uppercase ${
                brokerFlow?.bandar_status?.includes("ACCUMULATION")
                  ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                  : brokerFlow?.bandar_status?.includes("DISTRIBUTION")
                    ? "bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                    : "bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30"
              }`}>
                {brokerFlow?.bandar_status?.includes("ACCUMULATION") ? "🟢" : brokerFlow?.bandar_status?.includes("DISTRIBUTION") ? "🔴" : "🟡"}{" "}
                {brokerFlow?.bandar_status || "NEUTRAL"}
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-1.5">
                <span className="text-[var(--color-text-muted)]">Konsentrasi Top 3 Buyer:</span>
                <span className="font-bold text-[var(--color-text-strong)]">
                  {brokerFlow?.top3_buyer_concentration_percent ? `${brokerFlow.top3_buyer_concentration_percent}%` : "-"}
                  <span className="ml-1 text-[11px] font-normal text-[var(--color-text-muted)]">
                    ({(brokerFlow?.top3_buyer_concentration_percent ?? 0) >= 70 ? "Sangat terakumulasi" : "Wajar"})
                  </span>
                </span>
              </div>

              <div>
                <span className="text-[var(--color-text-muted)] block mb-1">Akumulator Utama:</span>
                <p className="font-medium text-[var(--color-text-strong)] leading-relaxed">
                  {brokerFlow?.top_buyers?.length > 0
                    ? brokerFlow.top_buyers.slice(0, 3).map((b: any, idx: number) => {
                        const val = formatMiliar(b.value_idr);
                        const pct = b.market_share_percent ? `, porsi ${b.market_share_percent}%` : "";
                        return `Broker ${b.broker} (${val}${pct})`;
                      }).join(", disusul ")
                    : "Tersebar merata antar broker pasar"}
                </p>
              </div>

              <div className="pt-1">
                <span className="text-[var(--color-text-muted)] block mb-1">Distribusi Penjual:</span>
                <p className="font-medium text-[var(--color-text-strong)]">
                  {brokerFlow?.top_sellers?.length > 0
                    ? `Didominasi broker (${brokerFlow.top_sellers.slice(0, 4).map((s: any) => s.broker).filter(Boolean).join(", ")})`
                    : "Tersebar merata"}
                </p>
              </div>
            </div>
          </div>

          {/* Foreign Flow Panel */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase text-[var(--color-text-muted)]">Status Asing</span>
              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-0.5 text-xs font-extrabold uppercase ${
                foreignFlow?.foreign_status?.includes("ACCUMULATION")
                  ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                  : foreignFlow?.foreign_status?.includes("DISTRIBUTION")
                    ? "bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                    : "bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30"
              }`}>
                {foreignFlow?.foreign_status?.includes("ACCUMULATION") ? "🟢" : foreignFlow?.foreign_status?.includes("DISTRIBUTION") ? "🔴" : "🟡"}{" "}
                {foreignFlow?.foreign_status || "NEUTRAL"}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg bg-[var(--color-surface-standard)] p-2 border border-[var(--color-border-subtle)]">
                <span className="text-[var(--color-text-muted)] block text-[10px] uppercase font-bold">1 Hari</span>
                <span className={`font-black ${(foreignFlow?.today_1d?.net_value_idr ?? 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                  {foreignFlow?.today_1d ? formatMiliar(foreignFlow.today_1d.net_value_idr) : "-"}
                </span>
                <span className="block text-[10px] text-[var(--color-text-muted)] truncate">
                  {foreignFlow?.today_1d ? formatShares(foreignFlow.today_1d.net_shares) : ""}
                </span>
              </div>

              <div className="rounded-lg bg-[var(--color-surface-standard)] p-2 border border-[var(--color-border-subtle)]">
                <span className="text-[var(--color-text-muted)] block text-[10px] uppercase font-bold">1 Minggu</span>
                <span className={`font-black ${(foreignFlow?.weekly_1w?.net_value_idr ?? 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                  {foreignFlow?.weekly_1w ? formatMiliar(foreignFlow.weekly_1w.net_value_idr) : "-"}
                </span>
                <span className="block text-[10px] text-[var(--color-text-muted)] truncate">
                  {foreignFlow?.weekly_1w ? formatShares(foreignFlow.weekly_1w.net_shares) : ""}
                </span>
              </div>

              <div className="rounded-lg bg-[var(--color-surface-standard)] p-2 border border-[var(--color-border-subtle)]">
                <span className="text-[var(--color-text-muted)] block text-[10px] uppercase font-bold">1 Bulan</span>
                <span className={`font-black ${(foreignFlow?.monthly_1m?.net_value_idr ?? 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                  {foreignFlow?.monthly_1m ? formatMiliar(foreignFlow.monthly_1m.net_value_idr) : "-"}
                </span>
                <span className="block text-[10px] text-[var(--color-text-muted)] truncate">
                  {foreignFlow?.monthly_1m ? formatShares(foreignFlow.monthly_1m.net_shares) : ""}
                </span>
              </div>

              <div className="rounded-lg bg-[var(--color-surface-standard)] p-2 border border-[var(--color-border-subtle)]">
                <span className="text-[var(--color-text-muted)] block text-[10px] uppercase font-bold">3 Bulan</span>
                <span className={`font-black ${(foreignFlow?.three_month_3m?.net_value_idr ?? 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                  {foreignFlow?.three_month_3m ? formatMiliar(foreignFlow.three_month_3m.net_value_idr) : "-"}
                </span>
                <span className="block text-[10px] text-[var(--color-text-muted)] truncate">
                  {foreignFlow?.three_month_3m ? formatShares(foreignFlow.three_month_3m.net_shares) : ""}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Kesimpulan Flow & Orderbook Baseline */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-indigo-500/5 border border-indigo-500/20 p-3.5 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-indigo-600 dark:text-indigo-400">👉 Kesimpulan Flow:</span>
            <span className="text-[var(--color-text-strong)] font-medium">
              {foreignFlow?.foreign_status?.includes("ACCUMULATION") && brokerFlow?.bandar_status?.includes("ACCUMULATION")
                ? "Dana institusi & asing terus masuk secara konsisten dalam skala besar."
                : foreignFlow?.foreign_status?.includes("DISTRIBUTION")
                  ? "Tekanan jual asing masih terasa, konfirmasi akumulasi baru masih ditunggu."
                  : "Aliran dana institusi dan ritel bergerak relatif berimbang (konsolidasi)."}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3 font-semibold text-[var(--color-text-muted)] text-[11px]">
            <span>Orderbook: <strong className="text-[var(--color-text-strong)]">{orderbook?.bid_ask_ratio ? Number(orderbook.bid_ask_ratio).toFixed(2) : "1.00"}x</strong></span>
            <span>Spread: <strong className="text-[var(--color-text-strong)]">Rp {orderbook?.spread ? Number(orderbook.spread).toLocaleString("id-ID") : "0"}</strong></span>
            <span>Bid: <strong className="text-emerald-600 dark:text-emerald-400">{Number(orderbook?.total_bid_lots || 0).toLocaleString("id-ID")} lot</strong></span>
            <span>Ask: <strong className="text-rose-600 dark:text-rose-400">{Number(orderbook?.total_ask_lots || 0).toLocaleString("id-ID")} lot</strong></span>
          </div>
        </div>
      </section>

      {/* 📈 Modul 3: ANALISIS TEKNIKAL & STRUKTUR TREN */}
      <section className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border-subtle)] pb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">📈</span>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-strong)]">
              ANALISIS TEKNIKAL & STRUKTUR TREN
            </h2>
          </div>
          <span className={`inline-flex items-center rounded-md px-3 py-1 text-xs font-black uppercase ${
            tech?.ma_alignment === "BULLISH_ALIGNMENT"
              ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
              : tech?.ma_alignment === "BEARISH_ALIGNMENT"
                ? "bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                : "bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30"
          }`}>
            Tren Utama: {tech?.ma_alignment?.replace("_", " ") || "MIXED"}
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {/* Moving Average */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5 space-y-1">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">Moving Averages</span>
            <p className="text-xs font-bold text-[var(--color-text-strong)]">
              MA20: Rp {tech?.ma20 ? Math.round(Number(tech.ma20)).toLocaleString("id-ID") : "-"}
            </p>
            <p className="text-xs font-bold text-[var(--color-text-strong)]">
              MA50: Rp {tech?.ma50 ? Math.round(Number(tech.ma50)).toLocaleString("id-ID") : "-"}
            </p>
            <span className="text-[11px] text-[var(--color-text-muted)] block">
              Harga (Rp {currentPrice.toLocaleString("id-ID")}) {currentPrice >= Number(tech?.ma20 || 0) ? "kokoh di atas MA20" : "di bawah MA20"}
            </span>
          </div>

          {/* RSI 14 */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5 space-y-1">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">RSI (14 Momentum)</span>
            <div className="flex items-center gap-2">
              <p className="text-xl font-black text-[var(--color-text-strong)]">
                {tech?.rsi14 ? Number(tech.rsi14).toFixed(2) : "50.00"}
              </p>
              <span className={`rounded-md px-2 py-0.5 text-[10px] font-extrabold ${
                Number(tech?.rsi14 || 50) >= 70
                  ? "bg-rose-500/20 text-rose-600 dark:text-rose-400"
                  : Number(tech?.rsi14 || 50) <= 30
                    ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                    : "bg-blue-500/20 text-blue-600 dark:text-blue-400"
              }`}>
                {Number(tech?.rsi14 || 50) >= 70 ? "Overbought" : Number(tech?.rsi14 || 50) <= 30 ? "Oversold" : "Netral"}
              </span>
            </div>
            <span className="text-[11px] text-[var(--color-text-muted)] block truncate">
              {Number(tech?.rsi14 || 50) >= 70 ? "Waspadai pullback sehat" : "Momentum stabil"}
            </span>
          </div>

          {/* ATR 14 */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5 space-y-1">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">ATR (14 Volatilitas)</span>
            <p className="text-xl font-black text-[var(--color-text-strong)]">
              {tech?.atr14 ? Number(tech.atr14).toFixed(2) : "-"}
            </p>
            <span className="text-[11px] text-[var(--color-text-muted)] block">
              Poin rentang fluktuasi harian normal
            </span>
          </div>

          {/* Level Kunci Support / Resistance */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-subtle)] p-3.5 space-y-1">
            <span className="text-[11px] font-semibold text-[var(--color-text-muted)] uppercase">Level Kunci</span>
            <p className="text-xs font-bold text-emerald-600 dark:text-emerald-400 truncate">
              Resist: Rp {tech?.key_resistances?.[0] ? Math.round(tech.key_resistances[0]).toLocaleString("id-ID") : Math.round(currentPrice * 1.04).toLocaleString("id-ID")}
              {tech?.high_52w ? ` (52W: ${Math.round(tech.high_52w)})` : ""}
            </p>
            <p className="text-xs font-bold text-rose-600 dark:text-rose-400 truncate">
              Support: Rp {tech?.key_supports?.[0] ? Math.round(tech.key_supports[0]).toLocaleString("id-ID") : Math.round(currentPrice * 0.96).toLocaleString("id-ID")}
              {tech?.low_52w ? ` (52W: ${Math.round(tech.low_52w)})` : ""}
            </p>
            <span className="text-[11px] text-[var(--color-text-muted)] block">
              Area batas dinamis & fraktal
            </span>
          </div>
        </div>
      </section>

      {/* 🎯 Modul 4: SKENARIO & REKOMENDASI TRADING PLAN */}
      <section className={`rounded-[var(--radius-large)] border ${currentTheme.border} ${currentTheme.bg} p-5 sm:p-6 shadow-sm space-y-5`}>
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-border-subtle)] pb-4">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎯</span>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-strong)]">
              SKENARIO & REKOMENDASI TRADING PLAN
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-2xl sm:text-3xl font-black tracking-tight ${currentTheme.text}`}>
              {isInTrade
                ? action === "TAKE_PROFIT"
                  ? "🎯 TAKE PROFIT"
                  : action === "CUT_LOSS"
                    ? "⚠️ CUT LOSS ALERT"
                    : action === "TRAILING_STOP"
                      ? "🔒 TRAILING STOP"
                      : "🛡️ HOLD (KAWAL)"
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

        {/* Kondisi Pasar & Strategi */}
        <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 space-y-2">
          <p className="text-xs text-[var(--color-text-default)] leading-relaxed">
            <strong className="text-[var(--color-text-strong)]">Kondisi Pasar:</strong>{" "}
            {reasoning?.thesis || `IHSG sedang ${Number(marketContext?.index_change_percent || 0) >= 0 ? "menguat" : "melemah"}, emiten ${session?.ticker || quote?.symbol} bergerak sesuai dinamika pasar.`}
          </p>
          <p className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
            📌 Strategi: {isInTrade ? "Kawal Posisi Sesuai Rencana Trading" : action === "BUY" ? (Number(tech?.rsi14 || 50) >= 70 ? "Buy on Weakness (BoW) / Antri Pullback" : "Buy on Breakout / Follow Through") : action === "WAIT" ? "Wait for Confirmation / Antri Pullback" : "Avoid / Cari Peluang Lain"}
          </p>
        </div>

        {/* 4 Color-Accented Key Price Cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {/* Card 1: Area Entry */}
          <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4 shadow-xs">
            <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400">🎯 AREA ENTRY (BELI)</span>
            <p className="mt-1 text-lg sm:text-xl font-black text-[var(--color-text-strong)]">
              Rp {keyLevels?.entry_range?.[0]?.toLocaleString("id-ID") ?? "-"} – {keyLevels?.entry_range?.[1]?.toLocaleString("id-ID") ?? "-"}
            </p>
            <span className="text-xs text-[var(--color-text-muted)]">Optimal Buy Range</span>
          </div>

          {/* Card 2: Target Profit */}
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 shadow-xs">
            <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">🚀 TARGET PROFIT (TP)</span>
            <p className="mt-1 text-lg sm:text-xl font-black text-emerald-600 dark:text-emerald-400">
              TP1: Rp {keyLevels?.target_price_1?.toLocaleString("id-ID") ?? "-"}
            </p>
            <span className="text-xs text-[var(--color-text-muted)] block truncate">
              TP2: Rp {keyLevels?.target_price_2?.toLocaleString("id-ID") ?? "-"}
            </span>
          </div>

          {/* Card 3: Stop Loss */}
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-4 shadow-xs">
            <span className="text-xs font-bold text-rose-600 dark:text-rose-400">🛑 STOP LOSS (SL)</span>
            <p className="mt-1 text-lg sm:text-xl font-black text-rose-600 dark:text-rose-400">
              Rp {keyLevels?.stop_loss?.toLocaleString("id-ID") ?? "-"}
            </p>
            <span className="text-xs text-[var(--color-text-muted)] block truncate">
              Invalidasi: Rp {keyLevels?.invalidation_level?.toLocaleString("id-ID") ?? "-"}
            </span>
          </div>

          {/* Card 4: Risk / Reward */}
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 shadow-xs">
            <span className="text-xs font-bold text-[var(--color-text-muted)]">⚖️ RISK / REWARD</span>
            <p className="mt-1 text-lg sm:text-xl font-black text-[var(--color-text-strong)]">
              1 : {keyLevels?.risk_reward_ratio ?? "2.0"}
            </p>
            <span className="text-xs text-[var(--color-text-muted)]">
              ATR(14): Rp {keyLevels?.atr14 ?? "0"}
            </span>
          </div>
        </div>

        {/* Detailed Guidance & Reasoning */}
        {(reasoning?.action_guidance || reasoning?.wait_guidance) && (
          <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface-standard)] p-4 space-y-2">
            <h3 className="text-xs font-bold uppercase text-[var(--color-text-strong)]">
              {isInTrade ? "🛡️ Panduan Pengawalan Posisi:" : action === "BUY" ? "🚀 Panduan Entry & Target:" : action === "WAIT" ? "⏳ Panduan Wait (Tunggu Apa?):" : "⏭️ Panduan Skip:"}
            </h3>
            <p className="text-xs text-[var(--color-text-default)] leading-relaxed whitespace-pre-line">
              {reasoning?.action_guidance || reasoning?.wait_guidance}
            </p>
          </div>
        )}
      </section>

      {/* ⚠️ Modul 5: RISIKO & KATALIS YANG PERLU DIPERHATIKAN */}
      <section className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 border-b border-[var(--color-border-subtle)] pb-3">
          <span className="text-lg">⚠️</span>
          <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text-strong)]">
            RISIKO & KATALIS YANG PERLU DIPERHATIKAN
          </h2>
        </div>

        <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 text-xs text-[var(--color-text-default)] leading-relaxed whitespace-pre-line">
          {reasoning?.risk_factors || "1. Fluktuasi sentimen pasar acuan (IHSG) dan pergerakan sektor terkait.\n2. Disiplin batasi risiko jika harga bergerak menembus level batas aman stop loss."}
        </div>

        <p className="text-[11px] text-[var(--color-text-muted)] italic">
          ⚖️ Disclaimer: Analisis ini bersifat edukatif dan advisori berbasis data pasar terverifikasi. Keputusan investasi dan eksekusi tetap berada di tangan masing-masing trader.
        </p>
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
