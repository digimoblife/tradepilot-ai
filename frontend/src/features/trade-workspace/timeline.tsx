import type { SessionDetailAggregate } from "./types";
import { safeErrorMessage } from "./safe-error";

export type TimelineEventType =
  | "INITIAL_EVIDENCE" | "INITIAL_ANALYSIS" | "WAIT_DECISION" | "WAIT_UPDATE"
  | "BUY_DECISION" | "POSITION_UPDATE" | "SKIP_DECISION" | "CLOSE";

type TimelineEvent = { id: string; type: TimelineEventType; timestamp: string | null; title: string; details: string[][] };
type RecordValue = Record<string, unknown>;

const text = (value: unknown): string => value === null || value === undefined || value === "" ? "—" : String(value);
const record = (value: unknown): RecordValue => value && typeof value === "object" ? value as RecordValue : {};
const dateValue = (value: unknown): string | null => typeof value === "string" && value ? value : null;
const formatTime = (value: string | null): string => value ? new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
const statusLabel: Record<string, string> = { PENDING: "Menunggu", PROCESSING: "Diproses", COMPLETED: "Selesai", FAILED: "Gagal" };
const reasonLabel: Record<string, string> = { RISK_TOO_HIGH: "Risiko terlalu tinggi", SETUP_NOT_ATTRACTIVE: "Setup tidak menarik", ORDERBOOK_WEAK: "Order book lemah", MARKET_CONDITION_UNFAVORABLE: "Kondisi pasar tidak mendukung", WAITING_TOO_LONG: "Menunggu terlalu lama", USER_DECISION: "Keputusan pengguna", OTHER: "Lainnya" };

function requestTimestamp(item: RecordValue): string | null {
  return dateValue(item.observation_timestamp) ?? dateValue(item.completed_at) ?? dateValue(item.created_at);
}

function summary(item: RecordValue): string | null {
  const processed = record(item.processed_response);
  for (const key of ["summary", "update_summary", "conclusion"]) {
    if (processed[key] !== undefined && processed[key] !== null) return text(processed[key]);
  }
  return null;
}

