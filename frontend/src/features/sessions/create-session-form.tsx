"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { createSession } from "@/features/trade-workspace/api";
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

  const pendingRef = useRef(false);
  const attemptRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => () => {
    mountedRef.current = false;
    controllerRef.current?.abort();
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
      onCreated?.(session);
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

  const controlClass =
    "mt-1 min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-base text-[var(--color-text-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:bg-[var(--color-surface-muted)]";

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-6 min-w-0 space-y-[var(--space-5)]">
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

      {createdSession ? (
        <p role="status" className="text-sm font-semibold text-[var(--color-status-success)]">
          {successMessage}
        </p>
      ) : null}

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
              disabled={pending || createdSession !== null}
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
          placeholder="Contoh: BBCA, BBRI, TLKM..."
          value={ticker}
          onChange={(event) => handleTickerChange(event.target.value)}
          maxLength={32}
          autoCapitalize="characters"
          autoComplete="off"
          disabled={pending || createdSession !== null}
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
          disabled={pending || createdSession !== null}
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
              disabled={pending || createdSession !== null}
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
          disabled={pending || createdSession !== null}
          className={`${controlClass} resize-y break-words`}
        />
      </div>

      {/* 6. Action Buttons */}
      <div className="flex min-w-0 flex-col gap-[var(--space-3)] sm:flex-row sm:items-center">
        <button
          type="submit"
          disabled={pending || createdSession !== null}
          aria-label={pending ? "Membuat sesi…" : createdSession ? "Sesi dibuat" : "Buat Sesi"}
          className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-6 text-sm font-bold text-[var(--color-text-inverse)] shadow-sm hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
        >
          {pending ? (
            "⚡ Mengambil Data & Memproses…"
          ) : createdSession ? (
            "Sesi dibuat"
          ) : (
            <>
              <span>⚡ Ambil Data & Mulai Analisa</span>
            </>
          )}
        </button>
        {!createdSession ? (
          <Link
            href="/sessions"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] px-4 text-sm font-semibold text-[var(--color-action-primary)] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
          >
            Batal
          </Link>
        ) : null}
      </div>
    </form>
  );
}
