import Link from "next/link";
import type { TradeSessionSummary } from "@/types/trade-session";
import { formatTimestamp } from "./helpers";

interface Props {
  session: TradeSessionSummary;
}

export function SessionHeader({ session }: Props) {
  const displayName =
    session.company_name ?? `Saham ${session.ticker}`;

  return (
    <div className="mb-6">
      <Link
        href="/sessions"
        className="mb-3 inline-block text-sm text-blue-600 hover:underline"
      >
        &larr; Kembali ke Daftar Sesi
      </Link>
      <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
        {session.ticker}
      </h1>
      <p className="mt-0.5 text-base text-zinc-500">{displayName}</p>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-zinc-400">
        <span>{session.exchange}</span>
        <span>{session.currency}</span>
        {session.updated_at && (
          <time dateTime={session.updated_at}>
            {formatTimestamp(session.updated_at)}
          </time>
        )}
      </div>
    </div>
  );
}
