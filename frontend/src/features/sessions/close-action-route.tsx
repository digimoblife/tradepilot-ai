"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useRouteSession } from "@/features/sessions/use-route-session";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import { SessionDetailHeader } from "@/features/sessions/session-detail-header";
import { SessionNavigation } from "@/features/sessions/session-navigation";
import { closePosition } from "@/features/trade-workspace/api";

export function CloseActionRoute({ sessionId }: { sessionId: string }) {
  const routeState = useRouteSession(sessionId);
  const detailState = useSessionCurrentStep(sessionId);
  const router = useRouter();

  const mountedRef = useRef(true);
  const currentSessionId = useRef(sessionId);
  const routeGeneration = useRef(0);
  const mutationGeneration = useRef(0);
  const submitInFlightRef = useRef(false);
  const navigatedRef = useRef(false);

  const [closePrice, setClosePrice] = useState("");
  const [closeTimestamp, setCloseTimestamp] = useState("");
  const [closeReason, setCloseReason] = useState("");
  const [note, setNote] = useState("");

  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [errorFeedback, setErrorFeedback] = useState<string | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    currentSessionId.current = sessionId;
    routeGeneration.current += 1;
    mutationGeneration.current += 1;
    submitInFlightRef.current = false;
    navigatedRef.current = false;

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setClosePrice("");
    setCloseTimestamp("");
    setCloseReason("");
    setNote("");
    setShowConfirm(false);
    setIsSubmitting(false);
    setValidationError(null);
    setErrorFeedback(null);
  }, [sessionId]);

  const isCurrentMutation = (
    reqSessionId: string,
    reqRouteGen: number,
    reqMutGen: number,
  ) =>
    mountedRef.current &&
    currentSessionId.current === reqSessionId &&
    routeGeneration.current === reqRouteGen &&
    mutationGeneration.current === reqMutGen;

  const currentStep = detailState.status === "success" ? detailState.currentStep : null;
  const isEligible =
    routeState.status === "success" &&
    detailState.status === "success" &&
    currentStep !== null &&
    currentStep.mode === "ACTIONABLE" &&
    !currentStep.read_only &&
    currentStep.workflow_actions.includes("CLOSE") &&
    detailState.detail.session.status === "OPEN_POSITION";

  const backHref = `/sessions/${encodeURIComponent(sessionId)}`;

  const handleInitialSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!isEligible || isSubmitting || submitInFlightRef.current) return;

    const price = Number.parseFloat(closePrice);
    if (!closePrice || Number.isNaN(price) || price <= 0) {
      setValidationError("Harga penutupan harus berupa angka positif.");
      return;
    }

    if (!closeTimestamp || closeTimestamp.trim().length === 0) {
      setValidationError("Waktu penutupan harus diisi.");
      return;
    }

    if (!closeReason || closeReason.trim().length === 0) {
      setValidationError("Alasan penutupan harus diisi.");
      return;
    }

    setValidationError(null);
    setErrorFeedback(null);
    setShowConfirm(true);
  };

  const handleConfirmClose = async () => {
    if (!isEligible || isSubmitting || submitInFlightRef.current) return;

    setIsSubmitting(true);
    submitInFlightRef.current = true;

    const reqSessionId = sessionId;
    const reqRouteGen = routeGeneration.current;
    const reqMutGen = ++mutationGeneration.current;

    let formattedTimestamp = closeTimestamp;
    try {
      const parsedDate = new Date(closeTimestamp);
      if (!Number.isNaN(parsedDate.getTime())) {
        formattedTimestamp = parsedDate.toISOString();
      }
    } catch {
      // Use raw input
    }

    try {
      await closePosition(reqSessionId, {
        close_price: closePrice,
        close_timestamp: formattedTimestamp,
        close_reason: closeReason,
        note: note.trim() ? note.trim() : null,
      });

      if (!isCurrentMutation(reqSessionId, reqRouteGen, reqMutGen) || navigatedRef.current) return;

      navigatedRef.current = true;
      await detailState.refetch();
      router.push(backHref);
    } catch {
      if (isCurrentMutation(reqSessionId, reqRouteGen, reqMutGen)) {
        setErrorFeedback(
          "Posisi belum dapat ditutup. Periksa kembali data yang dimasukkan lalu coba lagi.",
        );
        setShowConfirm(false);
      }
    } finally {
      if (isCurrentMutation(reqSessionId, reqRouteGen, reqMutGen)) {
        setIsSubmitting(false);
        submitInFlightRef.current = false;
      }
    }
  };

  if (routeState.status === "loading" || detailState.status === "loading") {
    return (
      <section className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-10 sm:px-6 lg:px-8">
        <p role="status" className="text-sm text-[var(--color-text-muted)]">
          Memuat konteks sesi…
        </p>
      </section>
    );
  }

  if (routeState.status !== "success" || detailState.status !== "success") {
    return (
      <section className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-10 sm:px-6 lg:px-8">
        <p role="alert" className="text-sm text-[var(--color-status-danger)]">
          Konteks sesi tidak dapat dimuat. Silakan coba lagi nanti.
        </p>
      </section>
    );
  }

  return (
    <>
      <SessionDetailHeader session={routeState.session} />
      <SessionNavigation sessionId={sessionId} />

      <main className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <div className="mx-auto max-w-2xl min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] shadow-[var(--elevation-low)] sm:p-6">
          <Link
            href={backHref}
            className="inline-flex min-h-11 items-center text-sm font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            ← Kembali ke Ringkasan
          </Link>

          {!isEligible ? (
            <div className="mt-6 min-w-0 space-y-3 border-t border-[var(--color-border-default)] pt-5">
              <h1 className="text-xl font-bold text-[var(--color-text-strong)]">
                Penutupan posisi tidak tersedia
              </h1>
              <p className="break-words text-sm text-[var(--color-text-muted)]">
                Sesi ini tidak dapat ditutup pada tahap saat ini.
              </p>
              <Link
                href={backHref}
                className="mt-4 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                Kembali ke Ringkasan
              </Link>
            </div>
          ) : (
            <div className="mt-6 min-w-0 border-t border-[var(--color-border-default)] pt-5">
              <div>
                <h1 className="text-xl font-bold text-[var(--color-text-strong)]">
                  Tutup Posisi
                </h1>
                <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                  Masukkan data penutupan posisi. Sesi akan menjadi selesai setelah penutupan dikonfirmasi.
                </p>
                <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                  Menutup posisi tidak menghapus sesi atau riwayatnya.
                </p>
              </div>

              {validationError ? (
                <p id="close-validation-error" role="alert" className="mt-4 break-words text-sm font-medium text-[var(--color-status-danger)]">
                  {validationError}
                </p>
              ) : null}

              {errorFeedback ? (
                <div role="alert" className="mt-4 rounded-[var(--radius-compact)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-3 text-sm text-[var(--color-status-danger)]">
                  <p className="font-bold">Posisi belum dapat ditutup</p>
                  <p className="mt-1">{errorFeedback}</p>
                </div>
              ) : null}

              {showConfirm ? (
                <div className="mt-6 min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-muted)] p-5 space-y-4">
                  <div>
                    <h2 className="text-lg font-bold text-[var(--color-text-strong)]">
                      Konfirmasi Penutupan Posisi
                    </h2>
                    <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                      Posisi akan ditutup dan sesi menjadi selesai. Seluruh data dan riwayat tetap tersimpan, dan sesi tidak akan diarsipkan secara otomatis.
                    </p>
                  </div>

                  <dl className="grid min-w-0 gap-2 border-t border-[var(--color-border-default)] pt-3 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-[var(--color-text-muted)]">Harga Penutupan:</dt>
                      <dd className="font-semibold text-[var(--color-text-strong)]">{closePrice}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-[var(--color-text-muted)]">Waktu Penutupan:</dt>
                      <dd className="font-semibold text-[var(--color-text-strong)]">{closeTimestamp}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-[var(--color-text-muted)]">Alasan Penutupan:</dt>
                      <dd className="font-semibold text-[var(--color-text-strong)]">{closeReason}</dd>
                    </div>
                    {note ? (
                      <div className="flex justify-between">
                        <dt className="text-[var(--color-text-muted)]">Catatan:</dt>
                        <dd className="font-semibold text-[var(--color-text-strong)]">{note}</dd>
                      </div>
                    ) : null}
                  </dl>

                  <div className="flex min-w-0 flex-col gap-3 pt-2 sm:flex-row sm:justify-end">
                    <button
                      type="button"
                      disabled={isSubmitting}
                      onClick={() => setShowConfirm(false)}
                      className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
                    >
                      Batal
                    </button>
                    <button
                      type="button"
                      disabled={isSubmitting}
                      aria-busy={isSubmitting}
                      onClick={() => void handleConfirmClose()}
                      className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-6 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
                    >
                      {isSubmitting ? "Menutup posisi..." : "Konfirmasi Tutup Posisi"}
                    </button>
                  </div>
                </div>
              ) : (
                <form
                  noValidate
                  onSubmit={handleInitialSubmit}
                  className="mt-6 min-w-0 space-y-5"
                >
                  <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                    Harga Penutupan *
                    <input
                      type="number"
                      inputMode="decimal"
                      step="any"
                      min="0"
                      required
                      disabled={isSubmitting}
                      value={closePrice}
                      onChange={(e) => setClosePrice(e.target.value)}
                      placeholder="cth. 5200"
                      className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                    />
                  </label>

                  <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                    Waktu Penutupan *
                    <input
                      type="datetime-local"
                      required
                      disabled={isSubmitting}
                      value={closeTimestamp}
                      onChange={(e) => setCloseTimestamp(e.target.value)}
                      className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                    />
                  </label>

                  <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                    Alasan Penutupan *
                    <input
                      type="text"
                      required
                      disabled={isSubmitting}
                      value={closeReason}
                      onChange={(e) => setCloseReason(e.target.value)}
                      placeholder="cth. Target harga tercapai"
                      className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                    />
                  </label>

                  <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                    Catatan (opsional)
                    <textarea
                      rows={3}
                      disabled={isSubmitting}
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      placeholder="Catatan tambahan mengenai penutupan..."
                      className="mt-1 block w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                    />
                  </label>

                  <div className="flex min-w-0 flex-col gap-3 pt-3 sm:flex-row sm:justify-end">
                    <Link
                      href={backHref}
                      className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-4 font-semibold text-[var(--color-text-strong)] hover:bg-[var(--color-surface-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
                    >
                      Batal
                    </Link>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-6 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
                    >
                      Lanjutkan
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
