"use client";

import { useState } from "react";
import type { EvidenceSnapshot } from "@/types/market-evidence";

interface Props {
  snapshot: EvidenceSnapshot;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export function EvidenceInspector({ snapshot, onRefresh, isRefreshing = false }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const q = snapshot.quote;
  const ob = snapshot.orderbook;
  const ff = snapshot.foreign_flow;
  const bf = snapshot.broker_flow;
  const tech = snapshot.historical_ohlcv.computed_technical;

  const isBullishChange = q.change >= 0;
  const isBidDom = ob.bid_ask_ratio >= 1.0;
  const isForeignAccum = ff.foreign_status.includes("ACCUMULATION");
  const isBandarAccum = bf.bandar_status.includes("ACCUMULATION");

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      {/* Header Info */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
              ⚡ System-Acquired Evidence
            </span>
            <span className="text-xs text-muted-foreground">
              ID: <code className="font-mono">{snapshot.snapshot_id}</code>
            </span>
          </div>
          <h3 className="mt-1 text-base font-semibold text-foreground">
            Snapshot Pasar {snapshot.symbol} •{" "}
            <span className="text-xs font-normal text-muted-foreground">
              {new Date(snapshot.captured_at).toLocaleTimeString("id-ID", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}{" "}
              WIB
            </span>
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-accent disabled:opacity-50"
            >
              <span className={isRefreshing ? "animate-spin" : ""}>🔄</span>
              {isRefreshing ? "Memperbarui..." : "Refresh Data Pasar"}
            </button>
          )}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <span>{isOpen ? "Tutup Detail" : "🔍 Detail Bukti"}</span>
          </button>
        </div>
      </div>

      {/* Snapshot Metric Badges */}
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {/* Harga */}
        <div className="rounded-lg border border-border/50 bg-background/50 p-3">
          <span className="text-[11px] font-medium text-muted-foreground">Harga Terkini</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-foreground">
              Rp {q.last_price.toLocaleString("id-ID")}
            </span>
            <span
              className={`text-xs font-semibold ${
                isBullishChange ? "text-emerald-500" : "text-rose-500"
              }`}
            >
              {isBullishChange ? "+" : ""}
              {q.change_percent.toFixed(2)}%
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground">
            Vol: {q.volume_lots.toLocaleString("id-ID")} lot • Pluang
          </span>
        </div>

        {/* Orderbook */}
        <div className="rounded-lg border border-border/50 bg-background/50 p-3">
          <span className="text-[11px] font-medium text-muted-foreground">Orderbook Ratio</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-foreground">
              {ob.bid_ask_ratio.toFixed(2)}x
            </span>
            <span
              className={`text-xs font-semibold ${
                isBidDom ? "text-emerald-500" : "text-amber-500"
              }`}
            >
              {isBidDom ? "Bid Dom" : "Offer Dom"}
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground">
            Bid: {ob.total_bid_lots.toLocaleString("id-ID")} lot • Pluang
          </span>
        </div>

        {/* Foreign Flow */}
        <div className="rounded-lg border border-border/50 bg-background/50 p-3">
          <span className="text-[11px] font-medium text-muted-foreground">Foreign Flow 1W</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-foreground">
              {ff.weekly_1w ? `${(ff.weekly_1w.net_shares / 100).toLocaleString("id-ID")} lot` : "0"}
            </span>
            <span
              className={`text-xs font-semibold ${
                isForeignAccum ? "text-emerald-500" : "text-rose-500"
              }`}
            >
              {isForeignAccum ? "Accum" : "Distrib"}
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground">
            Status: {ff.foreign_status} • IDX
          </span>
        </div>

        {/* Broker Flow */}
        <div className="rounded-lg border border-border/50 bg-background/50 p-3">
          <span className="text-[11px] font-medium text-muted-foreground">Bandarmology 1D</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-base font-bold text-foreground">
              {bf.top_buyers[0]?.broker || "N/A"}
            </span>
            <span
              className={`text-xs font-semibold ${
                isBandarAccum ? "text-emerald-500" : "text-muted-foreground"
              }`}
            >
              {bf.bandar_status}
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground">
            Top3: {bf.top3_buyer_concentration_percent.toFixed(0)}% vs {bf.top3_seller_concentration_percent.toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Expandable Deep-Dive Details */}
      {isOpen && (
        <div className="mt-5 space-y-5 border-t border-border pt-4">
          {/* Orderbook Depth Table */}
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Kedalaman Antrean Orderbook (Pluang)
            </h4>
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/50 text-[11px] font-semibold text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-right">Bid Lots</th>
                    <th className="px-3 py-2 text-right text-emerald-500">Bid Price</th>
                    <th className="px-3 py-2 text-left text-rose-500">Offer Price</th>
                    <th className="px-3 py-2 text-left">Offer Lots</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-mono">
                  {Array.from({
                    length: Math.max(ob.bids.length, ob.asks.length, 3),
                  }).map((_, i) => (
                    <tr key={i} className="hover:bg-muted/30">
                      <td className="px-3 py-1.5 text-right text-foreground">
                        {ob.bids[i]?.lots ? ob.bids[i].lots.toLocaleString("id-ID") : "-"}
                      </td>
                      <td className="px-3 py-1.5 text-right font-semibold text-emerald-500">
                        {ob.bids[i]?.price ? `Rp ${ob.bids[i].price.toLocaleString("id-ID")}` : "-"}
                      </td>
                      <td className="px-3 py-1.5 text-left font-semibold text-rose-500">
                        {ob.asks[i]?.price ? `Rp ${ob.asks[i].price.toLocaleString("id-ID")}` : "-"}
                      </td>
                      <td className="px-3 py-1.5 text-left text-foreground">
                        {ob.asks[i]?.lots ? ob.asks[i].lots.toLocaleString("id-ID") : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Broker Summary Table */}
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Top Broker Akumulasi & Distribusi (Pluang / IDX)
            </h4>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Buyers */}
              <div className="rounded-lg border border-border p-3">
                <span className="text-xs font-semibold text-emerald-500">Top Net Buyers</span>
                <div className="mt-2 space-y-1.5 font-mono text-xs">
                  {bf.top_buyers.map((b, i) => (
                    <div key={i} className="flex justify-between border-b border-border/30 pb-1">
                      <span className="font-bold text-foreground">{b.broker}</span>
                      <span className="text-muted-foreground">
                        {b.lots.toLocaleString("id-ID")} lot @ Rp {b.avg_price.toLocaleString("id-ID")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sellers */}
              <div className="rounded-lg border border-border p-3">
                <span className="text-xs font-semibold text-rose-500">Top Net Sellers</span>
                <div className="mt-2 space-y-1.5 font-mono text-xs">
                  {bf.top_sellers.map((s, i) => (
                    <div key={i} className="flex justify-between border-b border-border/30 pb-1">
                      <span className="font-bold text-foreground">{s.broker}</span>
                      <span className="text-muted-foreground">
                        {s.lots.toLocaleString("id-ID")} lot @ Rp {s.avg_price.toLocaleString("id-ID")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Technical Summary */}
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Indikator Teknikal Terkomputasi (IDX - {snapshot.historical_ohlcv.horizon_days} Hari)
            </h4>
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-md border border-border bg-muted/40 px-2.5 py-1">
                MA20: <strong className="font-mono">{tech.ma20 || "N/A"}</strong>
              </span>
              <span className="rounded-md border border-border bg-muted/40 px-2.5 py-1">
                MA50: <strong className="font-mono">{tech.ma50 || "N/A"}</strong>
              </span>
              <span className="rounded-md border border-border bg-muted/40 px-2.5 py-1">
                MA200: <strong className="font-mono">{tech.ma200 || "N/A"}</strong>
              </span>
              <span className="rounded-md border border-border bg-muted/40 px-2.5 py-1">
                RSI(14): <strong className="font-mono">{tech.rsi14 || "N/A"}</strong>
              </span>
              <span className="rounded-md border border-border bg-muted/40 px-2.5 py-1">
                Alignment: <strong className="font-mono text-primary">{tech.ma_alignment || "N/A"}</strong>
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
