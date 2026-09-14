"use client";

import { useEffect, useState } from "react";

import { getSessionWorkspaceData } from "@/features/trade-workspace/api";
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

// Statuses reached only after at least one AI analysis has run for the session —
// DRAFT (no evidence acquired yet) is intentionally excluded.
const STATUSES_WITH_POSSIBLE_ANALYSIS = new Set<SessionStatus>([
  "ANALYZED",
  "WAITING",
  "OPEN_POSITION",
  "CLOSED",
  "CLOSED_SKIPPED",
]);

function depthLabelFromRatio(ratio: number | null): string | null {
  if (ratio === null) return null;
  if (ratio >= 1.15) return "(Dominan Beli)";
  if (ratio <= 0.87) return "(Dominan Jual)";
  return "(Seimbang)";
}

/**
 * Reads whatever session intelligence is already cached server-side for this
 * session, without ever triggering a live ZAPI/Gemini call. The session-list
 * page renders many of these at once, so it always calls the workspace
 * endpoint in "passive" mode (`passive=true`): a session that has already
 * been analyzed (its cache is warm) shows real data, one that hasn't yet
 * simply falls back to the card's own placeholder text. Opening the session
 * itself (via ModernSessionWorkspace) is what performs the actual live
 * analysis / cache warm-up.
 */
export function useSessionIntelligence(sessionId: string, status: SessionStatus) {
  const [data, setData] = useState<SessionIntelligenceData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!STATUSES_WITH_POSSIBLE_ANALYSIS.has(status)) {
      setData(null);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);

    getSessionWorkspaceData(sessionId, false, controller.signal, { passive: true })
      .then((workspace) => {
        if (controller.signal.aborted) return;

        const analysis = workspace?.analysis;
        if (!analysis) {
          setData(null);
          return;
        }

        const evidence = analysis.market_evidence ?? {};
        const quote = evidence.quote ?? {};
        const orderbook = evidence.orderbook ?? {};
        const foreignFlow = evidence.foreign_flow ?? {};
        const brokerFlow = evidence.broker_flow ?? {};
        const companyProfile = evidence.company_profile ?? {};
        const marketContext = evidence.market_context ?? {};

        const orderbookDepthRatio =
          typeof orderbook.bid_ask_ratio === "number" ? orderbook.bid_ask_ratio : null;

        setData({
          currentPrice: typeof quote.last_price === "number" ? quote.last_price : null,
          priceChangePercent:
            typeof quote.change_percent === "number" ? quote.change_percent : null,
          orderbookDepthRatio,
          orderbookDepthLabel: depthLabelFromRatio(orderbookDepthRatio),
          foreignStatus: foreignFlow.foreign_status ?? null,
          bandarStatus: brokerFlow.bandar_status ?? null,
          recommendation: analysis.action ?? null,
          convictionScore:
            typeof analysis.confidence_score === "number" ? analysis.confidence_score : null,
          sector: companyProfile.sector ?? null,
          indexTag: marketContext.index_code ?? null,
        });
      })
      .catch(() => {
        if (!controller.signal.aborted) setData(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [sessionId, status]);

  return { data, loading };
}
