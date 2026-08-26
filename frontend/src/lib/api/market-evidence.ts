import { get, post } from "./client";
import type { MarketEvidenceResponse } from "@/types/market-evidence";

export function previewMarketEvidence(
  sessionId: string,
  symbol?: string,
): Promise<MarketEvidenceResponse> {
  const query = symbol ? { symbol } : undefined;
  return get<MarketEvidenceResponse>(`/api/sessions/${sessionId}/market-evidence/preview`, query);
}

export function acquireMarketEvidence(
  sessionId: string,
): Promise<MarketEvidenceResponse> {
  return post<MarketEvidenceResponse>(`/api/sessions/${sessionId}/market-evidence/acquire`);
}
