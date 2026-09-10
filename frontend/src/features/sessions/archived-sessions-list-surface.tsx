"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { useArchivedSessionsList } from "./use-archived-sessions-list";
import type { SessionStatus, TradeSessionListItem } from "@/features/trade-workspace/types";

const TERMINAL_STATUS_PRESENTATIONS: Record<
  string,
  { label: string; badgeClassName: string }
> = {
  CLOSED: {
    label: "Selesai",
    badgeClassName: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  CLOSED_SKIPPED: {
    label: "Dilewati",
    badgeClassName: "bg-slate-100 text-slate-700 border-slate-200",
  },
};

const UNKNOWN_STATUS_PRESENTATION = {
  label: "Status tidak dikenali",
  badgeClassName: "bg-slate-100 text-slate-700 border-slate-200",
};

const TIMESTAMP_FORMATTER = new Intl.DateTimeFormat("id-ID", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function formatTimestamp(value: string | null | undefined): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return TIMESTAMP_FORMATTER.format(parsed);
}

const PAGE_SIZE = 5;

export function ArchivedSessionCard({ session }: { session: TradeSessionListItem }) {
  const statusInfo =
    TERMINAL_STATUS_PRESENTATIONS[session.status as SessionStatus] ?? UNKNOWN_STATUS_PRESENTATION;

  const detailHref = `/sessions/${encodeURIComponent(session.id)}`;
  const formattedArchivedAt = formatTimestamp(session.archived_at);
  const formattedClosedAt = formatTimestamp(session.closed_at);
  const isSkipped = session.status === "CLOSED_SKIPPED";

  return (
    <article
      className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md hover:border-slate-300 transition-all duration-200"
      data-purpose="session-card"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-2 min-w-0">
          {/* Header with Ticker, Company Name and Status Badge */}
          <div className="flex items-center space-x-3">
            <div className="flex items-baseline space-x-2 min-w-0">
              <span className="text-lg font-bold text-slate-900 tracking-tight font-mono">
                {session.ticker}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-xs font-medium text-slate-500 truncate">
                {session.company_name}
              </span>
            </div>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusInfo.badgeClassName}`}
            >
              {statusInfo.label}
            </span>
          </div>

          {/* Metadata Timestamps */}
          <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs text-slate-500 font-mono">
            {formattedArchivedAt ? (
              <div className="flex items-center">
                <span className="text-slate-400 mr-1.5">Diarsipkan:</span>
                <span className="text-slate-700">{formattedArchivedAt}</span>
              </div>
            ) : null}
            {formattedArchivedAt && formattedClosedAt ? (
              <div className="hidden sm:inline text-slate-300">•</div>
            ) : null}
            {formattedClosedAt ? (
              <div className="flex items-center">
                <span className="text-slate-400 mr-1.5">Waktu Ditutup:</span>
                <span className="text-slate-700">{formattedClosedAt}</span>
              </div>
            ) : null}
          </div>

          {/* Trade Result / AI Outcome Tag */}
          <div className="flex flex-wrap items-center gap-2 pt-0.5">
            {isSkipped ? (
              <>
                <span className="text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-mono">
                  Keputusan: Dilewati
                </span>
                <span className="text-[11px] text-slate-500 font-medium">
                  {session.note || "Kondisi pasar tidak memenuhi parameter / resiko melebihi reward"}
                </span>
              </>
            ) : (
              <>
                <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-mono">
                  Posisi Selesai
                </span>
                <span className="text-[11px] text-slate-500 font-medium">
                  {session.note || "Sesi perdagangan telah diselesaikan dan diarsipkan"}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Action Button */}
        <div className="flex-shrink-0 flex items-center md:self-center">
          <Link
            href={detailHref}
            className="w-full sm:w-auto inline-flex justify-center items-center px-4 py-2 min-h-11 sm:min-h-9 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-2xs focus-visible:outline-2 focus-visible:outline-blue-600"
          >
            Lihat Sesi
          </Link>
        </div>
      </div>
    </article>
  );
}

export function ArchivedSessionsListSurface() {
  const { state, retry } = useArchivedSessionsList();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "CLOSED" | "CLOSED_SKIPPED">("ALL");
  const [currentPage, setCurrentPage] = useState(1);

  const filteredSessions = useMemo(() => {
    if (state.status !== "success") return [];

    return state.sessions.filter((session) => {
      // Search query filter
      if (searchQuery.trim()) {
        const query = searchQuery.trim().toLowerCase();
        const matchesTicker = session.ticker.toLowerCase().includes(query);
        const matchesCompany = session.company_name.toLowerCase().includes(query);
        if (!matchesTicker && !matchesCompany) return false;
      }

      // Status filter
      if (statusFilter !== "ALL" && session.status !== statusFilter) {
        return false;
      }

      return true;
    });
  }, [state, searchQuery, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredSessions.length / PAGE_SIZE));
  const activePage = Math.min(currentPage, totalPages);

  const paginatedSessions = useMemo(() => {
    const start = (activePage - 1) * PAGE_SIZE;
    return filteredSessions.slice(start, start + PAGE_SIZE);
  }, [filteredSessions, activePage]);

  const startIndex = filteredSessions.length > 0 ? (activePage - 1) * PAGE_SIZE + 1 : 0;
  const endIndex = Math.min(activePage * PAGE_SIZE, filteredSessions.length);

  return (
    <main className="mx-auto w-full max-w-7xl min-w-0 px-4 py-6 sm:px-6 sm:py-8 lg:px-8 space-y-6 flex-1">
      {/* BEGIN: PageHeader */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Sesi Diarsipkan</h1>
          <p className="text-sm text-slate-500 mt-1">
            Sesi trading yang telah selesai dan dipindahkan dari daftar Sesi aktif.
          </p>
        </div>
        <div className="flex-shrink-0">
          <Link
            href="/sessions"
            className="inline-flex min-h-11 sm:min-h-9 items-center justify-center px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 hover:border-slate-400 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="w-4 h-4 mr-1.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M10 19l-7-7m0 0l7-7m-7 7h18" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
            </svg>
            Kembali ke Sesi
          </Link>
        </div>
      </section>
      {/* END: PageHeader */}

      {/* BEGIN: FilterAndSearchToolbar */}
      {state.status === "success" && state.sessions.length > 0 ? (
        <section className="mt-6 mb-6">
          <div className="bg-white p-3 sm:p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
            {/* Search Input */}
            <div className="relative flex-1 min-w-[240px]">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-4 w-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                  />
                </svg>
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                placeholder="Cari kode saham (e.g. AKRA, PGEO, BBRI)..."
              />
            </div>

            {/* Filter Controls */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Status Pill Selection */}
              <div className="inline-flex p-1 bg-slate-100 rounded-lg text-xs font-medium">
                <button
                  type="button"
                  onClick={() => {
                    setStatusFilter("ALL");
                    setCurrentPage(1);
                  }}
                  className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                    statusFilter === "ALL"
                      ? "bg-white text-slate-900 font-semibold shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Semua
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStatusFilter("CLOSED");
                    setCurrentPage(1);
                  }}
                  className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                    statusFilter === "CLOSED"
                      ? "bg-white text-slate-900 font-semibold shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Selesai (TP)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStatusFilter("CLOSED_SKIPPED");
                    setCurrentPage(1);
                  }}
                  className={`px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                    statusFilter === "CLOSED_SKIPPED"
                      ? "bg-white text-slate-900 font-semibold shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Dilewati (Skip)
                </button>
              </div>
            </div>
          </div>
        </section>
      ) : null}
      {/* END: FilterAndSearchToolbar */}

      {state.status === "loading" ? (
        <div
          role="status"
          className="rounded-xl border border-slate-200 bg-white p-8 sm:p-12 text-center space-y-3 shadow-xs"
        >
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-3 border-blue-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-500">Memuat sesi yang diarsipkan…</p>
        </div>
      ) : state.status === "authentication-required" ? (
        <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 space-y-3">
          <p className="font-semibold">Sesi Anda telah berakhir. Silakan masuk kembali.</p>
          <Link
            href="/login?next=%2Fsessions%2Farchived"
            className="inline-flex min-h-11 items-center font-semibold text-rose-600 hover:underline"
          >
            Masuk kembali
          </Link>
        </div>
      ) : state.status === "error" ? (
        <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 space-y-3">
          <p className="font-semibold">Daftar sesi yang diarsipkan tidak dapat dimuat. Silakan coba lagi.</p>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={retry}
              className="inline-flex min-h-11 items-center justify-center rounded-lg bg-rose-600 px-4 text-sm font-semibold text-white hover:bg-rose-700 shadow-sm cursor-pointer"
            >
              Coba lagi
            </button>
            <Link
              href="/sessions"
              className="inline-flex min-h-11 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Kembali ke Sesi
            </Link>
          </div>
        </div>
      ) : state.sessions.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 sm:p-12 text-center space-y-3 shadow-sm">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400 text-xl">
            📁
          </div>
          <h2 className="text-lg font-bold text-slate-900">Belum ada sesi yang diarsipkan</h2>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Sesi yang Anda arsipkan setelah selesai akan muncul di sini.
          </p>
          <div className="pt-2">
            <Link
              href="/sessions"
              className="inline-flex min-h-11 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
            >
              Kembali ke Sesi
            </Link>
          </div>
        </div>
      ) : filteredSessions.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center space-y-3 shadow-xs">
          <p className="text-sm font-medium text-slate-600">
            Tidak ada sesi yang cocok dengan filter atau kata kunci &ldquo;{searchQuery}&rdquo;.
          </p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery("");
              setStatusFilter("ALL");
              setCurrentPage(1);
            }}
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 underline cursor-pointer"
          >
            Reset Filter
          </button>
        </div>
      ) : (
        <section className="space-y-3.5" data-purpose="archive-sessions-container">
          {paginatedSessions.map((session) => (
            <ArchivedSessionCard key={session.id} session={session} />
          ))}

          {/* BEGIN: PaginationBar */}
          {filteredSessions.length > PAGE_SIZE ? (
            <nav
              aria-label="Pagination"
              className="mt-8 pt-4 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4"
            >
              <div className="text-xs text-slate-500 font-medium">
                Menampilkan <span className="text-slate-900 font-semibold">{startIndex}</span> -{" "}
                <span className="text-slate-900 font-semibold">{endIndex}</span> dari{" "}
                <span className="text-slate-900 font-semibold">{filteredSessions.length}</span> sesi diarsipkan
              </div>
              <div className="inline-flex items-center space-x-1">
                <button
                  type="button"
                  disabled={activePage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  className="px-3 py-1.5 border border-slate-200 rounded-md text-xs font-medium text-slate-600 hover:bg-slate-50 bg-white disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                >
                  Sebelumnya
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => setCurrentPage(num)}
                    className={`px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer ${
                      activePage === num
                        ? "bg-blue-600 text-white shadow-xs"
                        : "border border-slate-200 text-slate-600 hover:bg-slate-50 bg-white"
                    }`}
                  >
                    {num}
                  </button>
                ))}
                <button
                  type="button"
                  disabled={activePage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  className="px-3 py-1.5 border border-slate-200 rounded-md text-xs font-medium text-slate-600 hover:bg-slate-50 bg-white disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                >
                  Berikutnya
                </button>
              </div>
            </nav>
          ) : null}
          {/* END: PaginationBar */}
        </section>
      )}

      {/* BEGIN: InstitutionalFooter */}
      <footer className="border-t border-slate-200 pt-6 mt-12">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-800">TradePilot AI Institutional</span>
            <span className="text-slate-300">•</span>
            <span>Data terverifikasi Bursa Efek Indonesia</span>
          </div>
          <div className="text-slate-400">Hak Cipta © 2026 TradePilot AI. All rights reserved.</div>
        </div>
      </footer>
      {/* END: InstitutionalFooter */}
    </main>
  );
}
