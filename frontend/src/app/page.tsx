"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/sessions");
    }
  }, [user, loading, router]);

  if (loading || user) {
    return null;
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-1 flex-col justify-between">
      {/* Hero Section */}
      <section className="relative overflow-hidden px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3.5 py-1 text-xs font-semibold text-blue-700 shadow-xs">
            <span className="h-2 w-2 rounded-full bg-blue-600 animate-pulse" />
            AI-Assisted Stock Analysis Workspace
          </div>

          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-[var(--color-text-strong)] sm:text-6xl sm:leading-tight">
            TradePilot AI
          </h1>
          <p className="mt-4 text-xl font-medium text-[var(--color-text-muted)] sm:text-2xl">
            One Trade, One Story.
          </p>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-[var(--color-text-default)] sm:text-lg">
            Platform komprehensif untuk memantau siklus satu keputusan perdagangan saham dari analisis awal, manajemen posisi real-time, hingga evaluasi jurnal akhir dengan bantuan multi-modal AI.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/login"
              className="inline-flex min-h-12 w-full items-center justify-center rounded-[var(--radius-standard)] bg-[var(--color-action-primary)] px-8 text-base font-semibold text-[var(--color-text-inverse)] shadow-md transition-all hover:bg-[var(--color-action-primary-hover)] hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
            >
              Masuk ke TradePilot
            </Link>
            <Link
              href="/sessions"
              className="inline-flex min-h-12 w-full items-center justify-center rounded-[var(--radius-standard)] border border-[var(--color-border-strong)] bg-[var(--color-surface-standard)] px-8 text-base font-semibold text-[var(--color-text-strong)] transition-all hover:bg-[var(--color-surface-muted)] sm:w-auto"
            >
              Lihat Workspace
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section className="border-t border-[var(--color-border-default)] bg-[var(--color-surface-factual)] px-4 py-12 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            <div className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-6 shadow-xs">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700 font-bold">
                1
              </div>
              <h3 className="mt-4 text-base font-bold text-[var(--color-text-strong)]">
                Initial Analysis
              </h3>
              <p className="mt-2 text-sm text-[var(--color-text-muted)] leading-relaxed">
                Unggah 4 bukti grafik & orderbook untuk mendapatkan kalkulasi level support, resistance, dan foreign flow secara objektif.
              </p>
            </div>

            <div className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-6 shadow-xs">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100 text-indigo-700 font-bold">
                2
              </div>
              <h3 className="mt-4 text-base font-bold text-[var(--color-text-strong)]">
                Keputusan BUY / WAIT / SKIP
              </h3>
              <p className="mt-2 text-sm text-[var(--color-text-muted)] leading-relaxed">
                Ambil keputusan terarah dengan catatan trading plan dan pembaruan observasi pasar yang terstruktur.
              </p>
            </div>

            <div className="rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-6 shadow-xs">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700 font-bold">
                3
              </div>
              <h3 className="mt-4 text-base font-bold text-[var(--color-text-strong)]">
                Jurnal & Riwayat Lengkap
              </h3>
              <p className="mt-2 text-sm text-[var(--color-text-muted)] leading-relaxed">
                Setiap sesi perdagangan tercatat abadi dalam linimasa dan riwayat evaluasi untuk terus mengasah disiplin eksekusi trading.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
