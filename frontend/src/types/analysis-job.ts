/** Analysis job reference from create response */
export interface AnalysisJobCreated {
  job_id: string;
  session_id: string;
  analysis_type: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  available_at: string;
  created_at: string;
  previous_session_status: string | null;
}

/** GET /api/analysis-jobs/{id} */
export interface AnalysisJobStatus {
  job_id: string;
  session_id: string;
  analysis_type: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  available_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  analysis_id: string | null;
  created_at: string;
  updated_at: string;
}

/** POST /api/analysis-jobs/{id}/retry */
export interface RetryResponse {
  job_id: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
}
