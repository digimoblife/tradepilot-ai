"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useRouteSession } from "@/features/sessions/use-route-session";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import { SessionDetailHeader } from "@/features/sessions/session-detail-header";
import { SessionNavigation } from "@/features/sessions/session-navigation";
import { submitPositionUpdateAnalysis, uploadPositionUpdateInput } from "@/features/trade-workspace/api";
import type { ObservationPeriod } from "@/features/trade-workspace/types";

export const OBSERVATION_PERIOD_OPTIONS: ReadonlyArray<{ value: ObservationPeriod; label: string }> = [
  { value: "MORNING", label: "Sesi Pagi (MORNING)" },
  { value: "MIDDAY", label: "Sesi Siang (MIDDAY)" },
  { value: "AFTERNOON", label: "Sesi Sore (AFTERNOON)" },
];

export function PositionUpdateActionRoute({ sessionId }: { sessionId: string }) {
  const routeState = useRouteSession(sessionId);
  const detailState = useSessionCurrentStep(sessionId);
  const router = useRouter();

  const mountedRef = useRef(true);
  const currentSessionId = useRef(sessionId);
  const routeGeneration = useRef(0);
  const mutationGeneration = useRef(0);
  const submitInFlightRef = useRef(false);
  const navigatedRef = useRef(false);

  const [orderbookFile, setOrderbookFile] = useState<File | null>(null);
  const [brokerFlowFile, setBrokerFlowFile] = useState<File | null>(null);
  const [currentPrice, setCurrentPrice] = useState("");
  const [observationPeriod, setObservationPeriod] = useState<ObservationPeriod>("MORNING");
  const [observationTimestamp, setObservationTimestamp] = useState("");

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
    setOrderbookFile(null);
    setBrokerFlowFile(null);
    setCurrentPrice("");
    setObservationPeriod("MORNING");
    setObservationTimestamp("");
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
    currentStep.workflow_actions.includes("SUBMIT_POSITION_UPDATE") &&
    detailState.detail.session.status === "OPEN_POSITION";

  const backHref = `/sessions/${encodeURIComponent(sessionId)}`;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!isEligible || isSubmitting || submitInFlightRef.current) return;

    if (!orderbookFile) {
      setValidationError("Pilih satu berkas gambar orderbook.");
      return;
    }

    const price = Number.parseFloat(currentPrice);
    if (!currentPrice || Number.isNaN(price) || price <= 0) {
      setValidationError("Harga saat ini harus berupa angka positif.");
      return;
    }

    if (!observationPeriod) {
      setValidationError("Pilih periode pengamatan.");
      return;
    }

    if (!observationTimestamp || observationTimestamp.trim().length === 0) {
      setValidationError("Waktu pengamatan harus diisi.");
      return;
    }

    setValidationError(null);
    setErrorFeedback(null);
    setIsSubmitting(true);
    submitInFlightRef.current = true;

    const reqSessionId = sessionId;
    const reqRouteGen = routeGeneration.current;
    const reqMutGen = ++mutationGeneration.current;

    let formattedTimestamp = observationTimestamp;
    try {
      const parsedDate = new Date(observationTimestamp);
      if (!Number.isNaN(parsedDate.getTime())) {
        formattedTimestamp = parsedDate.toISOString();
      }
    } catch {
      // Use raw input
    }

    try {
      await uploadPositionUpdateInput(reqSessionId, {
        orderbook: orderbookFile,
        ...(brokerFlowFile ? { broker_flow_1d: brokerFlowFile } : {}),
        current_price: currentPrice,
        observation_period: observationPeriod,
        observation_timestamp: formattedTimestamp,
      });

      if (!isCurrentMutation(reqSessionId, reqRouteGen, reqMutGen)) return;

      await submitPositionUpdateAnalysis(reqSessionId);

      if (!isCurrentMutation(reqSessionId, reqRouteGen, reqMutGen) || navigatedRef.current) return;

      navigatedRef.current = true;
      await detailState.refetch();
      router.push(backHref);
    } catch {
      if (isCurrentMutation(reqSessionId, reqRouteGen, reqMutGen)) {
        setErrorFeedback(
          "Position Update belum dapat dikirim. Periksa kembali data yang dimasukkan lalu coba lagi.",
        );
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
                Position Update tidak tersedia
              </h1>
              <p className="break-words text-sm text-[var(--color-text-muted)]">
                Sesi ini tidak dapat menerima Position Update pada tahap saat ini.
              </p>
              <Link
                href={backHref}
                className="mt-4 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-5 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                Kembali ke Ringkasan
              </Link>
            </div>
          ) : (
            <form
              noValidate
              onSubmit={handleSubmit}
              className="mt-6 min-w-0 space-y-5 border-t border-[var(--color-border-default)] pt-5"
            >
              <div>
                <h1 className="text-xl font-bold text-[var(--color-text-strong)]">
                  Formulir Pembaruan Posisi
                </h1>
                <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                  Unggah orderbook terbaru, tambahkan Broker Flow 1D bila tersedia, dan masukkan informasi harga saat ini untuk memperbarui pemantauan posisi.
                </p>
              </div>

              {validationError ? (
                <p id="position-validation-error" role="alert" className="break-words text-sm font-medium text-[var(--color-status-danger)]">
                  {validationError}
                </p>
              ) : null}

              {errorFeedback ? (
                <div role="alert" className="rounded-[var(--radius-compact)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-3 text-sm text-[var(--color-status-danger)]">
                  <p className="font-bold">Position Update belum dapat dikirim</p>
                  <p className="mt-1">{errorFeedback}</p>
                </div>
              ) : null}

              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                Gambar Orderbook Terbaru *
                <input
                  type="file"
                  accept="image/*"
                  required
                  disabled={isSubmitting}
                  onChange={(e) => setOrderbookFile(e.target.files?.[0] ?? null)}
                  className="mt-2 block min-h-11 w-full min-w-0 text-sm text-[var(--color-text-strong)] file:mr-4 file:min-h-11 file:rounded-[var(--radius-compact)] file:border-0 file:bg-[var(--color-surface-muted)] file:px-4 file:py-2 file:text-sm file:font-semibold file:text-[var(--color-text-strong)] hover:file:bg-[var(--color-border-default)]"
                />
                {orderbookFile ? (
                  <span className="mt-1 block break-all [overflow-wrap:anywhere] text-xs font-normal text-[var(--color-text-muted)]">
                    File terpilih: {orderbookFile.name} ({(orderbookFile.size / 1024).toFixed(1)} KB)
                  </span>
                ) : null}
              </label>

              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                Broker Flow — 1D (Optional)
                <input
                  type="file"
                  accept="image/*"
                  disabled={isSubmitting}
                  onChange={(e) => setBrokerFlowFile(e.target.files?.[0] ?? null)}
                  className="mt-2 block min-h-11 w-full min-w-0 text-sm text-[var(--color-text-strong)] file:mr-4 file:min-h-11 file:rounded-[var(--radius-compact)] file:border-0 file:bg-[var(--color-surface-muted)] file:px-4 file:py-2 file:text-sm file:font-semibold file:text-[var(--color-text-strong)] hover:file:bg-[var(--color-border-default)]"
                />
                {brokerFlowFile ? (
                  <span className="mt-1 block break-all [overflow-wrap:anywhere] text-xs font-normal text-[var(--color-text-muted)]">
                    File terpilih: {brokerFlowFile.name} ({(brokerFlowFile.size / 1024).toFixed(1)} KB)
                  </span>
                ) : null}
              </label>

              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                Harga Saat Ini (Current Price) *
                <input
                  type="number"
                  inputMode="decimal"
                  step="any"
                  min="0"
                  required
                  disabled={isSubmitting}
                  value={currentPrice}
                  onChange={(e) => setCurrentPrice(e.target.value)}
                  placeholder="cth. 5000"
                  className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                />
              </label>

              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                Periode Pengamatan *
                <select
                  required
                  disabled={isSubmitting}
                  value={observationPeriod}
                  onChange={(e) => setObservationPeriod(e.target.value as ObservationPeriod)}
                  className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                >
                  {OBSERVATION_PERIOD_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block min-w-0 text-sm font-semibold text-[var(--color-text-strong)]">
                Waktu Pengamatan *
                <input
                  type="datetime-local"
                  required
                  disabled={isSubmitting}
                  value={observationTimestamp}
                  onChange={(e) => setObservationTimestamp(e.target.value)}
                  className="mt-1 block min-h-11 w-full min-w-0 rounded-[var(--radius-compact)] border border-[var(--color-border-default)] px-3 py-2 text-sm text-[var(--color-text-strong)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
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
                  aria-busy={isSubmitting}
                  className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-6 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
                >
                  {isSubmitting ? "Mengirim Pembaruan Posisi..." : "Kirim Pembaruan Posisi"}
                </button>
              </div>
            </form>
          )}
        </div>
      </main>
    </>
  );
}
