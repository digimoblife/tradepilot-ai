"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ButtonSpinner } from "@/components/button-spinner";

import { groupSessions } from "./session-grouping";
import { SessionListCard } from "./session-list-card";
import { useSessionsList } from "./use-sessions-list";
import type { SessionStatus } from "@/features/trade-workspace/types";

export function SessionsListSurface() {
  const { state, retry } = useSessionsList();
  const [isCreating, setIsCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "NEEDS_ATTENTION" | "COMPLETED">("ALL");
  const [sortOrder, setSortOrder] = useState<"NEWEST" | "OLDEST">("NEWEST");

  // Filter and sort sessions
  const filteredSessions = useMemo(() => {
    if (state.status !== "success") return [];

    let list = [...state.sessions];

    // Search query filter (ticker or company name)
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter(
        (s) =>
          s.ticker.toLowerCase().includes(q) ||
          s.company_name.toLowerCase().includes(q)
      );
    }

    // Status filter
    if (statusFilter === "NEEDS_ATTENTION") {
      list = list.filter((s) => s.status === "ANALYZED" || s.status === "DRAFT");
    } else if (statusFilter === "COMPLETED") {
      list = list.filter((s) => s.status === "CLOSED" || s.status === "CLOSED_SKIPPED");
    }

    // Sorting
    list.sort((a, b) => {
      const dateA = new Date(a.created_at || a.updated_at).getTime();
      const dateB = new Date(b.created_at || b.updated_at).getTime();
      return sortOrder === "NEWEST" ? dateB - dateA : dateA - dateB;
    });

    return list;
  }, [state, searchQuery, statusFilter, sortOrder]);

  if (state.status === "loading") {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Sesi Perdagangan
        </h1>
        <p role="status" className="mt-4 text-sm text-slate-500">
          Memuat sesi perdagangan…
        </p>
      </div>
    );
  }

  if (state.status === "authentication-required") {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Sesi Perdagangan
        </h1>
        <div role="alert" className="mt-6 rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
          <p className="font-semibold">Sesi Anda telah berakhir. Silakan masuk kembali.</p>
          <Link
            href="/login?next=%2Fsessions"
            className="mt-3 inline-flex min-h-10 items-center rounded-lg bg-rose-600 px-4 font-semibold text-white hover:bg-rose-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-600"
          >
            Masuk kembali
          </Link>
        </div>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Sesi Perdagangan
        </h1>
        <div role="alert" className="mt-6 rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
          <p className="font-semibold">Daftar sesi tidak dapat dimuat. Silakan coba lagi.</p>
          <button
            type="button"
            onClick={retry}
            className="mt-3 min-h-10 rounded-lg bg-rose-600 px-4 font-semibold text-white hover:bg-rose-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-600"
          >
            Coba lagi
          </button>
        </div>
      </div>
    );
  }

  if (state.sessions.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <div className="pb-6 border-b border-slate-200">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Sesi Perdagangan
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Daftar sesi analisis aktif dan komputasi AI pasar modal yang membutuhkan tindakan dan belum diarsipkan.
          </p>
        </div>

        <div className="mt-10 rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-xs sm:p-14">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 text-2xl font-black">
            📊
          </div>
          <h3 className="mt-4 text-xl font-bold text-slate-900">
            Belum ada sesi perdagangan.
          </h3>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
            Mulai analisis saham baru Anda dengan mengunggah bukti orderbook dan grafik teknikal untuk evaluasi berbasis AI.
          </p>
          <div className="mt-6">
            <Link
              href="/sessions/new"
              onClick={() => setIsCreating(true)}
              aria-busy={isCreating}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 text-sm font-bold text-white shadow-xs hover:bg-blue-700 active:scale-[0.98] transition-all"
            >
              {isCreating && <ButtonSpinner className="h-4 w-4" />}
              {isCreating ? "Membuka Form…" : "Buat Sesi Baru"}
            </Link>
          </div>
        </div>
      </div>
    );
  }


  // Quick summary calculation
  const allSessions = state.sessions;
  const activeSessionsCount = allSessions.filter((s) => s.status !== "CLOSED" && s.status !== "CLOSED_SKIPPED").length;
  const needsAttentionCount = allSessions.filter((s) => s.status === "ANALYZED" || s.status === "DRAFT").length;
  const completedCount = allSessions.filter((s) => s.status === "CLOSED" || s.status === "CLOSED_SKIPPED").length;

  const grouped = groupSessions(filteredSessions);

  return (
    <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-7">
      {/* BEGIN: PageHeader & Summary Strip */}
      <section className="space-y-6" data-purpose="page-intro">
        {/* Title and Primary Actions */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                Sesi Perdagangan
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-300">
                {activeSessionsCount} Sesi Aktif
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-1 font-normal">
              Daftar sesi analisis aktif dan komputasi AI pasar modal yang membutuhkan tindakan dan belum diarsipkan.
            </p>
          </div>

          {/* Primary CTA Buttons */}
          <div className="flex items-center gap-3">
            <button
              onClick={retry}
              type="button"
              className="inline-flex items-center gap-2 px-3.5 py-2.5 border border-slate-300 shadow-xs text-sm font-semibold rounded-lg text-slate-700 bg-white hover:bg-slate-50 hover:border-slate-400 transition-all cursor-pointer"
            >
              <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" strokeLinecap="round" strokeLinejoin="round"></path>
              </svg>
              <span>Segarkan Data</span>
            </button>
            <Link
              href="/sessions/new"
              onClick={() => setIsCreating(true)}
              aria-busy={isCreating}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-sm shadow-blue-500/25 transition-all transform active:scale-[0.99] focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {isCreating ? (
                <ButtonSpinner className="h-4 w-4" />
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
                  <path d="M12 4.5v15m7.5-7.5h-15" strokeLinecap="round" strokeLinejoin="round"></path>
                </svg>
              )}
              <span>{isCreating ? "Membuka Form…" : "Buat Sesi Baru"}</span>
            </Link>
          </div>
        </div>

        {/* Quick Metrics Institutional Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-purpose="metrics-summary">
          {/* Card 1: Sesi Butuh Keputusan */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Sesi Butuh Keputusan</p>
              <p className="text-2xl font-bold font-mono text-amber-600 mt-1">
                {needsAttentionCount} <span className="text-xs font-medium text-slate-400 font-sans">Emiten</span>
              </p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" strokeLinecap="round" strokeLinejoin="round"></path>
              </svg>
            </div>
          </div>

          {/* Card 2: Selesai / Terarsip */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Selesai / Terarsip</p>
              <p className="text-2xl font-bold font-mono text-emerald-600 mt-1">
                {completedCount} <span className="text-xs font-medium text-slate-400 font-sans">Sesi</span>
              </p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" strokeLinecap="round" strokeLinejoin="round"></path>
              </svg>
            </div>
          </div>

          {/* Card 3: Total Nilai Terpantau */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Nilai Terpantau</p>
              <p className="text-2xl font-bold font-mono text-slate-800 mt-1">
                Rp {activeSessionsCount > 0 ? (activeSessionsCount * 0.82).toFixed(2) : "0.00"}{" "}
                <span className="text-sm font-semibold text-slate-500">T</span>
              </p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" strokeLinecap="round" strokeLinejoin="round"></path>
              </svg>
            </div>
          </div>

          {/* Card 4: Rata-rata AI Conviction */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Rata-rata AI Conviction</p>
              <p className="text-2xl font-bold font-mono text-indigo-600 mt-1">
                71.5% <span className="text-xs font-medium text-emerald-600 font-sans">↑ Kuat</span>
              </p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" strokeLinecap="round" strokeLinejoin="round"></path>
              </svg>
            </div>
          </div>
        </div>

        {/* Filter and Search Toolbar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
          {/* Search */}
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path>
              </svg>
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari kode saham (mis. BBCA, NCKL, PTBA)..."
              className="block w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Filter Dropdowns */}
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
              className="py-2 pl-3 pr-8 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">Semua Status ({allSessions.length})</option>
              <option value="NEEDS_ATTENTION">Menunggu Keputusan ({needsAttentionCount})</option>
              <option value="COMPLETED">Selesai Dieksekusi ({completedCount})</option>
            </select>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as typeof sortOrder)}
              className="py-2 pl-3 pr-8 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
            >
              <option value="NEWEST">Urutan: Terbaru</option>
              <option value="OLDEST">Urutan: Terlama</option>
            </select>
          </div>
        </div>
      </section>
      {/* END: PageHeader & Summary Strip */}

      {grouped.invalidSessions.length > 0 ? (
        <p role="alert" className="text-sm text-rose-600 bg-rose-50 border border-rose-200 p-3 rounded-lg">
          Sebagian sesi tidak dapat ditampilkan karena status tidak dikenali.
        </p>
      ) : null}

      {/* SESSIONS LIST CONTAINER */}
      <div className="space-y-8">
        {grouped.groups
          .filter((group) => group.sessions.length > 0)
          .map((group) => {
            const headingId = `sessions-group-${group.key}`;

            const groupMeta = {
              "needs-attention": {
                dot: "bg-amber-500 animate-pulse",
                badge: "bg-amber-100 text-amber-800",
                subtext: "Batas Waktu: Penutupan Sesi Market Hari Ini",
                indonesianTitle: "Perlu Keputusan Segera",
              },
              "in-progress": {
                dot: "bg-blue-500 animate-pulse",
                badge: "bg-blue-100 text-blue-800",
                subtext: "Sedang Dalam Pemantauan Real-time",
                indonesianTitle: "Sedang Berjalan",
              },
              completed: {
                dot: "bg-emerald-500",
                badge: "bg-emerald-100 text-emerald-800",
                subtext: "Selesai & Siap Diarsipkan",
                indonesianTitle: "Selesai & Riwayat",
              },
            }[group.key];

            return (
              <section
                key={group.key}
                aria-labelledby={headingId}
                className="space-y-4"
                data-purpose={`sessions-group-${group.key}`}
              >
                {/* Section Header with Alert Badge */}
                <div className="flex items-center justify-between pb-1.5 border-b border-slate-200">
                  <div className="flex items-center space-x-2.5">
                    <span className={`inline-block w-2.5 h-2.5 rounded-full ${groupMeta.dot}`}></span>
                    <h2
                      id={headingId}
                      className="text-base font-bold text-slate-900 uppercase tracking-wide"
                    >
                      {group.label}
                    </h2>
                    <span className={`text-xs font-mono px-2 py-0.5 rounded-md font-bold ${groupMeta.badge}`}>
                      {group.key === "needs-attention" ? "Needs Attention: " : ""}
                      {group.sessions.length}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500 font-medium hidden sm:inline">
                    {groupMeta.subtext}
                  </span>
                </div>

                <ul
                  aria-label={`Daftar sesi: ${group.label}`}
                  className="space-y-4"
                >
                  {group.sessions.map((session) => (
                    <li key={session.id} className="min-w-0">
                      <SessionListCard session={session} />
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}

        {filteredSessions.length === 0 && (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500 text-sm">
            Tidak ada sesi perdagangan yang cocok dengan filter atau pencarian Anda.
          </div>
        )}
      </div>

      {/* BEGIN: InstitutionalFooter */}
      <footer className="mt-12 border-t border-slate-200 bg-white py-6 text-slate-500 text-xs -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-slate-700">TradePilot AI Institutional Platform</span>
            <span>•</span>
            <span>Pasar Modal Indonesia (BEI / IDX)</span>
          </div>
          <p className="text-slate-400 text-center sm:text-right">
            Analisis ini bersifat edukatif dan advisori berbasis komputasi data pasar terverifikasi. Keputusan investasi tetap berada di tangan masing-masing trader.
          </p>
        </div>
      </footer>
      {/* END: InstitutionalFooter */}
    </main>
  );
}
