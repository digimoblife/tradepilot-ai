import type { InitialAnalysisResult, MarketFactsSnapshot } from "./types";

interface Props {
  result: InitialAnalysisResult;
  marketFacts?: MarketFactsSnapshot | null;
}

const labels: Array<[keyof InitialAnalysisResult, string]> = [
  ["summary", "Ringkasan"],
  ["orderbook_analysis", "Analisis Order Book"],
  ["three_month_chart_analysis", "Analisis Grafik 3 Bulan"],
  ["six_month_chart_analysis", "Analisis Grafik 6 Bulan"],
  ["foreign_flow_analysis", "Analisa Foreign Flow"],
  ["support", "Support"],
  ["resistance", "Resistance"],
  ["entry_area", "Area Entry"],
  ["stop_recommendation", "Rekomendasi Stop"],
  ["target_recommendation", "Rekomendasi Target"],
  ["probabilities", "Probabilitas"],
  ["risks", "Risiko"],
  ["trading_plan", "Rencana Trading"],
  ["conclusion", "Kesimpulan"],
];

function value(v: unknown): string {
  if (Array.isArray(v)) return v.join(" • ");
  if (v && typeof v === "object") {
    return Object.entries(v)
      .map(([k, x]) => `${k}: ${String(x)}`)
      .join(" | ");
  }
  return String(v ?? "-");
}

function formatIDR(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "-";
  if (Math.abs(val) >= 1_000_000_000_000) {
    return `Rp ${(val / 1_000_000_000_000).toFixed(2)} Triliun`;
  }
  if (Math.abs(val) >= 1_000_000_000) {
    return `Rp ${(val / 1_000_000_000).toFixed(2)} Miliar`;
  }
  if (Math.abs(val) >= 1_000_000) {
    return `Rp ${(val / 1_000_000).toFixed(2)} Juta`;
  }
  return `Rp ${val.toLocaleString("id-ID")}`;
}

function formatShares(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "-";
  if (Math.abs(val) >= 1_000_000_000) {
    return `${(val / 1_000_000_000).toFixed(2)} M lembar`;
  }
  if (Math.abs(val) >= 1_000_000) {
    return `${(val / 1_000_000).toFixed(2)} jt lembar`;
  }
  return `${val.toLocaleString("id-ID")} lembar`;
}

