import { get, post, patch } from "./client";
import type {
  CreateTradeSessionRequest,
  CreateTradeSessionResponse,
  ListTradeSessionsResponse,
  TradeSessionDetail,
  UpdateTradeSessionRequest,
  ReadyResponse,
  ArchiveResponse,
} from "@/types/trade-session";
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

export function archiveSession(sessionId: string): Promise<ArchiveResponse> {
  return post<ArchiveResponse>(`/api/trade-sessions/${sessionId}/archive`);
}

export function getSessionContext(sessionId: string): Promise<Record<string, unknown>> {
  return get<Record<string, unknown>>(`/api/trade-sessions/${sessionId}/context`);
}
