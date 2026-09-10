"use client";

import { useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { Suspense } from "react";
import { ButtonSpinner } from "@/components/button-spinner";
import { InstitutionalBrand } from "@/components/ui";

const defaultDestination = "/sessions";
const protectedDestinationPatterns = [
  /^\/sessions$/,
  /^\/sessions\/(?:new|archived)$/,
  /^\/sessions\/[^/]+$/,
  /^\/sessions\/[^/]+\/(?:analysis|history)$/,
  /^\/trade-workspace$/,
];

function getSafeNext(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) {
    return defaultDestination;
  }

  try {
    const target = new URL(next, "http://tradepilot.local");
    const decodedPathname = decodeURIComponent(target.pathname);
    const isProtectedDestination = protectedDestinationPatterns.some((pattern) =>
      pattern.test(decodedPathname),
    );

    if (
      target.origin !== "http://tradepilot.local" ||
      target.hash ||
      decodedPathname.includes("\\") ||
      /[\u0000-\u001f\u007f]/.test(decodedPathname) ||
      !isProtectedDestination
    ) {
      return defaultDestination;
    }

    if (decodedPathname === "/trade-workspace") {
      return `${defaultDestination}${target.search}`;
    }

    return `${target.pathname}${target.search}`;
  } catch {
    return defaultDestination;
  }
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const next = searchParams.get("next");
  const safeNext = getSafeNext(next);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email || !password) {
      setError("Email dan password harus diisi");
      return;
    }
    setSubmitting(true);
    try {
      await login({ email, password });
      router.push(safeNext);
    } catch {
      setError("Email atau password salah");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-8 sm:py-14">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="flex justify-center mb-3">
            <InstitutionalBrand
              iconSizeClass="w-12 h-12"
              textSizeClass="text-2xl"
              showEngineTag={false}
            />
          </div>
          <p className="text-xs uppercase tracking-wider font-mono font-semibold text-slate-400">
            Institutional Trading Intelligence
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          {/* Card Sub-header Banner */}
          <div className="px-6 py-3.5 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 font-mono">
                Portal Autentikasi
              </span>
            </div>
            <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded font-semibold">
              SISTEM AKTIF
            </span>
          </div>

          <div className="p-6 sm:p-8">
            <h1 className="text-xl font-bold tracking-tight text-slate-900 mb-1">
              Masuk
            </h1>
            <p className="text-xs text-slate-500 mb-6">
              Masuk ke akun TradePilot AI Anda untuk mengelola sesi perdagangan.
            </p>

            {error && (
              <div
                role="alert"
                className="mb-5 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs font-semibold text-rose-700 flex items-start gap-2"
              >
                <svg
                  className="w-4 h-4 text-rose-500 shrink-0 mt-0.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                  />
                </svg>
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-xs font-bold text-slate-700 mb-1.5">
                  Email
                </label>
                <div className="relative rounded-lg shadow-2xs">
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={submitting}
                    className="block w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 transition"
                    placeholder="user@example.com"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label htmlFor="password" className="block text-xs font-bold text-slate-700">
                    Kata Sandi
                  </label>
                </div>
                <div className="relative rounded-lg shadow-2xs">
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={submitting}
                    className="block w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500 transition"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 active:scale-[0.98] transition-all shadow-sm shadow-blue-500/25 focus:outline-hidden focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:opacity-50 cursor-pointer"
                >
                  {submitting && <ButtonSpinner className="h-4 w-4" />}
                  <span>{submitting ? "Memproses..." : "Masuk"}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Card Footer */}
          <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-100 flex items-center justify-center text-[11px] text-slate-500">
            <span className="flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                />
              </svg>
              Koneksi Terenkripsi & Akses Otoritatif
            </span>
          </div>
        </div>

        {/* Back Link */}
        <p className="mt-6 text-center text-xs text-slate-400">
          <Link href="/" className="hover:text-slate-700 transition font-medium">
            Kembali ke Beranda
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