export function InitialAnalysisResultView({ result, marketFacts }: Props) {
  const hasProfileFacts =
    marketFacts &&
    (marketFacts.sector ||
      marketFacts.pe_ratio != null ||
      marketFacts.dividend_yield_percent != null ||
      marketFacts.eps_ttm != null ||
      marketFacts.beta != null ||
      marketFacts.one_year_return_percent != null);

  const hasOrderbookFacts =
    marketFacts &&
    (marketFacts.system_bid_ask_ratio != null ||
      marketFacts.system_spread_percent != null ||
      marketFacts.avg_daily_value_idr_20d != null ||
      marketFacts.system_total_bid_lots != null);

  const hasTechnicalFacts =
    marketFacts &&
    (marketFacts.ma_alignment ||
      marketFacts.ma20 != null ||
      marketFacts.rsi14 != null ||
      marketFacts.atr14 != null ||
      marketFacts.high_52w != null);

  const hasFlowFacts =
    marketFacts &&
    (marketFacts.foreign_status ||
      marketFacts.foreign_flow_1m?.net_value_idr != null ||
      marketFacts.foreign_flow_3m?.net_value_idr != null);

  const probabilities = result.probabilities;
  const upsidePct =
    typeof probabilities?.upside === "number"
      ? probabilities.upside
      : parseFloat(String(probabilities?.upside || "50")) || 50;
  const downsidePct =
    typeof probabilities?.downside === "number"
      ? probabilities.downside
      : parseFloat(String(probabilities?.downside || "50")) || 50;

  return (
    <section aria-label="Hasil Initial Analysis" className="space-y-4">
      {/* 🏢 Profil & Valuasi Emiten Banner (if market facts present) */}
      {hasProfileFacts && (
        <article className="overflow-hidden rounded-2xl border border-zinc-200 bg-gradient-to-br from-white via-zinc-50/50 to-blue-50/20 p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200/80 pb-4">
            <div className="flex items-center gap-2">
              <span className="text-xl">🏢</span>
              <div>
                <h4 className="text-sm font-bold uppercase tracking-wider text-zinc-900">
                  Profil & Valuasi Emiten
                </h4>
                <p className="text-xs text-zinc-500">
                  Data fundamental terverifikasi dari Investing & Stockbit
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {marketFacts?.sector && (
                <span className="inline-flex items-center rounded-md border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
                  {marketFacts.sector}
                </span>
              )}
              {marketFacts?.sub_sector && (
                <span className="inline-flex items-center rounded-md border border-zinc-200 bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-700">
                  {marketFacts.sub_sector}
                </span>
              )}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <div className="rounded-xl border border-zinc-200/70 bg-white p-3 shadow-xs">
              <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                P/E Ratio
              </span>
              <p className="mt-1 text-lg font-extrabold text-zinc-900">
                {marketFacts?.pe_ratio != null ? `${marketFacts.pe_ratio}x` : "-"}
              </p>
              <span className="text-[10px] text-zinc-400">Trailing Twelve Months</span>
            </div>

            <div className="rounded-xl border border-zinc-200/70 bg-white p-3 shadow-xs">
              <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                EPS (TTM)
              </span>
              <p className="mt-1 text-lg font-extrabold text-zinc-900">
                {marketFacts?.eps_ttm != null ? `Rp ${marketFacts.eps_ttm.toFixed(2)}` : "-"}
              </p>
              <span className="text-[10px] text-zinc-400">Laba per lembar</span>
            </div>

            <div className="rounded-xl border border-zinc-200/70 bg-white p-3 shadow-xs">
              <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                Dividend Yield
              </span>
              <p className="mt-1 text-lg font-extrabold text-emerald-600">
                {marketFacts?.dividend_yield_percent != null
                  ? `${marketFacts.dividend_yield_percent}%`
                  : "-"}
              </p>
              <span className="text-[10px] text-zinc-400">
                {marketFacts?.dividend_per_share != null
                  ? `Rp ${marketFacts.dividend_per_share}/lbr`
                  : "Imbal hasil dividen"}
              </span>
            </div>

            <div className="rounded-xl border border-zinc-200/70 bg-white p-3 shadow-xs">
              <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                Beta vs IHSG
              </span>
              <p className="mt-1 text-lg font-extrabold text-zinc-900">
                {marketFacts?.beta != null ? marketFacts.beta : "-"}
              </p>
              <span className="text-[10px] text-zinc-400">
                {marketFacts?.beta != null && marketFacts.beta < 0.5
                  ? "Defensif / Low Risk"
                  : "Volatilitas Relatif"}
              </span>
            </div>

            <div className="rounded-xl border border-zinc-200/70 bg-white p-3 shadow-xs">
              <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                Momentum 1-Thn
              </span>
              <p
                className={`mt-1 text-lg font-extrabold ${
                  (marketFacts?.one_year_return_percent ?? 0) >= 0
                    ? "text-emerald-600"
                    : "text-rose-600"
                }`}
              >
                {marketFacts?.one_year_return_percent != null
                  ? `${marketFacts.one_year_return_percent > 0 ? "+" : ""}${
                      marketFacts.one_year_return_percent
                    }%`
                  : "-"}
              </p>
              <span className="text-[10px] text-zinc-400">Trailing return</span>
            </div>

            <div className="rounded-xl border border-zinc-200/70 bg-white p-3 shadow-xs">
              <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                Katalis Lapkeu
              </span>
              <p className="mt-1 text-sm font-bold text-zinc-900">
                {marketFacts?.next_earnings_date ?? "-"}
              </p>
              <span className="text-[10px] text-zinc-400">Rilis Laporan Keuangan</span>
            </div>
          </div>
        </article>
      )}

      {/* Sections rendering maintaining exact h3 headings */}
      {labels.map(([key, label]) => {
        const fieldValue = result[key];
        if (key === "foreign_flow_analysis" && !fieldValue) return null;

        // Custom card styling based on section
        const isEntry = key === "entry_area";
        const isTarget = key === "target_recommendation";
        const isStop = key === "stop_recommendation";
        const isConclusion = key === "conclusion";
        const isProbabilities = key === "probabilities";
        const isRisks = key === "risks";

        return (
          <article
            key={key}
            className={`rounded-xl border p-4 transition-colors ${
              isEntry
                ? "border-blue-200 bg-blue-50/30"
                : isTarget
                ? "border-emerald-200 bg-emerald-50/30"
                : isStop
                ? "border-rose-200 bg-rose-50/30"
                : isConclusion
                ? "border-indigo-200 bg-gradient-to-r from-white to-indigo-50/30"
                : "border-zinc-200 bg-white"
            }`}
          >
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-zinc-900">{label}</h3>

              {/* Status pill badges for relevant sections */}
              {key === "foreign_flow_analysis" && marketFacts?.foreign_status && (
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide ${
                    marketFacts.foreign_status.includes("ACCUMULATION")
                      ? "bg-emerald-100 text-emerald-800"
                      : marketFacts.foreign_status.includes("DISTRIBUTION")
                      ? "bg-rose-100 text-rose-800"
                      : "bg-zinc-100 text-zinc-800"
                  }`}
                >
                  {marketFacts.foreign_status}
                </span>
              )}
              {key === "three_month_chart_analysis" && marketFacts?.ma_alignment && (
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold tracking-wide ${
                    marketFacts.ma_alignment === "BULLISH_ALIGNMENT"
                      ? "bg-emerald-100 text-emerald-800"
                      : marketFacts.ma_alignment === "BEARISH_ALIGNMENT"
                      ? "bg-rose-100 text-rose-800"
                      : "bg-zinc-100 text-zinc-800"
                  }`}
                >
                  {marketFacts.ma_alignment.replace("_", " ")}
                </span>
              )}
            </div>

            {/* Supplemental Micro-structure metrics inside Orderbook Analysis */}
            {key === "orderbook_analysis" && hasOrderbookFacts && (
              <div className="mt-3 mb-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-2 text-xs">
                  <span className="text-zinc-500">Bid/Ask Ratio:</span>{" "}
                  <strong className="text-zinc-800">
                    {marketFacts?.system_bid_ask_ratio != null
                      ? `${marketFacts.system_bid_ask_ratio}x`
                      : "-"}
                  </strong>
                </div>
                <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-2 text-xs">
                  <span className="text-zinc-500">Spread:</span>{" "}
                  <strong className="text-zinc-800">
                    {marketFacts?.system_spread_percent != null
                      ? `${marketFacts.system_spread_percent}%`
                      : "-"}
                  </strong>
                </div>
                <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-2 text-xs">
                  <span className="text-zinc-500">Bid / Ask Lots:</span>{" "}
                  <strong className="text-zinc-800">
                    {marketFacts?.system_total_bid_lots?.toLocaleString("id-ID") ?? "-"} /{" "}
                    {marketFacts?.system_total_ask_lots?.toLocaleString("id-ID") ?? "-"}
                  </strong>
                </div>
                <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-2 text-xs">
                  <span className="text-zinc-500">Turnover 20D:</span>{" "}
                  <strong className="text-zinc-800">
                    {formatIDR(marketFacts?.avg_daily_value_idr_20d)}/hari
                  </strong>
                </div>
              </div>
            )}

            {/* Supplemental Technical metrics inside Chart Analysis */}
            {key === "three_month_chart_analysis" && hasTechnicalFacts && (
              <div className="mt-3 mb-2 flex flex-wrap gap-2 text-xs">
                {marketFacts?.ma20 != null && (
                  <span className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-zinc-700">
                    MA20: <strong>{marketFacts.ma20}</strong>
                  </span>
                )}
                {marketFacts?.ma50 != null && (
                  <span className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-zinc-700">
                    MA50: <strong>{marketFacts.ma50}</strong>
                  </span>
                )}
                {marketFacts?.rsi14 != null && (
                  <span
                    className={`rounded-md border px-2 py-1 font-semibold ${
                      marketFacts.rsi14 > 70
                        ? "border-amber-300 bg-amber-50 text-amber-800"
                        : marketFacts.rsi14 < 30
                        ? "border-blue-300 bg-blue-50 text-blue-800"
                        : "border-zinc-200 bg-zinc-50 text-zinc-700"
                    }`}
                  >
                    RSI (14): {marketFacts.rsi14}{" "}
                    {marketFacts.rsi14 > 70
                      ? "(Overbought)"
                      : marketFacts.rsi14 < 30
                      ? "(Oversold)"
                      : ""}
                  </span>
                )}
                {marketFacts?.atr14 != null && (
                  <span className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-zinc-700">
                    ATR (14): <strong>{marketFacts.atr14}</strong>
                  </span>
                )}
                {marketFacts?.high_52w != null && marketFacts?.low_52w != null && (
                  <span className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-zinc-700">
                    52W Range: <strong>{marketFacts.low_52w}</strong> -{" "}
                    <strong>{marketFacts.high_52w}</strong>
                  </span>
                )}
              </div>
            )}

            {/* Supplemental Foreign Flow Multi-Horizon metrics */}
            {key === "foreign_flow_analysis" && hasFlowFacts && (
              <div className="mt-3 mb-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {marketFacts?.foreign_flow_1m && (
                  <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-2.5 text-xs">
                    <span className="text-zinc-500">Foreign Net 1 Bulan:</span>
                    <p className="mt-0.5 font-bold text-zinc-800">
                      {formatIDR(marketFacts.foreign_flow_1m.net_value_idr)} (
                      {formatShares(marketFacts.foreign_flow_1m.net_shares)})
                    </p>
                  </div>
                )}
                {marketFacts?.foreign_flow_3m && (
                  <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-2.5 text-xs">
                    <span className="text-zinc-500">Foreign Net 3 Bulan:</span>
                    <p className="mt-0.5 font-bold text-zinc-800">
                      {formatIDR(marketFacts.foreign_flow_3m.net_value_idr)} (
                      {formatShares(marketFacts.foreign_flow_3m.net_shares)})
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Visual Probability Bar */}
            {isProbabilities && (
              <div className="mt-3 mb-2 space-y-1.5">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-emerald-700">Upside: {upsidePct}%</span>
                  <span className="text-rose-700">Downside: {downsidePct}%</span>
                </div>
                <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-zinc-100 border border-zinc-200">
                  <div
                    style={{ width: `${upsidePct}%` }}
                    className="bg-emerald-500 transition-all"
                  />
                  <div
                    style={{ width: `${downsidePct}%` }}
                    className="bg-rose-500 transition-all"
                  />
                </div>
              </div>
            )}

            {/* Section Text Body */}
            {isRisks && Array.isArray(fieldValue) ? (
              <ul className="mt-2 space-y-1.5 text-sm leading-6 text-zinc-700">
                {fieldValue.map((risk, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-amber-500 font-bold">•</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-zinc-700">
                {value(fieldValue)}
              </p>
            )}

            {/* Key Support / Resistance badges */}
            {key === "support" && marketFacts?.key_supports && marketFacts.key_supports.length > 0 && (
              <div className="mt-2 flex flex-wrap items-center gap-1.5 pt-2 border-t border-zinc-100 text-xs text-zinc-500">
                <span>Level Kunci Tambahan:</span>
                {marketFacts.key_supports.map((lvl, idx) => (
                  <span
                    key={idx}
                    className="inline-flex rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-bold text-emerald-800"
                  >
                    Rp {lvl.toLocaleString("id-ID")}
                  </span>
                ))}
              </div>
            )}
            {key === "resistance" &&
              marketFacts?.key_resistances &&
              marketFacts.key_resistances.length > 0 && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5 pt-2 border-t border-zinc-100 text-xs text-zinc-500">
                  <span>Level Kunci Tambahan:</span>
                  {marketFacts.key_resistances.map((lvl, idx) => (
                    <span
                      key={idx}
                      className="inline-flex rounded-md border border-rose-200 bg-rose-50 px-2 py-0.5 font-bold text-rose-800"
                    >
                      Rp {lvl.toLocaleString("id-ID")}
                    </span>
                  ))}
                </div>
              )}
          </article>
        );
      })}
    </section>
  );
}
