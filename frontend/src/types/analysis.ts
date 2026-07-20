/** POST /api/trade-sessions/{id}/analyses */
export interface AnalysisRequest {
  analysis_type: string;
}

/** Analysis summary for list */
export interface AnalysisSummary {
  id: string;
  session_id: string;
  analysis_type: string;
  acceptance_status: string;
  accepted_at: string | null;
  created_at: string;
  prompt_version: string;
  schema_name: string;
  schema_version: string;
  supersedes_analysis_id: string | null;
}

/** GET /api/trade-sessions/{id}/analyses */
export interface ListAnalysesResponse {
  analyses: AnalysisSummary[];
  total: number;
}

/** GET /api/analyses/{id} */
export interface AnalysisDetail {
  id: string;
  session_id: string;
  analysis_type: string;
  acceptance_status: string;
  accepted_at: string | null;
  created_at: string;
  prompt_name: string;
  prompt_version: string;
  schema_name: string;
  schema_version: string;
  payload: Record<string, unknown> | null;
  supersedes_analysis_id: string | null;
}
