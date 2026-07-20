import { get, post } from "./client";
import type { AnalysisRequest, ListAnalysesResponse, AnalysisDetail } from "@/types/analysis";
import type { AnalysisJobCreated, AnalysisJobStatus, RetryResponse } from "@/types/analysis-job";

export function requestAnalysis(
  sessionId: string,
  data: AnalysisRequest,
): Promise<AnalysisJobCreated> {
  return post<AnalysisJobCreated>(`/api/trade-sessions/${sessionId}/analyses`, data);
}

export function listAnalyses(
  sessionId: string,
  query?: { analysis_type?: string; limit?: number; offset?: number },
): Promise<ListAnalysesResponse> {
  return get<ListAnalysesResponse>(`/api/trade-sessions/${sessionId}/analyses`, query);
}

export function getAnalysis(analysisId: string): Promise<AnalysisDetail> {
  return get<AnalysisDetail>(`/api/analyses/${analysisId}`);
}

export function getJobStatus(jobId: string): Promise<AnalysisJobStatus> {
  return get<AnalysisJobStatus>(`/api/analysis-jobs/${jobId}`);
}

export function retryJob(jobId: string): Promise<RetryResponse> {
  return post<RetryResponse>(`/api/analysis-jobs/${jobId}/retry`);
}
