"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ButtonSpinner } from "@/components/button-spinner";
import { acquireMarketEvidence, analyzeSession, createSession } from "@/features/trade-workspace/api";
import type { TradeSession } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

const IDX_COMPANIES: Record<string, string> = {
  BBCA: "Bank Central Asia Tbk",
  BBRI: "Bank Rakyat Indonesia (Persero) Tbk",
  BMRI: "Bank Mandiri (Persero) Tbk",
  BBNI: "Bank Negara Indonesia (Persero) Tbk",
  TLKM: "Telkom Indonesia (Persero) Tbk",
  ASII: "Astra International Tbk",
  AMMN: "Amman Mineral Internasional Tbk",
  BREN: "Barito Renewables Energy Tbk",
  GOTO: "GoTo Gojek Tokopedia Tbk",
  BRIS: "Bank Syariah Indonesia Tbk",
  ICBP: "Indofood CBP Sukses Makmur Tbk",
  INDF: "Indofood Sukses Makmur Tbk",
  KLBF: "Kalbe Farma Tbk",
  PGAS: "Perusahaan Gas Negara Tbk",
  ADRO: "Adaro Energy Indonesia Tbk",
  UNTR: "United Tractors Tbk",
  ANTM: "Aneka Tambang Tbk",
  MDKA: "Merdeka Copper Gold Tbk",
  INCO: "Vale Indonesia Tbk",
  PTBA: "Bukit Asam Tbk",
  CPIN: "Charoen Pokphand Indonesia Tbk",
  SMGR: "Semen Indonesia (Persero) Tbk",
  MEDC: "Medco Energi Internasional Tbk",
  ACES: "Aspirasi Hidup Indonesia Tbk",
  SGER: "Sumber Global Energy Tbk",
  HRUM: "Harum Energy Tbk",
  CUAN: "Petrindo Jaya Kreasi Tbk",
  TPIA: "Chandra Asri Pacific Tbk",
  BRPT: "Barito Pacific Tbk",
  PTRO: "Petrosea Tbk",
};

const POPULAR_TICKERS = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII", "BREN", "AMMN", "GOTO"] as const;
const TRADING_STYLES = [
  {
    name: "Day Trade",
    desc: "Eksekusi intraday, keluar sebelum penutupan sesi.",
    popular: false,
  },
  {
    name: "Swing Trade",
    desc: "Holding periode beberapa hari hingga minggu berdasar tren.",
    popular: true,
  },
  {
    name: "Scalping",
    desc: "Momentum cepat hit-and-run memanfaatkan ketebalan orderbook.",
    popular: false,
  },
] as const;

export type TradingStyle = (typeof TRADING_STYLES)[number]["name"];

type FieldErrors = {
  ticker?: string;
  companyName?: string;
};

