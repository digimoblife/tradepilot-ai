"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useRouteSession } from "@/features/sessions/use-route-session";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import { submitInitialAnalysis, uploadInitialEvidence } from "@/features/trade-workspace/api";
import { previewMarketEvidence } from "@/lib/api/market-evidence";
import type { EvidenceSnapshot } from "@/types/market-evidence";
import { EvidenceInspector } from "@/features/evidence/evidence-inspector";

type EvidenceField = "orderbook" | "chart_3_month" | "chart_6_month" | "foreign_flow_1w";
type Files = Partial<Record<EvidenceField, File>>;
type Operation =
  | "idle"
  | "fetching-market"
  | "uploading"
  | "reconciling"
  | "submitting-analysis"
  | "confirmation-failed";

const fields: ReadonlyArray<readonly [EvidenceField, string]> = [
  ["orderbook", "Orderbook"],
  ["chart_3_month", "Chart 3 Bulan"],
  ["chart_6_month", "Chart 6 Bulan"],
  ["foreign_flow_1w", "Foreign Flow — 1W"],
];

function isActionable(
  step: { code: string; mode: string; read_only: boolean; workflow_actions: string[] },
  action: string,
) {
  return (
    step.mode === "ACTIONABLE" &&
    !step.read_only &&
    step.workflow_actions.length === 1 &&
    step.workflow_actions[0] === action
  );
}

