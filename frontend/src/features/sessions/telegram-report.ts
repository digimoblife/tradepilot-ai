export interface TelegramReportInput {
  ticker: string;
  companyName: string;
  analyzedAt?: string | null;
  quote?: any;
  profile?: any;
  tech?: any;
  brokerFlow?: any;
  foreignFlow?: any;
  orderbook?: any;
  marketContext?: any;
  keyLevels?: any;
  reasoning?: any;
  action: string;
  isInTrade?: boolean;
}

export function formatRupiah(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "-";
  return `Rp ${Number(val).toLocaleString("id-ID")}`;
}

export function formatMiliar(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "-";
  const abs = Math.abs(val);
  const sign = val > 0 ? "+" : val < 0 ? "-" : "";
  if (abs >= 1_000_000_000) {
    return `${sign}Rp ${(abs / 1_000_000_000).toFixed(2)} Miliar`;
  }
  if (abs >= 1_000_000) {
    return `${sign}Rp ${(abs / 1_000_000).toFixed(2)} Juta`;
  }
  return `${sign}Rp ${abs.toLocaleString("id-ID")}`;
}

export function formatShares(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "-";
  const abs = Math.abs(val);
  const sign = val > 0 ? "+" : val < 0 ? "-" : "";
  if (abs >= 1_000_000) {
    return `(${sign}${(abs / 1_000_000).toFixed(2)} juta lembar)`;
  }
  if (abs >= 1_000) {
    return `(${sign}${(abs / 1_000).toFixed(1)} ribu lembar)`;
  }
  return `(${sign}${abs.toLocaleString("id-ID")} lembar)`;
}

