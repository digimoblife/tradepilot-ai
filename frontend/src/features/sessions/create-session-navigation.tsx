"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { CreateSessionForm } from "./create-session-form";
import { isStructurallyValidSessionId } from "./use-route-session";
import type { TradeSession } from "@/features/trade-workspace/types";

type NavigationState =
  | { status: "idle" }
  | { status: "navigating"; href: string }
  | { status: "failed"; href: string | null };

export function CreateSessionNavigation() {
  const router = useRouter();
  const navigationAttempted = useRef(false);
  const [navigation, setNavigation] = useState<NavigationState>({ status: "idle" });

  const pushToCreatedSession = useCallback(
    (href: string) => {
      setNavigation({ status: "navigating", href });
      try {
        router.push(href);
      } catch {
        setNavigation({ status: "failed", href });
      }
    },
    [router],
  );

  const handleCreated = useCallback(
    (session: TradeSession) => {
      if (navigationAttempted.current) return;
      navigationAttempted.current = true;

      if (!isStructurallyValidSessionId(session.id)) {
        setNavigation({ status: "failed", href: null });
        return;
      }

      pushToCreatedSession(`/sessions/${encodeURIComponent(session.id)}`);
    },
    [pushToCreatedSession],
  );

  const retryNavigation = useCallback(() => {
    if (navigation.status !== "failed" || navigation.href === null) return;
    pushToCreatedSession(navigation.href);
  }, [navigation, pushToCreatedSession]);

  return (
    <>
      <CreateSessionForm
        onCreated={handleCreated}
        successMessage={
          navigation.status === "failed"
            ? "Sesi berhasil dibuat."
            : "Sesi dibuat. Membuka sesi…"
        }
      />

      {navigation.status === "failed" ? (
        <div role="alert" className="mt-4 text-sm text-[var(--color-status-danger)]">
          <p>Halaman sesi baru tidak dapat dibuka. Sesi tidak akan dibuat ulang.</p>
          {navigation.href ? (
            <button
              type="button"
              onClick={retryNavigation}
              className="mt-3 min-h-11 rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-4 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              Buka sesi
            </button>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
