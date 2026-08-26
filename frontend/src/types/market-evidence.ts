export interface QuoteDomain {
  last_price: number;
  change: number;
  change_percent: number;
  previous_close: number;
  open: number;
  high: number;
  low: number;
  volume_shares: number;
  volume_lots: number;
  value_idr: number;
  frequency: number;
  pe_ratio?: number;
  pbv_ratio?: number;
  market_cap?: number;
  timestamp?: string;
}

export interface OrderbookLevel {
  price: number;
  lots: number;
}

export interface OrderbookDomain {
  best_bid: number;
  best_ask: number;
  spread: number;
  spread_percent: number;
  total_bid_lots: number;
  total_ask_lots: number;
  bid_ask_ratio: number;
  bid_percent: number;
  ask_percent: number;
  bids: OrderbookLevel[];
  asks: OrderbookLevel[];
  timestamp?: string;
}

export interface HistoricalBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  value?: number;
  net_foreign_shares?: number;
}

export interface HistoricalDomain {
  horizon_days: number;
  start_date?: string;
  end_date?: string;
  computed_technical: Record<string, any>;
  recent_bars: HistoricalBar[];
}

export interface ForeignFlowPeriod {
  net_shares: number;
  net_value_idr: number;
  buy_shares?: number;
  sell_shares?: number;
}

export interface ForeignFlowDomain {
  today_1d?: ForeignFlowPeriod;
  weekly_1w?: ForeignFlowPeriod;
  monthly_1m?: ForeignFlowPeriod;
  three_month_3m?: ForeignFlowPeriod;
  foreign_status: string;
  recent_daily_series: Array<{ date: string; net_shares: number; close: number }>;
}

export interface BrokerItem {
  broker: string;
  lots: number;
  value_idr: number;
  avg_price: number;
  market_share_percent?: number;
}

export interface BrokerFlowDomain {
  date?: string;
  is_net: boolean;
  top3_buyer_concentration_percent: number;
  top3_seller_concentration_percent: number;
  bandar_status: string;
  top_buyers: BrokerItem[];
  top_sellers: BrokerItem[];
}

export interface MarketContextDomain {
  index_code: string;
  index_name: string;
  index_price?: number;
  index_change_percent?: number;
  index_trend: string;
}

export interface EvidenceSnapshot {
  snapshot_id: string;
  session_id: string;
  symbol: string;
  market: string;
  captured_at: string;
  snapshot_type: string;
  sequence_number: number;
  providers_used: Record<string, string>;
  completeness_status: string;
  quote: QuoteDomain;
  orderbook: OrderbookDomain;
  historical_ohlcv: HistoricalDomain;
  foreign_flow: ForeignFlowDomain;
  broker_flow: BrokerFlowDomain;
  market_context: MarketContextDomain;
}

export interface SnapshotValidation {
  is_valid: boolean;
  completeness_status: string;
  critical_errors: string[];
  warnings: string[];
}

export interface MarketEvidenceResponse {
  snapshot: EvidenceSnapshot;
  validation: SnapshotValidation;
}
