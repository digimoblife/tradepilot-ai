"use client";

import Link from "next/link";
import type { CurrentStep, SessionDetailAggregate } from "@/features/trade-workspace/types";

export function SessionOpenPositionSummary({
  sessionId,
  detail,
  step,
}: {
  sessionId: string;
  detail: SessionDetailAggregate;
  step: CurrentStep;
}) {
  if (detail.session.status !== "OPEN_POSITION") return null;

  const position = detail.position;
  const actions = step.workflow_actions;
  const canUpdate = actions.includes("SUBMIT_POSITION_UPDATE") && !step.read_only;
  const canClose = actions.includes("CLOSE") && !step.read_only;
  const hasAnalysis = detail.latest_analysis?.has_result ?? false;

  return (
    <section
      aria-labelledby="open-position-summary-title"
      className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8 sm:px-6 sm:pb-10 lg:px-8"
    >
      <div className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-status-success)] bg-[var(--color-status-success-subtle)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
        <h2
          id="open-position-summary-title"
          className="text-xl font-bold leading-[var(--text-line-heading)] text-[var(--color-text-strong)]"
        >
          Posisi Terbuka
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text-default)]">
          Sesi ini memiliki posisi yang sedang dipantau.
        </p>

        {!position ? (
          <p className="mt-4 text-sm text-[var(--color-text-muted)]">Detail posisi belum tersedia.</p>
        ) : (
          <dl className="mt-4 grid min-w-0 grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {position.entry_price !== null && position.entry_price !== undefined ? (
              <div>
                <dt className="font-semibold text-[var(--color-text-muted)]">Harga Entry</dt>
                <dd className="mt-1 font-bold text-[var(--color-text-strong)]">
                  {typeof position.entry_price === "number"
                    ? `Rp ${position.entry_price.toLocaleString("id-ID")}`
                    : String(position.entry_price)}
                </dd>
              </div>
            ) : null}

            {position.quantity !== null && position.quantity !== undefined ? (
              <div>
                <dt className="font-semibold text-[var(--color-text-muted)]">Jumlah</dt>
                <dd className="mt-1 font-bold text-[var(--color-text-strong)]">
                  {typeof position.quantity === "number"
                    ? position.quantity.toLocaleString("id-ID")
                    : String(position.quantity)}
                </dd>
              </div>
            ) : null}

            {position.stop_loss !== null && position.stop_loss !== undefined ? (
              <div>
                <dt className="font-semibold text-[var(--color-text-muted)]">Stop Loss</dt>
                <dd className="mt-1 font-bold text-[var(--color-text-strong)]">
                  {typeof position.stop_loss === "number"
                    ? `Rp ${position.stop_loss.toLocaleString("id-ID")}`
                    : String(position.stop_loss)}
                </dd>
              </div>
            ) : null}

            {position.target_price !== null && position.target_price !== undefined ? (
              <div>
                <dt className="font-semibold text-[var(--color-text-muted)]">Target Harga</dt>
                <dd className="mt-1 font-bold text-[var(--color-text-strong)]">
                  {typeof position.target_price === "number"
                    ? `Rp ${position.target_price.toLocaleString("id-ID")}`
                    : String(position.target_price)}
                </dd>
              </div>
            ) : null}

            {position.entry_timestamp || position.entry_at ? (
              <div>
                <dt className="font-semibold text-[var(--color-text-muted)]">Waktu Entry</dt>
                <dd className="mt-1 font-bold text-[var(--color-text-strong)]">
                  {String(position.entry_timestamp || position.entry_at)}
                </dd>
              </div>
            ) : null}

            {position.note ? (
              <div className="sm:col-span-2 lg:col-span-3">
                <dt className="font-semibold text-[var(--color-text-muted)]">Catatan</dt>
                <dd className="mt-1 break-words text-[var(--color-text-strong)]">
                  {String(position.note)}
                </dd>
              </div>
            ) : null}
          </dl>
        )}

        <div className="mt-6 flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
          {canUpdate ? (
            <Link
              href={`/sessions/${encodeURIComponent(sessionId)}/position-update`}
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              Kirim Pembaruan Posisi
            </Link>
          ) : null}

          {canClose ? (
            <Link
              href={`/sessions/${encodeURIComponent(sessionId)}/close`}
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-5 text-sm font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              Tutup Posisi
            </Link>
          ) : null}

          {hasAnalysis ? (
            <Link
              href={`/sessions/${encodeURIComponent(sessionId)}/analysis`}
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] border border-transparent px-4 text-sm font-semibold text-[var(--color-action-primary)] hover:underline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              Lihat Analisis Terbaru
            </Link>
          ) : null}
        </div>
      </div>
    </section>
  );
}
