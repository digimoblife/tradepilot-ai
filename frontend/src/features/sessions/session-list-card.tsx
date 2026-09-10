"use client";

import { SessionCardOpenLink } from "./session-card-open-link";
import { useSessionIntelligence } from "./use-session-intelligence";
import { StatusBadge } from "@/components/ui";
import type {
  SessionStatus,
  TradeSessionListItem,
} from "@/features/trade-workspace/types";

type StatusPresentation = {
  label: string;
  nextStage: string;
  badgeClassName: string;
  dotClassName: string;
};

export const SESSION_STATUS_PRESENTATIONS = {
  DRAFT: {
    label: "Sesi Baru",
    nextStage: "Mulai atau lanjutkan Bukti Awal.",
    badgeClassName: "border-slate-200 bg-slate-100 text-slate-700",
    dotClassName: "bg-slate-400",
  },
  ANALYZING: {
    label: "Sedang Diproses",
    nextStage: "Analisis Awal sedang diproses. Tunggu hingga proses selesai.",
    badgeClassName: "border-blue-200 bg-blue-50 text-blue-700",
    dotClassName: "bg-blue-500 animate-pulse",
  },
  ANALYZED: {
    label: "Menunggu Keputusan",
    nextStage: "Tinjau Analisis Awal, lalu pilih BUY, WAIT, atau SKIP.",
    badgeClassName: "border-amber-300 bg-amber-50 text-amber-700",
    dotClassName: "bg-amber-500 animate-ping",
  },
  WAITING: {
    label: "Menunggu",
    nextStage: "Tinjau hasil terbaru atau kirim Pembaruan WAIT.",
    badgeClassName: "border-indigo-200 bg-indigo-50 text-indigo-700",
    dotClassName: "bg-indigo-500",
  },
  OPEN_POSITION: {
    label: "Posisi Terbuka",
    nextStage: "Pantau posisi, kirim Pembaruan Posisi, atau tutup sesi.",
    badgeClassName: "border-emerald-300 bg-emerald-50 text-emerald-700",
    dotClassName: "bg-emerald-500",
  },
  CLOSED: {
    label: "Selesai",
    nextStage: "Tinjau sesi perdagangan yang telah selesai.",
    badgeClassName: "border-emerald-200 bg-emerald-50 text-emerald-700",
    dotClassName: "bg-emerald-500",
  },
  CLOSED_SKIPPED: {
    label: "Dilewati",
    nextStage: "Tinjau sesi yang dilewati tanpa membuka posisi.",
    badgeClassName: "border-slate-300 bg-slate-100 text-slate-700",
    dotClassName: "bg-slate-400",
  },
} satisfies Record<SessionStatus, StatusPresentation>;

const UNKNOWN_STATUS_PRESENTATION: StatusPresentation = {
  label: "Status tidak dikenali",
  nextStage: "Buka sesi untuk meninjau status terbaru.",
  badgeClassName: "border-slate-300 bg-slate-100 text-slate-700",
  dotClassName: "bg-slate-400",
};

const UPDATED_AT_FORMATTER = new Intl.DateTimeFormat("id-ID", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function sessionStatusPresentation(status: string): StatusPresentation {
  return SESSION_STATUS_PRESENTATIONS[status as SessionStatus] ?? UNKNOWN_STATUS_PRESENTATION;
}

export function formatSessionUpdatedAt(value: string): string | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : UPDATED_AT_FORMATTER.format(date);
}

