"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";
import { ButtonSpinner } from "./button-spinner";

function primaryLinkClass(active: boolean) {
  return [
    "inline-flex min-h-11 min-w-0 items-center justify-center border-b-2 px-3 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
    active
      ? "border-[var(--color-action-primary)] font-semibold text-[var(--color-text-strong)]"
      : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-strong)]",
  ].join(" ");
}

export function Header() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [loggingOut, setLoggingOut] = useState(false);
  const archiveActive = pathname === "/sessions/archived";
  const sessionsActive =
    !archiveActive && (pathname === "/sessions" || pathname.startsWith("/sessions/"));

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
    <header className="border-b border-[var(--color-border-default)] bg-[var(--color-surface-standard)]">
      <div className="mx-auto grid min-w-0 max-w-5xl grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-4 py-2 sm:min-h-14 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:gap-x-6 sm:py-0">
        <Link
          href={user ? "/sessions" : "/"}
          className={`${user ? "col-span-2 sm:col-span-1" : "col-span-1"} min-w-0 truncate whitespace-nowrap text-lg font-bold tracking-tight text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]`}
        >
          TradePilot AI
        </Link>

        {!loading && user ? (
          <nav
            aria-label="Navigasi utama"
            className="col-start-1 row-start-2 flex min-w-0 items-center gap-1 sm:col-start-2 sm:row-start-1"
          >
            <Link
              href="/sessions"
              aria-current={sessionsActive ? "page" : undefined}
              className={primaryLinkClass(sessionsActive)}
            >
              Sessions
            </Link>
            <Link
              href="/sessions/archived"
              aria-current={archiveActive ? "page" : undefined}
              className={primaryLinkClass(archiveActive)}
            >
              Archive
            </Link>
          </nav>
        ) : null}

        {!loading ? (
          <div
            className={`${user ? "row-start-2 sm:row-start-1" : "row-start-1"} col-start-2 flex min-w-0 items-center justify-end gap-2 sm:col-start-3`}
          >
            {user ? (
              <>
                <span
                  title={user.email}
                  className="sr-only text-sm leading-tight text-[var(--color-text-muted)] sm:not-sr-only sm:block sm:max-w-[12rem] sm:truncate"
                >
                  {user.email}
                </span>
                <button
                  onClick={handleLogout}
                  disabled={loggingOut}
                  className="inline-flex min-h-11 shrink-0 items-center justify-center gap-1.5 rounded-[var(--radius-compact)] bg-[var(--color-surface-muted)] px-3 text-sm text-[var(--color-text-default)] hover:bg-[var(--color-border-default)] active:scale-[0.98] transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
                >
                  {loggingOut && <ButtonSpinner className="h-3.5 w-3.5" />}
                  {loggingOut ? "Keluar…" : "Keluar"}
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="inline-flex min-h-11 items-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-3 text-sm text-[var(--color-text-inverse)] hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
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
