"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";

export function Header() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

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
      <div className="mx-auto flex min-h-14 min-w-0 max-w-5xl flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-2 sm:h-14 sm:flex-nowrap sm:py-0">
        <Link href={user ? "/trade-workspace" : "/"} className="shrink-0 whitespace-nowrap text-lg font-bold tracking-tight text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]">
          TradePilot AI
        </Link>
        <nav className="flex min-w-0 w-full flex-wrap items-center justify-end gap-x-3 gap-y-1 text-sm sm:w-auto sm:flex-1 sm:flex-nowrap">
          {loading ? null : user ? (
            <>
              <Link href="/trade-workspace" className="min-h-11 shrink-0 py-2 text-[var(--color-text-muted)] hover:text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]">
                Sesi
              </Link>
              <span title={user.email} className="min-w-0 max-w-[9rem] truncate text-right leading-tight text-[var(--color-text-muted)] sm:max-w-none">{user.email}</span>
              <button
                onClick={handleLogout}
                disabled={loggingOut}
                className="min-h-11 shrink-0 rounded-[var(--radius-compact)] bg-[var(--color-surface-muted)] px-3 text-[var(--color-text-default)] hover:bg-[var(--color-border-default)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:opacity-50"
              >
                {loggingOut ? "..." : "Keluar"}
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-3 text-[var(--color-text-inverse)] hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              Masuk
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
