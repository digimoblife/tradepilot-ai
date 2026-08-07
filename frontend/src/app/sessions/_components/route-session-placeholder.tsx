"use client";

import Link from "next/link";

import { RoutePlaceholder } from "@/app/sessions/_components/route-placeholder";
import { SessionDetailHeader } from "@/features/sessions/session-detail-header";
import { SessionCurrentStepSection } from "@/features/sessions/session-current-step-section";
import { SessionNavigation } from "@/features/sessions/session-navigation";
import { useRouteSession } from "@/features/sessions/use-route-session";

type RouteSessionPlaceholderProps = {
  sessionId: string;
  currentHref: string;
  title: string;
  description: string;
  backHref: string;
  backLabel: string;
  successMode?: "placeholder" | "session-detail-header";
};

export function RouteSessionPlaceholder({
  sessionId,
  currentHref,
  title,
  description,
  backHref,
  backLabel,
  successMode = "placeholder",
}: RouteSessionPlaceholderProps) {
  const state = useRouteSession(sessionId);

  if (state.status === "success" && successMode === "session-detail-header") {
    return (
      <>
        <SessionDetailHeader session={state.session} />
        <SessionNavigation sessionId={sessionId} />
        <SessionCurrentStepSection sessionId={sessionId} />
      </>
    );
  }

  return (
    <>
      {state.status === "success" ? <SessionNavigation sessionId={sessionId} /> : null}
      <RoutePlaceholder
      title={title}
      description={description}
      backHref={backHref}
      backLabel={backLabel}
    >
      {state.status === "loading" ? (
        <p role="status" className="mt-4 text-sm text-[var(--color-text-muted)]">
          Memuat konteks sesi…
        </p>
      ) : null}

      {state.status === "success" ? (
        <p className="mt-4 text-sm text-[var(--color-text-muted)]">
          Konteks sesi untuk <span className="font-semibold">{state.session.ticker}</span> telah
          dimuat.
        </p>
      ) : null}

      {state.status === "not-found" ? (
        <p role="alert" className="mt-4 text-sm text-[var(--color-status-danger)]">
          Sesi tidak ditemukan atau tidak dapat diakses.
        </p>
      ) : null}

      {state.status === "authentication-required" ? (
        <div role="alert" className="mt-4 text-sm text-[var(--color-status-danger)]">
          <p>Sesi Anda telah berakhir. Silakan masuk kembali.</p>
          <Link
            href={`/login?next=${encodeURIComponent(currentHref)}`}
            className="mt-3 inline-flex min-h-11 items-center font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            Masuk kembali
          </Link>
        </div>
      ) : null}

      {state.status === "error" ? (
        <p role="alert" className="mt-4 text-sm text-[var(--color-status-danger)]">
          Konteks sesi tidak dapat dimuat. Silakan coba lagi nanti.
        </p>
      ) : null}
      </RoutePlaceholder>
    </>
  );
}
