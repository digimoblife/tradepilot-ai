"""Deterministic Gemini transport-to-canonical adapter for Open Position Update."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.ai.providers.gemini import GeminiNormalizationError


def normalize_open_position_update_transport_payload(
    payload: Mapping[str, object], *, application_metadata: Mapping[str, object]
) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        raise GeminiNormalizationError(message="Open Position transport payload must be an object")
    decision = _mapping(payload.get("decision"), "decision")
    findings = _mapping(payload.get("evidence_findings"), "evidence_findings")
    position = _mapping(payload.get("position_assessment"), "position_assessment")
    plan = _mapping(payload.get("trade_plan"), "trade_plan")
    probabilities = _mapping(payload.get("probabilities"), "probabilities")
    next_action = _mapping(payload.get("next_action"), "next_action")
    facts = application_metadata.get("canonical_facts")
    canonical_facts = facts if isinstance(facts, Mapping) else {}
    warnings = _strings(payload.get("warnings")) + _strings(findings.get("limitations"))
    warnings.append("Output Gemini Open Position dinormalisasi ke kontrak canonical.")
    snapshot = canonical_facts.get("market_snapshot")
    snapshot = snapshot if isinstance(snapshot, Mapping) else {}
    market = _mapping_or_empty(payload.get("market_facts"))
    orderbook = _strings(findings.get("orderbook"))
    chart = _strings(findings.get("chart"))
    entry = _number(canonical_facts.get("entry_price"))
    stop = _number(canonical_facts.get("active_stop_loss"))
    target = _number(canonical_facts.get("active_target"))
    current = _number(position.get("current_price")) or _number(snapshot.get("last")) or _number(market.get("current_price"))
    if current is None:
        raise GeminiNormalizationError(
            message="Open Position transport must provide current_price for canonical validation",
        )
    target_probability = _number(probabilities.get("target"))
    downside_probability = _number(probabilities.get("downside"))
    best_bid = _number(market.get("best_bid"))
    best_offer = _number(market.get("best_offer"))
    spread = best_offer - best_bid if best_bid is not None and best_offer is not None else 0
    spread_percentage = (spread / current * 100) if current else 0
    summary = _text(decision.get("summary"), "decision.summary")
    scenarios = _mapping_or_empty(payload.get("scenarios"))
    scenario_lines = _scenario_lines(scenarios)
    return {
        "metadata": _canonical_metadata(application_metadata),
        "update_period": "AD_HOC",
        "comparison": {"comparison_available": False, "previous_analysis_id": None, "previous_analysis_timestamp": None, "previous_update_period": None, "summary": "Perbandingan sebelumnya tidak diisi oleh transport."},
        "evidence_summary": {"evidence_ids": list(application_metadata.get("evidence_ids") or []), "orderbook_available": bool(orderbook), "chart_3_month_available": bool(chart), "chart_6_month_available": False, "latest_orderbook_timestamp": None, "latest_chart_timestamp": None, "has_unreadable_evidence": False, "has_stale_evidence": False, "summary": "Temuan evidence dinormalisasi dari output Open Position transport.", "limitations": _strings(findings.get("limitations"))},
        "market_snapshot": {"trading_date": None, "market_timestamp": None, "update_period": "AD_HOC", "currency": str(canonical_facts.get("currency") or "IDR"), "data_available": bool(market or snapshot), "open": _number(market.get("open")), "high": _number(market.get("high")), "low": _number(market.get("low")), "last": current, "close": None, "previous_close": None, "average": _number(market.get("average")), "change": None, "change_percentage": _number(market.get("change_percentage")), "volume": None, "transaction_value": None, "best_bid": best_bid, "best_offer": best_offer, "spread": spread, "spread_percentage": spread_percentage, "summary": str(market.get("summary") or "Fakta pasar terbaru belum tersedia secara lengkap."), "source": "MIXED" if market else "UNAVAILABLE", "limitations": ["Fakta pasar canonical tidak tersedia lengkap pada transport minimal."]},
        "today_summary": {"open": _number(market.get("open")), "high": _number(market.get("high")), "low": _number(market.get("low")), "last_or_close": current, "average": _number(market.get("average")), "change_percentage": _number(market.get("change_percentage")), "position_in_daily_range": "UNKNOWN", "summary": str(market.get("summary") or "Ringkasan pasar dinormalisasi dari observasi transport.")},
        "orderbook_analysis": {"available": bool(orderbook), "buyer_strength": "UNKNOWN", "seller_pressure": "UNKNOWN", "best_bid": _number(market.get("best_bid")), "best_offer": _number(market.get("best_offer")), "bid_support": None, "offer_resistance": None, "spread_observation": "Spread tidak tersedia pada transport.", "buyer_observations": orderbook, "seller_observations": [], "important_changes": [], "supports_position": None, "conclusion": " ".join(orderbook) or "Belum ada temuan orderbook yang dapat dinormalisasi.", "limitations": _strings(findings.get("limitations"))},
        "chart_update": {"updated_chart_available": False, "using_historical_context": False, "chart_context_timestamp": None, "short_term_trend": "UNKNOWN", "medium_term_trend": "UNKNOWN", "structure_status": "UNKNOWN", "nearest_support": None, "nearest_resistance": None, "breakout_status": "UNKNOWN", "breakdown_status": "UNKNOWN", "supports_position": None, "conclusion": " ".join(chart) or "Chart terbaru tidak tersedia pada transport minimal.", "limitations": _strings(findings.get("limitations")) or ["Konteks chart tidak tersedia pada transport minimal."]},
        "position_assessment": {"entry_price": entry, "current_price": current, "remaining_quantity": _number(canonical_facts.get("remaining_quantity")), "active_stop_loss": stop, "active_target": target, "unrealized_profit_loss": None, "unrealized_return_percentage": _number(position.get("unrealized_return_percentage")), "distance_to_stop_percentage": None, "distance_to_target_percentage": None, "holding_duration_days": 0, "health": _enum(position.get("health"), "UNKNOWN", {"HEALTHY", "HEALTHY_WITH_CAUTION", "UNDER_PRESSURE", "AT_RISK", "UNKNOWN"}), "summary": _text(position.get("summary"), "position_assessment.summary")},
        "thesis_assessment": {"status": "UNDER_REVIEW", "remains_valid": True, "summary": " ".join(scenario_lines) or summary, "strengthening_evidence": [scenarios["bullish"]] if isinstance(scenarios.get("bullish"), str) else [], "weakening_evidence": [scenarios["bearish"]] if isinstance(scenarios.get("bearish"), str) else [], "invalidation_condition": str(plan.get("exit_condition") or "Tinjau posisi bila kondisi risiko terkonfirmasi."), "invalidation_price": stop, "invalidation_triggered": False},
        "target_assessment": {"target_price": target, "still_realistic": True, "realism": _enum(position.get("target_realism"), "UNKNOWN", {"HIGHLY_REALISTIC", "REALISTIC", "POSSIBLE_BUT_CHALLENGING", "UNLIKELY", "NO_LONGER_REALISTIC", "NOT_APPLICABLE", "UNKNOWN"}), "target_probability": target_probability, "distance_to_target_percentage": None, "primary_obstacle": str(position.get("target_obstacle") or "Belum ditentukan oleh transport."), "required_condition": str(position.get("target_condition") or "Pantau kondisi pasar dan orderbook."), "revised_target_proposed": False, "proposed_target": _number(plan.get("proposed_target")), "summary": str(position.get("target_summary") or "Realistisnya target dinilai dari observasi transport.")},
        "stop_loss_assessment": {"stop_loss_price": stop, "still_appropriate": True, "distance_to_stop_percentage": None, "approached": False, "triggered": False, "risk_if_unchanged": "UNKNOWN", "revised_stop_proposed": False, "proposed_stop_loss": _number(plan.get("proposed_stop_loss")), "summary": "Stop loss canonical dipertahankan sebagai fakta aplikasi."},
        "trading_plan": {"current_action": _enum(plan.get("current_action"), "HOLD", {"HOLD", "HOLD_WITH_CAUTION", "REDUCE_RISK", "REVIEW_EXIT", "NO_ACTION"}), "action_rationale": summary, "plan_for_next_session": str(plan.get("rationale") or summary), "hold_condition": str(plan.get("hold_condition") or "Pertahankan selama kondisi posisi tetap valid."), "reduce_risk_condition": str(plan.get("reduce_risk_condition") or "Tinjau risiko bila tekanan turun meningkat."), "exit_condition": str(plan.get("exit_condition") or "Tinjau exit bila stop loss terpicu."), "add_position_condition": None, "levels_to_monitor": [], "requires_user_confirmation": True},
        "ai_assessment": {"bias": _enum(decision.get("bias"), "UNCERTAIN", {"STRONGLY_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "STRONGLY_BEARISH", "UNCERTAIN"}), "confidence": _number(decision.get("confidence")) or 0, "bullish_probability": _number(probabilities.get("bullish")), "target_probability": target_probability, "downside_probability": downside_probability, "risk_level": "UNKNOWN", "summary": summary},
        "changes_from_previous": [],
        "warnings_and_missing_information": {"missing_information": ["Transport minimal tidak memuat seluruh konteks historis."] if not scenarios else [], "warnings": warnings},
    }


def _canonical_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    required = {"analysis_id": metadata.get("canonical_analysis_id"), "session_id": metadata.get("session_id"), "analysis_type": "OPEN_POSITION_UPDATE", "ticker": metadata.get("ticker") or _fact(metadata, "ticker"), "company_name": metadata.get("company_name") or _fact(metadata, "company_name"), "analysis_timestamp": metadata.get("canonical_analysis_timestamp"), "language": "id", "schema": {"schema_name": "open_position_update", "schema_version": "1.0.0"}, "prompt_version": metadata.get("prompt_version", "1.0.0"), "provider": "GEMINI", "model": metadata.get("provider_model", "gemini-3.1-flash-lite")}
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise GeminiNormalizationError(message=f"Open Position canonical metadata is missing application fields: {', '.join(missing)}")
    return required


def _fact(metadata: Mapping[str, object], name: str) -> object:
    facts = metadata.get("canonical_facts")
    return facts.get(name) if isinstance(facts, Mapping) else None


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GeminiNormalizationError(message=f"Open Position transport field '{name}' must be an object")
    return value


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _scenario_lines(scenarios: Mapping[str, object]) -> list[str]:
    return [f"{label}: {scenarios[label]}" for label in ("bullish", "base", "bearish") if isinstance(scenarios.get(label), str) and scenarios[label].strip()]


def _number(value: object) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip():
        try:
            number = float(value)
            return int(number) if number.is_integer() else number
        except ValueError:
            return None
    return None


def _enum(value: object, default: str, allowed: set[str]) -> str:
    return str(value) if value in allowed else default


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeminiNormalizationError(message=f"Open Position transport field '{field}' must be non-empty")
    return value
