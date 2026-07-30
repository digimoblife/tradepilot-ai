import { publicEnv } from "@/lib/env";
import type { BuyDecisionResult, DecisionAvailability, EvidenceFile, InitialAnalysisRead, InitialAnalysisSubmission, InitialEvidenceUploadResponse, SkipDecisionResult, SkipReason, TradeSession, WaitDecisionResult } from "./types";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${publicEnv.apiBaseUrl}${path}`, { ...options, credentials: "include" });
  if (!response.ok) {
    let message = "Permintaan tidak dapat diproses.";
    try { const body = await response.json(); message = body?.detail?.message ?? body?.detail ?? message; } catch { /* non-json error */ }
    throw new Error(typeof message === "string" ? message : "Permintaan tidak dapat diproses.");
  }
  return response.json() as Promise<T>;
}

const base = "/api/v2/trade-sessions";

export function listSessions(): Promise<{ sessions: TradeSession[] }> { return request(`${base}`); }
export function getSession(id: string): Promise<TradeSession> { return request(`${base}/${id}`); }
export function createSession(input: { ticker: string; company_name: string; note?: string | null }): Promise<TradeSession> {
  return request(base, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) });
}
export function uploadInitialEvidence(id: string, files: { orderbook: File; chart_3_month: File; chart_6_month: File }): Promise<InitialEvidenceUploadResponse> {
  const body = new FormData(); body.append("orderbook", files.orderbook); body.append("chart_3_month", files.chart_3_month); body.append("chart_6_month", files.chart_6_month);
  return request(`${base}/${id}/initial-evidence`, { method: "POST", body });
}
export function submitInitialAnalysis(id: string): Promise<InitialAnalysisSubmission> { return request(`${base}/${id}/initial-analysis`, { method: "POST" }); }
export function readInitialAnalysis(id: string): Promise<InitialAnalysisRead> { return request(`${base}/${id}/initial-analysis`); }
export function retryInitialAnalysis(id: string): Promise<InitialAnalysisSubmission> { return request(`${base}/${id}/initial-analysis/retry`, { method: "POST" }); }
export function getAvailableActions(id: string): Promise<DecisionAvailability> { return request(`${base}/${id}/available-actions`); }
export function waitDecision(id: string): Promise<WaitDecisionResult> { return request(`${base}/${id}/decisions/wait`, { method: "POST" }); }
export function skipDecision(id: string, body: { reason: SkipReason; note?: string | null }): Promise<SkipDecisionResult> {
  return request(`${base}/${id}/decisions/skip`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
export function buyDecision(id: string, body: { entry_price: string; entry_timestamp: string; quantity: string; stop_loss: string; target_price: string; note?: string | null }): Promise<BuyDecisionResult> {
  return request(`${base}/${id}/decisions/buy`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export type { EvidenceFile };
