"use client";

import { useEffect, useState } from "react";
import { readInitialAnalysis } from "@/features/trade-workspace/api";
import type { SessionStatus } from "@/features/trade-workspace/types";

export interface SessionIntelligenceData {
  currentPrice: number | null;
  priceChangePercent: number | null;
  orderbookDepthRatio: number | null;
  orderbookDepthLabel: string | null;
  foreignStatus: string | null;
  bandarStatus: string | null;
  recommendation: string | null;
  convictionScore: number | null;
  sector: string | null;
  indexTag: string | null;
}

const intelligenceCache = new Map<string, SessionIntelligenceData>();

export function useSessionIntelligence(sessionId: string, status: SessionStatus) {
  const [data, setData] = useState<SessionIntelligenceData | null>(
    intelligenceCache.get(sessionId) ?? null
  );
  const [loading, setLoading] = useState(!intelligenceCache.has(sessionId));

  useEffect(() => {
    if (intelligenceCache.has(sessionId)) {
      setData(intelligenceCache.get(sessionId) ?? null);
      setLoading(false);
      return;
    }

    // Only attempt to load analysis if session has progressed beyond DRAFT & ANALYZING
    if (status === "DRAFT" || status === "ANALYZING") {
      setLoading(false);
      return;
    }

    let isMounted = true;
    const controller = new AbortController();

    async function load() {
      try {
        const res = await readInitialAnalysis(sessionId, controller.signal);
        if (!isMounted) return;

        const processed = (res?.processed_response as unknown as Record<string, unknown>) || {};
        const marketFacts = (res?.market_facts as unknown as Record<string, unknown>) || {};

        let currentPrice: number | null = null;
        if (typeof marketFacts.current_price === "number") {
          currentPrice = marketFacts.current_price;
        } else if (typeof marketFacts.current_price === "string") {
          currentPrice = parseFloat(marketFacts.current_price);
        } else if (typeof marketFacts.pe_ratio === "number" && typeof marketFacts.eps_ttm === "number") {
          currentPrice = Math.round(marketFacts.pe_ratio * marketFacts.eps_ttm);
        }


        let changePct: number | null = null;
        if (typeof marketFacts.index_change_percent === "number") changePct = marketFacts.index_change_percent;
        else if (typeof marketFacts.one_year_return_percent === "number") changePct = marketFacts.one_year_return_percent;

        const depthRatio = typeof marketFacts.system_bid_ask_ratio === "number"
          ? marketFacts.system_bid_ask_ratio
          : null;

        let depthLabel: string | null = null;
        if (depthRatio !== null) {
          if (depthRatio < 0.5) depthLabel = "(Tipis / Kritis)";
          else if (depthRatio > 1.5) depthLabel = "(Bid Kuat)";
          else depthLabel = "(Seimbang)";
        }

        const bandarObj = processed.bandarmology_assessment as Record<string, unknown> | undefined;
        const bandarStatus = (typeof bandarObj?.status === "string" ? bandarObj.status : null) ||
          (typeof marketFacts.foreign_status === "string" ? marketFacts.foreign_status : null);

        const recommendation = (typeof processed.action === "string" ? processed.action : null) ||
          (typeof processed.recommendation === "string" ? processed.recommendation : null);

        const convictionScore = typeof processed.conviction_score === "number"
          ? processed.conviction_score
          : (typeof processed.confidence_score === "number" ? Math.round(processed.confidence_score * 100) : null);

        const sector = typeof marketFacts.sector === "string" ? marketFacts.sector : null;
        const indexName = typeof marketFacts.index_name === "string" ? marketFacts.index_name : null;
        const indexTag = indexName ? `IDX:${indexName}` : (sector ? `IDX:${sector}` : null);

        const parsed: SessionIntelligenceData = {
          currentPrice,
          priceChangePercent: changePct,
          orderbookDepthRatio: depthRatio,
          orderbookDepthLabel: depthLabel,
          foreignStatus: typeof marketFacts.foreign_status === "string" ? marketFacts.foreign_status : null,
          bandarStatus,
          recommendation: recommendation ? recommendation.toUpperCase() : null,
          convictionScore,
          sector,
          indexTag,
        };

        intelligenceCache.set(sessionId, parsed);
        setData(parsed);
      } catch {
        // Silently fallback if analysis not yet available or in test environments
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    load();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [sessionId, status]);

  return { data, loading };
}
