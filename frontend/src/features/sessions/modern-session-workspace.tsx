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
import { formatMiliar, formatShares } from "./telegram-report";

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
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mb-4" />
          <h2 className="text-xl font-bold text-slate-800">Mempersiapkan Workspace AI…</h2>
          <p role="status" className="text-sm text-slate-500 mt-1">
            Memuat konteks sesi…
          </p>
        </div>
      </main>
    );
  }

  if (error && !session) {
    return (
      <main className="mx-auto min-w-0 w-full max-w-[var(--layout-application-max)] px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="sr-only">Ringkasan Sesi</h1>
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

  const displayPe = companyProfile?.pe_ratio ?? quote?.pe_ratio;
  const displayEps = companyProfile?.eps_ttm ?? quote?.eps_ttm;
  const displayYield = companyProfile?.dividend_yield_percent ?? quote?.dividend_yield;
  const displayDps = companyProfile?.dividend_per_share ?? quote?.dps;
  const displayBeta = companyProfile?.beta ?? quote?.beta;
  const display1YReturn = companyProfile?.one_year_return_percent ?? quote?.one_year_return;
  const displayNextEarnings = companyProfile?.next_earnings_date || quote?.next_earnings_date;

  const currentPrice = Number(quote?.last_price || keyLevels?.current_price || 0);
  const changePercent = Number(quote?.change_percent || 0);
  const changeNominal = Number(quote?.change || 0);

  // Position PnL Calculations
  const entryPrice = position ? Number(position.entry_price) : 0;
  const quantityLots = position ? Number(position.quantity) : 0;
  const totalShares = quantityLots * 100;
  const capitalInvested = entryPrice * totalShares;
  const currentValue = currentPrice * totalShares;
  const floatingPnL = currentValue - capitalInvested;
  const floatingPnLPercent = capitalInvested > 0 ? (floatingPnL / capitalInvested) * 100 : 0;

  const isInTrade = session?.status === "OPEN_POSITION" || Boolean(position && position.status === "OPEN") || Boolean(analysis?.is_in_trade);

  // Conviction Index
  const convictionScore = analysis?.confidence_score ?? (action === "BUY" ? 78 : action === "WAIT" ? 62 : 47);
  const convictionLabel = convictionScore >= 70 ? "Tinggi" : convictionScore >= 55 ? "Moderat" : "Rendah";

  // Formatted analyzed timestamp
  const analyzedDateStr = analysis?.analyzed_at
    ? new Date(analysis.analyzed_at).toLocaleDateString("id-ID", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : new Date().toLocaleDateString("id-ID", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });

  const analyzedTimeWib = analysis?.analyzed_at
    ? new Date(analysis.analyzed_at).toLocaleTimeString("id-ID", {
        hour: "2-digit",
        minute: "2-digit",
      }) + " WIB"
    : new Date().toLocaleTimeString("id-ID", {
        hour: "2-digit",
        minute: "2-digit",
      }) + " WIB";

  // Action badge theme
  const actionBadges: Record<ActionType, { bg: string; border: string; text: string; dot: string }> = {
    BUY: {
      bg: "bg-emerald-50",
      border: "border-emerald-200",
      text: "text-emerald-700",
      dot: "bg-emerald-500",
    },
    WAIT: {
      bg: "bg-amber-50",
      border: "border-amber-200",
      text: "text-amber-700",
      dot: "bg-amber-500",
    },
    SKIP: {
      bg: "bg-rose-50",
      border: "border-rose-200",
      text: "text-rose-700",
      dot: "bg-rose-500",
    },
    HOLD: {
      bg: "bg-teal-50",
      border: "border-teal-200",
      text: "text-teal-700",
      dot: "bg-teal-500",
    },
    TAKE_PROFIT: {
      bg: "bg-emerald-50",
      border: "border-emerald-200",
      text: "text-emerald-700",
      dot: "bg-emerald-500",
    },
    CUT_LOSS: {
      bg: "bg-rose-50",
      border: "border-rose-200",
      text: "text-rose-700",
      dot: "bg-rose-500",
    },
    TRAILING_STOP: {
      bg: "bg-blue-50",
      border: "border-blue-200",
      text: "text-blue-700",
      dot: "bg-blue-500",
    },
  };

  const currentBadge = actionBadges[action] || actionBadges.WAIT;

  // Orderbook metrics
  const bidPct = orderbook?.bid_percent != null ? Number(orderbook.bid_percent) : 50;
  const askPct = orderbook?.ask_percent != null ? Number(orderbook.ask_percent) : 50;
  const bidAskRatio = orderbook?.bid_ask_ratio != null ? Number(orderbook.bid_ask_ratio) : 1.0;
  const orderbookStatusLabel = bidAskRatio < 0.5 ? "Tipis / Kritis" : bidAskRatio < 0.9 ? "Cenderung Lemah" : bidAskRatio > 1.5 ? "Tebal / Akumulasi" : "Seimbang";

  // Technical metrics
  const rsi = tech?.rsi14 != null ? Number(tech.rsi14).toFixed(2) : "47.87";
  const rsiTag = tech?.rsi14_tag || (Number(rsi) >= 70 ? "Overbought" : Number(rsi) <= 30 ? "Oversold" : "Netral");
  const atr = tech?.atr14 != null ? Number(tech.atr14).toFixed(2) : String(keyLevels?.atr14 || "0");
  const maAlignment = tech?.ma_alignment || "MIXED";

  // Top Accumulator & Seller text
  const topBuyers = brokerFlow?.top_buyers || [];
  const topSellers = brokerFlow?.top_sellers || [];
  const topBuyerDesc = topBuyers.length > 0
    ? topBuyers.slice(0, 3).map((b: any) => `Broker ${b.broker_code} (+${formatMiliar(b.value_idr)}, porsi ${b.market_share_percent}%)`).join(", disusul ")
    : "Distribusi volume merata di berbagai broker";
  const topSellerDesc = topSellers.length > 0
    ? `Didominasi broker (${topSellers.slice(0, 4).map((s: any) => s.broker_code).join(", ")}) dengan volume transaksi dominan.`
    : "Tekanan jual normal tanpa dominasi broker tertentu.";

  // Risk factors
  const riskList = reasoning?.risk_factors
    ? reasoning.risk_factors.split("\n").map((r: string) => r.replace(/^\d+\.\s*/, "").trim()).filter(Boolean)
    : [
        "Tekanan jual berkelanjutan dari broker distribusi dan arus dana asing.",
        `Koreksi lanjutan jika harga breakdown di bawah support Rp ${(tech?.key_supports?.[0] || keyLevels?.stop_loss || 0).toLocaleString("id-ID")}.`,
      ];

  return (
    <div className="flex flex-col min-h-screen w-full bg-slate-50 text-slate-800 font-sans selection:bg-blue-600 selection:text-white">
      <h1 className="sr-only">Ringkasan Sesi</h1>

      {/* TOP HEADER NAVIGATION BAR */}
      <header className="sticky top-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-xs">
        <div className="h-16 w-full px-4 sm:px-6 flex items-center justify-between gap-3 max-w-[1600px] mx-auto">
          {/* Brand & Breadcrumbs */}
          <div className="flex items-center gap-4 min-w-0">
            <div className="flex items-center gap-2.5 shrink-0">
              <div className="w-9 h-9 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-xs font-bold text-lg">
                ⚡
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-base tracking-tight text-slate-900">TradePilot</span>
                  <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-bold uppercase border border-blue-200">
                    AI
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span className="font-mono text-[10px] text-slate-500 font-medium">GEMINI ENGINE PRO</span>
                </div>
              </div>
            </div>

            <div className="hidden xl:flex items-center gap-2 pl-3 border-l border-slate-200 text-xs text-slate-500 truncate">
              <Link
                href="/sessions"
                className="hover:text-blue-600 transition-colors flex items-center gap-1 shrink-0 font-medium"
              >
                ← Kembali ke Daftar Sesi
              </Link>
              <span className="text-slate-300">•</span>
              <span className="font-semibold text-slate-800 truncate">${session?.ticker || quote?.symbol || "EMITEN"} Analysis</span>
            </div>

            <div className="hidden md:flex items-center gap-2 shrink-0">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono text-[11px] font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                STATUS: {session?.status === "OPEN_POSITION" ? "OPEN POSITION" : session?.status || "ANALYZED"}
              </div>
              <span className="px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 font-mono text-[11px] text-slate-600 font-medium">
                {analysis?.trading_style || "Swing Trade"}
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-slate-500 border border-slate-200">
                {analyzedDateStr}
              </span>
            </div>
          </div>

          {/* Right Header Actions */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => loadData(true)}
              disabled={evaluating}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-mono text-xs font-semibold shadow-xs transition-all disabled:opacity-50 active:scale-[0.98]"
            >
              {evaluating ? (
                <>
                  <ButtonSpinner className="h-3.5 w-3.5" />
                  <span>Mengevaluasi…</span>
                </>
              ) : (
                <>
                  <span>⚡</span>
                  <span>Refresh Data & Re-Evaluasi</span>
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* MAIN VIEWPORT CANVAS */}
      <main className="relative pt-6 pb-28 w-full px-4 sm:px-6 bg-slate-50 flex-1">
        <div className="flex flex-col w-full space-y-4 max-w-[1600px] mx-auto">
          {/* In-Trade Floating Banner if Position is Active */}
          {isInTrade && (
            <div className="w-full rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 sm:p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-emerald-500 animate-ping" />
                <div>
                  <h2 className="text-base font-bold text-slate-900">
                    🟢 POSISI AKTIF: {session?.ticker} ({quantityLots} Lot)
                  </h2>
                  <p className="text-xs text-slate-600 font-mono mt-0.5">
                    Entry: Rp {entryPrice.toLocaleString("id-ID")} • Nilai Modal: Rp {capitalInvested.toLocaleString("id-ID")}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4 font-mono">
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Floating P&L</span>
                  <span className={`text-xl font-black ${floatingPnL >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                    {floatingPnL >= 0 ? "+" : ""}Rp {floatingPnL.toLocaleString("id-ID")} ({floatingPnLPercent >= 0 ? "+" : ""}{floatingPnLPercent.toFixed(2)}%)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowCloseModal(true)}
                  className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-mono text-xs font-bold shadow-xs transition-all active:scale-[0.98]"
                >
                  🚪 Tutup Posisi
                </button>
              </div>
            </div>
          )}

          {/* 1. TOP SUCCESS NOTIFICATION BANNER */}
          <div className="w-full bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-2.5 flex items-center justify-between shadow-xs">
            <div className="flex items-center gap-2.5">
              <div className="w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0 font-bold text-xs">
                ✓
              </div>
              <p className="text-xs font-semibold text-emerald-800">
                {actionSuccess || `Data pasar & analisa AI ${session?.ticker || quote?.symbol || ""} berhasil diperbarui ke harga terkini!`}
              </p>
            </div>
            <div className="flex items-center gap-3 font-mono text-[11px] text-emerald-700">
              <span className="hidden sm:inline">Sinkronisasi Realtime</span>
              <span className="px-2 py-0.5 rounded bg-white/80 border border-emerald-200 text-emerald-800 font-bold">
                {analyzedDateStr} • {analyzedTimeWib}
              </span>
            </div>
          </div>

          {/* 2. TOP TELEMETRY STRIP */}
          <section className="w-full bg-white rounded-xl p-4 sm:p-5 border border-slate-200 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-6 min-w-0">
                <div className="flex items-center gap-3.5">
                  <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-2xl text-blue-700 font-extrabold shadow-xs">
                    {(session?.ticker || quote?.symbol || "B").charAt(0)}
                  </div>
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl text-slate-900 font-bold tracking-tight">
                        ${session?.ticker || quote?.symbol}
                      </span>
                      <span className="text-sm text-slate-500 font-medium">
                        ({session?.company_name || quote?.company_name || "Perusahaan Tercatat di BEI"})
                      </span>
                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 font-semibold">
                        IDX:{companyProfile?.sector ? companyProfile.sector.toUpperCase().replace(/\s+/g, "") : "LQ45"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-500 font-mono text-xs mt-0.5">
                      <span>Tanggal: <strong className="text-slate-800 font-semibold">{analyzedDateStr}</strong></span>
                      <span className="text-slate-300">•</span>
                      <span className="flex items-center gap-1 text-slate-600">
                        ⏱️ {analysis?.trading_style || "Swing Trade"} / 1D Timeframe
                      </span>
                      <span className="text-slate-300">•</span>
                      <span>ATR(14): <strong className="text-slate-800 font-semibold">{atr}</strong></span>
                    </div>
                  </div>
                </div>

                <div className="h-10 w-px bg-slate-200 hidden lg:block" />

                {/* Price & Change Telemetry */}
                <div className="flex items-baseline gap-4">
                  <div className="flex flex-col">
                    <span className="font-mono text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                      HARGA SAAT INI
                    </span>
                    <div className="flex items-baseline gap-2">
                      <span className="font-mono text-2xl font-bold text-slate-900">
                        Rp {currentPrice.toLocaleString("id-ID")}
                      </span>
                      <span
                        className={`font-mono text-xs flex items-center font-bold px-1.5 py-0.5 rounded border ${
                          changePercent >= 0
                            ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                            : "text-rose-600 bg-rose-50 border-rose-200"
                        }`}
                      >
                        {changePercent >= 0 ? "▲ +" : "▼ "}{changePercent.toFixed(2)}% (Hari ini)
                      </span>
                    </div>
                  </div>

                  <div className="hidden sm:flex flex-col pl-2">
                    <span className="font-mono text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                      NET CHANGE
                    </span>
                    <span
                      className={`font-mono text-xs font-semibold mt-1 ${
                        changeNominal >= 0 ? "text-emerald-700" : "text-rose-600"
                      }`}
                    >
                      {changeNominal >= 0 ? "+" : ""}{changeNominal} pts ({changeNominal >= 0 ? "Bullish Momentum" : "Bearish Pressure"})
                    </span>
                  </div>
                </div>
              </div>

              {/* Recommendation & Conviction Badge */}
              <div className="flex items-center gap-3">
                <div className={`px-4 py-2 rounded-xl ${currentBadge.bg} border ${currentBadge.border} flex items-center gap-3`}>
                  <div className={`w-3 h-3 rounded-full ${currentBadge.dot} animate-pulse`} />
                  <div className="flex flex-col">
                    <span className={`font-mono text-[10px] uppercase font-bold tracking-wider ${currentBadge.text}`}>
                      REKOMENDASI AI
                    </span>
                    <span className={`text-base font-extrabold tracking-wide ${currentBadge.text}`}>
                      REKOMENDASI: {action}
                    </span>
                  </div>
                </div>

                <div className="hidden md:flex flex-col items-end px-3.5 py-1.5 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs">
                  <span className="text-slate-400 text-[10px] font-semibold uppercase">CONVICTION INDEX</span>
                  <span className={`font-bold text-base leading-tight ${convictionScore >= 70 ? "text-emerald-600" : convictionScore >= 55 ? "text-amber-600" : "text-rose-600"}`}>
                    {convictionScore}% <span className="text-xs font-normal text-slate-500">({convictionLabel})</span>
                  </span>
                </div>
              </div>
            </div>
          </section>

          {/* 3. PROFIL & VALUASI EMITEN (+ 6 METRIC CARDS & ORDERBOOK DEPTH) */}
          <section className="w-full bg-white rounded-xl p-4 sm:p-5 border border-slate-200 shadow-xs space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <span className="text-blue-600 text-lg">🏢</span>
                <h2 className="text-base text-slate-900 font-bold">PROFIL & VALUASI EMITEN</h2>
              </div>
              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="px-2.5 py-1 rounded bg-blue-50 text-blue-700 border border-blue-200 font-medium">
                  Sektor: {companyProfile?.sector || "IDX General"}
                </span>
                <span className="px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                  Sub-sektor: {companyProfile?.sub_sector || "Saham Terbuka"}
                </span>
              </div>
            </div>

            {/* 6 Financial Metric Cards */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="font-mono text-[10px] font-semibold uppercase text-slate-400">P/E RATIO (TTM)</span>
                <p className="mt-1 font-mono text-lg font-bold text-slate-900">
                  {displayPe != null ? `${Number(displayPe).toFixed(2)}x` : "-"}
                </p>
                <span className="text-[10px] text-slate-500">Valuasi atraktif</span>
              </div>

              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="font-mono text-[10px] font-semibold uppercase text-slate-400">EPS (TTM)</span>
                <p className="mt-1 font-mono text-lg font-bold text-slate-900">
                  {displayEps != null ? `Rp ${Number(displayEps).toFixed(2)}` : "-"}
                </p>
                <span className="text-[10px] text-slate-500">Per lembar saham</span>
              </div>

              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="font-mono text-[10px] font-semibold uppercase text-slate-400">DIVIDEND YIELD</span>
                <p className="mt-1 font-mono text-lg font-bold text-emerald-600">
                  {displayYield != null ? `${Number(displayYield).toFixed(2)}%` : "-"}
                </p>
                <span className="text-[10px] text-slate-500">
                  {displayDps != null ? `DPS Rp ${Number(displayDps).toLocaleString("id-ID")}` : "Dividen teratur"}
                </span>
              </div>

              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="font-mono text-[10px] font-semibold uppercase text-slate-400">BETA VS IHSG</span>
                <p className="mt-1 font-mono text-lg font-bold text-slate-900">
                  {displayBeta != null ? Number(displayBeta).toFixed(2) : "-"}
                </p>
                <span className="text-[10px] text-slate-500">
                  {displayBeta != null && Number(displayBeta) < 0 ? "Defensif / Kontra" : "Korelasi pasar"}
                </span>
              </div>

              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="font-mono text-[10px] font-semibold uppercase text-slate-400">MOMENTUM 1 THN</span>
                <p className={`mt-1 font-mono text-lg font-bold ${Number(display1YReturn || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {display1YReturn != null ? `${Number(display1YReturn) >= 0 ? "+" : ""}${Number(display1YReturn).toFixed(2)}%` : "-"}
                </p>
                <span className="text-[10px] text-slate-500">Performa tahunan</span>
              </div>

              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="font-mono text-[10px] font-semibold uppercase text-slate-400">KATALIS LAPKEU</span>
                <p className="mt-1 font-mono text-sm font-bold text-slate-900 truncate">
                  {displayNextEarnings || "Menunggu Rilis"}
                </p>
                <span className="text-[10px] text-slate-500">Jadwal earnings</span>
              </div>
            </div>

            {/* ORDERBOOK DEPTH RATIO CARD */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-3 shadow-xs">
              <div className="flex items-center justify-between gap-2 pb-1">
                <div className="flex items-center gap-2">
                  <span className="text-rose-600 text-base">📊</span>
                  <span className="font-mono text-xs font-bold text-slate-600 uppercase tracking-wider">
                    ORDERBOOK DEPTH RATIO
                  </span>
                </div>
                <span className="px-3 py-1 rounded-md bg-white text-slate-800 border border-slate-200 font-mono font-bold text-xs shadow-xs">
                  {bidAskRatio.toFixed(2)}x ({orderbookStatusLabel})
                </span>
              </div>

              <div className="flex items-center justify-between font-mono text-xs font-bold">
                <span className="text-emerald-700 tracking-wide">BID (BELI) {bidPct.toFixed(0)}%</span>
                <span className="text-rose-700 tracking-wide">ASK (JUAL) {askPct.toFixed(0)}%</span>
              </div>

              {/* Progress visual bar */}
              <div className="w-full h-3 bg-slate-200 rounded-full flex overflow-hidden p-0.5 shadow-inner">
                <div className="h-full bg-emerald-500 rounded-l-full transition-all" style={{ width: `${bidPct}%` }} />
                <div className="h-full bg-rose-500 rounded-r-full transition-all" style={{ width: `${askPct}%` }} />
              </div>

              <div className="flex items-center justify-between font-mono text-xs text-slate-500 pt-0.5">
                <span>{bidPct > 50 ? "Dukungan Beli Solid" : "Dukungan Beli Rapuh"}</span>
                <span>Spread: <strong className="text-slate-900 font-bold font-mono">Rp {orderbook?.spread ?? 25}</strong></span>
                <span>{askPct > 50 ? "Tembok Penjual Padat" : "Penjual Longgar"}</span>
              </div>

              <div className="pt-2 border-t border-slate-200 flex items-center justify-between gap-2 text-xs text-slate-600">
                <span className="font-medium">
                  <strong className="text-slate-900 font-semibold">Kesimpulan Flow: </strong>
                  {reasoning?.flow_conclusion || "Tekanan jual asing masih terasa, konfirmasi akumulasi baru masih ditunggu."}
                </span>
                <span className="hidden sm:inline-flex items-center gap-2 font-mono text-[11px] text-slate-500 shrink-0">
                  <span>Bid: <strong className="text-emerald-700">{orderbook?.total_bid_lots?.toLocaleString("id-ID") ?? "0"} lot</strong></span>
                  <span>•</span>
                  <span>Ask: <strong className="text-rose-700">{orderbook?.total_ask_lots?.toLocaleString("id-ID") ?? "0"} lot</strong></span>
                </span>
              </div>
            </div>
          </section>

          {/* 4. ARUS DANA (BANDARMOLOGY & FOREIGN FLOW) */}
          <section className="w-full bg-white rounded-xl p-4 sm:p-5 border border-slate-200 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <span className="text-blue-600 text-lg">💰</span>
                <h2 className="text-base text-slate-900 font-bold">ARUS DANA (BANDARMOLOGY & FOREIGN FLOW)</h2>
              </div>
              <span className={`px-2.5 py-0.5 rounded font-mono text-[11px] font-bold border ${
                brokerFlow?.bandar_status?.includes("ACCUMULATION")
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : "bg-rose-50 text-rose-800 border-rose-200"
              }`}>
                {brokerFlow?.bandar_status || "DISTRIBUSI TERKONFIRMASI"}
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Panel Kiri: STATUS BANDAR */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-rose-600">🥧</span>
                    <span className="font-mono text-xs font-bold text-slate-800">STATUS BANDAR</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-white font-mono text-[10px] font-bold uppercase tracking-wide ${
                    brokerFlow?.bandar_status?.includes("ACCUMULATION") ? "bg-emerald-600" : "bg-rose-600"
                  }`}>
                    {brokerFlow?.bandar_status || "BIG_DISTRIBUTION"}
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-white border border-slate-200 flex items-center justify-between">
                  <span className="font-mono text-xs text-slate-600 font-medium">Konsentrasi Top 3 Buyer:</span>
                  <span className="font-mono text-xs font-bold text-slate-900">
                    {brokerFlow?.top3_buyers_concentration_percent ?? "57.6"}%{" "}
                    <span className="text-emerald-700 font-semibold">
                      {Number(brokerFlow?.top3_buyers_concentration_percent || 0) > 75 ? "(Sangat Terakumulasi)" : "(Wajar)"}
                    </span>
                  </span>
                </div>

                <div className="space-y-2 text-xs leading-relaxed">
                  <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                    <span className="font-mono text-[10px] text-blue-700 font-bold uppercase block mb-1">
                      Akumulator Utama
                    </span>
                    <p className="text-slate-600">{topBuyerDesc}</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                    <span className="font-mono text-[10px] text-rose-700 font-bold uppercase block mb-1">
                      Distribusi Penjual
                    </span>
                    <p className="text-slate-600">{topSellerDesc}</p>
                  </div>
                </div>
              </div>

              {/* Panel Kanan: STATUS ASING */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-blue-600">🌐</span>
                    <span className="font-mono text-xs font-bold text-slate-800">STATUS ASING</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-white font-mono text-[10px] font-bold uppercase tracking-wide ${
                    foreignFlow?.foreign_status?.includes("ACCUMULATION") ? "bg-emerald-600" : "bg-rose-600"
                  }`}>
                    {foreignFlow?.foreign_status || "DISTRIBUTION"}
                  </span>
                </div>

                {/* 4 Timeframe Cards 2x2 Grid */}
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="p-2.5 rounded-lg bg-white border border-slate-200 flex flex-col">
                    <span className="font-mono text-[10px] text-slate-400 uppercase font-bold">1 HARI</span>
                    <span className={`font-mono text-sm font-bold mt-0.5 ${Number(foreignFlow?.today_1d?.net_value_idr || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {foreignFlow?.today_1d ? formatMiliar(foreignFlow.today_1d.net_value_idr) : "-"}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500 font-medium mt-0.5">
                      {foreignFlow?.today_1d ? formatShares(foreignFlow.today_1d.net_shares) : ""}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-white border border-slate-200 flex flex-col">
                    <span className="font-mono text-[10px] text-slate-400 uppercase font-bold">1 MINGGU</span>
                    <span className={`font-mono text-sm font-bold mt-0.5 ${Number(foreignFlow?.weekly_1w?.net_value_idr || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {foreignFlow?.weekly_1w ? formatMiliar(foreignFlow.weekly_1w.net_value_idr) : "-"}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500 font-medium mt-0.5">
                      {foreignFlow?.weekly_1w ? formatShares(foreignFlow.weekly_1w.net_shares) : ""}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-white border border-slate-200 flex flex-col">
                    <span className="font-mono text-[10px] text-slate-400 uppercase font-bold">1 BULAN</span>
                    <span className={`font-mono text-sm font-bold mt-0.5 ${Number(foreignFlow?.monthly_1m?.net_value_idr || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {foreignFlow?.monthly_1m ? formatMiliar(foreignFlow.monthly_1m.net_value_idr) : "-"}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500 font-medium mt-0.5">
                      {foreignFlow?.monthly_1m ? formatShares(foreignFlow.monthly_1m.net_shares) : ""}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-white border border-slate-200 flex flex-col">
                    <span className="font-mono text-[10px] text-slate-400 uppercase font-bold">3 BULAN</span>
                    <span className={`font-mono text-sm font-bold mt-0.5 ${Number(foreignFlow?.three_month_3m?.net_value_idr || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {foreignFlow?.three_month_3m ? formatMiliar(foreignFlow.three_month_3m.net_value_idr) : "-"}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500 font-medium mt-0.5">
                      {foreignFlow?.three_month_3m ? formatShares(foreignFlow.three_month_3m.net_shares) : ""}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Flow Bar */}
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-slate-700">
                <span className="text-blue-600 text-sm">💡</span>
                <span className="font-medium">
                  <strong className="text-slate-900 font-semibold">Kesimpulan Flow: </strong>
                  {reasoning?.flow_conclusion || "Tekanan jual asing masih terasa, konfirmasi akumulasi baru masih ditunggu."}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
                <span className="px-2 py-1 rounded bg-white border border-slate-200 text-rose-600 font-bold">
                  Orderbook: {bidAskRatio.toFixed(2)}x
                </span>
                <span className="px-2 py-1 rounded bg-white border border-slate-200 text-slate-700 font-medium">
                  Spread: Rp {orderbook?.spread ?? 25}
                </span>
                <span className="px-2 py-1 rounded bg-white border border-slate-200 text-emerald-700 font-medium">
                  Bid: {orderbook?.total_bid_lots?.toLocaleString("id-ID") ?? "0"} lot
                </span>
                <span className="px-2 py-1 rounded bg-white border border-slate-200 text-rose-700 font-medium">
                  Ask: {orderbook?.total_ask_lots?.toLocaleString("id-ID") ?? "0"} lot
                </span>
              </div>
            </div>
          </section>

          {/* 5. ANALISIS TEKNIKAL & STRUKTUR TREN */}
          <section className="w-full bg-white rounded-xl p-4 sm:p-5 border border-slate-200 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <span className="text-blue-600 text-lg">📈</span>
                <h2 className="text-base text-slate-900 font-bold">ANALISIS TEKNIKAL & STRUKTUR TREN</h2>
              </div>
              <span className={`px-2.5 py-0.5 rounded font-mono text-[11px] font-bold border uppercase ${
                maAlignment === "BULLISH_ALIGNMENT"
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : maAlignment === "BEARISH_ALIGNMENT"
                  ? "bg-rose-50 text-rose-800 border-rose-200"
                  : "bg-amber-50 text-amber-800 border-amber-200"
              }`}>
                TREN UTAMA: {maAlignment}
              </span>
            </div>

            {/* 4 Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
                <span className="font-mono text-[10px] text-slate-400 uppercase font-bold">MOVING AVERAGES</span>
                <div className="mt-1">
                  <div className="flex items-center justify-between font-mono text-xs font-bold text-slate-900">
                    <span>MA20: Rp {tech?.ma20 ? Number(tech.ma20).toLocaleString("id-ID") : "-"}</span>
                    <span>MA50: Rp {tech?.ma50 ? Number(tech.ma50).toLocaleString("id-ID") : "-"}</span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-600 font-semibold block mt-1">
                    {tech?.price_vs_ma20 ? `Harga ${tech.price_vs_ma20}` : `Harga Rp ${currentPrice.toLocaleString("id-ID")}`}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-slate-400 uppercase font-bold">RSI (14 MOMENTUM)</span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-mono text-[9px] font-bold">
                    {rsiTag}
                  </span>
                </div>
                <div className="mt-1">
                  <span className="font-mono text-base font-bold text-slate-900 block">{rsi}</span>
                  <span className="font-mono text-[10px] text-slate-500 font-medium">Momentum tren stabil</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
                <span className="font-mono text-[10px] text-slate-400 uppercase font-bold">ATR (14 VOLATILITAS)</span>
                <div className="mt-1">
                  <span className="font-mono text-base font-bold text-slate-900 block">{atr}</span>
                  <span className="font-mono text-[10px] text-slate-500 font-medium">Poin rentang fluktuasi harian</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
                <span className="font-mono text-[10px] text-slate-400 uppercase font-bold">LEVEL KUNCI</span>
                <div className="mt-1">
                  <div className="font-mono text-[11px] text-slate-800 font-bold leading-tight">
                    Resist: Rp {(tech?.key_resistances?.[0] || keyLevels?.target_price_1 || 0).toLocaleString("id-ID")}{" "}
                    <span className="text-slate-400 text-[9px]">(52W: {tech?.high_52w ?? "-"})</span>
                  </div>
                  <div className="font-mono text-[11px] text-slate-800 font-bold leading-tight mt-0.5">
                    Support: Rp {(tech?.key_supports?.[0] || keyLevels?.stop_loss || 0).toLocaleString("id-ID")}{" "}
                    <span className="text-slate-400 text-[9px]">(52W: {tech?.low_52w ?? "-"})</span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-500 font-medium block mt-0.5">
                    Area batas dinamis & fraktal
                  </span>
                </div>
              </div>
            </div>

            {/* SVG Candlestick Visualizer */}
            <div className="w-full h-52 bg-slate-50 border border-slate-200 rounded-xl p-3 relative overflow-hidden flex flex-col justify-between">
              <div className="absolute inset-0 flex flex-col justify-between p-3 opacity-60 pointer-events-none">
                <div className="w-full h-px bg-slate-200" />
                <div className="w-full h-px bg-slate-200" />
                <div className="w-full h-px bg-slate-200" />
                <div className="w-full h-px bg-slate-200" />
              </div>

              <div className="relative z-10 flex items-center justify-between font-mono text-[11px] text-slate-500">
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-1 text-rose-600 font-medium">
                    <span className="w-2.5 h-0.5 bg-rose-500"></span> MA20 ({tech?.ma20 ? Number(tech.ma20).toLocaleString("id-ID") : "6.481"})
                  </span>
                  <span className="inline-flex items-center gap-1 text-blue-600 font-medium">
                    <span className="w-2.5 h-0.5 bg-blue-500"></span> MA50 ({tech?.ma50 ? Number(tech.ma50).toLocaleString("id-ID") : "6.350"})
                  </span>
                </div>
                <span className="text-slate-400 font-semibold">${session?.ticker || quote?.symbol} / 1D INTERVAL</span>
              </div>

              <div className="relative w-full h-36">
                <svg className="w-full h-full" fill="none" preserveAspectRatio="none" viewBox="0 0 460 140">
                  <path
                    className="text-blue-500"
                    d="M 0,110 C 100,105 200,98 320,102 C 380,105 420,108 460,110"
                    stroke="currentColor"
                    strokeDasharray="3 3"
                    strokeWidth="2"
                  />
                  <path
                    className="text-rose-500"
                    d="M 0,55 C 120,60 220,68 330,72 C 390,75 420,78 460,82"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <rect className="text-blue-600" fill="currentColor" fillOpacity="0.08" height="38" rx="4" width="195" x="260" y="70" />
                  <line className="text-blue-500" stroke="currentColor" strokeDasharray="2 2" strokeOpacity="0.5" strokeWidth="1" x1="260" x2="455" y1="70" y2="70" />
                  <line className="text-blue-500" stroke="currentColor" strokeDasharray="2 2" strokeOpacity="0.5" strokeWidth="1" x1="260" x2="455" y1="108" y2="108" />
                  <text className="text-[9px] fill-blue-700 font-mono font-bold" x="265" y="80">
                    Entry Band Rp {keyLevels?.entry_range?.[0]?.toLocaleString("id-ID") ?? "6.325"} - {keyLevels?.entry_range?.[1]?.toLocaleString("id-ID") ?? "6.450"}
                  </text>
                  <line className="text-emerald-600" stroke="currentColor" strokeWidth="1" x1="30" x2="30" y1="40" y2="85" />
                  <rect className="text-emerald-500" fill="currentColor" height="28" rx="1" width="8" x="26" y="48" />
                  <line className="text-rose-600" stroke="currentColor" strokeWidth="1" x1="65" x2="65" y1="42" y2="92" />
                  <rect className="text-rose-500" fill="currentColor" height="32" rx="1" width="8" x="61" y="52" />
                  <line className="text-emerald-600" stroke="currentColor" strokeWidth="1" x1="100" x2="100" y1="45" y2="88" />
                  <rect className="text-emerald-500" fill="currentColor" height="25" rx="1" width="8" x="96" y="50" />
                  <line className="text-rose-600" stroke="currentColor" strokeWidth="1" x1="135" x2="135" y1="48" y2="95" />
                  <rect className="text-rose-500" fill="currentColor" height="30" rx="1" width="8" x="131" y="55" />
                  <line className="text-emerald-600" stroke="currentColor" strokeWidth="1" x1="170" x2="170" y1="52" y2="90" />
                  <rect className="text-emerald-500" fill="currentColor" height="20" rx="1" width="8" x="166" y="58" />
                  <line className="text-rose-600" stroke="currentColor" strokeWidth="1" x1="205" x2="205" y1="50" y2="98" />
                  <rect className="text-rose-500" fill="currentColor" height="26" rx="1" width="8" x="201" y="62" />
                  <line className="text-rose-600" stroke="currentColor" strokeWidth="1" x1="240" x2="240" y1="58" y2="105" />
                  <rect className="text-rose-500" fill="currentColor" height="28" rx="1" width="8" x="236" y="68" />
                  <line className="text-emerald-600" stroke="currentColor" strokeWidth="1" x1="275" x2="275" y1="62" y2="102" />
                  <rect className="text-emerald-500" fill="currentColor" height="18" rx="1" width="8" x="271" y="72" />
                  <line className="text-rose-600" stroke="currentColor" strokeWidth="1" x1="310" x2="310" y1="65" y2="108" />
                  <rect className="text-rose-500" fill="currentColor" height="24" rx="1" width="8" x="306" y="74" />
                  <line className="text-rose-600" stroke="currentColor" strokeWidth="1" x1="345" x2="345" y1="68" y2="112" />
                  <rect className="text-rose-500" fill="currentColor" height="26" rx="1" width="8" x="341" y="78" />
                  <line className="text-rose-600" stroke="currentColor" strokeWidth="1" x1="380" x2="380" y1="70" y2="114" />
                  <rect className="text-rose-500" fill="currentColor" height="26" rx="1" width="8" x="376" y="80" />
                  <line className="text-rose-700" stroke="currentColor" strokeWidth="2" x1="415" x2="415" y1="72" y2="118" />
                  <rect className="text-rose-600" fill="currentColor" height="30" rx="1" width="10" x="410" y="82" />
                  <circle className="text-rose-600" cx="415" cy="97" fill="currentColor" r="4" />
                  <circle className="animate-ping text-rose-500" cx="415" cy="97" opacity="0.6" r="8" stroke="currentColor" strokeWidth="1.5" />
                </svg>
              </div>

              <div className="relative z-10 flex items-center justify-between font-mono text-[11px] pt-1 border-t border-slate-200">
                <span className="text-slate-600 flex items-center gap-1.5 font-medium">
                  <span className="w-2 h-2 rounded-full bg-rose-500"></span> MA20 Resistance: Rp {tech?.ma20 ? Number(tech.ma20).toLocaleString("id-ID") : "6.481"}
                </span>
                <span className="text-slate-600 flex items-center gap-1.5 font-medium">
                  <span className="w-2 h-2 rounded-full bg-blue-600"></span> MA50 Support: Rp {tech?.ma50 ? Number(tech.ma50).toLocaleString("id-ID") : "6.350"}
                </span>
              </div>
            </div>
          </section>

          {/* 6. SKENARIO & REKOMENDASI TRADING PLAN */}
          <section className="w-full bg-white rounded-xl p-4 sm:p-5 border border-slate-200 shadow-xs flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <span className="text-blue-600 text-lg">🎯</span>
                <h2 className="text-base text-slate-900 font-bold">SKENARIO & REKOMENDASI TRADING PLAN</h2>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2.5 py-0.5 rounded text-white font-mono text-xs font-bold ${
                  action === "BUY" ? "bg-emerald-600" : action === "WAIT" ? "bg-amber-600" : "bg-rose-600"
                }`}>
                  {action}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-[10px] font-bold border border-slate-200">
                  Kualitas: {analysis?.setup_quality || "STANDARD"} • Akurasi: {convictionScore}%
                </span>
              </div>
            </div>

            {/* Alert Kondisi Pasar */}
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-800 flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-slate-700">ℹ️</span>
                <span className="font-bold text-xs text-slate-900">
                  Kondisi Pasar: {marketContext?.index_summary || "IHSG bergerak konsolidasi"}
                </span>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed">
                {reasoning?.thesis_summary || `Setup ${session?.ticker || ""} sebaiknya dipantau secara seksama. Disiplin batasi risiko dan perhatikan level reaksi harga.`}
              </p>
              <span className="font-mono text-[11px] text-blue-700 font-bold mt-0.5">
                Strategi: {action === "BUY" ? "Buy on Weakness / Antri Pullback" : action === "WAIT" ? "Wait for Confirmation / Pantau Level" : "Avoid / Cari Peluang Lain"}
              </span>
            </div>

            {/* 4 Key Levels Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg bg-blue-50/50 border border-blue-200 border-l-4 border-l-blue-600 flex flex-col justify-between">
                <span className="font-mono text-[10px] text-blue-800 font-bold uppercase">AREA ENTRY (BELI)</span>
                <div className="mt-1">
                  <span className="font-mono text-sm font-bold text-slate-900 block">
                    Rp {keyLevels?.entry_range?.[0]?.toLocaleString("id-ID") ?? "-"} – {keyLevels?.entry_range?.[1]?.toLocaleString("id-ID") ?? "-"}
                  </span>
                  <span className="font-mono text-[10px] text-blue-700 font-semibold">Optimal Buy Range</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-emerald-50/50 border border-emerald-200 border-l-4 border-l-emerald-500 flex flex-col justify-between">
                <span className="font-mono text-[10px] text-emerald-800 font-bold uppercase">TARGET PROFIT (TP)</span>
                <div className="mt-1">
                  <div className="font-mono text-xs font-bold text-emerald-700">
                    TP1: Rp {keyLevels?.target_price_1?.toLocaleString("id-ID") ?? "-"}
                  </div>
                  <div className="font-mono text-xs font-bold text-emerald-700">
                    TP2: Rp {keyLevels?.target_price_2?.toLocaleString("id-ID") ?? "-"}
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-rose-50/50 border border-rose-200 border-l-4 border-l-rose-500 flex flex-col justify-between">
                <span className="font-mono text-[10px] text-rose-800 font-bold uppercase">STOP LOSS (SL)</span>
                <div className="mt-1">
                  <span className="font-mono text-sm font-bold text-rose-700 block">
                    Rp {keyLevels?.stop_loss?.toLocaleString("id-ID") ?? "-"}
                  </span>
                  <span className="font-mono text-[10px] text-slate-500 font-medium">
                    Invalidasi: Rp {keyLevels?.invalidation_level?.toLocaleString("id-ID") ?? "-"}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 border-l-4 border-l-slate-400 flex flex-col justify-between">
                <span className="font-mono text-[10px] text-slate-700 font-bold uppercase">RISK / REWARD</span>
                <div className="mt-1">
                  <span className="font-mono text-sm font-bold text-slate-900 block">
                    1 : {keyLevels?.risk_reward_ratio ?? "1.8"}
                  </span>
                  <span className="font-mono text-[10px] text-slate-500 font-medium">
                    ATR(14): Rp {atr}
                  </span>
                </div>
              </div>
            </div>

            {/* PANDUAN ACTION 3-Column Card */}
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <span className="text-blue-600 text-sm">🧠</span>
                <span className="font-mono text-xs font-bold text-slate-900 uppercase">
                  {action === "BUY" ? "PANDUAN ENTRY & TARGET" : action === "WAIT" ? "PANDUAN WAIT (PEMANTAUAN)" : "PANDUAN SKIP (LEWATI)"}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="bg-white p-2.5 rounded border border-slate-200">
                  <span className="font-mono text-[10px] text-slate-400 uppercase font-bold block mb-0.5">STRATEGI</span>
                  <p className="font-semibold text-slate-800">
                    {action === "BUY" ? "Buy on Weakness / Follow-through" : action === "WAIT" ? "Tunggu Reaksi Support / Pullback" : "Avoid / Cari Peluang Lain"}
                  </p>
                </div>
                <div className="bg-white p-2.5 rounded border border-slate-200">
                  <span className="font-mono text-[10px] text-slate-400 uppercase font-bold block mb-0.5">ALASAN</span>
                  <p className="text-slate-600">
                    {reasoning?.action_guidance || reasoning?.wait_guidance || "Rasio risk/reward serta konfirmasi arus dana dianalisis secara objektif."}
                  </p>
                </div>
                <div className="bg-white p-2.5 rounded border border-slate-200">
                  <span className="font-mono text-[10px] text-slate-400 uppercase font-bold block mb-0.5">BATAS PANTAU</span>
                  <p className="text-slate-600">
                    Batas aman stop loss berada di level <strong className="text-slate-900 font-mono font-semibold">Rp {keyLevels?.stop_loss?.toLocaleString("id-ID") ?? "-"}</strong>.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* 7. RISIKO & KATALIS YANG PERLU DIPERHATIKAN */}
          <section className="w-full bg-amber-50/70 rounded-xl p-4 sm:p-5 border border-amber-200 shadow-xs flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <span className="text-amber-600 text-lg">⚠️</span>
              <h2 className="text-base text-amber-900 font-bold">RISIKO & KATALIS YANG PERLU DIPERHATIKAN</h2>
            </div>
            <div className="space-y-2 text-xs">
              {riskList.map((risk: string, idx: number) => (
                <div key={idx} className="p-2.5 rounded-lg bg-white border border-amber-200 flex items-start gap-2 text-slate-700">
                  <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-800 font-mono font-bold flex items-center justify-center shrink-0 text-[11px]">
                    {idx + 1}
                  </span>
                  <p className="mt-0.5 leading-relaxed">{risk}</p>
                </div>
              ))}
            </div>
            <div className="pt-2 border-t border-amber-200 text-slate-500 font-mono text-[10px] leading-relaxed">
              <strong className="text-slate-700">Disclaimer: </strong>
              Analisis ini bersifat edukatif dan advisori berbasis data pasar terverifikasi. Keputusan investasi dan eksekusi tetap berada di tangan masing-masing trader.
            </div>
          </section>
        </div>
      </main>

      {/* FIXED BOTTOM EXECUTION DESK STRIP */}
      <aside className="fixed bottom-0 left-0 right-0 z-40 h-16 bg-white/95 backdrop-blur-md border-t border-slate-200 px-4 sm:px-6 flex items-center justify-between gap-4 shadow-md">
        <div className="flex items-center gap-4 min-w-0 max-w-[1600px]">
          <div className="flex items-center gap-2 shrink-0">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-ping"></span>
            <span className="font-mono text-xs text-slate-800 uppercase tracking-wider font-bold">Aksi Cepat:</span>
          </div>
          <p className="text-xs text-slate-600 truncate hidden sm:block">
            {isInTrade ? "Kelola posisi aktif saham ini" : "Eksekusi atau pantau setup emiten ini secara terarah"}
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          {isInTrade ? (
            <>
              <button
                type="button"
                onClick={() => loadData(true)}
                disabled={evaluating}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-mono text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 disabled:opacity-50 active:scale-[0.98]"
              >
                {evaluating ? <ButtonSpinner className="h-3.5 w-3.5" /> : "⚡"}
                <span>Update Posisi</span>
              </button>
              <button
                type="button"
                onClick={() => setShowCloseModal(true)}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-mono text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 active:scale-[0.98]"
              >
                <span>🚪</span>
                <span>Tutup Posisi</span>
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setShowBuyModal(true)}
                className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 active:scale-[0.98]"
              >
                <span>▲</span>
                <span>BUY</span>
              </button>
              <button
                type="button"
                onClick={handleWait}
                disabled={isWaiting || submittingAction}
                className="px-5 py-2 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 font-mono text-xs font-bold transition-all flex items-center gap-1.5 disabled:opacity-50 active:scale-[0.98]"
              >
                {isWaiting ? <ButtonSpinner className="h-3.5 w-3.5" /> : <span>⏳</span>}
                <span>WAIT</span>
              </button>
              <button
                type="button"
                onClick={() => setShowSkipModal(true)}
                className="px-5 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-mono text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 active:scale-[0.98]"
              >
                <span>✕</span>
                <span>SKIP</span>
              </button>

              {session?.archived_at ? (
                <button
                  type="button"
                  onClick={handleRestore}
                  disabled={isRestoring || submittingAction}
                  className="px-3.5 py-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-mono text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
                >
                  {isRestoring ? <ButtonSpinner className="h-3.5 w-3.5" /> : "Pulihkan"}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleArchive}
                  disabled={isArchiving || submittingAction}
                  className="px-3.5 py-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-mono text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
                >
                  {isArchiving ? <ButtonSpinner className="h-3.5 w-3.5" /> : "Arsip"}
                </button>
              )}
            </>
          )}
        </div>
      </aside>

      {/* BUY Modal */}
      {showBuyModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-xl font-bold text-slate-900">
              🚀 Eksekusi Posisi BUY - {session?.ticker}
            </h3>
            <form onSubmit={handleBuy} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase">
                  Harga Beli (Rp)
                </label>
                <input
                  type="number"
                  value={buyPrice}
                  onChange={(e) => setBuyPrice(e.target.value)}
                  placeholder={String(currentPrice || "0")}
                  required
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-base font-bold text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase">
                  Jumlah Lot
                </label>
                <input
                  type="number"
                  value={buyLots}
                  onChange={(e) => setBuyLots(e.target.value)}
                  min="1"
                  required
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-base font-bold text-slate-900"
                />
                <p className="mt-1 text-xs text-slate-500 font-mono">
                  Total Nilai: Rp {(Number(buyPrice || currentPrice) * Number(buyLots || 0) * 100).toLocaleString("id-ID")}
                </p>
              </div>

              <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600 space-y-1 font-mono">
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
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
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

      {/* CLOSE Position Modal */}
      {showCloseModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-xl font-bold text-slate-900">
              🚪 Tutup Posisi (Jual) - {session?.ticker}
            </h3>
            <form onSubmit={handleClosePosition} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase">
                  Harga Jual / Exit (Rp)
                </label>
                <input
                  type="number"
                  value={closePrice}
                  onChange={(e) => setClosePrice(e.target.value)}
                  placeholder={String(currentPrice || "0")}
                  required
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-base font-bold text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase">
                  Alasan Penutupan Posisi
                </label>
                <select
                  value={closeReason}
                  onChange={(e) => setCloseReason(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900"
                >
                  <option value="TARGET_HIT">🎯 Mencapai Target TP1 / TP2</option>
                  <option value="STOP_LOSS_HIT">🛑 Kena Stop Loss (SL)</option>
                  <option value="MANUAL">💼 Tutup Manual / Amankan Profit</option>
                  <option value="INVALIDATED">⚠️ Struktur Berubah (Invalidasi)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase">
                  Catatan Exit (Opsional)
                </label>
                <input
                  type="text"
                  value={closeNote}
                  onChange={(e) => setCloseNote(e.target.value)}
                  placeholder="Catatan evaluasi trading..."
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800"
                />
              </div>

              <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600 space-y-1 font-mono">
                <div className="flex justify-between">
                  <span>Harga Beli (Entry):</span>
                  <span className="font-bold text-slate-900">Rp {entryPrice.toLocaleString("id-ID")}</span>
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
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
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

      {/* SKIP Modal */}
      {showSkipModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-xl font-bold text-slate-900">
              ⏭️ Lewati Saham ({session?.ticker})
            </h3>
            <p className="text-xs text-slate-500">
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
                  className="flex items-center justify-between rounded-lg border border-slate-200 p-3 text-left text-sm font-semibold text-slate-800 hover:bg-slate-50 active:scale-[0.98] transition-all disabled:opacity-50"
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
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Batal
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
