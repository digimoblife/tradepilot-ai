import type { AnalysisType } from "@/features/trade-workspace/types";

export type AnalysisPayload = Record<string, unknown>;

const knownFields: Record<AnalysisType, readonly string[]> = {
  INITIAL_ANALYSIS: [
    "summary", "orderbook_analysis", "three_month_chart_analysis", "six_month_chart_analysis",
    "support", "resistance", "entry_area", "stop_recommendation", "target_recommendation",
    "probabilities", "risks", "trading_plan", "conclusion",
  ],
  WAIT_UPDATE: [
    "update_summary", "current_price", "orderbook_assessment", "change_from_previous_analysis",
    "current_entry_condition", "upside_probability", "downside_probability", "key_risks",
    "recommended_action", "next_plan", "conclusion",
  ],
  POSITION_UPDATE: [
    "update_summary", "current_price", "position_condition", "orderbook_assessment",
    "change_from_previous_analysis", "target_realism", "downside_risk", "target_probability",
    "trading_plan", "monitoring_points", "warnings", "conclusion",
  ],
};

function object(value: unknown): value is AnalysisPayload {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function usable(value: unknown): boolean {
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.some(usable);
  if (object(value)) return Object.values(value).some(usable);
  return false;
}

/**
 * Keeps the current backend payload intact when it contains at least one
 * displayable, type-specific field. Unknown keys are intentionally ignored by
 * the presentation layer rather than making an otherwise usable result fail.
 */
export function parsePresentationPayload(_type: AnalysisType, value: unknown): AnalysisPayload | null {
  return object(value) ? value : null;
}

export function hasPresentationContent(type: AnalysisType, payload: AnalysisPayload): boolean {
  return knownFields[type].some((field) => usable(payload[field]));
}