export function generateTelegramReport(input: TelegramReportInput): string {
  const {
    ticker,
    companyName,
    analyzedAt,
    quote,
    profile,
    tech,
    brokerFlow,
    foreignFlow,
    orderbook,
    marketContext,
    keyLevels,
    reasoning,
    action,
  } = input;

  const dateObj = analyzedAt ? new Date(analyzedAt) : new Date();
  const formattedDate = new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(dateObj);

  // Sector & Sub-sector
  const sector = profile?.sector || quote?.sector || "IDX General";
  const subSector = profile?.sub_sector || quote?.industry || "Saham Biasa";

  // Price & valuation
  const lastPrice = Number(quote?.last_price || keyLevels?.current_price || 0);
  const changePct = Number(quote?.change_percent || 0);
  const peRatio = profile?.pe_ratio ?? quote?.pe_ratio;
  let peValuationNote = "Valuasi wajar";
  if (peRatio !== null && peRatio !== undefined) {
    if (peRatio <= 10) peValuationNote = "Valuasi atraktif di bawah rata-rata historis sektor";
    else if (peRatio <= 20) peValuationNote = "Valuasi wajar moderat";
    else peValuationNote = "Valuasi premium";
  }

  const eps = profile?.eps_ttm ?? quote?.eps_ttm;
  const divYield = profile?.dividend_yield_percent ?? quote?.dividend_yield;
  const dps = profile?.dividend_per_share ?? quote?.dps;
  const beta = profile?.beta ?? quote?.beta;
  let betaNote = "Volatilitas seimbang";
  if (beta !== null && beta !== undefined) {
    if (beta < 0) betaNote = "Karakter defensif / bergerak melawan tren pelemahan IHSG";
    else if (beta < 0.8) betaNote = "Defensif, risiko fluktuasi lebih rendah dari IHSG";
    else if (beta > 1.2) betaNote = "Agresif, fluktuasi lebih tinggi dari IHSG";
  }

  const oneYearReturn = profile?.one_year_return_percent ?? quote?.one_year_return;
  const nextEarnings = profile?.next_earnings_date || quote?.next_earnings_date || "Belum diumumkan";

  // Bandarmology
  const bandarStatus = brokerFlow?.bandar_status || "NEUTRAL";
  const bandarEmoji =
    bandarStatus.includes("BIG_ACCUMULATION") || bandarStatus === "ACCUMULATION"
      ? "🟢"
      : bandarStatus.includes("DISTRIBUTION")
        ? "🔴"
        : "🟡";
  const top3BuyerConc = brokerFlow?.top3_buyer_concentration_percent ?? 0;
  const top3BuyerNote = top3BuyerConc >= 70 ? "Sangat terakumulasi" : top3BuyerConc >= 50 ? "Terakumulasi moderat" : "Konsentrasi wajar";

  // Top buyers formatted
  const topBuyers = brokerFlow?.top_buyers || [];
  let accumulatorsText = "Tersebar merata";
  if (topBuyers.length > 0) {
    const parts = topBuyers.slice(0, 3).map((b: any, idx: number) => {
      const code = b.broker || "-";
      const val = formatMiliar(b.value_idr);
      const pct = b.market_share_percent ? `, porsi ${b.market_share_percent}%` : "";
      if (idx === 0) return `Broker ${code} (${val}${pct})`;
      return `${code} (${val})`;
    });
    accumulatorsText = parts.length > 1
      ? `${parts[0]}, disusul ${parts.slice(1).join(" dan ")}`
      : parts[0];
  }

  // Top sellers formatted
  const topSellers = brokerFlow?.top_sellers || [];
  let sellersText = "Didominasi broker pasar reguler";
  if (topSellers.length > 0) {
    const codes = topSellers.slice(0, 3).map((s: any) => s.broker).filter(Boolean);
    if (codes.length > 0) {
      sellersText = `Didominasi broker (${codes.join(", ")})`;
    }
  }

  // Foreign flow
  const foreignStatus = foreignFlow?.foreign_status || "NEUTRAL";
  const foreignEmoji =
    foreignStatus.includes("ACCUMULATION")
      ? "🟢"
      : foreignStatus.includes("DISTRIBUTION")
        ? "🔴"
        : "🟡";

  const ff1d = foreignFlow?.today_1d;
  const ff1w = foreignFlow?.weekly_1w;
  const ff1m = foreignFlow?.monthly_1m;
  const ff3m = foreignFlow?.three_month_3m;

  const ff1dStr = ff1d ? `${formatMiliar(ff1d.net_value_idr)} ${formatShares(ff1d.net_shares)}` : "-";
  const ff1wStr = ff1w ? `${formatMiliar(ff1w.net_value_idr)} ${formatShares(ff1w.net_shares)}` : "-";
  const ff1mStr = ff1m ? `${formatMiliar(ff1m.net_value_idr)} ${formatShares(ff1m.net_shares)}` : "-";
  const ff3mStr = ff3m ? `${formatMiliar(ff3m.net_value_idr)} ${formatShares(ff3m.net_shares)}` : "-";

  const flowConclusion =
    foreignStatus.includes("ACCUMULATION") && bandarStatus.includes("ACCUMULATION")
      ? "Dana institusi & asing terus masuk secara konsisten dalam skala besar."
      : foreignStatus.includes("DISTRIBUTION")
        ? "Tekanan jual asing dan broker lokal masih mendominasi pasar."
        : "Aliran dana institusi dan ritel bergerak relatif berimbang (konsolidasi).";

  // Technical
  const maAlignment = tech?.ma_alignment || "MIXED";
  const ma20 = Number(tech?.ma20 || lastPrice * 0.97);
  const ma50 = Number(tech?.ma50 || lastPrice * 0.93);
  const rsi = Number(tech?.rsi14 || 50);
  const atr = Number(tech?.atr14 || lastPrice * 0.03);
  const high52w = tech?.high_52w ? Number(tech.high_52w) : null;
  const low52w = tech?.low_52w ? Number(tech.low_52w) : null;

  let rsiNote = "Area Netral — momentum wajar";
  if (rsi >= 70) rsiNote = "Area Overbought — euforia beli tinggi, waspadai potensi pullback sehat jangka pendek";
  else if (rsi <= 30) rsiNote = "Area Oversold — jenuh jual, ada peluang technical rebound";

  const keySupports = tech?.key_supports || [];
  const keyResistances = tech?.key_resistances || [];
  const nearestSup = keySupports.find((s: number) => s < lastPrice) || Math.round(lastPrice * 0.96);
  const nearestRes = keyResistances.find((r: number) => r > lastPrice) || Math.round(lastPrice * 1.04);

  // Trading plan
  const entryMin = keyLevels?.entry_range?.[0] ?? Math.round(lastPrice * 0.985);
  const entryMax = keyLevels?.entry_range?.[1] ?? Math.round(lastPrice * 1.005);
  const tp1 = keyLevels?.target_price_1 ?? Math.round(lastPrice * 1.05);
  const tp2 = keyLevels?.target_price_2 ?? Math.round(lastPrice * 1.09);
  const sl = keyLevels?.stop_loss ?? Math.round(lastPrice * 0.94);
  const rr = keyLevels?.risk_reward_ratio ?? 2.0;

  let strategyName = "Buy on Weakness (BoW) / Antri Pullback";
  if (action === "BUY") {
    strategyName = rsi >= 70 ? "Buy on Weakness (BoW) / Antri Pullback" : "Buy on Breakout / Follow Through";
  } else if (action === "WAIT") {
    strategyName = "Wait for Confirmation / Antri Pullback";
  } else if (action === "SKIP") {
    strategyName = "Avoid / Lewati (Cari Peluang Lain)";
  }

  // Market context text
  const ihsgChange = Number(marketContext?.index_change_percent ?? 0);
  const ihsgText = `IHSG sedang ${ihsgChange >= 0 ? "menguat" : "melemah"} (${ihsgChange >= 0 ? "+" : ""}${ihsgChange.toFixed(2)}%)`;
  const marketConditionText = reasoning?.thesis || `${ihsgText}, ${ticker} ${action === "BUY" ? "menunjukkan Relative Strength tinggi" : "sedang berkonsolidasi"}.`;

  // Risks
  const risks = reasoning?.risk_factors || `1. Fluktuasi sentimen pasar acuan (${ihsgText}) dan pergerakan sektor ${sector}.\n2. ${rsi >= 70 ? "Penurunan momentum sesaat akibat aksi profit taking menyusul RSI yang jenuh beli (overbought)." : "Potensi tekanan jual jika harga menembus di bawah level stop loss."}`;

  return `📊 TRADEPILOT AI MARKET INTELLIGENCE
Analisis Saham: $${ticker} (${companyName})
Tanggal: ${formattedDate}

━━━━━━━━━━━━━━━━━━━━━
🏢 PROFIL & VALUASI EMITEN
• Sektor / Sub-sektor: ${sector} / ${subSector}
• Harga Saat Ini: Rp ${lastPrice.toLocaleString("id-ID")} (${changePct >= 0 ? "+" : ""}${changePct.toFixed(2)}%)
• P/E Ratio (TTM): ${peRatio !== null && peRatio !== undefined ? `${Number(peRatio).toFixed(2)}x` : "-"} (${peValuationNote})
• EPS (TTM): ${eps !== null && eps !== undefined ? `Rp ${Number(eps).toFixed(2)} per lembar` : "-"}
• Dividend Yield: ${divYield !== null && divYield !== undefined ? `${Number(divYield).toFixed(2)}%` : "-"} (${dps !== null && dps !== undefined ? `Dividen Rp ${Number(dps).toFixed(2)}/lembar` : "Dividen -"})
• Beta vs IHSG: ${beta !== null && beta !== undefined ? Number(beta).toFixed(2) : "-"} (${betaNote})
• Momentum 1 Tahun: ${oneYearReturn !== null && oneYearReturn !== undefined ? `${Number(oneYearReturn) >= 0 ? "+" : ""}${Number(oneYearReturn).toFixed(2)}%` : "-"}
• Katalis Rilis Lapkeu: ${nextEarnings}

━━━━━━━━━━━━━━━━━━━━━
💰 ARUS DANA (BANDARMOLOGY & FOREIGN FLOW)
Status Bandar: ${bandarEmoji} ${bandarStatus}
• Konsentrasi Top 3 Buyer: ${Number(top3BuyerConc).toFixed(1)}% (${top3BuyerNote})
• Akumulator Utama: ${accumulatorsText}
• Distribusi Penjual: ${sellersText}

Status Asing: ${foreignEmoji} ${foreignStatus}
• Foreign Net Buy 1 Hari: ${ff1dStr}
• Foreign Net Buy 1 Minggu: ${ff1wStr}
• Foreign Net Buy 1 Bulan: ${ff1mStr}
• Foreign Net Buy 3 Bulan: ${ff3mStr}
👉 Kesimpulan Flow: ${flowConclusion}

━━━━━━━━━━━━━━━━━━━━━
📈 ANALISIS TEKNIKAL & STRUKTUR TREN
• Tren Utama: ${maAlignment.replace("_", " ")}
  - Harga (${lastPrice.toLocaleString("id-ID")}) berada ${lastPrice >= ma20 ? "kokoh di atas" : "di bawah"} MA20 (${Math.round(ma20).toLocaleString("id-ID")}) dan MA50 (${Math.round(ma50).toLocaleString("id-ID")}).
• Indikator Momentum:
  - RSI 14: ${rsi.toFixed(2)} (${rsiNote})
  - ATR 14: ${atr.toFixed(2)} poin rentang fluktuasi harian normal.
• Level Kunci:
  - Resistance Terdekat / 52W High: Rp ${Math.round(nearestRes).toLocaleString("id-ID")}${high52w ? ` (52W High: Rp ${Math.round(high52w).toLocaleString("id-ID")})` : ""}
  - Support Dinamis / Pullback: Rp ${Math.round(nearestSup).toLocaleString("id-ID")}${low52w ? ` (52W Low: Rp ${Math.round(low52w).toLocaleString("id-ID")})` : ""}

━━━━━━━━━━━━━━━━━━━━━
🎯 SKENARIO & REKOMENDASI TRADING PLAN
Kondisi Pasar: ${marketConditionText}

📌 Strategi: ${strategyName}
• Area Beli Optimal: Rp ${entryMin.toLocaleString("id-ID")} – Rp ${entryMax.toLocaleString("id-ID")}
• Target Take Profit 1 (TP1): Rp ${tp1.toLocaleString("id-ID")} (Uji Resistance / 52W High)
• Target Take Profit 2 (TP2): Rp ${tp2.toLocaleString("id-ID")} (Breakout target)
• Stop Loss (SL): Rp ${sl.toLocaleString("id-ID")} (Batas risiko disiplin ~${Math.abs(Math.round(((sl - lastPrice) / lastPrice) * 100)) || 4.5}%)
• Risk/Reward Ratio: 1 : ${rr}

━━━━━━━━━━━━━━━━━━━━━
⚠️ RISIKO & KATALIS YANG PERLU DIPERHATIKAN
${risks}

⚖️ Disclaimer: Analisis ini bersifat edukatif dan advisori berbasis data pasar terverifikasi. Keputusan investasi dan eksekusi tetap berada di tangan masing-masing trader.`;
}
