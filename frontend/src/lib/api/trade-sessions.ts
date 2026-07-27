import { get, post, patch } from "./client";
import type {
  CreateTradeSessionRequest,
  CreateTradeSessionResponse,
  ListTradeSessionsResponse,
  TradeSessionDetail,
  UpdateTradeSessionRequest,
  ReadyResponse,
  ArchiveResponse,
  EvidenceBatchSummary,
} from "@/types/trade-session";

export interface ConfirmStopRequest {
  price: number;
  confirmed_at?: string;
  note?: string;
  idempotency_key: string;
}

export interface ConfirmTargetRequest {
  price: number;
  confirmed_at?: string;
  note?: string;
  idempotency_key: string;
}

export interface StopLossConfirmResponse {
  session_id: string;
  action_type: string;
  active_stop_loss: number | null;
}

export interface TargetConfirmResponse {
  session_id: string;
  action_type: string;
  active_target: number | null;
}

export function createSession(data: CreateTradeSessionRequest): Promise<CreateTradeSessionResponse> {
  return post<CreateTradeSessionResponse>("/api/trade-sessions", data);
}

export function listSessions(
  query?: { status?: string; ticker?: string; limit?: number; offset?: number },
): Promise<ListTradeSessionsResponse> {
  return get<ListTradeSessionsResponse>("/api/trade-sessions", query);
}

export function getSession(sessionId: string): Promise<TradeSessionDetail> {
  return get<TradeSessionDetail>(`/api/trade-sessions/${sessionId}`);
}

export function updateSession(
  sessionId: string,
  data: UpdateTradeSessionRequest,
): Promise<CreateTradeSessionResponse> {
  return patch<CreateTradeSessionResponse>(`/api/trade-sessions/${sessionId}`, data);
}

export function markReady(sessionId: string): Promise<ReadyResponse> {
  return post<ReadyResponse>(`/api/trade-sessions/${sessionId}/ready`);
}

export function ensureWatchingBatch(sessionId: string): Promise<EvidenceBatchSummary> {
  return post<EvidenceBatchSummary>(`/api/trade-sessions/${sessionId}/watching-batches`);
}

export function markWatchingBatchReady(
  sessionId: string,
  batchId: string,
): Promise<EvidenceBatchSummary> {
  return post<EvidenceBatchSummary>(
    `/api/trade-sessions/${sessionId}/watching-batches/${batchId}/ready`,
  );
}

export function ensureOpenPositionBatch(sessionId: string): Promise<EvidenceBatchSummary> {
  return post<EvidenceBatchSummary>(`/api/trade-sessions/${sessionId}/open-position-batches`);
}

export function updateOpenPositionBatchSlot(
  sessionId: string,
  batchId: string,
  slot: string,
): Promise<EvidenceBatchSummary> {
  return patch<EvidenceBatchSummary>(
    `/api/trade-sessions/${sessionId}/open-position-batches/${batchId}/slot`,
    { slot },
  );
}

export function markOpenPositionBatchReady(
  sessionId: string,
  batchId: string,
): Promise<EvidenceBatchSummary> {
  return post<EvidenceBatchSummary>(
    `/api/trade-sessions/${sessionId}/open-position-batches/${batchId}/ready`,
  );
}

export function confirmStop(
  sessionId: string,
  data: ConfirmStopRequest,
): Promise<StopLossConfirmResponse> {
  return post<StopLossConfirmResponse>(`/api/trade-sessions/${sessionId}/confirm-stop`, data);
}

export function confirmTarget(
  sessionId: string,
  data: ConfirmTargetRequest,
): Promise<TargetConfirmResponse> {
  return post<TargetConfirmResponse>(`/api/trade-sessions/${sessionId}/confirm-target`, data);
}

export function archiveSession(sessionId: string): Promise<ArchiveResponse> {
  return post<ArchiveResponse>(`/api/trade-sessions/${sessionId}/archive`);
}

export function getSessionContext(sessionId: string): Promise<Record<string, unknown>> {
  return get<Record<string, unknown>>(`/api/trade-sessions/${sessionId}/context`);
}