export function buildTimelineEvents(detail: SessionDetailAggregate): TimelineEvent[] {
  const events: TimelineEvent[] = [];
  const evidence = detail.initial_evidence.map(record);
  if (evidence.length) {
    const ordered = [...evidence].sort((a, b) => String(a.uploaded_at ?? "").localeCompare(String(b.uploaded_at ?? "")));
    events.push({ id: `evidence:${ordered.map((item) => text(item.id)).join(",")}`, type: "INITIAL_EVIDENCE", timestamp: dateValue(ordered[0].uploaded_at), title: "Bukti Awal Diunggah", details: ordered.map((item) => [text(item.evidence_type), `${text(item.original_filename)} · ${formatTime(dateValue(item.uploaded_at))}`]) });
  }
  const initial = record(detail.initial_analysis);
  if (Object.keys(initial).length) {
    const status = text(initial.status);
    const timestamp = dateValue(initial.completed_at) ?? dateValue(initial.created_at);
    events.push({ id: `analysis:${text(initial.request_id)}`, type: "INITIAL_ANALYSIS", timestamp, title: "Analisis Awal", details: [["Status", statusLabel[status] ?? status], ["Waktu", formatTime(timestamp)], ...(status === "FAILED" ? [["Pesan", safeErrorMessage(initial.error_message, "initial")]] : []), ...(summary(initial) ? [["Ringkasan", summary(initial)!]] : [])] });
  }
  for (const decision of detail.decisions.map(record)) {
    const kind = text(decision.decision);
    const type = kind === "WAIT" ? "WAIT_DECISION" : kind === "BUY" ? "BUY_DECISION" : "SKIP_DECISION";
    const details: string[][] = [["Waktu", formatTime(dateValue(decision.created_at))]];
    if (kind === "WAIT") details.push(["Keputusan", "WAIT"]);
    if (kind === "SKIP") { details.push(["Alasan", reasonLabel[text(decision.reason)] ?? text(decision.reason)]); details.push(["Catatan", text(decision.note)]); }
    if (kind === "BUY") {
      const position = record(detail.position);
      details.push(["Harga masuk", text(position.entry_price)], ["Jumlah", text(position.quantity)], ["Stop loss", text(position.stop_loss)], ["Target harga", text(position.target_price)], ["Catatan", text(position.note ?? decision.note)]);
    }
    events.push({ id: `decision:${text(decision.decision_id)}:${text(decision.created_at)}`, type, timestamp: dateValue(decision.created_at), title: kind === "WAIT" ? "Keputusan WAIT" : kind === "BUY" ? "Keputusan BUY" : "Keputusan SKIP", details });
  }
  for (const item of detail.wait_updates.map(record)) {
    const timestamp = requestTimestamp(item);
    events.push({ id: `wait:${text(item.request_id)}`, type: "WAIT_UPDATE", timestamp, title: "Pembaruan WAIT", details: [["Periode", text(item.observation_period)], ["Harga saat ini", text(item.current_price)], ["Waktu observasi", formatTime(dateValue(item.observation_timestamp))], ["Status", statusLabel[text(item.status)] ?? text(item.status)], ...(text(item.status) === "FAILED" ? [["Pesan", safeErrorMessage(item.error_message, "wait")]] : []), ["Catatan", text(item.note)], ...(summary(item) ? [["Ringkasan", summary(item)!]] : []), ...(record(item.evidence).original_filename ? [["Bukti", text(record(item.evidence).original_filename)]] : [])] });
  }
  for (const item of detail.position_updates.map(record)) {
    const timestamp = requestTimestamp(item);
    events.push({ id: `position-update:${text(item.request_id)}`, type: "POSITION_UPDATE", timestamp, title: "Pembaruan Posisi", details: [["Periode", text(item.observation_period)], ["Harga saat ini", text(item.current_price)], ["Waktu observasi", formatTime(dateValue(item.observation_timestamp))], ["Status", statusLabel[text(item.status)] ?? text(item.status)], ...(text(item.status) === "FAILED" ? [["Pesan", safeErrorMessage(item.error_message, "position")]] : []), ...(summary(item) ? [["Ringkasan", summary(item)!]] : []), ...(record(item.evidence).original_filename ? [["Bukti", text(record(item.evidence).original_filename)]] : [])] });
  }
  const closure = record(detail.closure);
  if (Object.keys(closure).length) events.push({ id: `close:${text(closure.closure_id)}`, type: "CLOSE", timestamp: dateValue(closure.close_timestamp) ?? dateValue(closure.created_at), title: "Posisi Ditutup", details: [["Harga tutup", text(closure.close_price)], ["Waktu", formatTime(dateValue(closure.close_timestamp))], ["Alasan", text(closure.close_reason)], ["Catatan", text(closure.note)], ["Hasil", text(closure.realized_result)]] });
  return events.map((event, index) => ({ event, index })).sort((a, b) => {
    const time = (a.event.timestamp ? new Date(a.event.timestamp).getTime() : Number.POSITIVE_INFINITY) - (b.event.timestamp ? new Date(b.event.timestamp).getTime() : Number.POSITIVE_INFINITY);
    return time || a.event.id.localeCompare(b.event.id) || a.index - b.index;
  }).map(({ event }) => event);
}

type TimelinePresentation = {
  surface: string;
  marker: string;
};

