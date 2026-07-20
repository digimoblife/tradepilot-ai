/** POST /api/trade-sessions */
export interface CreateTradeSessionRequest {
  ticker: string;
  company_name?: string | null;
  exchange?: string | null;
  currency?: string;
  title?: string | null;
}

export interface TradeSessionSummary {
  id: string;
  ticker: string;
  company_name: string | null;
  exchange: string;
  currency: string;
  title: string | null;
  lifecycle_status: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface TradeState {
  position_status: string;
  thesis_status: string;
  entry_price: string | null;
  entry_at: string | null;
  original_quantity: string | null;
  remaining_quantity: string | null;
  active_stop_loss: string | null;
  active_target: string | null;
  average_exit_price: string | null;
  realized_pnl: string | null;
  realized_return: string | null;
  state_version: number;
}

/** GET /api/trade-sessions */
export interface ListTradeSessionsResponse {
  sessions: TradeSessionSummary[];
  total: number;
}

/** GET /api/trade-sessions/{id} */
export interface TradeSessionDetail {
  session: TradeSessionSummary;
  trade_state: TradeState;
  allowed_actions: string[];
}

/** POST /api/trade-sessions */
export type CreateTradeSessionResponse = TradeSessionSummary;

/** PATCH /api/trade-sessions/{id} */
export type UpdateTradeSessionRequest = Partial<{
  title: string;
  company_name: string;
  exchange: string;
  currency: string;
  ticker: string;
}>;

/** POST /api/trade-sessions/{id}/ready */
export interface ReadyResponse {
  id: string;
  lifecycle_status: string;
}

/** POST /api/trade-sessions/{id}/archive */
export interface ArchiveResponse {
  id: string;
  lifecycle_status: string;
  archived_at: string | null;
}
