"""Small Gemini transport-to-canonical adapter for Watching Update."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.ai.providers.gemini import GeminiNormalizationError


def normalize_watching_update_transport_payload(
    payload: Mapping[str, object],
    *,
    application_metadata: Mapping[str, object],
) -> dict[str, object]:
    """Map the compact Gemini Watching contract into the canonical payload.

    Application metadata and context are authoritative. The transport can only
    contribute recommendations, observations, proposed levels, and narrative.
    """
    if not isinstance(payload, Mapping):
        raise GeminiNormalizationError(message="Watching transport payload must be an object")

    decision = _mapping(payload.get("decision"), "decision")
    findings = _mapping(payload.get("evidence_findings"), "evidence_findings")
    plan = _mapping(payload.get("trade_plan"), "trade_plan")
    probabilities = _mapping(payload.get("probabilities"), "probabilities")
    scenarios = _mapping(payload.get("scenarios"), "scenarios")
    next_action = _mapping(payload.get("next_action"), "next_action")

    facts = application_metadata.get("canonical_facts")
    canonical_facts = facts if isinstance(facts, Mapping) else {}
    context_snapshot = canonical_facts.get("market_snapshot")
    canonical_snapshot = context_snapshot if isinstance(context_snapshot, Mapping) else {}
    warnings = _strings(payload.get("warnings"), "warnings")
    limitations = _strings(findings.get("limitations"), "evidence_findings.limitations")
    warnings.extend(limitations)
    warnings.append("Transport Watching output was normalized into the canonical contract.")

    market_facts = _mapping_or_empty(payload.get("market_facts"))
    snapshot = _market_snapshot(
        market_facts,
        canonical_snapshot,
        currency=str(canonical_facts.get("currency") or "IDR"),
        warnings=warnings,
    )
    action = _safe_action(next_action.get("action"), decision.get("recommendation"))
    action_rationale = _text(
        decision.get("summary") or plan.get("rationale"),
        "decision.summary",
    )
    scenario_summary = _scenario_summary(scenarios)
    orderbook = _strings(findings.get("orderbook"), "evidence_findings.orderbook")
    chart = _strings(findings.get("chart"), "evidence_findings.chart")

    return {
        "metadata": _canonical_metadata(application_metadata),
        "update_period": "AD_HOC",
        "comparison": {
            "comparison_available": False,
            "previous_analysis_id": None,
            "previous_analysis_type": None,
            "previous_analysis_timestamp": None,
            "previous_update_period": None,
            "summary": "Konteks perbandingan sebelumnya tidak diisi oleh transport.",
        },
        "evidence_summary": {
            "evidence_ids": list(application_metadata.get("evidence_ids") or []),
            "orderbook_available": bool(orderbook),
            "chart_3_month_available": bool(chart),
            "chart_6_month_available": False,
            "latest_orderbook_timestamp": None,
            "latest_chart_timestamp": None,
            "has_unreadable_evidence": False,
            "has_stale_evidence": False,
            "summary": "Temuan evidence dinormalisasi dari output Watching transport.",
            "limitations": limitations,
        },
        "market_snapshot": snapshot,
        "today_summary": {
            "open": snapshot["open"],
            "high": snapshot["high"],
            "low": snapshot["low"],
            "last_or_close": snapshot["last"],
            "average": snapshot["average"],
            "change_percentage": snapshot["change_percentage"],
            "position_in_daily_range": "UNKNOWN",
            "distance_from_reference_entry_percentage": None,
            "summary": "Ringkasan harga hanya tersedia bila fakta pasar canonical tersedia.",
        },
        "orderbook_analysis": {
            "available": bool(orderbook),
            "buyer_strength": "UNKNOWN",
            "seller_pressure": "UNKNOWN",
            "best_bid": snapshot["best_bid"],
            "best_offer": snapshot["best_offer"],
            "bid_support": None,
            "offer_resistance": None,
            "buyer_observations": orderbook,
            "seller_observations": [],
            "important_changes": orderbook,
            "supports_entry": None,
            "entry_confirmation_visible": None,
            "conclusion": " ".join(orderbook) or "Belum ada temuan orderbook yang dapat dinormalisasi.",
            "limitations": limitations or ["Temuan orderbook terbatas pada output transport."],
        },
        "chart_update": {
            "updated_chart_available": False,
            "using_historical_context": False,
            "chart_context_timestamp": None,
            "short_term_trend": "UNKNOWN",
            "medium_term_trend": "UNKNOWN",
            "structure_status": "UNKNOWN",
            "nearest_support": None,
            "nearest_resistance": None,
            "breakout_status": "UNKNOWN",
            "breakdown_status": "UNKNOWN",
            "supports_setup": None,
            "important_changes": [],
            "conclusion": " ".join(chart) or "Belum ada temuan chart yang dapat dinormalisasi.",
            "limitations": limitations or ["Konteks chart tidak tersedia pada transport minimal."],
        },
        "setup_assessment": {
            "status": "WAITING_FOR_CONFIRMATION",
            "still_valid": False,
            "original_thesis_summary": "Thesis canonical tetap menjadi otoritas aplikasi.",
            "current_thesis_summary": scenario_summary,
            "strengthening_evidence": chart,
            "weakening_evidence": warnings[:3],
            "invalidation_condition": _text_or_default(plan.get("wait_condition"), "Tidak ditentukan oleh transport."),
            "invalidation_price": _number(plan.get("invalidation")),
            "invalidation_triggered": False,
            "summary": action_rationale,
        },
        "entry_assessment": {
            "reference_entry_type": "WAIT",
            "reference_entry_price": None,
            "reference_entry_zone_low": None,
            "reference_entry_zone_high": None,
            "current_price": _number(canonical_snapshot.get("last") or market_facts.get("current_price")),
            "entry_still_attractive": False,
            "entry_confirmation_met": False,
            "price_already_extended": None,
            "chase_risk": "UNKNOWN",
            "maximum_acceptable_entry": _number(plan.get("chase_limit")),
            "revised_entry_proposed": False,
            "proposed_entry_type": None,
            "proposed_entry_price": None,
            "proposed_entry_zone_low": None,
            "proposed_entry_zone_high": None,
            "entry_condition": _text_or_default(next_action.get("action"), "Tunggu konfirmasi pengguna."),
            "wait_condition": _text_or_default(next_action.get("wait_condition"), _text_or_default(plan.get("wait_condition"), "Tunggu data tambahan.")),
            "cancel_entry_condition": _text_or_default(plan.get("invalidation"), "Batalkan bila tesis tidak lagi valid."),
            "summary": action_rationale,
        },
        "price_levels": {
            "supports": [],
            "resistances": [],
            "reference_entry": None,
            "maximum_acceptable_entry": None,
            "invalidation_level": None,
            "proposed_stop_loss": _level(plan.get("proposed_stop_loss")),
            "proposed_target": _level(plan.get("proposed_target")),
            "summary": "Level hanya berupa proposal AI dan belum menjadi fakta eksekusi.",
        },
        "trading_plan": {
            "current_action": "NO_ACTION",
            "action_rationale": action_rationale,
            "entry_condition": _text_or_default(next_action.get("action"), "Tunggu konfirmasi pengguna."),
            "wait_condition": _text_or_default(next_action.get("wait_condition"), _text_or_default(plan.get("wait_condition"), "Tunggu data tambahan.")),
            "do_not_chase_condition": _text_or_default(plan.get("chase_limit"), "Jangan mengejar harga."),
            "cancel_setup_condition": _text_or_default(plan.get("invalidation"), "Batalkan bila tesis tidak lagi valid."),
            "next_checkpoint": _text_or_default(next_action.get("monitoring"), "Perbarui evidence sebelum keputusan berikutnya."),
            "levels_to_monitor": [],
            "requires_user_confirmation": False,
        },
        "ai_assessment": {
            "bias": _enum(decision.get("bias"), "UNCERTAIN"),
            "confidence": _number_or_default(decision.get("confidence"), 0),
            "setup_quality": (
                _enum(decision.get("setup_quality"), "UNKNOWN")
                if _enum(decision.get("setup_quality"), "UNKNOWN")
                in {"WEAK", "INVALID", "UNKNOWN"}
                else "UNKNOWN"
            ),
            "bullish_probability": _number(probabilities.get("bullish")),
            "target_probability": _number(probabilities.get("target")),
            "downside_probability": _number(probabilities.get("downside")),
            "entry_probability": None,
            "risk_level": _enum(decision.get("risk_level"), "UNKNOWN"),
            "setup_valid": False,
            "summary": action_rationale + " " + scenario_summary,
        },
        "changes_from_previous": [],
        "warnings_and_missing_information": {
            "missing_information": ["Konteks perbandingan sebelumnya belum dipetakan oleh transport minimal."],
            "warnings": warnings,
        },
    }


def _canonical_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    required = {
        "analysis_id": metadata.get("canonical_analysis_id"),
        "session_id": metadata.get("session_id"),
        "analysis_type": "WATCHING_UPDATE",
        "ticker": _metadata_value(metadata, "ticker"),
        "company_name": metadata.get("company_name"),
        "analysis_timestamp": metadata.get("canonical_analysis_timestamp"),
        "language": "id",
        "schema": {"schema_name": "watching_update", "schema_version": "1.0.0"},
        "prompt_version": metadata.get("prompt_version", "1.0.0"),
        "provider": "GEMINI",
        "model": metadata.get("provider_model", "gemini-3.1-flash-lite"),
    }
    missing = [key for key, value in required.items() if value is None]
    if missing:
        raise GeminiNormalizationError(
            message=f"Watching canonical metadata is missing application fields: {', '.join(missing)}",
        )
    return required


def _metadata_value(metadata: Mapping[str, object], name: str) -> object:
    direct = metadata.get(name)
    if direct is not None:
        return direct
    facts = metadata.get("canonical_facts")
    return facts.get(name) if isinstance(facts, Mapping) else None


def _market_snapshot(
    transport: Mapping[str, object],
    canonical: Mapping[str, object],
    *,
    currency: str,
    warnings: list[str],
) -> dict[str, object]:
    def value(name: str, alias: str | None = None) -> object:
        if name in canonical:
            return canonical[name]
        return transport.get(alias or name)

    available = any(value(name) is not None for name in ("open", "high", "low", "last"))
    limitations = list(canonical.get("limitations") or []) if isinstance(canonical.get("limitations"), list) else []
    if not available:
        limitations.append("Fakta pasar tidak tersedia secara authoritative pada konteks aplikasi.")
    return {
        "trading_date": canonical.get("trading_date"),
        "market_timestamp": canonical.get("market_timestamp"),
        "update_period": canonical.get("update_period", "AD_HOC"),
        "currency": currency,
        "data_available": available,
        "open": value("open"),
        "high": value("high"),
        "low": value("low"),
        "last": value("last", "current_price"),
        "close": canonical.get("close"),
        "previous_close": canonical.get("previous_close"),
        "average": value("average"),
        "change": canonical.get("change"),
        "change_percentage": value("change_percentage"),
        "volume": canonical.get("volume"),
        "transaction_value": canonical.get("transaction_value"),
        "best_bid": value("best_bid"),
        "best_offer": value("best_offer"),
        "spread": canonical.get("spread"),
        "spread_percentage": canonical.get("spread_percentage"),
        "summary": str(transport.get("summary") or "Fakta pasar dinormalisasi dengan otoritas konteks aplikasi."),
        "source": "MIXED" if available else "UNAVAILABLE",
        "limitations": limitations,
    }


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GeminiNormalizationError(message=f"Watching transport field '{name}' must be an object")
    return value


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: object, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise GeminiNormalizationError(message=f"Watching transport field '{name}' must be a string array")
    return [item.strip() for item in value]


def _text(value: object, name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise GeminiNormalizationError(message=f"Watching transport field '{name}' must be non-empty")


def _text_or_default(value: object, default: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value) or str(default)
    return value.strip() if isinstance(value, str) and value.strip() else str(default)


def _number(value: object) -> int | float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _number_or_default(value: object, default: int) -> int | float:
    return _number(value) if _number(value) is not None else default


def _enum(value: object, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _safe_action(next_action: object, recommendation: object) -> str:
    candidate = next_action if isinstance(next_action, str) else recommendation
    return {
        "WAIT": "WAIT",
        "SKIP": "DO_NOT_ENTER",
        "ENTER_IF_CONFIRMED": "ENTER_IF_CONFIRMED",
        "REFRESH_DATA": "WAIT",
        "UNCERTAIN": "NO_ACTION",
    }.get(candidate, "NO_ACTION")


def _scenario_summary(scenarios: Mapping[str, object]) -> str:
    parts = []
    for label in ("bullish", "neutral", "bearish"):
        value = scenarios.get(label)
        if isinstance(value, str) and value.strip():
            parts.append(f"{label.title()}: {value.strip()}")
    return " ".join(parts) or "Skenario tidak tersedia."


def _level(value: object) -> dict[str, object] | None:
    number = _number(value)
    if number is None:
        return None
    return {"price": number, "label": "Proposal AI", "summary": "Level ini hanya proposal dan memerlukan konfirmasi pengguna."}