export function InitialEvidenceActionRoute({ sessionId }: { sessionId: string }) {
  const identity = useRouteSession(sessionId);
  const detail = useSessionCurrentStep(sessionId);
  const router = useRouter();
  const mounted = useRef(true);
  const currentSessionId = useRef(sessionId);
  const routeGeneration = useRef(0);
  const mutationGeneration = useRef(0);
  const uploadInFlightRef = useRef(false);
  const analysisInFlightRef = useRef(false);
  const navigatedRef = useRef(false);

  const [files, setFiles] = useState<Files>({});
  const [feedback, setFeedback] = useState<string | null>(null);
  const [operation, setOperation] = useState<Operation>("idle");

  // Automated ZAPI Ingestion States
  const [acquisitionStep, setAcquisitionStep] = useState<number>(0);
  const [snapshot, setSnapshot] = useState<EvidenceSnapshot | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const backHref = `/sessions/${encodeURIComponent(sessionId)}`;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    currentSessionId.current = sessionId;
    routeGeneration.current += 1;
    mutationGeneration.current += 1;
    uploadInFlightRef.current = false;
    analysisInFlightRef.current = false;
    navigatedRef.current = false;
    setFiles({});
    setFeedback(null);
    setOperation("idle");
    setAcquisitionStep(0);
    setSnapshot(null);
    setFetchError(null);
  }, [sessionId]);

  const isCurrentMutation = (
    requestedSessionId: string,
    requestedRouteGeneration: number,
    requestedMutationGeneration: number,
  ) =>
    mounted.current &&
    currentSessionId.current === requestedSessionId &&
    routeGeneration.current === requestedRouteGeneration &&
    mutationGeneration.current === requestedMutationGeneration;

  const actions = detail.status === "success" ? detail.currentStep.workflow_actions : [];
  const canUpload =
    detail.status === "success" &&
    detail.currentStep.code === "INITIAL_EVIDENCE" &&
    isActionable(detail.currentStep, "SUBMIT_INITIAL_EVIDENCE");
  const canSubmitAnalysis =
    detail.status === "success" &&
    detail.currentStep.code === "INITIAL_ANALYSIS" &&
    isActionable(detail.currentStep, "REQUEST_INITIAL_ANALYSIS");
  const processing =
    detail.status === "success" && detail.currentStep.mode === "PROCESSING" && actions.length === 0;
  const controlsLocked = operation !== "idle";
  const complete = Boolean(
    files.orderbook && files.chart_3_month && files.chart_6_month && files.foreign_flow_1w,
  );

  const reconcile = async (
    requestedSessionId: string,
    requestedRouteGeneration: number,
    requestedMutationGeneration: number,
    message: string,
  ) => {
    if (!isCurrentMutation(requestedSessionId, requestedRouteGeneration, requestedMutationGeneration))
      return false;
    setFeedback(message);
    setOperation("reconciling");
    const refreshed = await detail.refetch();
    if (!isCurrentMutation(requestedSessionId, requestedRouteGeneration, requestedMutationGeneration))
      return false;
    if (refreshed.status === "success") {
      setOperation("idle");
      return true;
    }
    setFeedback("Status terbaru sesi belum dapat dikonfirmasi. Muat ulang halaman sebelum mencoba lagi.");
    setOperation("confirmation-failed");
    return false;
  };

  // 1-Click Automated Acquisition & AI Trigger
  const handleAutoAcquisition = async () => {
    if (identity.status !== "success" || !identity.session.ticker) return;
    const ticker = identity.session.ticker;
    setOperation("fetching-market");
    setFetchError(null);
    setAcquisitionStep(1);

    try {
      // Step 1 & 2: Fetch ZAPI
      await new Promise((r) => setTimeout(r, 400));
      setAcquisitionStep(2);

      const res = await previewMarketEvidence(sessionId, ticker);
      setSnapshot(res.snapshot);
      setAcquisitionStep(3);

      await new Promise((r) => setTimeout(r, 400));
      setAcquisitionStep(4);

      // Trigger AI Analysis
      await submitAnalysis();
    } catch (err: any) {
      setFetchError(err.message || "Gagal mengambil data dari ZAPI. Silakan coba lagi.");
      setOperation("idle");
      setAcquisitionStep(0);
    }
  };

  const select = (key: EvidenceField, file?: File) => {
    if (controlsLocked) return;
    setFiles((current) => ({ ...current, [key]: file }));
  };

  const upload = async () => {
    if (!complete) {
      setFeedback("Lengkapi Orderbook, Chart 3 Bulan, Chart 6 Bulan, dan Foreign Flow 1W sebelum mengunggah.");
      return;
    }
    if (!canUpload || uploadInFlightRef.current || analysisInFlightRef.current || controlsLocked)
      return;
    uploadInFlightRef.current = true;
    const requestedSessionId = sessionId;
    const requestedRouteGeneration = routeGeneration.current;
    const requestedMutationGeneration = ++mutationGeneration.current;
    setOperation("uploading");
    setFeedback("Mengunggah Bukti Awal…");
    try {
      await uploadInitialEvidence(requestedSessionId, files as Required<Files>);
      if (!isCurrentMutation(requestedSessionId, requestedRouteGeneration, requestedMutationGeneration))
        return;
      setFiles({});
      setFeedback("Bukti Awal berhasil disimpan.");
      await reconcile(
        requestedSessionId,
        requestedRouteGeneration,
        requestedMutationGeneration,
        "Bukti Awal berhasil disimpan. Memeriksa status terbaru sesi…",
      );
    } catch {
      await reconcile(
        requestedSessionId,
        requestedRouteGeneration,
        requestedMutationGeneration,
        "Memeriksa status terbaru sesi…",
      );
    } finally {
      if (
        isCurrentMutation(requestedSessionId, requestedRouteGeneration, requestedMutationGeneration)
      ) {
        uploadInFlightRef.current = false;
      }
    }
  };

  const submitAnalysis = async () => {
    if (uploadInFlightRef.current || analysisInFlightRef.current) return;
    analysisInFlightRef.current = true;
    const requestedSessionId = sessionId;
    const requestedRouteGeneration = routeGeneration.current;
    const requestedMutationGeneration = ++mutationGeneration.current;
    setOperation("submitting-analysis");
    setFeedback("Memulai Analisis Awal…");
    try {
      await submitInitialAnalysis(requestedSessionId);
      if (
        !isCurrentMutation(requestedSessionId, requestedRouteGeneration, requestedMutationGeneration) ||
        navigatedRef.current
      )
        return;
      navigatedRef.current = true;
      setFeedback("Permintaan Analisis Awal diterima.");
      router.push(`/sessions/${encodeURIComponent(requestedSessionId)}`);
    } catch {
      await reconcile(
        requestedSessionId,
        requestedRouteGeneration,
        requestedMutationGeneration,
        "Memeriksa status terbaru sesi…",
      );
    } finally {
      if (
        isCurrentMutation(requestedSessionId, requestedRouteGeneration, requestedMutationGeneration)
      ) {
        analysisInFlightRef.current = false;
      }
    }
  };

  const title = canUpload
    ? "Bukti Awal"
    : canSubmitAnalysis
      ? "Bukti Awal Lengkap"
      : processing
        ? "Analisis Awal Sedang Diproses"
        : "Bukti Awal Tidak Tersedia";

  const description = canUpload
    ? "Unggah satu orderbook, chart 3 bulan, chart 6 bulan, dan Foreign Flow 1W untuk menyiapkan Analisis Awal."
    : canSubmitAnalysis
      ? "Bukti Awal telah lengkap. Analisis Awal siap dimulai melalui tindakan terpisah."
      : processing
        ? "Permintaan Analisis Awal sedang diproses."
        : "Tindakan Bukti Awal tidak tersedia untuk kondisi sesi saat ini.";

  if (identity.status !== "success") {
    return (
      <section className="mx-auto w-full max-w-3xl min-w-0 px-4 py-10">
        <p role="status" className="text-muted-foreground">
          Memuat konteks sesi…
        </p>
      </section>
    );
  }

  const ticker = identity.session.ticker;
  const company = identity.session.company_name;

  return (
    <section className="mx-auto flex w-full max-w-3xl min-w-0 flex-col px-4 py-10">
      <p className="break-words text-sm text-[var(--color-text-muted)]">
        {ticker} · {company}
      </p>
      <h1 className="mt-3 break-words text-2xl font-bold text-[var(--color-text-strong)]">
        {title}
      </h1>
      <p className="mt-3 break-words text-[var(--color-text-muted)]">{description}</p>

      {/* Error Alert */}
      {fetchError && (
        <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400">
          ⚠️ {fetchError}
        </div>
      )}

      {/* Snapshot Inspector Preview (If fetched) */}
      {snapshot && (
        <div className="mt-6">
          <EvidenceInspector snapshot={snapshot} />
        </div>
      )}

      {/* 1-Click Automated Ingestion Card (when upload is needed) */}
      {canUpload && (
        <div className="mt-6 rounded-xl border border-primary/40 bg-primary/5 p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-md bg-primary/20 px-2.5 py-0.5 text-xs font-bold text-primary">
              ⚡ REKOMENDASI (1-CLICK)
            </span>
          </div>
          <h2 className="mt-3 text-lg font-bold text-foreground">
            Ambil Bukti Otomatis dari ZAPI (Pluang, IDX, Stockbit)
          </h2>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            TradePilot akan secara otomatis mengunduh harga terkini, kedalaman orderbook, riwayat 130 candle bursa, Foreign Flow harian/mingguan, dan ringkasan broker 1D dalam hitungan detik.
          </p>

          {operation === "fetching-market" || operation === "submitting-analysis" ? (
            <div className="mt-5 space-y-2.5 rounded-lg border border-primary/20 bg-background/80 p-4 font-mono text-xs">
              <div className={`flex items-center gap-2 ${acquisitionStep >= 1 ? "text-emerald-500 font-semibold" : "text-muted-foreground"}`}>
                <span>{acquisitionStep >= 1 ? "✓" : "○"}</span>
                <span>1. Mengambil Harga Terkini & Live Orderbook (Pluang)</span>
              </div>
              <div className={`flex items-center gap-2 ${acquisitionStep >= 2 ? "text-emerald-500 font-semibold" : "text-muted-foreground"}`}>
                <span>{acquisitionStep >= 2 ? "✓" : "○"}</span>
                <span>2. Mengunduh 130 Candle Bursa & Foreign Flow (IDX)</span>
              </div>
              <div className={`flex items-center gap-2 ${acquisitionStep >= 3 ? "text-emerald-500 font-semibold" : "text-muted-foreground"}`}>
                <span>{acquisitionStep >= 3 ? "✓" : "○"}</span>
                <span>3. Menganalisis Akumulasi Broker 1D (Pluang)</span>
              </div>
              <div className={`flex items-center gap-2 ${acquisitionStep >= 4 ? "text-emerald-500 font-semibold" : "text-muted-foreground"}`}>
                <span>{acquisitionStep >= 4 ? "✓" : "○"}</span>
                <span>4. Validasi Snapshot Lengkap & Memulai Analisis AI...</span>
              </div>
            </div>
          ) : (
            <button
              type="button"
              disabled={controlsLocked}
              onClick={handleAutoAcquisition}
              className="mt-5 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-[var(--color-action-primary)] px-6 text-sm font-semibold text-white shadow transition-all hover:bg-[var(--color-action-primary-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
            >
              ⚡ Ambil Bukti Otomatis & Mulai Analisa
            </button>
          )}
        </div>
      )}

      {/* Manual Upload Form */}
      {canUpload ? (
        <details className="mt-6 rounded-xl border border-border bg-card p-4">
          <summary className="cursor-pointer text-xs font-semibold text-muted-foreground hover:text-foreground">
            Atau unggah screenshot manual (Opsi Cadangan)
          </summary>
          <form
            className="mt-4 min-w-0 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void upload();
            }}
            aria-busy={controlsLocked}
          >
            {fields.map(([key, label]) => (
              <label key={key} className="block min-w-0 text-sm font-semibold">
                {label}
                <input
                  type="file"
                  accept="image/*"
                  required
                  disabled={controlsLocked}
                  onChange={(event) => select(key, event.target.files?.[0])}
                  className="mt-2 block min-h-11 w-full min-w-0 text-sm"
                />
                {files[key] ? (
                  <span className="mt-1 block break-all [overflow-wrap:anywhere] font-normal text-[var(--color-text-muted)]">
                    {files[key]?.name}
                  </span>
                ) : null}
              </label>
            ))}
            <button
              type="submit"
              disabled={controlsLocked || !complete}
              aria-busy={operation === "uploading" || operation === "reconciling"}
              className="min-h-11 w-full rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-4 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-auto"
            >
              Unggah Bukti Awal
            </button>
          </form>
        </details>
      ) : null}

      {/* Mulai Analisis Button */}
      {canSubmitAnalysis ? (
        <button
          type="button"
          onClick={() => void submitAnalysis()}
          disabled={controlsLocked}
          aria-busy={operation === "submitting-analysis" || operation === "reconciling"}
          className="mt-6 min-h-11 w-full rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-4 font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)] sm:w-fit"
        >
          Mulai Analisis Awal
        </button>
      ) : null}

      {/* Feedback Message */}
      {feedback ? (
        <p aria-live="polite" className="mt-4 min-w-0 break-words text-sm">
          {feedback}
        </p>
      ) : null}

      {/* Back Link */}
      <Link
        href={backHref}
        className="mt-8 inline-flex min-h-11 w-fit items-center font-semibold text-[var(--color-action-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
      >
        Kembali ke Ringkasan
      </Link>
    </section>
  );
}
