"use client";

import Link from "next/link";
import type { SessionDetailAggregate } from "@/features/trade-workspace/types";

export function SessionWaitingSummary({
  sessionId,
  detail,
}: {
  sessionId: string;
  detail: SessionDetailAggregate;
}) {
  const step = detail.current_step;
  const isWaitingState =
    detail.session.status === "WAITING" || step.code === "WAIT_UPDATE";

  if (!isWaitingState) return null;

  const canSubmitWaitUpdate = step.workflow_actions.includes("SUBMIT_WAIT_UPDATE");
  const hasLatestAnalysis = Boolean(detail.latest_analysis?.has_result);

  const waitUpdateHref = `/sessions/${encodeURIComponent(sessionId)}/wait-update`;
  const analysisHref = `/sessions/${encodeURIComponent(sessionId)}/analysis`;

  return (
    <section
      aria-labelledby="waiting-summary-title"
      className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8 sm:px-6 sm:pb-10 lg:px-8"
    >
      <div className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Ringkasan Status Sesi
        </p>
        <h2
          id="waiting-summary-title"
          className="mt-2 break-words text-xl font-bold leading-[var(--text-line-heading)] text-[var(--color-text-strong)] sm:text-2xl"
        >
          Menunggu Update
        </h2>
        <p className="mt-3 break-words text-sm leading-[var(--text-line-body)] text-[var(--color-text-default)] sm:text-base">
          Sesi ini sedang menunggu data orderbook terbaru sebelum analisis berikutnya dilakukan.
        </p>
        <p className="mt-3 break-words text-sm font-medium text-[var(--color-text-muted)]">
          Belum ada posisi yang dibuka.
        </p>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
          {canSubmitWaitUpdate ? (
            <Link
              href={waitUpdateHref}
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              Kirim Pembaruan WAIT
            </Link>
          ) : null}

          {hasLatestAnalysis ? (
            <Link
              href={analysisHref}
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-5 text-sm font-semibold text-[var(--color-action-primary)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              Lihat Analisis Terbaru
            </Link>
          ) : null}
        </div>
      </div>
    </section>
  );
}
