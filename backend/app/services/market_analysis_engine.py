"""Market Analysis Engine for TradePilot AI.

Synthesizes authoritative ZAPI market evidence (Price, Orderbook, Historical OHLCV,
Foreign Flow, Broker Flow, and Investing fundamentals) into a compact tabular prompt
and asks Gemini to act as the analyst. All numeric evidence is computed by this
engine and treated as confirmed fact; Gemini is only responsible for the
BUY/WAIT/SKIP (or HOLD/TRAILING_STOP/TAKE_PROFIT/CUT_LOSS) judgment, the
recommended trade levels, and the Indonesian-language narrative.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.api.schemas.evidence_snapshot import EvidenceSnapshotSchema
from app.config import AppConfig
from app.services.market_analysis_prompt import (
    IN_TRADE_OUTPUT_SCHEMA,
    PRE_TRADE_OUTPUT_SCHEMA,
    build_in_trade_evidence_table,
    build_pre_trade_evidence_table,
    load_prompt,
)
from app.trade_workspace.ai.gemini_adapter import GeminiAdapter, GeminiAdapterError

logger = logging.getLogger(__name__)


def _confidence_percent(value: Any) -> int:
    """Convert Gemini's 0.0-1.0 confidence_score into the 0-100 integer the frontend renders."""
    try:
        fraction = float(value)
    except (TypeError, ValueError):
        fraction = 0.5
    return round(max(0.0, min(1.0, fraction)) * 100)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        val = obj.get(key, default)
        return val if val is not None else default
    val = getattr(obj, key, default)
    return val if val is not None else default


class MarketAnalysisEngineError(Exception):
    """Raised when Gemini analysis cannot be completed."""


