"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { hasPresentationContent, parsePresentationPayload, type AnalysisPayload } from "@/features/sessions/analysis-schema";
import { SessionDetailHeader } from "@/features/sessions/session-detail-header";
import { SessionNavigation } from "@/features/sessions/session-navigation";
import { useRouteSession } from "@/features/sessions/use-route-session";
import { getSessionDetail } from "@/features/trade-workspace/api";
import type { AnalysisType, SessionDetailAggregate } from "@/features/trade-workspace/types";

type AnalysisRecord = { id: string; type: AnalysisType; completedAt: string; payload: AnalysisPayload };
const labels: Record<AnalysisType, string> = { INITIAL_ANALYSIS: "Analisis Awal", WAIT_UPDATE: "Analisis WAIT", POSITION_UPDATE: "Analisis Posisi" };

function record(value: Record<string, unknown>, type: AnalysisType, sessionId: string): AnalysisRecord | null {
  if (value.session_id !== sessionId || value.analysis_type !== type || value.status !== "COMPLETED" || typeof value.request_id !== "string" || typeof value.completed_at !== "string") return null;
  const date = new Date(value.completed_at);
  if (Number.isNaN(date.getTime())) return null;
  const payload = parsePresentationPayload(type, value.processed_response);
  return payload ? { id: value.request_id, type, completedAt: value.completed_at, payload } : null;
}

