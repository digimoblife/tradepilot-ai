/** Reference to a related Trade Action */
export interface TimelineActionRef {
  id: string;
  action_type: string;
  confirmed_at: string;
  price: string | null;
  quantity: string | null;
}

/** Reference to a related accepted Analysis */
export interface TimelineAnalysisRef {
  id: string;
  analysis_type: string;
  accepted_at: string | null;
  schema_name: string;
  schema_version: string;
}

/** One timeline event */
export interface TimelineEvent {
  id: string;
  session_id: string;
  event_type: string;
  occurred_at: string;
  created_at: string;
  summary: string | null;
  price: string | null;
  quantity: string | null;
  related_action: TimelineActionRef | null;
  related_analysis: TimelineAnalysisRef | null;
}

/** GET /api/trade-sessions/{id}/timeline */
export interface ListTimelineResponse {
  events: TimelineEvent[];
  total: number;
}
