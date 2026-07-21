export interface PriceLevel {
  price: number;
  label: string;
  summary: string;
}

export interface Metadata {
  analysis_id: string;
  session_id: string;
  analysis_type: string;
  ticker: string;
  company_name: string;
  analysis_timestamp: string;
  language: string;
  schema: { schema_name: string; schema_version: string };
  prompt_version: string;
  provider: string;
  model: string;
}

export interface ExecutiveSummary {
  headline: string;
  main_opportunity: string;
  main_risk: string;
  setup_status: string;
  recommended_action: string;
  summary: string;
}

export interface OrderbookAnalysis {
  market_timestamp: string;
  available: boolean;
  buyer_strength: string;
  seller_pressure: string;
  best_bid: number;
  best_offer: number;
  bid_support: PriceLevel | null;
  offer_resistance: PriceLevel | null;
  positive_signals: string[];
  buyer_observations: string[];
  risk_signals: string[];
  seller_observations: string[];
  supports_entry: boolean;
  conclusion: string;
  limitations: string[];
}

export interface ChartAnalysis {
  available: boolean;
  timeframe: string;
  chart_timestamp: string;
  momentum: string;
  volume_condition: string;
  breakout_status: string;
  breakdown_status: string;
  positive_signals: string[];
  risk_signals: string[];
  trend: string;
  structure_status: string;
  nearest_support: PriceLevel | null;
  nearest_resistance: PriceLevel | null;
  conclusion: string;
  supports_setup: boolean;
  limitations: string[];
}

export interface CombinedChartAnalysis {
  multi_timeframe_alignment: string;
  short_term_trend: string;
  dominant_structure: string;
  setup_supported: boolean;
  medium_term_trend: string;
  main_confirmation: string;
  main_conflict: string;
  conclusion: string;
}

export interface PriceLevels {
  entry_reference: PriceLevel | null;
  invalidation_level: PriceLevel | null;
  stop_loss_level: PriceLevel | null;
  target_level: PriceLevel | null;
  summary: string;
  supports: PriceLevel[];
  resistances: PriceLevel[];
}

export interface EntryPlan {
  entry_recommended: boolean;
  entry_type: string;
  entry_price: number | null;
  confirmation_required: boolean;
  confirmation_condition: string;
  chase_risk: string;
  maximum_acceptable_entry: number;
  cancel_entry_condition: string;
  entry_zone_low: number;
  entry_zone_high: number;
  summary: string;
}

export interface StopLossPlan {
  stop_loss_recommended: boolean;
  stop_loss_price: number;
  risk_from_reference_entry_percentage: number;
  invalidation_condition: string;
  reason: string;
  maximum_risk_respected: boolean;
  summary: string;
}

export interface TargetPlan {
  target_recommended: boolean;
  target_price: number;
  reward_from_reference_entry_percentage: number;
  target_basis: string;
  primary_obstacle: string;
  required_condition: string;
  risk_reward_ratio: number;
  summary: string;
}

export interface InitialThesis {
  status: string;
  setup_reason: string;
  supporting_factors: string[];
  risk_factors: string[];
  support_condition: string;
  invalidation_price: number;
  expected_holding_period: string;
  review_conditions: string[];
  invalidation_condition: string;
  summary: string;
}

export interface TradingPlan {
  current_action: string;
  action_rationale: string;
  entry_condition: string;
  post_entry_hold_condition: string;
  post_entry_exit_condition: string;
  wait_condition: string;
  next_checkpoint: string;
  cancel_setup_condition: string;
  levels_to_monitor: string[];
  requires_user_confirmation: boolean;
}

export interface AiAssessment {
  setup_quality: string;
  setup_valid: boolean;
  bias: string;
  confidence: number;
  bullish_probability: number;
  target_probability: number;
  downside_probability: number;
  risk_level: string;
  summary: string;
}

export interface WarningsInfo {
  missing_information: string[];
  warnings: string[];
}

export interface InitialAnalysisPayload {
  metadata: Metadata;
  evidence_summary: Record<string, unknown>;
  market_snapshot: Record<string, unknown>;
  executive_summary: ExecutiveSummary;
  orderbook_analysis: OrderbookAnalysis;
  chart_3_month_analysis: ChartAnalysis;
  chart_6_month_analysis: ChartAnalysis;
  combined_chart_analysis: CombinedChartAnalysis;
  price_levels: PriceLevels;
  entry_plan: EntryPlan;
  stop_loss_plan: StopLossPlan;
  target_plan: TargetPlan;
  initial_thesis: InitialThesis;
  trading_plan: TradingPlan;
  ai_assessment: AiAssessment;
  warnings_and_missing_information: WarningsInfo;
}