const timelinePresentation: Record<TimelineEventType, TimelinePresentation> = {
  INITIAL_EVIDENCE: {
    surface: "border-[var(--color-border-default)] bg-[var(--color-surface-factual)]",
    marker: "rounded-full border-2 border-[var(--color-border-strong)] bg-[var(--color-surface-standard)]",
  },
  INITIAL_ANALYSIS: {
    surface: "border-[var(--color-status-information)] bg-[var(--color-surface-advisory)]",
    marker: "rotate-45 rounded-[2px] border border-[var(--color-status-information)] bg-[var(--color-surface-advisory)]",
  },
  WAIT_DECISION: {
    surface: "border-[var(--color-border-default)] bg-[var(--color-surface-action)]",
    marker: "rounded-sm border-2 border-[var(--color-border-strong)] bg-[var(--color-surface-standard)]",
  },
  BUY_DECISION: {
    surface: "border-[var(--color-border-default)] bg-[var(--color-surface-action)]",
    marker: "rounded-sm border-2 border-[var(--color-border-strong)] bg-[var(--color-surface-standard)]",
  },
  SKIP_DECISION: {
    surface: "border-[var(--color-border-default)] bg-[var(--color-surface-factual)]",
    marker: "rounded-full border-2 border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface-standard)]",
  },
  WAIT_UPDATE: {
    surface: "border-[var(--color-status-information)] bg-[var(--color-surface-advisory)]",
    marker: "rounded-full border border-[var(--color-status-warning)] bg-[var(--color-status-warning-subtle)]",
  },
  POSITION_UPDATE: {
    surface: "border-[var(--color-status-information)] bg-[var(--color-surface-advisory)]",
    marker: "rounded-full border border-[var(--color-status-information)] bg-[var(--color-status-information-subtle)]",
  },
  CLOSE: {
    surface: "border-[var(--color-border-strong)] bg-[var(--color-surface-factual)]",
    marker: "rounded-full border-2 border-[var(--color-border-strong)] bg-[var(--color-surface-standard)]",
  },
};

function TimelineEventItem({ event }: { event: TimelineEvent }) {
  const presentation = timelinePresentation[event.type];
  return (
    <li className="relative min-w-0 pl-8">
      <span
        aria-hidden="true"
        className={`absolute left-[0.375rem] top-5 z-10 h-3.5 w-3.5 shadow-xs ${presentation.marker}`}
      />
      <article
        className={`min-w-0 rounded-[var(--radius-standard)] border p-[var(--space-card)] shadow-[var(--elevation-low)] ${presentation.surface}`}
      >
        <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
          <h4 className="min-w-0 break-words font-semibold text-[var(--color-text-strong)]">
            {event.title}
          </h4>
          <time
            dateTime={event.timestamp ?? undefined}
            className="min-w-0 break-words text-xs text-[var(--color-text-muted)] sm:max-w-[12rem] sm:text-right"
          >
            {formatTime(event.timestamp)}
          </time>
        </div>
        <dl className="mt-[var(--space-3)] grid min-w-0 grid-cols-1 gap-x-[var(--space-5)] gap-y-[var(--space-3)] text-[var(--text-size-compact-body)] sm:grid-cols-2">
          {event.details.map(([label, value]) => (
            <div key={`${event.id}:${label}`} className="min-w-0">
              <dt className="break-words text-[var(--text-size-label)] font-medium text-[var(--color-text-muted)]">
                {label}
              </dt>
              <dd className="mt-1 min-w-0 break-words whitespace-pre-wrap text-[var(--color-text-default)]">
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </article>
    </li>
  );
}

export function SessionTimeline({
  aggregate,
  loading,
  error,
}: {
  aggregate: SessionDetailAggregate | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading && !aggregate) {
    return (
      <section aria-label="Riwayat sesi" className="rounded-xl border border-zinc-200 bg-white p-5">
        <p className="text-zinc-500" aria-live="polite">
          Memuat riwayat sesi…
        </p>
      </section>
    );
  }
  if (error && !aggregate) {
    return (
      <section aria-label="Riwayat sesi" className="rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-red-700" role="alert">
          Gagal memuat riwayat sesi
        </p>
      </section>
    );
  }
  const events = aggregate ? buildTimelineEvents(aggregate) : [];
  return (
    <section aria-label="Riwayat sesi" className="min-w-0 space-y-3">
      <h3 className="text-lg font-semibold text-[var(--color-text-strong)]">Riwayat Sesi</h3>
      {events.length === 0 ? (
        <p className="rounded-[var(--radius-compact)] border border-[var(--color-border-default)] bg-[var(--color-surface-standard)] p-[var(--space-card)] text-[var(--color-text-muted)]">
          Belum ada riwayat sesi.
        </p>
      ) : (
        <ol
          className="relative min-w-0 space-y-[var(--space-4)] before:absolute before:bottom-2 before:left-[0.75rem] before:top-2 before:w-0.5 before:bg-[var(--color-border-strong)]"
          aria-label="Urutan riwayat sesi"
        >
          {events.map((event) => (
            <TimelineEventItem key={event.id} event={event} />
          ))}
        </ol>
      )}
    </section>
  );
}
