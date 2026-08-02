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
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex min-w-0 min-h-14 max-w-5xl flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-2 sm:h-14 sm:flex-nowrap sm:py-0">
        <Link href={user ? "/trade-workspace" : "/"} className="shrink-0 whitespace-nowrap text-lg font-bold tracking-tight text-zinc-900">
          TradePilot AI
        </Link>
        <nav className="flex min-w-0 flex-1 flex-wrap items-center justify-end gap-x-3 gap-y-1 text-sm sm:flex-nowrap">
          {loading ? null : user ? (
            <>
              <Link href="/trade-workspace" className="shrink-0 text-zinc-600 hover:text-zinc-900">
                Sesi
              </Link>
              <span className="min-w-0 max-w-[9rem] break-words text-right leading-tight text-zinc-400 sm:max-w-none sm:truncate">{user.email}</span>
              <button
                onClick={handleLogout}
                disabled={loggingOut}
                className="shrink-0 rounded-md bg-zinc-100 px-3 py-1.5 text-zinc-700 hover:bg-zinc-200 disabled:opacity-50"
              >
                {loggingOut ? "..." : "Keluar"}
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-md bg-blue-600 px-3 py-1.5 text-white hover:bg-blue-700"
            >
              Masuk
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
