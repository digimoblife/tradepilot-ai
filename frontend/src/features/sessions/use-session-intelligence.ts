"use client";

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

// The initial-analysis lookup this hook used to perform (GET /{id}/initial-analysis)
// read from the retired rebuild analysis pipeline, which no active flow ever writes
// to anymore. There is no remaining data source for session intelligence, so this
// hook is kept as a stable no-op to avoid touching its caller (session-list-card.tsx).
export function useSessionIntelligence(_sessionId: string, _status: SessionStatus) {
  return { data: null as SessionIntelligenceData | null, loading: false };
}
