"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { acquireMarketEvidence, createSession } from "@/features/trade-workspace/api";
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

const POPULAR_TICKERS = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII", "BREN", "AMMN", "GOTO"];
const TRADING_STYLES = ["Day Trade", "Swing Trade", "Scalping"] as const;
export type TradingStyle = (typeof TRADING_STYLES)[number];

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
    const normalizedCompanyName = (companyName || (normalizedTicker ? IDX_COMPANIES[normalizedTicker.toUpperCase()] || `${normalizedTicker.toUpperCase()} Tbk` : "")).trim();

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

  function handleStartAnalysis() {
    if (!createdSession) return;
    onCreated?.(createdSession);
  }

  const controlClass =
    "mt-1 min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-base text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:bg-[var(--color-surface-muted)]";

  return (
    <div className="mt-6 min-w-0 space-y-[var(--space-5)]">
      {generalError === "authentication" ? (
        <div role="alert" className="text-sm text-[var(--color-status-danger)]">
          <p>Sesi Anda telah berakhir. Silakan masuk kembali.</p>
          <Link
            href="/login?next=%2Fsessions%2Fnew"
            className="mt-2 inline-flex min-h-11 items-center font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            Masuk kembali
          </Link>
        </div>
      ) : generalError === "request" ? (
        <p role="alert" className="text-sm text-[var(--color-status-danger)]">
          Sesi tidak dapat dibuat. Periksa data Anda lalu coba lagi.
        </p>
      ) : null}

      {/* STEP 2: PRATINJAU DATA PASAR TERAKUISISI */}
      {createdSession ? (
        <div className="space-y-4 min-w-0">
          <div className="rounded-[var(--radius-large)] border border-[var(--color-status-success)] bg-[var(--color-surface-standard)] p-5 sm:p-6 shadow-sm space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border-subtle)] pb-4">
              <div>
                <span className="text-xs font-semibold text-[var(--color-status-success)]">
                  LANGKAH 2: VERIFIKASI DATA PASAR
                </span>
                <h2 className="text-xl font-bold text-[var(--color-text-strong)]">
                  ✓ Data Pasar {createdSession.ticker} Berhasil Diambil
                </h2>
                <p className="text-xs text-[var(--color-text-muted)]">
                  {createdSession.company_name} • Data Otoritatif Real-Time Bursa (ZAPI)
                </p>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--color-status-success-subtle)] px-3 py-1 text-xs font-bold text-[var(--color-status-success)]">
                <span className="h-2 w-2 rounded-full bg-[var(--color-status-success)] animate-pulse" />
                EVIDENCE VALIDATED
              </span>
            </div>

            {/* Error state if fetching fails */}
            {previewError ? (
              <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-600 dark:text-rose-400">
                <p className="font-semibold">⚠️ {previewError}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Pastikan ZAPI_API_KEY aktif dan server backend dapat menjangkau api.zpi.web.id.
                </p>
              </div>
            ) : null}

            {/* Loading state */}
            {fetchingPreview && !previewData ? (
              <div className="p-8 text-center">
                <p className="text-sm font-semibold text-[var(--color-action-primary)] animate-pulse">
                  ⚡ Mengambil data pasar real-time {createdSession.ticker} dari ZAPI…
                </p>
              </div>
            ) : null}

            {/* 4 Metric Badges with REAL DATA */}
            {previewData ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-muted)] p-3">
                  <span className="text-xs text-[var(--color-text-muted)]">Harga Terkini</span>
                  <p className="text-lg font-bold text-[var(--color-text-strong)]">
                    Rp {previewData.quote?.last_price?.toLocaleString("id-ID") ?? "-"}
                  </p>
                  <span
                    className={`text-xs font-semibold ${
                      (previewData.quote?.change_percent ?? 0) >= 0
                        ? "text-[var(--color-status-success)]"
                        : "text-[var(--color-status-danger)]"
                    }`}
                  >
                    {(previewData.quote?.change_percent ?? 0) >= 0 ? "+" : ""}
                    {(previewData.quote?.change_percent ?? 0).toFixed(2)}%
                  </span>
                </div>

                <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-muted)] p-3">
                  <span className="text-xs text-[var(--color-text-muted)]">Orderbook Depth</span>
                  <p className="text-lg font-bold text-[var(--color-text-strong)]">
                    {(previewData.orderbook?.bid_ask_ratio ?? 0).toFixed(2)}x
                  </p>
                  <span className="text-xs text-[var(--color-text-muted)]">
                    Spread: Rp {previewData.orderbook?.spread ?? 0}
                  </span>
                </div>

                <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-muted)] p-3">
                  <span className="text-xs text-[var(--color-text-muted)]">Foreign Flow</span>
                  <p className="text-lg font-bold text-[var(--color-text-strong)]">
                    {previewData.foreign_flow?.foreign_status ?? "NEUTRAL"}
                  </p>
                  <span className="text-xs text-[var(--color-status-success)] font-semibold">
                    Multi-Horizon Flow
                  </span>
                </div>

                <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-muted)] p-3">
                  <span className="text-xs text-[var(--color-text-muted)]">Bandarmology</span>
                  <p className="text-lg font-bold text-[var(--color-text-strong)]">
                    {previewData.broker_flow?.bandar_status ?? "NEUTRAL"}
                  </p>
                  <span className="text-xs text-[var(--color-status-success)] font-semibold">
                    Akumulasi Broker 1D
                  </span>
                </div>
              </div>
            ) : null}

            {/* Action Trigger Buttons */}
            <div className="pt-2 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={handleStartAnalysis}
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-8 text-base font-bold text-[var(--color-text-inverse)] shadow-md hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                <span>🧠 Mulai Analisa AI Sekarang</span>
              </button>
              <button
                type="button"
                onClick={() => void fetchMarketData(createdSession)}
                disabled={fetchingPreview}
                className="inline-flex min-h-12 items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                {fetchingPreview ? "Mengambil data…" : "🔄 Tarik Ulang Data"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* STEP 1: FORM INPUT EMITEN & AMBIL DATA */
        <form onSubmit={handleSubmit} noValidate className="min-w-0 space-y-[var(--space-5)]">
          {/* 1. Quick Popular Tickers */}
          <div className="min-w-0">
            <span className="block text-xs font-semibold text-[var(--color-text-muted)]">
              Pilihan Cepat Saham Populer:
            </span>
            <div className="mt-2 flex flex-wrap gap-1.5" role="group" aria-label="Saham Populer">
              {POPULAR_TICKERS.map((symbol) => (
                <button
                  key={symbol}
                  type="button"
                  disabled={pending}
                  onClick={() => handleSelectTickerChip(symbol)}
                  className={`rounded-md border px-2.5 py-1 text-xs font-mono font-bold transition-colors ${
                    ticker.trim().toUpperCase() === symbol
                      ? "border-[var(--color-action-primary)] bg-[var(--color-action-primary)] text-white shadow-xs"
                      : "border-[var(--color-border-default)] bg-[var(--color-surface-standard)] text-[var(--color-text-strong)] hover:border-[var(--color-border-strong)]"
                  }`}
                >
                  {symbol}
                </button>
              ))}
            </div>
          </div>

          {/* 2. Ticker Input */}
          <div className="min-w-0">
            <label htmlFor="ticker" className="block text-sm font-semibold text-[var(--color-text-strong)]">
              Kode Saham
            </label>
            <input
              id="ticker"
              name="ticker"
              placeholder="Contoh: BBCA, BBRI, SGER, HRUM..."
              value={ticker}
              onChange={(event) => handleTickerChange(event.target.value)}
              maxLength={32}
              autoCapitalize="characters"
              autoComplete="off"
              disabled={pending}
              aria-required="true"
              aria-invalid={fieldErrors.ticker ? "true" : undefined}
              aria-describedby={fieldErrors.ticker ? "ticker-error" : "ticker-hint"}
              className={controlClass}
            />
            <p id="ticker-hint" className="mt-1 text-xs text-[var(--color-text-muted)]">
              Kode akan disimpan dalam huruf kapital.
            </p>
            {fieldErrors.ticker ? (
              <p id="ticker-error" className="mt-1 text-sm text-[var(--color-status-danger)]">
                {fieldErrors.ticker}
              </p>
            ) : null}
          </div>

          {/* 3. Company Name */}
          <div className="min-w-0">
            <label htmlFor="companyName" className="block text-sm font-semibold text-[var(--color-text-strong)]">
              Nama Perusahaan
            </label>
            <input
              id="companyName"
              name="company_name"
              placeholder="Terisi otomatis saat kode saham dimasukkan"
              value={companyName}
              onChange={(event) => {
                setCompanyName(event.target.value);
                setFieldErrors((current) => ({ ...current, companyName: undefined }));
              }}
              maxLength={255}
              disabled={pending}
              aria-required="true"
              aria-invalid={fieldErrors.companyName ? "true" : undefined}
              aria-describedby={fieldErrors.companyName ? "company-name-error" : undefined}
              className={controlClass}
            />
            {fieldErrors.companyName ? (
              <p id="company-name-error" className="mt-1 text-sm text-[var(--color-status-danger)]">
                {fieldErrors.companyName}
              </p>
            ) : null}
          </div>

          {/* 4. Trading Style Selector */}
          <div className="min-w-0">
            <span className="block text-sm font-semibold text-[var(--color-text-strong)]">
              Trading Style
            </span>
            <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Gaya Trading">
              {TRADING_STYLES.map((style) => (
                <button
                  key={style}
                  type="button"
                  disabled={pending}
                  onClick={() => setTradingStyle(style)}
                  className={`rounded-lg border px-3.5 py-1.5 text-xs font-semibold transition-all ${
                    tradingStyle === style
                      ? "border-[var(--color-action-primary)] bg-[var(--color-action-primary)] text-white shadow-xs"
                      : "border-[var(--color-border-default)] bg-[var(--color-surface-standard)] text-[var(--color-text-default)] hover:bg-[var(--color-surface-muted)]"
                  }`}
                >
                  {style}
                </button>
              ))}
            </div>
          </div>

          {/* 5. Note Textarea */}
          <div className="min-w-0">
            <label htmlFor="note" className="block text-sm font-semibold text-[var(--color-text-strong)]">
              Catatan <span className="font-normal text-[var(--color-text-muted)]">(opsional)</span>
            </label>
            <textarea
              id="note"
              name="note"
              rows={3}
              placeholder="Contoh: Menunggu konfirmasi pantulan support MA50..."
              value={note}
              onChange={(event) => setNote(event.target.value)}
              disabled={pending}
              className={`${controlClass} resize-y break-words`}
            />
          </div>

          {/* 6. Action Buttons */}
          <div className="flex min-w-0 flex-col gap-[var(--space-3)] sm:flex-row sm:items-center">
            <button
              type="submit"
              disabled={pending}
              aria-label={pending ? "Membuat sesi…" : "Buat Sesi"}
              className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-6 text-sm font-bold text-[var(--color-text-inverse)] shadow-sm hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
            >
              {pending ? "⚡ Mengambil Data & Memproses…" : "⚡ Ambil Data Pasar"}
            </button>
            <Link
              href="/sessions"
              className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] px-4 text-sm font-semibold text-[var(--color-action-primary)] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
            >
              Batal
            </Link>
          </div>
        </form>
      )}
    </div>
  );
}
