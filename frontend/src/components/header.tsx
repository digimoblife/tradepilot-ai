"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";
import { ButtonSpinner } from "./button-spinner";
import { InstitutionalBrand } from "@/components/ui";

export function Header() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [loggingOut, setLoggingOut] = useState(false);

  const archiveActive = pathname === "/sessions/archived";
  const sessionsActive =
    !archiveActive &&
    (pathname === "/sessions" || pathname.startsWith("/sessions/"));

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      router.push("/login");
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <header className="sticky top-0 z-30 w-full bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-xs">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-4">

        {/* LEFT — Brand */}
        <Link
          href={user ? "/sessions" : "/"}
          className="shrink-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 rounded-lg"
          aria-label="TradePilot AI — Beranda"
        >
          <InstitutionalBrand
            iconSizeClass="w-8 h-8"
            textSizeClass="text-sm sm:text-base"
            showEngineTag={false}
          />
        </Link>

        {/* CENTER — Navigation (only when logged in) */}
        {!loading && user ? (
          <nav
            aria-label="Navigasi utama"
            className="hidden sm:flex items-center"
          >
            {/* Separator kiri */}
            <span className="w-px h-5 bg-slate-200 mr-5" aria-hidden="true" />

            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
              <Link
                href="/sessions"
                aria-current={sessionsActive ? "page" : undefined}
                className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  sessionsActive
                    ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                    : "text-slate-500 hover:text-slate-700 hover:bg-white/60"
                }`}
              >
                Sesi Perdagangan
              </Link>
              <Link
                href="/sessions/archived"
                aria-current={archiveActive ? "page" : undefined}
                className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  archiveActive
                    ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                    : "text-slate-500 hover:text-slate-700 hover:bg-white/60"
                }`}
              >
                Arsip
              </Link>
            </div>

            {/* Separator kanan */}
            <span className="w-px h-5 bg-slate-200 ml-5" aria-hidden="true" />
          </nav>
        ) : null}

        {/* RIGHT — User info + actions */}
        {!loading ? (
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            {user ? (
              <>
                {/* Mobile nav pills — hidden from a11y tree, desktop nav is the canonical one */}
                <nav
                  aria-hidden="true"
                  className="flex sm:hidden items-center gap-1 bg-slate-100 p-1 rounded-lg"
                >
                  <Link
                    href="/sessions"
                    tabIndex={-1}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                      sessionsActive
                        ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                        : "text-slate-500"
                    }`}
                  >
                    Sesi
                  </Link>
                  <Link
                    href="/sessions/archived"
                    tabIndex={-1}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                      archiveActive
                        ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                        : "text-slate-500"
                    }`}
                  >
                    Arsip
                  </Link>
                </nav>

                {/* Email */}
                <span
                  title={user.email}
                  className="hidden lg:block text-xs text-slate-500 font-mono truncate max-w-[160px]"
                >
                  {user.email}
                </span>

                {/* Logout */}
                <button
                  onClick={handleLogout}
                  disabled={loggingOut}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 hover:border-slate-300 active:scale-[0.98] transition-all disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                >
                  {loggingOut && <ButtonSpinner className="h-3.5 w-3.5" />}
                  {loggingOut ? "Keluar…" : "Keluar"}
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="inline-flex items-center px-4 py-2 rounded-lg text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-xs shadow-blue-500/20 transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
              >
                Masuk
              </Link>
            )}
          </div>
        ) : null}

      </div>
    </header>
  );
}