class MarketAnalysisEngine:
    """Engine that asks Gemini for trading recommendations from evidence snapshots."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def analyze(
        self,
        snapshot: EvidenceSnapshotSchema,
        trading_style: str = "Swing Trade",
        setup_note: str | None = None,
        position: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ask Gemini for a trading recommendation grounded in the supplied evidence."""
        quote = snapshot.quote
        historical = snapshot.historical_ohlcv
        tech = _get(historical, "computed_technical") or {}

        last_price = float(_get(quote, "last_price", 0.0)) or 0.0
        atr14 = float(_get(tech, "atr14", max(1.0, last_price * 0.03)))

        adapter = GeminiAdapter(model=self.config.gemini_model)

        if position and position.get("entry_price") and float(position.get("entry_price", 0)) > 0:
            return await self._analyze_in_trade(
                adapter=adapter,
                snapshot=snapshot,
                position=position,
                last_price=last_price,
                atr14=atr14,
                tech=tech,
                trading_style=trading_style,
                setup_note=setup_note,
            )

        return await self._analyze_pre_trade(
            adapter=adapter,
            snapshot=snapshot,
            last_price=last_price,
            atr14=atr14,
            tech=tech,
            trading_style=trading_style,
            setup_note=setup_note,
        )

    async def _analyze_pre_trade(
        self,
        *,
        adapter: GeminiAdapter,
        snapshot: EvidenceSnapshotSchema,
        last_price: float,
        atr14: float,
        tech: dict[str, Any],
        trading_style: str,
        setup_note: str | None,
    ) -> dict[str, Any]:
        evidence_table = build_pre_trade_evidence_table(
            snapshot=snapshot,
            trading_style=trading_style,
            setup_note=setup_note,
            tech=tech,
        )
        prompt_text = self._compose_prompt("pre_trade_analysis", evidence_table)

        try:
            result = await adapter.generate(
                prompt_text=prompt_text,
                output_schema=PRE_TRADE_OUTPUT_SCHEMA,
            )
        except GeminiAdapterError as exc:
            logger.error("Pre-trade Gemini analysis failed for %s: %s", snapshot.symbol, exc)
            raise MarketAnalysisEngineError(str(exc)) from exc

        gemini_output = result.processed_response
        key_levels = dict(gemini_output.get("key_levels") or {})
        # Confirmed system facts always win over anything Gemini echoed back.
        key_levels["current_price"] = last_price
        key_levels["atr14"] = round(atr14, 1)

        return {
            "symbol": snapshot.symbol,
            "session_id": str(snapshot.session_id),
            "action": gemini_output.get("action"),
            "signal_quality": gemini_output.get("signal_quality"),
            "confidence_score": _confidence_percent(gemini_output.get("confidence_score")),
            "trading_style": trading_style,
            "is_in_trade": False,
            "key_levels": key_levels,
            "reasoning": {
                **(gemini_output.get("reasoning") or {}),
                "setup_note": setup_note,
            },
            "market_evidence": snapshot.model_dump(),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _analyze_in_trade(
        self,
        *,
        adapter: GeminiAdapter,
        snapshot: EvidenceSnapshotSchema,
        position: dict[str, Any],
        last_price: float,
        atr14: float,
        tech: dict[str, Any],
        trading_style: str,
        setup_note: str | None,
    ) -> dict[str, Any]:
        entry_price = float(position["entry_price"])
        stop_loss = float(position.get("stop_loss") or 0) or round(
            max(entry_price - (atr14 * 1.5), entry_price * 0.94)
        )
        target_price = float(position.get("target_price") or 0) or round(
            entry_price + ((entry_price - stop_loss) * 1.8)
        )

        floating_pnl_pct = (
            ((last_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
        )
        dist_to_tp1_pct = (
            ((target_price - last_price) / last_price * 100) if last_price > 0 else 0.0
        )
        dist_to_sl_pct = ((last_price - stop_loss) / last_price * 100) if last_price > 0 else 0.0

        evidence_table = build_in_trade_evidence_table(
            snapshot=snapshot,
            position=position,
            tech=tech,
            current_price=last_price,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            floating_pnl_percent=round(floating_pnl_pct, 2),
            distance_to_tp1_percent=round(dist_to_tp1_pct, 2),
            distance_to_sl_percent=round(dist_to_sl_pct, 2),
            setup_note=setup_note,
        )
        prompt_text = self._compose_prompt("in_trade_position_update", evidence_table)

        try:
            result = await adapter.generate(
                prompt_text=prompt_text,
                output_schema=IN_TRADE_OUTPUT_SCHEMA,
            )
        except GeminiAdapterError as exc:
            logger.error("In-trade Gemini analysis failed for %s: %s", snapshot.symbol, exc)
            raise MarketAnalysisEngineError(str(exc)) from exc

        gemini_output = result.processed_response
        key_levels = dict(gemini_output.get("key_levels") or {})
        # Confirmed position facts and pure arithmetic always win over Gemini's echo.
        key_levels["current_price"] = last_price
        key_levels["entry_price"] = entry_price
        key_levels["atr14"] = round(atr14, 1)
        key_levels["distance_to_tp1_percent"] = round(dist_to_tp1_pct, 2)
        key_levels["distance_to_sl_percent"] = round(dist_to_sl_pct, 2)
        key_levels["floating_pnl_percent"] = round(floating_pnl_pct, 2)

        return {
            "symbol": snapshot.symbol,
            "session_id": str(snapshot.session_id),
            "action": gemini_output.get("action"),
            "signal_quality": gemini_output.get("signal_quality"),
            "confidence_score": _confidence_percent(gemini_output.get("confidence_score")),
            "trading_style": trading_style,
            "is_in_trade": True,
            "key_levels": key_levels,
            "reasoning": {
                **(gemini_output.get("reasoning") or {}),
                "setup_note": setup_note,
            },
            "market_evidence": snapshot.model_dump(),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _compose_prompt(prompt_name: str, evidence_table: str) -> str:
        prompt_text = load_prompt(prompt_name)
        return (
            f"{prompt_text.rstrip()}\n\n"
            "## ACTUAL MARKET EVIDENCE FOR THIS REQUEST\n\n"
            f"{evidence_table}"
        )
