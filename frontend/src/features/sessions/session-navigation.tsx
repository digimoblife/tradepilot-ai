"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const DESTINATIONS = [
  { label: "Ringkasan", suffix: "" },
  { label: "Analisis", suffix: "/analysis" },
  { label: "Riwayat", suffix: "/history" },
] as const;

export function SessionNavigation({ sessionId }: { sessionId: string }) {
  const pathname = usePathname();
  const baseHref = `/sessions/${encodeURIComponent(sessionId)}`;

  return (
    <nav aria-label="Navigasi sesi" className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 sm:px-6 lg:px-8">
      <ul className="grid min-w-0 grid-cols-3 gap-1 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-1.5 shadow-[var(--elevation-low)]">
        {DESTINATIONS.map(({ label, suffix }) => {
          const href = `${baseHref}${suffix}`;
          const active = pathname === href;
          return (
            <li key={href} className="min-w-0">
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-11 min-w-0 items-center justify-center rounded-[var(--radius-compact)] px-2 text-center text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] ${
                  active
                    ? "bg-[var(--color-action-primary)] font-semibold text-[var(--color-text-inverse)] shadow-xs"
                    : "text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text-strong)]"
                }`}
              >
                <span className="truncate">{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
