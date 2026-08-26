"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { createSession } from "@/features/trade-workspace/api";
import type { TradeSession } from "@/features/trade-workspace/types";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

type FieldErrors = {
  ticker?: string;
  companyName?: string;
};

const POPULAR_STOCKS = [
  { code: "BBCA", name: "Bank Central Asia Tbk." },
  { code: "BBRI", name: "Bank Rakyat Indonesia Tbk." },
  { code: "BMRI", name: "Bank Mandiri (Persero) Tbk." },
  { code: "TLKM", name: "Telkom Indonesia Tbk." },
  { code: "ASII", name: "Astra International Tbk." },
  { code: "BREN", name: "Barito Renewables Energy Tbk." },
  { code: "AMMN", name: "Amman Mineral Internasional Tbk." },
];

const TRADING_STYLES = [
  { id: "SWING", label: "Swing Trade (Hari - Minggu)" },
  { id: "DAY_TRADE", label: "Day Trade (Intraday)" },
  { id: "SCALPING", label: "Scalping (Menit)" },
];

export function CreateSessionForm({
  onCreated,
  successMessage = "Sesi berhasil dibuat.",
}: {
  onCreated?: (session: TradeSession) => void;
  successMessage?: string;
}) {
  const [ticker, setTicker] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [note, setNote] = useState("");
  const [tradingStyle, setTradingStyle] = useState("SWING");
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

  function selectPopularStock(stock: { code: string; name: string }) {
    setTicker(stock.code);
    setCompanyName(stock.name);
    setFieldErrors({});
  }

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    const normalizedTicker = ticker.trim();
    const normalizedCompanyName = companyName.trim();

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

    pendingRef.current = true;
    setPending(true);
    const attempt = ++attemptRef.current;
    const controller = new AbortController();
    controllerRef.current = controller;

    const formattedNote = note.trim()
      ? `[Gaya: ${tradingStyle}] ${note.trim()}`
      : `[Gaya: ${tradingStyle}]`;

    try {
      const session = await createSession(
        {
          ticker: ticker.trim().toUpperCase(),
          company_name: companyName.trim(),
          note: formattedNote,
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
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4">
          <p role="status" className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
            ✓ {successMessage} Mengalihkan ke pengambilan bukti pasar otomatis...
          </p>
        </div>
      ) : null}

      {/* Quick Select Popular Stocks */}
      <div className="min-w-0">
        <span className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
          Pilihan Cepat Saham Populer
        </span>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {POPULAR_STOCKS.map((stock) => (
            <button
              key={stock.code}
              type="button"
              onClick={() => selectPopularStock(stock)}
              className={`rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors ${
                ticker.toUpperCase() === stock.code
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-background text-foreground hover:bg-accent"
              }`}
            >
              {stock.code}
            </button>
          ))}
        </div>
      </div>

      {/* Ticker & Company Input */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="min-w-0">
          <label htmlFor="ticker" className="block text-sm font-semibold text-[var(--color-text-strong)]">
            Kode Saham <span className="text-rose-500">*</span>
          </label>
          <input
            id="ticker"
            name="ticker"
            value={ticker}
            placeholder="e.g. BBCA"
            onChange={(event) => {
              setTicker(event.target.value);
              setFieldErrors((current) => ({ ...current, ticker: undefined }));
            }}
            maxLength={32}
            autoCapitalize="characters"
            autoComplete="off"
            disabled={pending || createdSession !== null}
            aria-required="true"
            aria-invalid={fieldErrors.ticker ? "true" : undefined}
            className={controlClass}
          />
          {fieldErrors.ticker ? (
            <p id="ticker-error" className="mt-1 text-sm text-[var(--color-status-danger)]">
              {fieldErrors.ticker}
            </p>
          ) : null}
        </div>

        <div className="min-w-0">
          <label htmlFor="companyName" className="block text-sm font-semibold text-[var(--color-text-strong)]">
            Nama Perusahaan <span className="text-rose-500">*</span>
          </label>
          <input
            id="companyName"
            name="company_name"
            value={companyName}
            placeholder="e.g. Bank Central Asia Tbk."
            onChange={(event) => {
              setCompanyName(event.target.value);
              setFieldErrors((current) => ({ ...current, companyName: undefined }));
            }}
            maxLength={255}
            disabled={pending || createdSession !== null}
            aria-required="true"
            aria-invalid={fieldErrors.companyName ? "true" : undefined}
            className={controlClass}
          />
          {fieldErrors.companyName ? (
            <p id="company-name-error" className="mt-1 text-sm text-[var(--color-status-danger)]">
              {fieldErrors.companyName}
            </p>
          ) : null}
        </div>
      </div>

      {/* Trading Style Chips */}
      <div className="min-w-0">
        <label className="block text-sm font-semibold text-[var(--color-text-strong)]">
          Gaya Trading (Horizon)
        </label>
        <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {TRADING_STYLES.map((style) => (
            <button
              key={style.id}
              type="button"
              onClick={() => setTradingStyle(style.id)}
              className={`flex items-center justify-center rounded-lg border p-3 text-xs font-semibold transition-colors ${
                tradingStyle === style.id
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-card text-muted-foreground hover:bg-accent"
              }`}
            >
              {style.label}
            </button>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div className="min-w-0">
        <label htmlFor="note" className="block text-sm font-semibold text-[var(--color-text-strong)]">
          Rencana / Catatan Setup <span className="font-normal text-[var(--color-text-muted)]">(opsional)</span>
        </label>
        <textarea
          id="note"
          name="note"
          rows={3}
          placeholder="e.g. Menunggu konfirmasi breakout di level 6.300 dengan volume asing."
          value={note}
          onChange={(event) => setNote(event.target.value)}
          disabled={pending || createdSession !== null}
          className={`${controlClass} resize-y break-words`}
        />
      </div>

      {/* Action Buttons */}
      <div className="flex min-w-0 flex-col gap-[var(--space-3)] sm:flex-row sm:items-center">
        <button
          type="submit"
          disabled={pending || createdSession !== null}
          className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-6 text-sm font-semibold text-white shadow-sm hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
        >
          {pending ? "Menghubungkan ke ZAPI…" : "⚡ Buat Sesi & Ambil Data Pasar"}
        </button>
        {!createdSession ? (
          <Link
            href="/sessions"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] px-4 text-sm font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
          >
            Batal
          </Link>
        ) : null}
      </div>
    </form>
  );
}
