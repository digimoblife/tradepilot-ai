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

export function SessionTimeline({ aggregate, loading, error }: { aggregate: SessionDetailAggregate | null; loading: boolean; error: string | null }) {
  if (loading && !aggregate) return <section aria-label="Riwayat sesi" className="rounded-xl border border-zinc-200 bg-white p-5"><p className="text-zinc-500" aria-live="polite">Memuat riwayat sesi…</p></section>;
  if (error && !aggregate) return <section aria-label="Riwayat sesi" className="rounded-xl border border-red-200 bg-red-50 p-5"><p className="text-red-700" role="alert">Gagal memuat riwayat sesi</p></section>;
  const events = aggregate ? buildTimelineEvents(aggregate) : [];
  return <section aria-label="Riwayat sesi" className="space-y-3"><h3 className="text-lg font-semibold">Riwayat Sesi</h3>{events.length === 0 ? <p className="rounded-xl border border-zinc-200 bg-white p-5 text-zinc-500">Belum ada riwayat sesi.</p> : <div className="space-y-3 border-l-2 border-zinc-200 pl-4">{events.map((event) => <article key={event.id} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-2"><h4 className="font-semibold">{event.title}</h4><time className="text-xs text-zinc-500">{formatTime(event.timestamp)}</time></div><dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">{event.details.map(([label, value]) => <div key={`${event.id}:${label}`}><dt className="font-medium text-zinc-500">{label}</dt><dd className="whitespace-pre-wrap break-words text-zinc-700">{value}</dd></div>)}</dl></article>)}</div>}</section>;
}
