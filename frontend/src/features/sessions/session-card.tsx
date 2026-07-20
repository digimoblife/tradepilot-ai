import Link from "next/link";
import type { TradeSessionSummary } from "@/types/trade-session";
import { formatTimestamp, statusLabel } from "./helpers";

interface Props {
  session: TradeSessionSummary;
}

export function SessionCard({ session }: Props) {
  const displayName =
    session.company_name ?? `Saham ${session.ticker}`;

  return (
    <Link
      href={`/sessions/${session.id}`}
      className="block rounded-lg border border-zinc-200 bg-white p-4 shadow-sm transition hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-semibold text-zinc-900">
            {session.ticker}
          </h3>
          <p className="mt-0.5 truncate text-sm text-zinc-500">
            {displayName}
          </p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-zinc-400">
            <span>{session.exchange}</span>
            <span>{session.currency}</span>
            {session.updated_at && (
              <time dateTime={session.updated_at}>
                {formatTimestamp(session.updated_at)}
              </time>
            )}
          </div>
        </div>
        <span className="shrink-0 rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-700">
          {statusLabel(session.lifecycle_status)}
        </span>
      </div>
    </Link>
  );
}
