export type SessionStatus =
  | "DRAFT" | "ANALYZING" | "ANALYZED" | "WAITING"
  | "OPEN_POSITION" | "CLOSED" | "CLOSED_SKIPPED";

export type RequestStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
export type DecisionAction = "BUY" | "WAIT" | "SKIP" | "CLOSE";
export type SkipReason =
  | "RISK_TOO_HIGH"
  | "SETUP_NOT_ATTRACTIVE"
  | "ORDERBOOK_WEAK"
  | "MARKET_CONDITION_UNFAVORABLE"
  | "WAITING_TOO_LONG"
  | "USER_DECISION"
  | "OTHER";

export interface TradeSession {
  id: string; ticker: string; company_name: string; status: SessionStatus;
  note: string | null; created_at: string; updated_at: string; closed_at: string | null;
}

export interface SessionDetailAggregate {
  session: {
    id: string;
    ticker: string;
    company_name: string;
    status: SessionStatus;
    initial_note: string | null;
    created_at: string;
    updated_at: string;
    closed_at: string | null;
  };
  initial_evidence: Array<Record<string, unknown>>;
  initial_analysis: Record<string, unknown> | null;
  decisions: Array<{ decision_id?: string; decision: "BUY" | "WAIT" | "SKIP"; reason?: string | null; note?: string | null; created_at: string }>;
  wait_updates: Array<Record<string, unknown>>;
  position: Record<string, unknown> | null;
  position_updates: Array<Record<string, unknown>>;
  closure: Record<string, unknown> | null;
}

export interface EvidenceFile {
  id: string; evidence_type: string; original_filename: string;
  mime_type: string; size_bytes: number; uploaded_at: string;
}

export interface InitialEvidenceUploadResponse { evidence: EvidenceFile[] }

export interface InitialAnalysisSubmission {
  analysis_request_id: string; session_id: string; analysis_type: string;
  request_status: RequestStatus; session_status: SessionStatus; created_at: string;
}

export interface InitialAnalysisRead extends InitialAnalysisSubmission {
  processed_response: InitialAnalysisResult | null;
  error_code: string | null; error_message: string | null;
  started_at: string | null; completed_at: string | null;
}

export type ObservationPeriod = "MORNING" | "MIDDAY" | "AFTERNOON";

export interface WaitUpdateInputResponse {
  evidence_id: string;
  session_id: string;
  evidence_type: "ORDERBOOK";
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  current_price: string;
  observation_period: ObservationPeriod;
  observation_timestamp: string;
  uploaded_at: string;
  session_status: "WAITING";
}

export interface WaitUpdateAnalysisSubmission {
  analysis_request_id: string;
  session_id: string;
  analysis_type: "WAIT_UPDATE";
  request_status: RequestStatus;
  evidence_id: string;
  observation_period: ObservationPeriod;
  session_status: SessionStatus;
  created_at: string;
}

export interface WaitUpdateAnalysisRead {
  analysis_request_id: string;
  session_id: string;
  analysis_type: "WAIT_UPDATE";
  request_status: RequestStatus;
  session_status: SessionStatus;
  processed_response: WaitUpdateResult | null;
  error_code: string | null;
  error_message: string | null;
  observation_period: ObservationPeriod | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface WaitUpdateRecoveryResponse {
  analysis_request_id: string;
  session_id: string;
  analysis_type: "WAIT_UPDATE";
  request_status: RequestStatus;
  session_status: SessionStatus;
  observation_period: ObservationPeriod | null;
  created_at: string;
}

export interface WaitUpdateResult {
  update_summary: unknown;
  current_price: unknown;
  orderbook_assessment: unknown;
  change_from_previous_analysis: unknown;
  current_entry_condition: unknown;
  upside_probability: unknown;
  downside_probability: unknown;
  key_risks: unknown;
  recommended_action: unknown;
  next_plan: unknown;
  conclusion: unknown;
}

export interface DecisionAvailability {
  session_id: string;
  session_status: SessionStatus;
  available_actions: DecisionAction[];
}

export interface WaitDecisionResult {
  decision_id: string;
  session_id: string;
  decision_type: "WAIT";
  decision_at: string;
  session_status: "WAITING";
}

export interface SkipDecisionResult {
  decision_id: string;
  session_id: string;
  decision_type: "SKIP";
  reason: SkipReason;
  note: string | null;
  decision_at: string;
  session_status: "CLOSED_SKIPPED";
  closed_at: string;
}

export interface BuyDecisionResult {
  decision_id: string;
  session_id: string;
  decision_type: "BUY";
  decision_at: string;
  position_id: string;
  position_status: "OPEN";
  entry_price: string;
  entry_timestamp: string;
  quantity: string;
  stop_loss: string;
  target_price: string;
  note: string | null;
  session_status: "OPEN_POSITION";
}

export interface InitialAnalysisResult {
  summary: string;
  orderbook_analysis: string;
  three_month_chart_analysis: string;
  six_month_chart_analysis: string;
  support: { low: number | string; high: number | string; note: string };
  resistance: { low: number | string; high: number | string; note: string };
  entry_area: { low: number | string; high: number | string; note: string };
  stop_recommendation: { level: number | string; note: string };
  target_recommendation: { level: number | string; note: string };
  probabilities: { upside: number | string; downside: number | string };
  risks: string[];
  trading_plan: string;
  conclusion: string;
}

export interface PositionUpdateInputResponse {
  evidence_id: string;
  session_id: string;
  position_id: string;
  evidence_type: "ORDERBOOK";
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  current_price: string;
  observation_period: ObservationPeriod;
  observation_timestamp: string;
  uploaded_at: string;
  session_status: "OPEN_POSITION";
  position_status: string;
}

export interface PositionUpdateAnalysisSubmission {
  analysis_request_id: string;
  session_id: string;
  position_id: string;
  analysis_type: "POSITION_UPDATE";
  request_status: RequestStatus;
  evidence_id: string;
  observation_period: ObservationPeriod;
  session_status: SessionStatus;
  position_status: string;
  created_at: string;
}

export interface PositionDetail {
  id: string;
  session_id: string;
  status: "OPEN" | "CLOSED" | string;
  entry_price: string;
  entry_timestamp: string;
  quantity: string;
  stop_loss: string;
  target_price: string;
  note: string | null;
  created_at: string;
}

export interface PositionUpdateResult {
  update_summary?: unknown;
  current_price?: unknown;
  position_condition?: unknown;
  orderbook_assessment?: unknown;
  change_from_previous_analysis?: unknown;
  target_realism?: unknown;
  downside_risk?: unknown;
  target_probability?: unknown;
  trading_plan?: unknown;
  monitoring_points?: unknown;
  warnings?: unknown;
  conclusion?: unknown;
}

export interface PositionUpdateItem {
  analysis_request_id: string;
  session_id: string;
  analysis_type: "POSITION_UPDATE";
  request_status: RequestStatus;
  current_price: string | null;
  observation_period: ObservationPeriod | null;
  observation_timestamp: string | null;
  processed_response: PositionUpdateResult | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  evidence_id?: string | null;
  original_filename?: string | null;
}

export interface PositionUpdatesRead {
  position: PositionDetail | null;
  updates: PositionUpdateItem[];
}

export interface CloseRequest {
  close_price: string;
  close_timestamp: string;
  close_reason: string;
  note?: string | null;
}

export interface CloseResponse {
  closure_id: string;
  session_id: string;
  position_id: string;
  close_price: string;
  close_timestamp: string;
  close_reason: string;
  note: string | null;
  realized_profit_loss: string;
  position_status: string;
  session_status: string;
  closed_at: string;
  created_at: string;
}
