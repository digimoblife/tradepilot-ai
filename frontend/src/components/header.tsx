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
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <Link href={user ? "/sessions" : "/"} className="text-lg font-bold tracking-tight text-zinc-900">
          TradePilot AI
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          {loading ? null : user ? (
            <>
              <Link href="/sessions" className="text-zinc-600 hover:text-zinc-900">
                Sesi
              </Link>
              <span className="text-zinc-400">{user.email}</span>
              <button
                onClick={handleLogout}
                disabled={loggingOut}
                className="rounded-md bg-zinc-100 px-3 py-1.5 text-zinc-700 hover:bg-zinc-200 disabled:opacity-50"
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
