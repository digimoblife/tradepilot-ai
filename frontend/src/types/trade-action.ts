/** Base fields for all trade actions */
export interface BaseActionRequest {
  session_id: string;
  idempotency_key: string;
}

/** POST /api/actions/open-position */
export interface OpenPositionRequest extends BaseActionRequest {
  entry_price: string | number;
  quantity: string | number;
  executed_at: string;
  stop_loss?: string | number | null;
  target?: string | number | null;
  note?: string | null;
}

/** POST /api/actions/confirm-stop */
export interface StopActionRequest extends BaseActionRequest {
  stop_loss: string | number;
  confirmed_at: string;
  note?: string | null;
}

/** POST /api/actions/confirm-target */
export interface TargetActionRequest extends BaseActionRequest {
  target: string | number;
  confirmed_at: string;
  note?: string | null;
}

/** POST /api/actions/partial-exit */
export interface PartialExitRequest extends BaseActionRequest {
  exit_price: string | number;
  exit_quantity: string | number;
  executed_at: string;
  reason?: string | null;
  note?: string | null;
}

/** POST /api/actions/full-exit */
export interface FullExitRequest extends BaseActionRequest {
  exit_price: string | number;
  exit_quantity: string | number;
  executed_at: string;
  closing_reason: string;
  fees?: string | number | null;
  note?: string | null;
}

/** POST /api/actions/cancel */
export interface CancelSessionRequest extends BaseActionRequest {
  cancelled_at: string;
  reason?: string | null;
  note?: string | null;
}

/** Action reference in response */
export interface TradeActionRef {
  id: string;
  session_id: string;
  action_type: string;
  confirmed_at: string;
  price: string | null;
  quantity: string | null;
}

/** Trade state snapshot */
export interface TradeStateSnapshot {
  position_status: string;
  entry_price: string | null;
  original_quantity: string | null;
  remaining_quantity: string | null;
  active_stop_loss: string | null;
  active_target: string | null;
  average_exit_price: string | null;
  realized_pnl: string | null;
  state_version: number;
}

/** Unified action result */
export interface ActionResult {
  action: TradeActionRef;
  session_status: string;
  trade_state: TradeStateSnapshot;
}
