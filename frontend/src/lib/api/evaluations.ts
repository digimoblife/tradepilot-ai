import { get } from "./client";

export interface EvaluationRecordItem {
  id: string;
  owner_id: string;
  session_id: string;
  source_analysis_id?: string | null;
  ticker: string;
  analysis_type: string;
  prompt_name?: string | null;
  prompt_version?: string | null;
  schema_name?: string | null;
  schema_version?: string | null;
  provider?: string | null;
  model?: string | null;
  prediction_data: Record<string, unknown>;
  user_decision_data: Record<string, unknown>;
  outcome_data: Record<string, unknown>;
  completeness_status: string;
  legacy_source: boolean;
  validation_warning_count: number;
  quality_notes: string[];
  created_at: string;
  updated_at: string;
}

export interface EvaluationRecordListResponse {
  items: EvaluationRecordItem[];
  total: number;
  page: number;
  limit: number;
}

export function listEvaluationRecords(params?: {
  ticker?: string;
  analysis_type?: string;
  completeness_status?: string;
  page?: number;
  limit?: number;
}): Promise<EvaluationRecordListResponse> {
  const query = new URLSearchParams();
  if (params?.ticker) query.set("ticker", params.ticker);
  if (params?.analysis_type) query.set("analysis_type", params.analysis_type);
  if (params?.completeness_status) query.set("completeness_status", params.completeness_status);
  if (params?.page) query.set("page", params.page.toString());
  if (params?.limit) query.set("limit", params.limit.toString());

  const qStr = query.toString();
  return get<EvaluationRecordListResponse>(`/api/evaluation-records${qStr ? `?${qStr}` : ""}`);
}

export function getEvaluationRecordDetail(recordId: string): Promise<EvaluationRecordItem> {
  return get<EvaluationRecordItem>(`/api/evaluation-records/${recordId}`);
}