export function SessionListCard({ session }: { session: TradeSessionListItem }) {
  const status = sessionStatusPresentation(session.status);
  const updatedAt = formatSessionUpdatedAt(session.updated_at);
  const { data: intel } = useSessionIntelligence(session.id, session.status as SessionStatus);

  const initialLetter = session.ticker ? session.ticker.charAt(0).toUpperCase() : "S";

  const avatarColors: Record<string, { bg: string; border: string; text: string }> = {
    B: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700" },
    N: { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700" },
    P: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700" },
  };
  const avatarColor = avatarColors[initialLetter] || {
    bg: "bg-slate-100",
    border: "border-slate-200",
    text: "text-slate-700",
  };

  const priceDisplay = intel?.currentPrice !== null && intel?.currentPrice !== undefined
    ? `Rp ${intel.currentPrice.toLocaleString("id-ID")}`
    : "Rp —";

  const changePct = intel?.priceChangePercent;
  const isPositiveChange = typeof changePct === "number" && changePct >= 0;

  const orderbookDepthRatio = intel?.orderbookDepthRatio;
  const depthDisplay = typeof orderbookDepthRatio === "number"
    ? `${orderbookDepthRatio.toFixed(2)}x`
    : "—";
  const depthLabel = intel?.orderbookDepthLabel || (session.status === "DRAFT" ? "(Menunggu Data)" : "(Seimbang)");

  const bandarDisplay = intel?.bandarStatus || intel?.foreignStatus || (session.status === "DRAFT" ? "Menunggu Bukti" : "Netral");

  const recommendation = intel?.recommendation || "WAIT";
  const convictionScore = intel?.convictionScore !== null && intel?.convictionScore !== undefined
    ? `${intel.convictionScore}%`
    : "—";

  const recBadgeClass = recommendation === "BUY"
    ? "bg-emerald-100 text-emerald-700 border-emerald-200"
    : recommendation === "SKIP"
    ? "bg-rose-100 text-rose-700 border-rose-200"
    : "bg-amber-100 text-amber-800 border-amber-200";

  return (
    <article
      className="group min-w-0 bg-white rounded-2xl border border-slate-200 p-5 shadow-xs transition-all duration-200 hover:border-slate-300 hover:shadow-md sm:p-6"
      data-purpose={`session-card-${session.ticker.toLowerCase()}`}
    >
      <div className="grid min-w-0 gap-4 sm:grid-cols-[minmax(0,1fr)_auto]">
        <div className="min-w-0 space-y-4">
          {/* Header row: Avatar, Ticker, Badges */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div
              className={`w-10 h-10 sm:w-11 sm:h-11 rounded-xl border flex items-center justify-center font-black text-base font-mono shrink-0 ${avatarColor.bg} ${avatarColor.border} ${avatarColor.text}`}
            >
              {initialLetter}
            </div>
            <h3 className="break-all text-xl sm:text-2xl font-black tracking-tight text-slate-900 font-mono">
              {session.ticker}
            </h3>
            <StatusBadge
              status={session.status}
              label={status.label}
              badgeClassName={status.badgeClassName}
              dotClassName={status.dotClassName}
            />
            {intel?.indexTag && (
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600">
                {intel.indexTag}
              </span>
            )}
            {intel?.sector && (
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600">
                {intel.sector}
              </span>
            )}
          </div>

          <p className="mt-1 [overflow-wrap:anywhere] text-sm font-medium text-slate-500">
            {session.company_name}
          </p>

          {/* Quick Intelligence Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3 bg-slate-50/80 p-3 rounded-xl border border-slate-100 font-mono text-xs">
            {/* Metric 1: Harga Saat Ini */}
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Harga Saat Ini
              </span>
              <div className="flex items-baseline gap-1.5 flex-wrap">
                <span className="font-bold text-slate-900 text-sm font-mono">
                  {priceDisplay}
                </span>
                {typeof changePct === "number" && (
                  <span
                    className={`text-[10px] sm:text-[11px] font-bold px-1 rounded ${
                      isPositiveChange
                        ? "text-emerald-600 bg-emerald-50"
                        : "text-rose-600 bg-rose-50"
                    }`}
                  >
                    {isPositiveChange ? `+${changePct.toFixed(2)}%` : `${changePct.toFixed(2)}%`}
                  </span>
                )}
              </div>
            </div>

            {/* Metric 2: Orderbook Depth */}
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Orderbook Depth
              </span>
              <div className="flex items-baseline gap-1.5 flex-wrap">
                <span className="font-bold text-slate-800 font-mono">
                  {depthDisplay}
                </span>
                <span className="text-[10px] text-slate-500 font-sans font-medium">
                  {depthLabel}
                </span>
              </div>
            </div>

            {/* Metric 3: Arus Dana / Bandar */}
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Status Bandar / Asing
              </span>
              <div className="flex items-baseline gap-1.5">
                <span className="font-bold font-sans uppercase text-[11px] text-slate-700 truncate">
                  {bandarDisplay}
                </span>
              </div>
            </div>

            {/* Metric 4: Sinyal AI Gemini */}
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Sinyal AI Gemini
              </span>
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className={`px-2 py-0.5 rounded text-[11px] font-extrabold border uppercase ${recBadgeClass}`}>
                  {recommendation}
                </span>
                <span className="text-[11px] text-slate-500 font-sans font-medium">
                  Conviction: <strong className="font-mono text-slate-700">{convictionScore}</strong>
                </span>
              </div>
            </div>
          </div>

          {/* Workflow Next Step Banner */}
          <div className="rounded-xl bg-slate-50 border border-slate-200/90 px-3.5 py-2.5 sm:px-4 sm:py-3 text-xs text-slate-700 flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-blue-600 shrink-0"></div>
            <p className="leading-relaxed">
              <span className="font-semibold text-slate-900">Tahap berikutnya: </span>
              <span className="break-words text-slate-600">{status.nextStage}</span>
            </p>
          </div>
        </div>

        {/* Right side: Timestamp & Action button */}
        <div className="flex min-w-0 flex-col items-start gap-4 sm:items-end sm:justify-between sm:pl-4">
          <p className="max-w-full break-words text-xs text-slate-500 sm:text-right">
            Diperbarui:{" "}
            {updatedAt ? (
              <time dateTime={session.updated_at} className="font-medium text-slate-700">
                {updatedAt}
              </time>
            ) : (
              <span>waktu tidak tersedia</span>
            )}
          </p>
          <SessionCardOpenLink
            href={`/sessions/${session.id}`}
            className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 text-sm font-bold text-white shadow-xs transition-all hover:bg-blue-700 active:scale-[0.98] sm:w-auto"
          >
            <span>Buka Sesi</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
              <path d="m8.25 4.5 7.5 7.5-7.5 7.5" strokeLinecap="round" strokeLinejoin="round"></path>
            </svg>
          </SessionCardOpenLink>
        </div>
      </div>
    </article>
  );
}
