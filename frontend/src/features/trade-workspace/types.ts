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
