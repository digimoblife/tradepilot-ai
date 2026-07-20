import { get } from "./client";
import type { ContextSummary } from "@/types/context";

export function getContextSummary(sessionId: string): Promise<ContextSummary> {
  return get<ContextSummary>(`/api/trade-sessions/${sessionId}/context`);
}
