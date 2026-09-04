"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { readInitialAnalysis, retryInitialAnalysis } from "@/features/trade-workspace/api";
import type { CurrentStep, InitialAnalysisRead } from "@/features/trade-workspace/types";
import { ButtonSpinner } from "@/components/button-spinner";

const POLL_MS = 5_000;
type Presentation = "IDLE" | "PROCESSING" | "FAILED_RETRY_AVAILABLE" | "FAILED_READ_ONLY" | "COMPLETED" | "UNAVAILABLE";

function presentationOf(request: InitialAnalysisRead, step: CurrentStep, requestId: string | null): Presentation {
  if (!requestId || request.analysis_request_id !== requestId || request.session_id === "") return "UNAVAILABLE";
  if (request.analysis_type !== "INITIAL_ANALYSIS") return "UNAVAILABLE";
  if (request.request_status === "PENDING" || request.request_status === "PROCESSING") return "PROCESSING";
  if (request.request_status === "COMPLETED") return "COMPLETED";
  if (request.request_status === "FAILED") return step.workflow_actions.length === 1 && step.workflow_actions[0] === "RETRY_INITIAL_ANALYSIS" && !step.read_only ? "FAILED_RETRY_AVAILABLE" : "FAILED_READ_ONLY";
  return "UNAVAILABLE";
}

export function InitialAnalysisRecovery({ sessionId, step, refetch }: { sessionId: string; step: CurrentStep; refetch: () => Promise<unknown> }) {
  const [request, setRequest] = useState<InitialAnalysisRead | null>(null);
  const [readFailed, setReadFailed] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [recoveryNonce, setRecoveryNonce] = useState(0);
  const generation = useRef(0);
  const inFlight = useRef(false);
  const retryInFlight = useRef(false);
  const mounted = useRef(true);
  const active = step.active_request;
  const failed = step.failed_request;
  const candidate = active?.analysis_type === "INITIAL_ANALYSIS" ? active : failed?.analysis_type === "INITIAL_ANALYSIS" ? failed : null;
  const shouldRecover = candidate !== null;

  useEffect(() => () => { mounted.current = false; }, []);

  useEffect(() => {
    if (!shouldRecover) return;
    const current = ++generation.current;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | null = null;
    const poll = async () => {
      if (inFlight.current || current !== generation.current) return;
      inFlight.current = true;
      try {
        const next = await readInitialAnalysis(sessionId, controller.signal);
        if (current !== generation.current) return;
        if (next.session_id !== sessionId || next.analysis_type !== "INITIAL_ANALYSIS" || next.analysis_request_id !== candidate?.id) { setReadFailed(true); return; }
        setRequest(next); setReadFailed(false);
        if (next.request_status === "COMPLETED" || next.request_status === "FAILED") { await refetch(); return; }
      } catch {
        if (current !== generation.current || controller.signal.aborted) return;
        setReadFailed(true); return;
      } finally { inFlight.current = false; }
      if (current === generation.current && !controller.signal.aborted) timer = setTimeout(() => void poll(), POLL_MS);
    };
    void poll();
    return () => { generation.current += 1; controller.abort(); if (timer) clearTimeout(timer); };
  }, [candidate?.id, recoveryNonce, refetch, sessionId, shouldRecover]);

  const state = request ? presentationOf(request, step, candidate?.id ?? null) : shouldRecover ? "PROCESSING" : "IDLE";
  const retry = async () => {
    if (retryInFlight.current || state !== "FAILED_RETRY_AVAILABLE") return;
    retryInFlight.current = true; setRetrying(true);
    const current = generation.current;
    try {
      await retryInitialAnalysis(sessionId);
      if (!mounted.current || current !== generation.current) return;
      await refetch();
      if (mounted.current && current === generation.current) { setRequest(null); setRecoveryNonce((value) => value + 1); }
    } catch {
      if (mounted.current && current === generation.current) setReadFailed(true);
    } finally {
      if (mounted.current && current === generation.current) { retryInFlight.current = false; setRetrying(false); }
    }
  };
  if (state === "IDLE") return null;
  if (readFailed) return <section aria-live="polite" className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8"><h2 className="text-xl font-bold">Status Analisis Awal belum tersedia</h2><p className="mt-2 break-words">Status terbaru belum dapat dikonfirmasi. Muat ulang halaman untuk memeriksa kembali.</p></section>;
  if (state === "PROCESSING") return <section aria-live="polite" aria-busy="true" className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8"><h2 className="text-xl font-bold">Analisis Awal sedang diproses</h2><p className="mt-2 break-words">Permintaan Analisis Awal telah diterima. Anda dapat meninggalkan halaman ini dan kembali lagi tanpa membuat permintaan baru.</p><p className="mt-2 break-words text-sm">Status akan diperbarui secara otomatis selama halaman ini terbuka.</p></section>;
  if (state === "COMPLETED") return <section aria-live="polite" className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8"><h2 className="text-xl font-bold">Analisis Awal selesai</h2><p className="mt-2">Hasil Analisis Awal sudah tersedia.</p><Link href={`/sessions/${encodeURIComponent(sessionId)}/analysis`} className="mt-4 inline-flex min-h-11 items-center font-semibold text-[var(--color-action-primary)]">Lihat Analisis</Link></section>;
  return <section aria-live="polite" className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8"><h2 className="text-xl font-bold">Analisis Awal gagal diproses</h2><p className="mt-2 break-words">Permintaan Analisis Awal tidak dapat diselesaikan. Silakan coba lagi jika tindakan ulang tersedia.</p>{state === "FAILED_RETRY_AVAILABLE" ? <button type="button" disabled={retrying} aria-busy={retrying} onClick={() => void retry()} className="mt-4 inline-flex items-center gap-2 min-h-11 rounded px-4 font-semibold active:scale-[0.98] transition-all">{retrying && <ButtonSpinner className="h-4 w-4" />}Coba Analisis Lagi</button> : null}</section>;
}
