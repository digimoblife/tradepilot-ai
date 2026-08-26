import { publicEnv } from "@/lib/env";
import { get, post } from "@/lib/api/client";
import type { BuyDecisionResult, CloseRequest, CloseResponse, CurrentStep, CurrentStepActiveRequest, CurrentStepCode, CurrentStepFailedRequest, CurrentStepMode, CurrentStepWorkflowAction, DecisionAvailability, EvidenceFile, InitialAnalysisRead, InitialAnalysisSubmission, InitialEvidenceUploadResponse, LatestAnalysisSummary, ObservationPeriod, PositionUpdateAnalysisSubmission, PositionUpdateInputResponse, PositionUpdatesRead, RequestStatus, SessionActivityType, SessionDetailAggregate, SessionRecentActivityItem, SessionSummaryClosure, SessionSummaryPosition, SkipDecisionResult, SkipReason, TradeSession, TradeSessionCreateInput, TradeSessionListResponse, WaitDecisionResult, WaitUpdateAnalysisRead, WaitUpdateAnalysisSubmission, WaitUpdateInputResponse, WaitUpdateRecoveryResponse } from "./types";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${publicEnv.apiBaseUrl}${path}`, { ...options, credentials: "include" });
  if (!response.ok) {
    let message = "Permintaan tidak dapat diproses.";
    try { const body = await response.json(); message = body?.detail?.message ?? body?.detail ?? message; } catch { /* non-json error */ }
    throw new Error(typeof message === "string" ? message : "Permintaan tidak dapat diproses.");
  }
  return response.json() as Promise<T>;
}

const base = "/v2/trade-sessions";

export function listSessions(signal?: AbortSignal): Promise<TradeSessionListResponse> {
  return get<TradeSessionListResponse>(`/api${base}`, undefined, signal);
}
export function listArchivedSessions(signal?: AbortSignal): Promise<TradeSessionListResponse> {
  return get<TradeSessionListResponse>(`/api${base}/archived`, undefined, signal);
}
export function getSession(id: string, signal?: AbortSignal): Promise<TradeSession> {
  return get<TradeSession>(`/api${base}/${id}`, undefined, signal);
}
export async function getSessionDetail(
  id: string,
  signal?: AbortSignal,
): Promise<SessionDetailAggregate> {
  const payload = await get<unknown>(`/api${base}/${id}/detail`, undefined, signal);
  return parseSessionDetailAggregate(payload);
}
export function createSession(input: TradeSessionCreateInput, signal?: AbortSignal): Promise<TradeSession> {
  return post<TradeSession>(`/api${base}`, input, { signal });
}
export function uploadInitialEvidence(id: string, files: { orderbook: File; chart_3_month: File; chart_6_month: File; foreign_flow_1w: File }): Promise<InitialEvidenceUploadResponse> {
  const body = new FormData(); body.append("orderbook", files.orderbook); body.append("chart_3_month", files.chart_3_month); body.append("chart_6_month", files.chart_6_month); body.append("foreign_flow_1w", files.foreign_flow_1w);
  return request(`${base}/${id}/initial-evidence`, { method: "POST", body });
}
export function readInitialEvidence(id: string): Promise<InitialEvidenceUploadResponse> { return request(`${base}/${id}/initial-evidence`); }
export function submitInitialAnalysis(id: string): Promise<InitialAnalysisSubmission> { return request(`${base}/${id}/initial-analysis`, { method: "POST" }); }
export function readInitialAnalysis(id: string, signal?: AbortSignal): Promise<InitialAnalysisRead> { return request(`${base}/${id}/initial-analysis`, { signal }); }
export function retryInitialAnalysis(id: string): Promise<InitialAnalysisSubmission> { return request(`${base}/${id}/initial-analysis/retry`, { method: "POST" }); }
export function uploadWaitUpdateInput(id: string, input: { orderbook: File; broker_flow_1d?: File | null; current_price: string; observation_period: ObservationPeriod; observation_timestamp: string }): Promise<WaitUpdateInputResponse> {
  const body = new FormData();
  body.append("orderbook", input.orderbook);
  if (input.broker_flow_1d) body.append("broker_flow_1d", input.broker_flow_1d);
  body.append("current_price", input.current_price);
  body.append("observation_period", input.observation_period);
  body.append("observation_timestamp", input.observation_timestamp);
  return request(`${base}/${id}/wait-update-input`, { method: "POST", body });
}
export function submitWaitUpdateAnalysis(id: string): Promise<WaitUpdateAnalysisSubmission> { return request(`${base}/${id}/wait-updates`, { method: "POST" }); }
export function readWaitUpdateAnalysis(id: string, signal?: AbortSignal): Promise<WaitUpdateAnalysisRead> { return request(`${base}/${id}/wait-update-analysis`, { signal }); }
export function retryWaitUpdateAnalysis(id: string): Promise<WaitUpdateRecoveryResponse> { return request(`${base}/${id}/wait-update-analysis/retry`, { method: "POST" }); }
export function getAvailableActions(id: string): Promise<DecisionAvailability> { return request(`${base}/${id}/available-actions`); }
export function waitDecision(id: string): Promise<WaitDecisionResult> { return request(`${base}/${id}/decisions/wait`, { method: "POST" }); }
export function skipDecision(id: string, body: { reason: SkipReason; note?: string | null }): Promise<SkipDecisionResult> {
  return request(`${base}/${id}/decisions/skip`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
export function buyDecision(id: string, body: { entry_price: string; entry_timestamp: string; quantity: string; stop_loss: string; target_price: string; note?: string | null }): Promise<BuyDecisionResult> {
  return request(`${base}/${id}/decisions/buy`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export function uploadPositionUpdateInput(id: string, input: { orderbook: File; broker_flow_1d?: File | null; current_price: string; observation_period: ObservationPeriod; observation_timestamp: string }): Promise<PositionUpdateInputResponse> {
  const body = new FormData();
  body.append("orderbook", input.orderbook);
  if (input.broker_flow_1d) body.append("broker_flow_1d", input.broker_flow_1d);
  body.append("current_price", input.current_price);
  body.append("observation_period", input.observation_period);
  body.append("observation_timestamp", input.observation_timestamp);
  return request(`${base}/${id}/position-update-input`, { method: "POST", body });
}
export function submitPositionUpdateAnalysis(id: string): Promise<PositionUpdateAnalysisSubmission> { return request(`${base}/${id}/position-updates`, { method: "POST" }); }
export function readPositionUpdates(id: string, signal?: AbortSignal): Promise<PositionUpdatesRead> { return request(`${base}/${id}/position-updates`, { signal }); }
export function closePosition(id: string, body: CloseRequest): Promise<CloseResponse> {
  return request(`${base}/${id}/close`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
export function archiveSessionV2(id: string): Promise<{ id: string; status: string; archived_at: string }> {
  return request(`${base}/${id}/archive`, { method: "POST" });
}
export function restoreSessionV2(id: string): Promise<{ id: string; status: string; archived_at: null }> {
  return request(`${base}/${id}/restore`, { method: "POST" });
}

export function previewMarketEvidence(
  sessionId: string,
  symbol?: string,
  signal?: AbortSignal,
): Promise<{ snapshot: any; validation: { is_valid: boolean; completeness_status: string; critical_errors: string[]; warnings: string[] } }> {
  const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
  return get(`/api/sessions/${sessionId}/market-evidence/preview${query}`, undefined, signal);
}

export function acquireMarketEvidence(
  sessionId: string,
  snapshotType = "INITIAL",
  symbol?: string,
  signal?: AbortSignal,
): Promise<{ snapshot: any; validation: { is_valid: boolean; completeness_status: string; critical_errors: string[]; warnings: string[] } }> {
  const params = new URLSearchParams({ snapshot_type: snapshotType });
  if (symbol) params.append("symbol", symbol);
  return post(`/api/sessions/${sessionId}/market-evidence/acquire?${params.toString()}`, {}, { signal });
}

export function analyzeSession(
  sessionId: string,
  symbol?: string,
  signal?: AbortSignal,
): Promise<any> {
  const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
  return post(`/api/sessions/${sessionId}/analyze${query}`, {}, { signal });
}

export function getSessionWorkspaceData(
  sessionId: string,
  signal?: AbortSignal,
): Promise<{ session: TradeSession; analysis: any }> {
  return get(`/api/sessions/${sessionId}/workspace`, undefined, signal);
}

export type { EvidenceFile };

const CURRENT_STEP_CODES = new Set<CurrentStepCode>([
  "INITIAL_EVIDENCE", "INITIAL_ANALYSIS", "PROCESSING", "DECISION",
  "WAIT_UPDATE", "POSITION_MONITORING", "FAILED_REQUEST", "TERMINAL_CLOSED",
  "TERMINAL_SKIPPED", "ARCHIVED_CLOSED", "ARCHIVED_SKIPPED", "INCONSISTENT",
]);
const CURRENT_STEP_MODES = new Set<CurrentStepMode>([
  "ACTIONABLE", "PROCESSING", "FAILED", "READ_ONLY", "INCONSISTENT",
]);
const CURRENT_STEP_ACTIONS = new Set<CurrentStepWorkflowAction>([
  "SUBMIT_INITIAL_EVIDENCE", "REQUEST_INITIAL_ANALYSIS", "BUY", "WAIT", "SKIP",
  "SUBMIT_WAIT_UPDATE", "SUBMIT_POSITION_UPDATE", "CLOSE",
  "RETRY_INITIAL_ANALYSIS", "RETRY_WAIT_UPDATE",
]);
const ANALYSIS_TYPES = new Set(["INITIAL_ANALYSIS", "WAIT_UPDATE", "POSITION_UPDATE"]);
const ACTIVITY_TYPES = new Set<SessionActivityType>([
  "SESSION_CREATED", "INITIAL_ANALYSIS_COMPLETED", "BUY_CONFIRMED", "WAIT_CONFIRMED",
  "SKIP_CONFIRMED", "WAIT_UPDATE_COMPLETED", "POSITION_UPDATE_COMPLETED", "SESSION_CLOSED",
  "SESSION_ARCHIVED",
]);
const DECISIONS = new Set(["BUY", "WAIT", "SKIP"]);
const REQUEST_STATUSES = new Set<RequestStatus>([
  "PENDING", "PROCESSING", "COMPLETED", "FAILED",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseRequest(value: unknown): CurrentStepActiveRequest | null | undefined {
  if (value === null) return null;
  if (
    !isRecord(value) ||
    typeof value.id !== "string" ||
    typeof value.analysis_type !== "string" ||
    !ANALYSIS_TYPES.has(value.analysis_type) ||
    typeof value.status !== "string" ||
    !REQUEST_STATUSES.has(value.status as RequestStatus)
  ) {
    return undefined;
  }
  return value as unknown as CurrentStepActiveRequest;
}

function parseFailedRequest(value: unknown): CurrentStepFailedRequest | null | undefined {
  const request = parseRequest(value);
  if (request === null || request === undefined) return request;
  if (!isRecord(value) || typeof value.retry_allowed !== "boolean") return undefined;
  return value as unknown as CurrentStepFailedRequest;
}

export function parseCurrentStep(value: unknown): CurrentStep | null {
  if (!isRecord(value)) return null;
  if (
    typeof value.code !== "string" ||
    !CURRENT_STEP_CODES.has(value.code as CurrentStepCode) ||
    typeof value.mode !== "string" ||
    !CURRENT_STEP_MODES.has(value.mode as CurrentStepMode) ||
    !Array.isArray(value.workflow_actions) ||
    !value.workflow_actions.every(
      (action) => typeof action === "string" && CURRENT_STEP_ACTIONS.has(action as CurrentStepWorkflowAction),
    ) ||
    typeof value.read_only !== "boolean"
  ) {
    return null;
  }
  const activeRequest = parseRequest(value.active_request);
  const failedRequest = parseFailedRequest(value.failed_request);
  if (activeRequest === undefined || failedRequest === undefined) return null;
  return {
    code: value.code as CurrentStepCode,
    mode: value.mode as CurrentStepMode,
    workflow_actions: [...value.workflow_actions] as CurrentStepWorkflowAction[],
    active_request: activeRequest,
    failed_request: failedRequest,
    read_only: value.read_only,
  };
}

export function parseSessionDetailAggregate(value: unknown): SessionDetailAggregate {
  if (!isRecord(value)) throw new Error("INVALID_SESSION_DETAIL_CONTRACT");
  const currentStep = parseCurrentStep(value.current_step);
  if (currentStep === null) throw new Error("INVALID_CURRENT_STEP_CONTRACT");
  return {
    ...(value as unknown as SessionDetailAggregate),
    current_step: currentStep,
    latest_analysis: parseLatestAnalysis(value.latest_analysis),
    recent_activity: parseRecentActivity(value.recent_activity),
    position: parsePosition(value.position) as unknown as Record<string, unknown> | null,
    closure: parseClosure(value.closure) as unknown as Record<string, unknown> | null,
  };
}

function isTimestamp(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(new Date(value).getTime());
}

function optionalFiniteNumber(value: unknown): number | null | undefined {
  if (value === null || value === undefined) return null;
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function optionalString(value: unknown): string | null | undefined {
  if (value === null || value === undefined) return null;
  return typeof value === "string" ? value : undefined;
}

function parseLatestAnalysis(value: unknown): LatestAnalysisSummary | null {
  if (value === null || !isRecord(value)) return null;
  if (
    typeof value.analysis_type !== "string" || !ANALYSIS_TYPES.has(value.analysis_type) ||
    !isTimestamp(value.completed_at) || typeof value.has_result !== "boolean"
  ) return null;
  return value as unknown as LatestAnalysisSummary;
}

function parseRecentActivity(value: unknown): SessionRecentActivityItem[] {
  if (!Array.isArray(value)) return [];
  return value.slice(0, 3).flatMap((item) => {
    if (!isRecord(item) || typeof item.type !== "string" || !ACTIVITY_TYPES.has(item.type as SessionActivityType) || !isTimestamp(item.occurred_at)) return [];
    const analysisType = item.analysis_type;
    const decision = item.decision;
    if (analysisType !== null && analysisType !== undefined && (typeof analysisType !== "string" || !ANALYSIS_TYPES.has(analysisType))) return [];
    if (decision !== null && decision !== undefined && (typeof decision !== "string" || !DECISIONS.has(decision))) return [];
    return [{ type: item.type, occurred_at: item.occurred_at, analysis_type: analysisType ?? null, decision: decision ?? null } as SessionRecentActivityItem];
  });
}

function parsePosition(value: unknown): SessionSummaryPosition | null {
  if (value === null || !isRecord(value) || typeof value.status !== "string") return null;
  const entryPrice = optionalFiniteNumber(value.entry_price);
  const quantity = optionalFiniteNumber(value.quantity);
  const stopLoss = optionalFiniteNumber(value.stop_loss);
  const targetPrice = optionalFiniteNumber(value.target_price);
  const entryTimestamp = optionalString(value.entry_timestamp);
  const note = optionalString(value.note);
  const closedAt = optionalString(value.closed_at);
  if ([entryPrice, quantity, stopLoss, targetPrice, entryTimestamp, note, closedAt].includes(undefined)) return null;
  return { status: value.status, entry_price: entryPrice!, quantity: quantity!, stop_loss: stopLoss!, target_price: targetPrice!, entry_timestamp: entryTimestamp!, note: note!, closed_at: closedAt! };
}

function parseClosure(value: unknown): SessionSummaryClosure | null {
  if (value === null || !isRecord(value)) return null;
  const closePrice = optionalFiniteNumber(value.close_price);
  const closeTimestamp = optionalString(value.close_timestamp);
  const closeReason = optionalString(value.close_reason);
  const note = optionalString(value.note);
  if ([closePrice, closeTimestamp, closeReason, note].includes(undefined)) return null;
  return { close_price: closePrice!, close_timestamp: closeTimestamp!, close_reason: closeReason!, note: note! };
}
