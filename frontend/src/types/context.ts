/** GET /api/trade-sessions/{id}/context */
export interface ContextSummary {
  id: string;
  session_id: string;
  context_version: number;
  source_cutoff: string | null;
  is_stale: boolean;
  quality: string;
  payload: Record<string, unknown> | null;
  created_at: string;
}
