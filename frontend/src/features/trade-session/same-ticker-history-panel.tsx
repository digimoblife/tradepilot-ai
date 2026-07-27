"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getSameTickerHistory,
  type SameTickerHistoryResponse,
} from "@/lib/api/trade-sessions";

interface Props {
  sessionId: string;
}

export function SameTickerHistoryPanel({ sessionId }: Props) {
  const [data, setData] = useState<SameTickerHistoryResponse | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await getSameTickerHistory(sessionId);
        if (!cancelled) {
          setData(res);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setData(null);
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  if (loading || !data || !data.historical_context_used || data.historical_session_count === 0) {
    return null;
  }

  return (
    <div className="mb-4 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center rounded bg-zinc-200 px-2 py-0.5 text-[11px] font-medium text-zinc-700">
            Konteks Sekunder
          </span>
          <span className="font-medium text-zinc-700">
            Riwayat ticker digunakan: {data.historical_session_count} sesi sebelumnya
          </span>
        </div>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="font-medium text-blue-600 hover:text-blue-800 hover:underline"
        >
          {expanded ? "Sembunyikan" : "Lihat Ringkasan Riwayat"}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-zinc-200 pt-3">
          <div className="flex space-x-4 text-[11px] text-zinc-500">
            <span>Selesai (Trade): {data.completed_trade_count}</span>
            <span>Dilewati (Skipped): {data.skipped_session_count}</span>
          </div>

          {data.recent_outcomes.length > 0 && (
            <div>
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                Hasil Sesi Sebelumnya
              </div>
              <ul className="space-y-1.5">
                {data.recent_outcomes.map((item) => (
                  <li
                    key={item.session_id}
                    className="rounded border border-zinc-200 bg-white p-2 text-xs"
                  >
                    <div className="flex items-center justify-between font-medium text-zinc-800">
                      <Link
                        href={`/sessions/${item.session_id}`}
                        className="text-blue-600 hover:underline"
                      >
                        Sesi {item.session_id.slice(0, 8)}
                      </Link>
                      <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] uppercase font-semibold text-zinc-600">
                        {item.lifecycle_status}
                      </span>
                    </div>

                    <div className="mt-1 grid grid-cols-2 gap-2 text-[11px] text-zinc-600">
                      {item.entry_price && <div>Harga Masuk: Rp {item.entry_price}</div>}
                      {item.average_exit_price && <div>Harga Keluar: Rp {item.average_exit_price}</div>}
                      {item.realized_return && <div>Return: {item.realized_return}%</div>}
                    </div>

                    {item.closing_summary && (
                      <p className="mt-1 text-[11px] text-zinc-500 italic">
                        &quot;{item.closing_summary}&quot;
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.useful_lessons.length > 0 && (
            <div>
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                Pelajaran Utama
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-[11px] text-zinc-700">
                {data.useful_lessons.map((lesson, idx) => (
                  <li key={idx}>{lesson}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