function collect(detail: SessionDetailAggregate): AnalysisRecord[] {
  const sessionId = detail.session.id;
  return [
    ...(detail.initial_analysis ? [record(detail.initial_analysis, "INITIAL_ANALYSIS", sessionId)] : []),
    ...detail.wait_updates.map((item) => record(item, "WAIT_UPDATE", sessionId)),
    ...detail.position_updates.map((item) => record(item, "POSITION_UPDATE", sessionId)),
  ]
    .filter((item): item is AnalysisRecord => item !== null)
    .sort((a, b) => {
      const diff = new Date(b.completedAt).getTime() - new Date(a.completedAt).getTime();
      if (diff !== 0) return diff;
      return b.id.localeCompare(a.id);
    });
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function scalar(value: unknown): string | null {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : text(value);
}

function payloadObject(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function TextSection({ title, value }: { title: string; value: unknown }) {
  const content = text(value);
  return content ? (
    <section className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 shadow-xs sm:p-6">
      <h3 className="break-words text-base font-bold text-[var(--color-text-strong)] sm:text-lg">{title}</h3>
      <p className="mt-2.5 break-words whitespace-pre-wrap text-sm leading-relaxed text-[var(--color-text-default)]">{content}</p>
    </section>
  ) : null;
}

function ValueRow({ label, value }: { label: string; value: unknown }) {
  const content = scalar(value);
  return content ? (
    <div className="min-w-0 rounded-[var(--radius-compact)] bg-[var(--color-surface-factual)] border border-[var(--color-border-default)] p-3">
      <dt className="break-words text-xs font-medium text-[var(--color-text-muted)]">{label}</dt>
      <dd className="mt-0.5 break-words text-base font-bold text-[var(--color-text-strong)] whitespace-pre-wrap">{content}</dd>
    </div>
  ) : null;
}

function ListSection({ title, value }: { title: string; value: unknown }) {
  const items = Array.isArray(value) ? value.map(text).filter((item): item is string => item !== null) : [];
  return items.length ? (
    <section className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 shadow-xs sm:p-6">
      <h3 className="break-words text-base font-bold text-[var(--color-text-strong)] sm:text-lg">{title}</h3>
      <ul className="mt-3 list-disc space-y-2 break-words pl-5 text-sm leading-relaxed text-[var(--color-text-default)]">
        {items.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}
      </ul>
    </section>
  ) : null;
}

function RangeSection({ title, value }: { title: string; value: unknown }) {
  const range = payloadObject(value);
  if (!range) return null;
  const low = scalar(range.low); const high = scalar(range.high); const note = text(range.note);
  if (!low && !high && !note) return null;
  return (
    <section className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 shadow-xs sm:p-6">
      <h3 className="break-words text-base font-bold text-[var(--color-text-strong)] sm:text-lg">{title}</h3>
      <dl className="mt-3 grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
        <ValueRow label="Batas bawah" value={range.low} />
        <ValueRow label="Batas atas" value={range.high} />
      </dl>
      {note ? <p className="mt-3 break-words whitespace-pre-wrap text-sm leading-relaxed text-[var(--color-text-default)]">{note}</p> : null}
    </section>
  );
}

function LevelSection({ title, value }: { title: string; value: unknown }) {
  const level = payloadObject(value);
  if (!level) return null;
  const amount = scalar(level.level); const note = text(level.note);
  if (!amount && !note) return null;
  return (
    <section className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 shadow-xs sm:p-6">
      <h3 className="break-words text-base font-bold text-[var(--color-text-strong)] sm:text-lg">{title}</h3>
      <dl className="mt-3">
        <ValueRow label="Level" value={level.level} />
      </dl>
      {note ? <p className="mt-3 break-words whitespace-pre-wrap text-sm leading-relaxed text-[var(--color-text-default)]">{note}</p> : null}
    </section>
  );
}

function FlowSection({ title, value }: { title: string; value: unknown }) {
  const flow = payloadObject(value);
  if (!flow || !text(flow.assessment) || !text(flow.analysis)) return null;
  return (
    <section className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 shadow-xs sm:p-6">
      <h3 className="break-words text-base font-bold text-[var(--color-text-strong)] sm:text-lg">{title}</h3>
      <dl className="mt-3">
        <ValueRow label="Penilaian" value={flow.assessment} />
      </dl>
      <p className="mt-3 break-words whitespace-pre-wrap text-sm leading-relaxed text-[var(--color-text-default)]">{text(flow.analysis)}</p>
    </section>
  );
}

function InitialAnalysisRenderer({ payload }: { payload: AnalysisPayload }) {
  const probabilities = payloadObject(payload.probabilities);
  return (
    <div className="min-w-0 space-y-6">
      <TextSection title="Ringkasan" value={payload.summary} />
      <TextSection title="Analisis Orderbook" value={payload.orderbook_analysis} />
      <div className="grid min-w-0 grid-cols-1 gap-6 sm:grid-cols-2">
        <TextSection title="Analisis Grafik 3 Bulan" value={payload.three_month_chart_analysis} />
        <TextSection title="Analisis Grafik 6 Bulan" value={payload.six_month_chart_analysis} />
      </div>
      <FlowSection title="Analisa Foreign Flow" value={payload.foreign_flow_analysis} />
      <div className="grid min-w-0 grid-cols-1 gap-6 sm:grid-cols-3">
        <RangeSection title="Support" value={payload.support} />
        <RangeSection title="Area Entry" value={payload.entry_area} />
        <RangeSection title="Resistance" value={payload.resistance} />
      </div>
      <div className="grid min-w-0 grid-cols-1 gap-6 sm:grid-cols-2">
        <LevelSection title="Rekomendasi Stop Loss" value={payload.stop_recommendation} />
        <LevelSection title="Rekomendasi Target" value={payload.target_recommendation} />
      </div>
      {probabilities ? (
        <section className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 shadow-xs sm:p-6">
          <h3 className="break-words text-base font-bold text-[var(--color-text-strong)] sm:text-lg">Probabilitas</h3>
          <dl className="mt-3 grid min-w-0 gap-3 sm:grid-cols-2">
            <ValueRow label="Potensi naik" value={probabilities.upside} />
            <ValueRow label="Potensi turun" value={probabilities.downside} />
          </dl>
        </section>
      ) : null}
      <ListSection title="Risiko" value={payload.risks} />
      <TextSection title="Rencana Trading" value={payload.trading_plan} />
      <TextSection title="Kesimpulan" value={payload.conclusion} />
    </div>
  );
}

function WaitUpdateRenderer({ payload }: { payload: AnalysisPayload }) {
  return (
    <div className="min-w-0 space-y-6">
      <TextSection title="Ringkasan Pembaruan" value={payload.update_summary} />
      <dl className="min-w-0">
        <ValueRow label="Harga saat ini" value={payload.current_price} />
      </dl>
      <TextSection title="Penilaian Orderbook" value={payload.orderbook_assessment} />
      <FlowSection title="Analisa Broker Flow" value={payload.broker_flow_analysis} />
      <TextSection title="Perubahan dari Analisis Sebelumnya" value={payload.change_from_previous_analysis} />
      <TextSection title="Kondisi Entry Saat Ini" value={payload.current_entry_condition} />
      <section className="min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-5 shadow-xs sm:p-6">
        <h3 className="break-words text-base font-bold text-[var(--color-text-strong)] sm:text-lg">Probabilitas</h3>
        <dl className="mt-3 grid min-w-0 gap-3 sm:grid-cols-2">
          <ValueRow label="Potensi naik" value={payload.upside_probability} />
          <ValueRow label="Potensi turun" value={payload.downside_probability} />
        </dl>
      </section>
      <ListSection title="Risiko Utama" value={payload.key_risks} />
      <dl>
        <ValueRow label="Rekomendasi" value={payload.recommended_action} />
      </dl>
      <TextSection title="Rencana Berikutnya" value={payload.next_plan} />
      <TextSection title="Kesimpulan" value={payload.conclusion} />
    </div>
  );
}

function PositionUpdateRenderer({ payload }: { payload: AnalysisPayload }) {
  return (
    <div className="min-w-0 space-y-6">
      <TextSection title="Ringkasan Pembaruan" value={payload.update_summary} />
      <dl>
        <ValueRow label="Harga saat ini" value={payload.current_price} />
      </dl>
      <TextSection title="Kondisi Posisi" value={payload.position_condition} />
      <TextSection title="Penilaian Orderbook" value={payload.orderbook_assessment} />
      <FlowSection title="Analisa Broker Flow" value={payload.broker_flow_analysis} />
      <TextSection title="Perubahan dari Analisis Sebelumnya" value={payload.change_from_previous_analysis} />
      <TextSection title="Realisme Target" value={payload.target_realism} />
      <TextSection title="Risiko Penurunan" value={payload.downside_risk} />
      <dl>
        <ValueRow label="Probabilitas Target" value={payload.target_probability} />
      </dl>
      <TextSection title="Rencana Trading" value={payload.trading_plan} />
      <ListSection title="Poin Pemantauan" value={payload.monitoring_points} />
      <ListSection title="Peringatan" value={payload.warnings} />
      <TextSection title="Kesimpulan" value={payload.conclusion} />
    </div>
  );
}

function AnalysisRenderer({ record: selected }: { record: AnalysisRecord }) {
  if (selected.type === "INITIAL_ANALYSIS") return <InitialAnalysisRenderer payload={selected.payload} />;
  if (selected.type === "WAIT_UPDATE") return <WaitUpdateRenderer payload={selected.payload} />;
  return <PositionUpdateRenderer payload={selected.payload} />;
}

export function SessionAnalysisView({ sessionId }: { sessionId: string }) {
  const identity = useRouteSession(sessionId);
  const generation = useRef(0);
  const activeControllerRef = useRef<AbortController | null>(null);
  const [records, setRecords] = useState<AnalysisRecord[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const current = ++generation.current;
    const controller = new AbortController();
    activeControllerRef.current?.abort();
    activeControllerRef.current = controller;

    // URL identity reset prevents stale Session A analysis from rendering under Session B.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRecords(null);
    setSelected(null);
    setFailed(false);

    void getSessionDetail(sessionId, controller.signal)
      .then((detail) => {
        if (controller.signal.aborted || current !== generation.current) return;
        const next = collect(detail);
        setRecords(next);
        setSelected(next[0]?.id ?? null);
      })
      .catch(() => {
        if (!controller.signal.aborted && current === generation.current) {
          setFailed(true);
        }
      });

    return () => {
      controller.abort();
    };
  }, [sessionId]);

  const reloadAnalysis = useCallback(() => {
    const current = ++generation.current;
    const controller = new AbortController();
    activeControllerRef.current?.abort();
    activeControllerRef.current = controller;

    setRecords(null);
    setSelected(null);
    setFailed(false);

    void getSessionDetail(sessionId, controller.signal)
      .then((detail) => {
        if (controller.signal.aborted || current !== generation.current) return;
        const next = collect(detail);
        setRecords(next);
        setSelected(next[0]?.id ?? null);
      })
      .catch(() => {
        if (!controller.signal.aborted && current === generation.current) {
          setFailed(true);
        }
      });
  }, [sessionId]);

  if (identity.status === "loading") {
    return (
      <main className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-8 sm:px-6 lg:px-8">
        <p role="status" className="text-sm text-[var(--color-text-muted)]">
          Memuat konteks sesi…
        </p>
      </main>
    );
  }

  if (identity.status === "not-found") {
    return (
      <main className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-8 sm:px-6 lg:px-8">
        <p role="alert" className="break-words text-sm text-[var(--color-status-danger)]">
          Sesi tidak ditemukan atau tidak dapat diakses.
        </p>
      </main>
    );
  }

  if (identity.status === "authentication-required") {
    return (
      <main className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-8 sm:px-6 lg:px-8">
        <div role="alert" className="text-sm text-[var(--color-status-danger)]">
          <p>Sesi Anda telah berakhir. Silakan masuk kembali.</p>
        </div>
      </main>
    );
  }

  if (identity.status === "error") {
    return (
      <main className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 py-8 sm:px-6 lg:px-8">
        <p role="alert" className="break-words text-sm text-[var(--color-status-danger)]">
          Konteks sesi tidak dapat dimuat. Silakan periksa kembali.
        </p>
      </main>
    );
  }

  const current = records?.find((item) => item.id === selected) ?? records?.[0] ?? null;
  const currentHasContent = current ? hasPresentationContent(current.type, current.payload) : false;

  return (
    <>
      <SessionDetailHeader session={identity.session} />
      <SessionNavigation sessionId={sessionId} />
      <main className="mx-auto w-full min-w-0 max-w-[var(--layout-application-max)] px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="break-words text-2xl font-bold text-[var(--color-text-strong)]">Analisis</h1>

        {records === null && !failed ? (
          <p role="status" className="mt-4 text-sm text-[var(--color-text-muted)]">
            Memuat analisis…
          </p>
        ) : null}

        {failed ? (
          <section
            role="alert"
            className="mt-5 min-w-0 rounded-[var(--radius-large)] border border-[var(--color-status-danger)] bg-[var(--color-status-danger-subtle)] p-4 sm:p-6"
          >
            <h2 className="break-words text-xl font-bold text-[var(--color-status-danger)]">
              Analisis belum dapat dimuat
            </h2>
            <p className="mt-2 break-words text-sm text-[var(--color-text-default)]">
              Data analisis belum dapat dimuat. Silakan periksa kembali.
            </p>
            <button
              type="button"
              onClick={() => reloadAnalysis()}
              className="mt-4 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-compact)] bg-[var(--color-action-primary)] px-4 text-sm font-semibold text-[var(--color-text-inverse)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              Muat Ulang
            </button>
          </section>
        ) : null}

        {records?.length === 0 ? (
          <section className="mt-5 min-w-0 rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-4 sm:p-6">
            <h2 className="break-words text-xl font-bold text-[var(--color-text-strong)]">
              Belum ada analisis
            </h2>
            <p className="mt-2 break-words text-sm text-[var(--color-text-muted)]">
              Belum ada hasil analisis yang tersedia untuk sesi ini.
            </p>
          </section>
        ) : null}

        {records?.length ? (
          <div className="mt-5 grid min-w-0 gap-6 lg:grid-cols-[minmax(0,18rem)_minmax(0,1fr)]">
            <nav aria-label="Pilihan analisis" className="min-w-0">
              <ul className="flex min-w-0 gap-2 overflow-x-auto pb-2 lg:flex-col lg:overflow-x-visible lg:pb-0">
                {records.map((item, index) => {
                  const isLatest = index === 0;
                  const isSelected = current?.id === item.id;
                  return (
                    <li key={item.id} className="min-w-[14rem] shrink-0 lg:min-w-0 lg:shrink">
                      <button
                        type="button"
                        onClick={() => setSelected(item.id)}
                        aria-pressed={isSelected}
                        className={`min-h-11 w-full min-w-0 rounded-[var(--radius-standard)] border p-3 text-left transition-colors outline-offset-2 focus-visible:outline-2 focus-visible:outline-ring ${
                          isSelected
                            ? "border-[var(--color-action-primary)] bg-[var(--color-action-primary-subtle)] font-medium shadow-xs"
                            : "border-[var(--color-border-default)] bg-[var(--color-surface-standard)] hover:bg-[var(--color-surface-muted)]"
                        }`}
                      >
                        <span className="block break-words font-semibold text-[var(--color-text-strong)]">
                          {labels[item.type]}
                          {isLatest ? " · Terbaru" : ""}
                        </span>
                        <span className="mt-1 block break-words text-xs text-[var(--color-text-muted)]">
                          {new Intl.DateTimeFormat("id-ID", {
                            dateStyle: "medium",
                            timeStyle: "short",
                          }).format(new Date(item.completedAt))}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </nav>
            <article
              aria-live="polite"
              className="min-w-0 max-w-3xl rounded-[var(--radius-large)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-4 shadow-[var(--elevation-low)] sm:p-6"
            >
              <h2 className="break-words text-xl font-bold text-[var(--color-text-strong)]">
                {current && currentHasContent
                  ? labels[current.type]
                  : "Hasil analisis tidak dapat ditampilkan"}
              </h2>
              {current && currentHasContent ? (
                <>
                  <p className="mt-2 break-words text-sm text-[var(--color-text-muted)]">
                    {new Intl.DateTimeFormat("id-ID", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }).format(new Date(current.completedAt))}
                  </p>
                  <div className="mt-6 min-w-0">
                    <AnalysisRenderer record={current} />
                  </div>
                </>
              ) : (
                <p className="mt-2 text-sm text-[var(--color-text-muted)]">
                  Data analisis ini belum dapat ditampilkan dengan baik.
                </p>
              )}
            </article>
          </div>
        ) : null}
      </main>
    </>
  );
}
