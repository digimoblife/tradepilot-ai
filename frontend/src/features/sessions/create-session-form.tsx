"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createSession } from "@/lib/api/trade-sessions";
import { ApiError, AuthenticationError } from "@/lib/api/errors";

interface FormErrors {
  ticker?: string;
  general?: string;
}

export function CreateSessionForm() {
  const router = useRouter();
  const [ticker, setTicker] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [exchange, setExchange] = useState("");
  const [currency, setCurrency] = useState("IDR");
  const [errors, setErrors] = useState<FormErrors>({});
  const [pending, setPending] = useState(false);

  function validate(): boolean {
    const e: FormErrors = {};
    if (!ticker.trim()) {
      e.ticker = "Kode saham wajib diisi.";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setPending(true);
    try {
      const session = await createSession({
        ticker: ticker.trim(),
        company_name: companyName.trim() || undefined,
        exchange: exchange.trim() || undefined,
        currency,
      });
      router.push(`/sessions/${session.id}`);
    } catch (err: unknown) {
      if (err instanceof AuthenticationError) {
        setErrors({
          general: "Silakan masuk terlebih dahulu untuk membuat sesi trading.",
        });
      } else if (err instanceof ApiError) {
        setErrors({ general: err.message });
      } else {
        setErrors({
          general: "Terjadi kesalahan. Silakan coba lagi.",
        });
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {errors.general && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {errors.general}
        </div>
      )}

      <div>
        <label htmlFor="ticker" className="mb-1 block text-sm font-medium text-zinc-700">
          Kode Saham <span className="text-red-500">*</span>
        </label>
        <input
          id="ticker"
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          placeholder="BBRI"
          disabled={pending}
          aria-required="true"
          aria-invalid={!!errors.ticker}
          aria-describedby={errors.ticker ? "ticker-error" : undefined}
        />
        {errors.ticker && (
          <p id="ticker-error" className="mt-1 text-sm text-red-600" role="alert">
            {errors.ticker}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="companyName" className="mb-1 block text-sm font-medium text-zinc-700">
          Nama Perusahaan
        </label>
        <input
          id="companyName"
          type="text"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          placeholder="PT Bank Rakyat Indonesia Tbk"
          disabled={pending}
        />
      </div>

      <div>
        <label htmlFor="exchange" className="mb-1 block text-sm font-medium text-zinc-700">
          Bursa
        </label>
        <input
          id="exchange"
          type="text"
          value={exchange}
          onChange={(e) => setExchange(e.target.value)}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          placeholder="IDX"
          disabled={pending}
        />
      </div>

      <div>
        <label htmlFor="currency" className="mb-1 block text-sm font-medium text-zinc-700">
          Mata Uang <span className="text-red-500">*</span>
        </label>
        <select
          id="currency"
          value={currency}
          onChange={(e) => setCurrency(e.target.value)}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          disabled={pending}
        >
          <option value="IDR">IDR — Rupiah</option>
          <option value="USD">USD — Dolar AS</option>
        </select>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {pending ? "Membuat sesi…" : "Buat Sesi"}
        </button>
        <Link
          href="/sessions"
          className="text-sm text-zinc-500 underline hover:text-zinc-700"
        >
          Kembali ke Daftar Sesi
        </Link>
      </div>
    </form>
  );
}