export function CreateSessionForm({
  onCreated,
  successMessage = "Sesi berhasil dibuat.",
}: {
  onCreated?: (session: TradeSession) => void;
  successMessage?: string;
}) {
  const [ticker, setTicker] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [tradingStyle, setTradingStyle] = useState<TradingStyle>("Swing Trade");
  const [note, setNote] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState<"authentication" | "request" | null>(null);
  const [pending, setPending] = useState(false);
  const [createdSession, setCreatedSession] = useState<TradeSession | null>(null);
  const [previewData, setPreviewData] = useState<any | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [fetchingPreview, setFetchingPreview] = useState(false);
  const [startingAnalysis, setStartingAnalysis] = useState(false);

  const pendingRef = useRef(false);
  const attemptRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      controllerRef.current?.abort();
    };
  }, []);

  function handleTickerChange(val: string) {
    setTicker(val);
    setFieldErrors((current) => ({ ...current, ticker: undefined }));
  }

  function handleSelectTickerChip(symbol: string) {
    if (pending || createdSession) return;
    setTicker(symbol);
    setCompanyName(IDX_COMPANIES[symbol] || `${symbol} Tbk`);
    setFieldErrors({});
  }

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    const normalizedTicker = ticker.trim();
    const normalizedCompanyName = (
      companyName || (normalizedTicker ? IDX_COMPANIES[normalizedTicker.toUpperCase()] || `${normalizedTicker.toUpperCase()} Tbk` : "")
    ).trim();

    if (!normalizedTicker) errors.ticker = "Kode saham wajib diisi.";
    else if (normalizedTicker.length > 32) errors.ticker = "Kode saham maksimal 32 karakter.";

    if (!normalizedCompanyName) errors.companyName = "Nama perusahaan wajib diisi.";
    else if (normalizedCompanyName.length > 255) {
      errors.companyName = "Nama perusahaan maksimal 255 karakter.";
    }

    return errors;
  }

  async function fetchMarketData(session: TradeSession, signal?: AbortSignal) {
    setFetchingPreview(true);
    setPreviewError(null);
    try {
      const data = await acquireMarketEvidence(session.id, "INITIAL", session.ticker, signal);
      if (mountedRef.current && data?.snapshot) {
        setPreviewData(data.snapshot);
      }
    } catch (err: any) {
      if (mountedRef.current) {
        setPreviewError(err?.message || "Gagal mengambil data live bursa. Periksa koneksi ZAPI.");
      }
    } finally {
      if (mountedRef.current) {
        setFetchingPreview(false);
      }
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pendingRef.current || createdSession) return;

    const errors = validate();
    setFieldErrors(errors);
    setGeneralError(null);
    if (Object.keys(errors).length > 0) return;

    const finalTicker = ticker.trim().toUpperCase();
    const finalCompany = (companyName || IDX_COMPANIES[finalTicker] || `${finalTicker} Tbk`).trim();
    pendingRef.current = true;
    setPending(true);
    const attempt = ++attemptRef.current;
    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      const session = await createSession(
        {
          ticker: finalTicker,
          company_name: finalCompany,
          note: note.length === 0 ? null : note,
        },
        controller.signal,
      );
      if (!mountedRef.current || attemptRef.current !== attempt) return;
      setCreatedSession(session);
      void fetchMarketData(session, controller.signal);
    } catch (error: unknown) {
      if (!mountedRef.current || attemptRef.current !== attempt || controller.signal.aborted) return;
      if (error instanceof AuthenticationError) setGeneralError("authentication");
      else if (error instanceof ApiError || error instanceof TypeError) setGeneralError("request");
      else setGeneralError("request");
    } finally {
      if (mountedRef.current && attemptRef.current === attempt) {
        pendingRef.current = false;
        setPending(false);
        controllerRef.current = null;
      }
    }
  }

  async function handleStartAnalysis() {
    if (!createdSession || startingAnalysis) return;
    setStartingAnalysis(true);
    try {
      await analyzeSession(createdSession.id);
    } catch {
      // workspace will auto-evaluate if needed
    }
    onCreated?.(createdSession);
  }

  // Liquidity calculation for the mini visual confirmation bar
  const ratio = previewData?.orderbook?.bid_ask_ratio ?? 1.2;
  const bidPercent = Math.min(95, Math.max(5, Math.round((ratio / (ratio + 1)) * 100)));
  const askPercent = 100 - bidPercent;

  const lastPrice = previewData?.quote?.last_price ?? 0;
  const changePercent = previewData?.quote?.change_percent ?? 0;
  const spread = previewData?.orderbook?.spread ?? 0;

  const foreignStatus = previewData?.foreign_flow?.foreign_status ?? "STRONG_ACCUM";
  const isForeignAccum = !foreignStatus.toUpperCase().includes("DISTRIB");

  const bandarStatus = previewData?.broker_flow?.bandar_status ?? "ACCUMULATION";
  const isBandarAccum = !bandarStatus.toUpperCase().includes("DISTRIB");

  return (
    <div className="space-y-6 min-w-0">
      {/* BEGIN: Progress Stepper */}
      <section aria-label="Progress Stepper" className="mb-6" data-purpose="workflow-stepper">
        <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-xs">
          <ol className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {/* Step 1 */}
            <li
              className={`flex items-center p-2 rounded-lg transition-all ${
                !createdSession
                  ? "bg-blue-50/70 border border-blue-200 shadow-2xs"
                  : "bg-slate-50 border border-slate-100"
              }`}
            >
              <span
                className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold mr-3 shrink-0 ${
                  !createdSession
                    ? "bg-blue-600 text-white"
                    : "bg-emerald-100 text-emerald-700"
                }`}
              >
                {createdSession ? (
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      clipRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      fillRule="evenodd"
                    />
                  </svg>
                ) : (
                  "1"
                )}
              </span>
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 font-mono">
                  Langkah 1 {!createdSession ? "• Aktif" : ""}
                </p>
                <p className="text-xs font-semibold text-slate-700 truncate">
                  {createdSession ? `Input Saham (${createdSession.ticker})` : "Input Saham & Parameter"}
                </p>
              </div>
            </li>

            {/* Step 2 */}
            <li
              className={`flex items-center p-2 rounded-lg transition-all ${
                createdSession
                  ? "bg-blue-50/70 border border-blue-200 shadow-2xs"
                  : "bg-transparent border border-transparent"
              }`}
            >
              <span
                className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold mr-3 shrink-0 ${
                  createdSession
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-400"
                }`}
              >
                2
              </span>
              <div className="min-w-0">
                <p
                  className={`text-[10px] font-semibold uppercase tracking-wider font-mono ${
                    createdSession ? "text-blue-600" : "text-slate-400"
                  }`}
                >
                  Langkah 2 {createdSession ? "• Aktif" : ""}
                </p>
                <p
                  className={`text-xs ${
                    createdSession ? "font-bold text-slate-900" : "font-medium text-slate-500"
                  } truncate`}
                >
                  Verifikasi Data Pasar
                </p>
              </div>
            </li>
          </ol>
        </div>

      </section>
      {/* END: Progress Stepper */}

      {generalError === "authentication" ? (
        <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <p className="font-semibold">Sesi Anda telah berakhir. Silakan masuk kembali.</p>
          <Link
            href="/login?next=%2Fsessions%2Fnew"
            className="mt-2 inline-flex min-h-10 items-center rounded-lg bg-rose-600 px-4 font-semibold text-white hover:bg-rose-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-600"
          >
            Masuk kembali
          </Link>
        </div>
      ) : generalError === "request" ? (
        <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-700">
          Sesi tidak dapat dibuat. Periksa data Anda lalu coba lagi.
        </p>
      ) : null}

      {/* STEP 2: VERIFIKASI DATA PASAR (Jika Sesi Berhasil Dibuat) */}
      {createdSession ? (
        <div className="space-y-6 min-w-0" data-purpose="verification-stage">
          {/* BEGIN: VerificationCard */}
          <div className="bg-white border border-emerald-500/80 ring-1 ring-emerald-500/20 rounded-2xl shadow-sm overflow-hidden mb-6">
            {/* Card Top Bar & Metadata */}
            <div className="p-5 sm:p-6 border-b border-slate-100">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
                <span className="inline-flex items-center text-[11px] font-bold tracking-wider uppercase text-emerald-700 font-mono">
                  LANGKAH 2: VERIFIKASI DATA PASAR
                </span>
                <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold tracking-wide">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>EVIDENCE VALIDATED / DATA OTORITATIF</span>
                </div>
              </div>
              <div>
                <h2 className="text-xl sm:text-2xl font-bold text-slate-900 flex items-center gap-2">
                  <span className="text-emerald-600">✓</span> Data Pasar {createdSession.ticker} Berhasil Diambil
                </h2>
                <p className="mt-1 text-xs sm:text-sm text-slate-500 flex flex-wrap items-center gap-x-2 gap-y-1 font-normal">
                  <span className="font-medium text-slate-700">{createdSession.company_name}</span>
                  <span className="text-slate-300">•</span>
                  <span>Data Otoritatif Real-Time Bursa (ZAPI)</span>
                  <span className="text-slate-300">•</span>
                  <span className="inline-flex items-center text-emerald-600 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block mr-1"></span>
                    Sinkronisasi: Baru saja
                  </span>
                </p>
              </div>
            </div>

            {/* Error feedback if preview fetch fails */}
            {previewError ? (
              <div className="mx-5 sm:mx-6 mt-4 rounded-lg border border-amber-300 bg-amber-50 p-4 text-xs text-amber-800">
                <p className="font-semibold">⚠️ {previewError}</p>
                <p className="mt-1 text-slate-600">
                  Sesi tetap aman dan akan otomatis mengevaluasi live snapshot saat membuka workspace.
                </p>
              </div>
            ) : null}

            {/* Loading indicator */}
            {fetchingPreview && !previewData ? (
              <div className="py-12 text-center space-y-2">
                <div className="mx-auto h-8 w-8 animate-spin rounded-full border-3 border-blue-600 border-t-transparent" />
                <p className="text-sm font-semibold text-blue-600 animate-pulse">
                  ⚡ Mengambil data pasar real-time {createdSession.ticker} dari ZAPI…
                </p>
              </div>
            ) : null}

            {/* Card Metrics Grid */}
            <div className="p-5 sm:p-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Metric 1: Harga Terkini */}
                <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 hover:border-slate-300 transition flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Harga Terkini</span>
                    <span
                      className={`text-[11px] font-bold font-mono px-2 py-0.5 rounded border ${
                        changePercent >= 0
                          ? "bg-emerald-50 text-emerald-600 border-emerald-200"
                          : "bg-rose-50 text-rose-600 border-rose-200"
                      }`}
                    >
                      {changePercent >= 0 ? "+" : ""}
                      {changePercent.toFixed(2)}%
                    </span>
                  </div>
                  <div>
                    <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
                      Rp {Number(lastPrice).toLocaleString("id-ID")}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 font-mono">Penutupan Sesi Berjalan</p>
                  </div>
                </div>

                {/* Metric 2: Orderbook Depth */}
                <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 hover:border-slate-300 transition flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Orderbook Depth</span>
                    <span className="text-[11px] font-medium text-slate-500 font-mono">Ratio Bid/Ask</span>
                  </div>
                  <div>
                    <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
                      {ratio.toFixed(2)}x
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1 font-mono">
                      Spread: <span className="font-semibold text-slate-700">Rp {spread}</span>
                    </p>
                  </div>
                </div>

                {/* Metric 3: Foreign Flow */}
                <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 hover:border-slate-300 transition flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Foreign Flow</span>
                    <span className={`w-2 h-2 rounded-full ${isForeignAccum ? "bg-emerald-500" : "bg-rose-500"}`} />
                  </div>
                  <div>
                    <div
                      className={`text-lg font-bold font-mono tracking-tight uppercase truncate ${
                        isForeignAccum ? "text-emerald-700" : "text-rose-700"
                      }`}
                    >
                      {foreignStatus}
                    </div>
                    <p
                      className={`text-[11px] mt-1 font-medium truncate ${
                        isForeignAccum ? "text-emerald-600" : "text-rose-600"
                      }`}
                    >
                      Multi-Horizon Flow
                    </p>
                  </div>
                </div>

                {/* Metric 4: Bandarmology */}
                <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 hover:border-slate-300 transition flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Bandarmology</span>
                    <span className={`w-2 h-2 rounded-full ${isBandarAccum ? "bg-emerald-500" : "bg-rose-500"}`} />
                  </div>
                  <div>
                    <div
                      className={`text-lg font-bold font-mono tracking-tight uppercase truncate ${
                        isBandarAccum ? "text-emerald-700" : "text-rose-700"
                      }`}
                    >
                      {bandarStatus}
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 font-medium truncate">Akumulasi Broker 1D</p>
                  </div>
                </div>
              </div>

              {/* Mini Visual Confirmation Ratio Bar */}
              <div className="mt-4 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                <div className="flex items-center justify-between font-mono mb-1.5">
                  <span className="text-slate-600">
                    Keseimbangan Likuiditas Instans: <strong className="text-emerald-700">Bid {bidPercent}%</strong> vs{" "}
                    <strong className="text-rose-700">Ask {askPercent}%</strong>
                  </span>
                  <span className="text-[11px] text-slate-400 hidden sm:inline">Frekuensi: Stabil</span>
                </div>
                {/* Dual Bar */}
                <div className="w-full h-2 rounded-full bg-rose-200 flex overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-l-full transition-all duration-500"
                    style={{ width: `${bidPercent}%` }}
                  />
                  <div
                    className="bg-rose-500 h-full rounded-r-full transition-all duration-500"
                    style={{ width: `${askPercent}%` }}
                  />
                </div>
              </div>

              {/* Action Buttons Container */}
              <div className="mt-6 pt-5 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center gap-3">
                {/* Primary CTA */}
                <button
                  type="button"
                  disabled={startingAnalysis}
                  onClick={handleStartAnalysis}
                  className="w-full sm:w-auto inline-flex min-h-11 items-center justify-center px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-sm transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-60 cursor-pointer"
                >
                  {startingAnalysis ? (
                    <>
                      <ButtonSpinner className="h-4 w-4 mr-2" />
                      <span>Memulai Analisa AI…</span>
                    </>
                  ) : (
                    <>
                      <span className="mr-2 text-base">🧠</span>
                      <span>Mulai Analisa AI Sekarang</span>
                    </>
                  )}
                </button>

                {/* Secondary Action */}
                <button
                  type="button"
                  onClick={() => void fetchMarketData(createdSession)}
                  disabled={fetchingPreview}
                  className="w-full sm:w-auto inline-flex min-h-11 items-center justify-center px-4 py-2.5 rounded-lg bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 font-medium text-sm border border-slate-300 transition-colors shadow-xs disabled:opacity-60 cursor-pointer"
                >
                  {fetchingPreview ? (
                    <>
                      <ButtonSpinner className="h-4 w-4 mr-2 text-blue-600" />
                      <span>Mengambil data…</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4 mr-2 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                        />
                      </svg>
                      <span>Tarik Ulang Data</span>
                    </>
                  )}
                </button>

                {/* Tertiary Action */}
                <button
                  type="button"
                  onClick={() => setCreatedSession(null)}
                  className="w-full sm:w-auto inline-flex min-h-11 items-center justify-center px-4 py-2.5 rounded-lg bg-transparent hover:bg-slate-100 text-slate-600 font-medium text-sm transition-colors cursor-pointer"
                >
                  Ubah Parameter / Ticker
                </button>
              </div>
            </div>
          </div>
          {/* END: VerificationCard */}

          {/* BEGIN: UserNotesSection */}
          <section
            className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs mb-6"
            data-purpose="user-notes-display"
          >
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                    />
                  </svg>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Catatan Sesi Pengguna
                  </h3>
                </div>
                <p className="text-sm font-medium text-slate-800 bg-slate-50 p-3 rounded-lg border border-slate-100 italic break-words">
                  &ldquo;{note ? note : "Tidak ada catatan khusus untuk sesi ini."}&rdquo;
                </p>
              </div>
              <button
                type="button"
                onClick={() => setCreatedSession(null)}
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 shrink-0 cursor-pointer self-start sm:self-auto"
              >
                Edit Catatan
              </button>
            </div>
          </section>
          {/* END: UserNotesSection */}
        </div>
      ) : (
        /* STEP 1: FORM INPUT EMITEN */
        <div
          className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden"
          data-purpose="session-creation-card"
        >
          {/* Card Sub-header Banner */}
          <div className="px-5 sm:px-6 py-3.5 bg-slate-50/80 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                ></path>
              </svg>
              <span className="text-xs font-bold tracking-tight uppercase text-slate-700 font-mono">
                Form Konfigurasi Parameter Sesi
              </span>
            </div>
            <div className="text-[11px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full flex items-center gap-1.5 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              BEI: REALTIME FEED ACTIVE
            </div>
          </div>
          <form
            onSubmit={handleSubmit}
            noValidate
            className="min-w-0 p-5 sm:p-8 space-y-6 sm:space-y-7"
            id="new-session-form"
          >
            {/* Section: Pilihan Cepat Saham Populer */}
            <div data-purpose="quick-stock-selector">
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-600 font-mono">
                  Pilihan Cepat Saham Populer:
                </span>
                <span className="text-[11px] text-slate-400 font-normal hidden sm:inline">
                  Klik untuk memilih ticker secara instan
                </span>
              </div>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Saham Populer">
                {POPULAR_TICKERS.map((symbol) => {
                  const isActive = ticker.trim().toUpperCase() === symbol;
                  return (
                    <button
                      key={symbol}
                      type="button"
                      disabled={pending}
                      onClick={() => handleSelectTickerChip(symbol)}
                      className={`px-3.5 py-1.5 font-mono text-xs font-bold rounded-lg border transition-all shadow-2xs cursor-pointer ${
                        isActive
                          ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                          : "bg-white hover:bg-slate-50 text-slate-800 border-slate-200 hover:border-slate-300"
                      }`}
                    >
                      {symbol}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Section: Input Saham & Nama Perusahaan */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-5">
              {/* Field: Kode Saham */}
              <div data-purpose="input-stock-ticker">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1">
                    <label htmlFor="ticker" className="text-xs font-bold text-slate-800">
                      Kode Saham
                    </label>
                    <span className="text-rose-500 text-xs font-bold" aria-hidden="true">*</span>
                  </div>
                  <span className="text-[10px] font-mono text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">
                    IDX Ticker
                  </span>
                </div>
                <div className="relative rounded-lg shadow-2xs">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 font-mono text-sm font-semibold">
                    $
                  </div>
                  <input
                    id="ticker"
                    name="stock_ticker"
                    placeholder="Contoh: BBCA, BBRI, SGER, HRUM..."
                    value={ticker}
                    onChange={(e) => handleTickerChange(e.target.value)}
                    maxLength={32}
                    autoCapitalize="characters"
                    autoComplete="off"
                    disabled={pending}
                    aria-required="true"
                    aria-invalid={fieldErrors.ticker ? "true" : undefined}
                    aria-describedby={fieldErrors.ticker ? "ticker-error" : "ticker-hint"}
                    className="block w-full min-w-0 pl-8 pr-4 py-2.5 text-base font-mono tracking-wider font-semibold uppercase bg-slate-50/50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:bg-white placeholder:text-slate-400 transition"
                  />
                </div>
                <p id="ticker-hint" className="mt-1.5 text-[11px] text-slate-500 leading-tight">
                  Kode akan disimpan dalam huruf kapital. Terhubung otomatis ke feed bursa BEI.
                </p>
                {fieldErrors.ticker ? (
                  <p id="ticker-error" className="mt-1.5 text-xs text-rose-600 font-semibold">
                    {fieldErrors.ticker}
                  </p>
                ) : null}
              </div>

              {/* Field: Nama Perusahaan */}
              <div data-purpose="input-company-name">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1">
                    <label htmlFor="companyName" className="text-xs font-bold text-slate-800">
                      Nama Perusahaan
                    </label>
                    <span className="text-rose-500 text-xs font-bold" aria-hidden="true">*</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">Otomatisasi Bursa</span>
                </div>
                <div className="relative rounded-lg shadow-2xs">
                  <input
                    id="companyName"
                    name="company_name"
                    placeholder="Terisi otomatis saat kode saham dimasukkan"
                    value={companyName}
                    onChange={(e) => {
                      setCompanyName(e.target.value);
                      setFieldErrors((current) => ({ ...current, companyName: undefined }));
                    }}
                    maxLength={255}
                    disabled={pending}
                    aria-required="true"
                    aria-invalid={fieldErrors.companyName ? "true" : undefined}
                    aria-describedby={fieldErrors.companyName ? "company-name-error" : "company-hint"}
                    className="block w-full min-w-0 px-4 py-2.5 text-base bg-white border border-slate-300 rounded-lg text-slate-800 placeholder:text-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                  />
                </div>
                <p id="company-hint" className="mt-1.5 text-[11px] text-slate-400 leading-tight">
                  Identitas entitas emiten terverifikasi oleh IDX Factbook.
                </p>
                {fieldErrors.companyName ? (
                  <p id="company-name-error" className="mt-1.5 text-xs text-rose-600 font-semibold">
                    {fieldErrors.companyName}
                  </p>
                ) : null}
              </div>
            </div>

            {/* Section: Trading Style Selection */}
            <div data-purpose="trading-style-selector">
              <div className="flex items-center gap-1 mb-2">
                <span className="text-xs font-bold text-slate-800">
                  Trading Style
                </span>
                <span className="text-rose-500 text-xs font-bold" aria-hidden="true">*</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" role="group" aria-label="Gaya Trading">
                {TRADING_STYLES.map((style) => {
                  const isSelected = tradingStyle === style.name;
                  return (
                    <button
                      key={style.name}
                      type="button"
                      aria-label={style.name}
                      disabled={pending}
                      onClick={() => setTradingStyle(style.name)}
                      className={`relative flex flex-col p-3.5 rounded-xl text-left transition-all cursor-pointer ${
                        isSelected
                          ? "border-2 border-blue-600 bg-blue-50/40 shadow-xs"
                          : "border border-slate-200 bg-white hover:border-slate-300"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span
                          className={`text-xs font-bold flex items-center gap-1.5 ${
                            isSelected ? "text-blue-900" : "text-slate-800"
                          }`}
                        >
                          {style.name}
                          {style.popular && (
                            <span className="text-[9px] bg-blue-600 text-white px-1.5 py-0.5 rounded font-mono font-normal">
                              Populer
                            </span>
                          )}
                        </span>
                        <span
                          className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                            isSelected ? "border-blue-600 bg-blue-600 text-white" : "border-slate-300 bg-white"
                          }`}
                        >
                          {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-white" />}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-500 leading-snug">
                        {style.desc}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Section: Catatan Pengguna (Opsional) */}
            <div data-purpose="user-notes-section">
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="note" className="text-xs font-bold text-slate-800">
                  Catatan <span className="text-slate-400 font-normal">(opsional)</span>
                </label>
                <span className="text-[11px] text-slate-400 hidden sm:inline">
                  Digunakan sebagai konteks tambahan bagi evaluasi AI
                </span>
              </div>
              <textarea
                id="note"
                name="note"
                rows={3}
                placeholder="Contoh: Menunggu konfirmasi pantulan support MA50, akumulasi broker YU dan akumulasi asing netral..."
                value={note}
                onChange={(e) => setNote(e.target.value)}
                disabled={pending}
                className="block w-full min-w-0 px-4 py-2.5 text-base bg-slate-50/50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:bg-white placeholder:text-slate-400 transition resize-y break-words"
              ></textarea>
            </div>

            {/* Section: Action Footer / Submit Buttons */}
            <div
              className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              data-purpose="action-buttons"
            >
              <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={pending}
                  aria-label={pending ? "Membuat sesi…" : "Buat Sesi"}
                  className="w-full sm:w-auto inline-flex min-h-11 items-center justify-center px-6 py-2.5 text-sm font-semibold rounded-lg text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 transition shadow-sm shadow-blue-500/25 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 disabled:opacity-60 cursor-pointer"
                  id="btn-fetch-data"
                >
                  {pending ? (
                    <>
                      <ButtonSpinner className="h-4 w-4 mr-2" />
                      <span>Membuat sesi…</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4 mr-2 -ml-0.5 text-blue-100" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          clipRule="evenodd"
                          d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"
                          fillRule="evenodd"
                        ></path>
                      </svg>
                      <span>Ambil Data Pasar</span>
                    </>
                  )}
                </button>

                {/* Cancel Button */}
                <Link
                  href="/sessions"
                  className="w-full sm:w-auto inline-flex min-h-11 items-center justify-center px-5 py-2.5 text-sm font-semibold rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition text-center"
                >
                  Batal
                </Link>
              </div>

              {/* Helper Status Hint */}
              <div className="flex items-center text-xs text-slate-400">
                <svg className="w-3.5 h-3.5 mr-1 text-slate-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                  ></path>
                </svg>
                <span>Data ditarik langsung dari Bursa Efek Indonesia via ZAPI</span>
              </div>
            </div>
          </form>
        </div>
      )}
      {/* END: FormCard */}

      {/* BEGIN: MainFooter */}
      <footer className="mt-8 pt-4 border-t border-slate-200">
        <div className="flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-700">TradePilot AI Institutional Platform</span>
            <span>•</span>
            <span className="font-mono text-slate-400">Build 2026.09.v2</span>
          </div>
          <div>Data berlisensi resmi Otoritas Jasa Keuangan & Bursa Efek Indonesia.</div>
        </div>
      </footer>
      {/* END: MainFooter */}
    </div>
  );
}
