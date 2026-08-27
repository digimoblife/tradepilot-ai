"""Evidence Normalizer service for TradePilot AI.

Transforms raw heterogeneous JSON responses from ZAPI providers (Pluang, IDX, Stockbit)
into standard canonical EvidenceSnapshot objects.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.api.schemas.evidence_snapshot import (
    BrokerFlowDomain,
    BrokerItem,
    EvidenceSnapshotSchema,
    ForeignFlowDomain,
    ForeignFlowPeriod,
    HistoricalBar,
    HistoricalDomain,
    MarketContextDomain,
    OrderbookDomain,
    OrderbookLevel,
    QuoteDomain,
)
from app.services.technical_indicators import compute_technical_summary

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")


def _to_float(val: Any, default: float = 0.0) -> float:
    """Safely convert any value to float, handling '-', '', None, and formatted strings."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.strip().replace(",", "")
        if not cleaned or cleaned in ("-", "--", "N/A", "null", "None", "nan", "Infinity", "-Infinity"):
            return default
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _to_optional_float(val: Any) -> float | None:
    """Safely convert any value to float or None."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.strip().replace(",", "")
        if not cleaned or cleaned in ("-", "--", "N/A", "null", "None", "nan", "Infinity", "-Infinity"):
            return None
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _to_int(val: Any, default: int = 0) -> int:
    """Safely convert any value to int, handling '-', float strings, etc."""
    if val is None:
        return default
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        cleaned = val.strip().replace(",", "")
        if not cleaned or cleaned in ("-", "--", "N/A", "null", "None", "nan"):
            return default
        try:
            return int(float(cleaned))
        except (ValueError, TypeError):
            return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _to_optional_int(val: Any) -> int | None:
    """Safely convert any value to int or None."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        cleaned = val.strip().replace(",", "")
        if not cleaned or cleaned in ("-", "--", "N/A", "null", "None", "nan"):
            return None
        try:
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


class EvidenceNormalizer:
    """Normalizes raw provider payloads into canonical EvidenceSnapshotSchema."""

    @staticmethod
    def _unwrap(raw: dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw, dict) and "data" in raw and isinstance(raw["data"], dict):
            return raw["data"]
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def normalize_quote(
        raw: dict[str, Any],
        stockbit_chart: dict[str, Any] | None = None,
        provider: str = "PLUANG",
    ) -> QuoteDomain:
        raw = EvidenceNormalizer._unwrap(raw)
        stats = raw.get("keyStats") or {}

        # Try extracting price from multiple known fields
        last_price_raw = (
            raw.get("lastPrice")
            or raw.get("Close")
            or raw.get("close")
            or raw.get("price")
            or stats.get("iep")
            or raw.get("highestIndicativePrice")
        )
        last_price = _to_float(last_price_raw, 0.0)

        prev_raw = raw.get("previousClose") or raw.get("Previous") or raw.get("previous")
        previous_close = _to_float(prev_raw, last_price)

        change_raw = raw.get("change") or raw.get("Change")
        change = _to_float(change_raw, last_price - previous_close)

        change_pct_raw = raw.get("changePercent") or raw.get("percentage")
        calc_pct = (change / previous_close * 100) if previous_close else 0.0
        change_pct = _to_float(change_pct_raw, calc_pct)

        # Real-time overlay from Stockbit Intraday Chart (Highest real-time fidelity during market hours)
        if stockbit_chart and isinstance(stockbit_chart, dict):
            sb_items = stockbit_chart.get("items") or []
            if sb_items and isinstance(sb_items, list) and isinstance(sb_items[0], dict):
                sb_p = _to_float(sb_items[0].get("price"))
                if sb_p > 0:
                    last_price = sb_p
                sb_prev = _to_float(stockbit_chart.get("previousClose"))
                if sb_prev > 0:
                    previous_close = sb_prev
                sb_chg = _to_float(stockbit_chart.get("change") or sb_items[0].get("change"))
                if sb_chg != 0 or sb_prev > 0:
                    change = sb_chg if sb_chg != 0 else (last_price - previous_close)
                sb_chg_pct = _to_float(stockbit_chart.get("changePercent") or sb_items[0].get("changePercent"))
                if sb_chg_pct != 0 or sb_prev > 0:
                    change_pct = sb_chg_pct if sb_chg_pct != 0 else ((change / previous_close * 100) if previous_close else 0.0)

        open_raw = raw.get("openPrice") or raw.get("OpenPrice") or raw.get("open")
        open_price = _to_float(open_raw, last_price)

        high_raw = raw.get("highPrice") or raw.get("High") or raw.get("high") or raw.get("highestIndicativePrice")
        high_price = _to_float(high_raw, max(last_price, open_price))

        low_raw = raw.get("lowPrice") or raw.get("Low") or raw.get("low")
        low_price = _to_float(low_raw, min(last_price, open_price))

        volume_shares = _to_int(raw.get("volume") or raw.get("Volume"), 0)
        volume_lots = volume_shares // 100 if volume_shares > 0 else 0

        value_raw = raw.get("value") or raw.get("Value")
        value_idr = _to_float(value_raw, volume_shares * last_price)

        freq = _to_int(raw.get("frequency") or raw.get("Frequency"), 0)

        pe = _to_optional_float(raw.get("pe"))
        pbv = _to_optional_float(raw.get("pbv"))
        mcap = _to_optional_float(raw.get("marketCap") or raw.get("MarketCapital"))

        return QuoteDomain(
            last_price=last_price,
            change=change,
            change_percent=round(change_pct, 2),
            previous_close=previous_close,
            open=open_price,
            high=high_price,
            low=low_price,
            volume_shares=volume_shares,
            volume_lots=volume_lots,
            value_idr=value_idr,
            frequency=freq,
            pe_ratio=pe,
            pbv_ratio=pbv,
            market_cap=mcap,
            timestamp=datetime.now(JAKARTA_TZ).isoformat(),
        )

    @staticmethod
    def normalize_orderbook(raw: dict[str, Any]) -> OrderbookDomain:
        raw = EvidenceNormalizer._unwrap(raw)
        raw_bids = raw.get("bids") or []
        raw_asks = raw.get("asks") or []

        bids = [
            OrderbookLevel(price=_to_float(b.get("price")), lots=_to_int(b.get("lots")))
            for b in raw_bids
            if b.get("price") and _to_float(b.get("price")) > 0
        ]
        asks = [
            OrderbookLevel(price=_to_float(a.get("price")), lots=_to_int(a.get("lots")))
            for a in raw_asks
            if a.get("price") and _to_float(a.get("price")) > 0
        ]

        best_bid = _to_float(raw.get("bestBid"), bids[0].price if bids else 0.0)
        best_ask = _to_float(raw.get("bestAsk"), asks[0].price if asks else 0.0)
        spread = best_ask - best_bid if best_ask and best_bid else 0.0
        spread_pct = round((spread / best_bid * 100), 2) if best_bid else 0.0

        total_bid_lots = sum(b.lots for b in bids)
        total_ask_lots = sum(a.lots for a in asks)
        ratio = round(total_bid_lots / total_ask_lots, 2) if total_ask_lots > 0 else 1.0

        total_lots = total_bid_lots + total_ask_lots
        bid_pct = round(total_bid_lots / total_lots * 100, 1) if total_lots > 0 else 50.0
        ask_pct = round(total_ask_lots / total_lots * 100, 1) if total_lots > 0 else 50.0

        return OrderbookDomain(
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            spread_percent=spread_pct,
            total_bid_lots=total_bid_lots,
            total_ask_lots=total_ask_lots,
            bid_ask_ratio=ratio,
            bid_percent=bid_pct,
            ask_percent=ask_pct,
            bids=bids[:10],
            asks=asks[:10],
            timestamp=datetime.now(JAKARTA_TZ).isoformat(),
        )

    @staticmethod
    def normalize_history_and_foreign_flow(raw_history: dict[str, Any]) -> tuple[HistoricalDomain, ForeignFlowDomain]:
        raw_history = EvidenceNormalizer._unwrap(raw_history)
        items = raw_history.get("items") or raw_history.get("data") or []
        if isinstance(items, dict):
            items = items.get("items") or []

        # Ensure chronological order: oldest to newest
        bars_chronological = list(reversed(items)) if items else []

        parsed_bars: list[HistoricalBar] = []
        for b in items[:15]:
            parsed_bars.append(
                HistoricalBar(
                    date=str(b.get("date") or b.get("Date") or ""),
                    open=_to_float(b.get("open") or b.get("OpenPrice")),
                    high=_to_float(b.get("high") or b.get("High")),
                    low=_to_float(b.get("low") or b.get("Low")),
                    close=_to_float(b.get("close") or b.get("Close")),
                    volume=_to_int(b.get("volume") or b.get("Volume")),
                    value=_to_float(b.get("value") or b.get("Value")),
                    net_foreign_shares=_to_optional_int(b.get("netForeignShares")),
                )
            )

        computed = compute_technical_summary(bars_chronological)
        start_date = items[-1].get("date") if items else None
        end_date = items[0].get("date") if items else None

        hist_domain = HistoricalDomain(
            horizon_days=len(items),
            start_date=str(start_date) if start_date else None,
            end_date=str(end_date) if end_date else None,
            computed_technical=computed,
            recent_bars=parsed_bars,
        )

        # Compute Foreign Flow aggregations from daily net rows
        today_bar = items[0] if items else {}
        today_net_shares = _to_int(today_bar.get("netForeignShares"), 0)
        today_close = _to_float(today_bar.get("close"), 0.0)
        today_net_val = _to_float(today_bar.get("netForeignValue"), float(today_net_shares * today_close))
        today_buy_shares = _to_optional_int(today_bar.get("foreignBuyShares"))
        today_sell_shares = _to_optional_int(today_bar.get("foreignSellShares"))

        today_1d = ForeignFlowPeriod(
            net_shares=today_net_shares,
            net_value_idr=today_net_val,
            buy_shares=today_buy_shares,
            sell_shares=today_sell_shares,
        )

        def sum_period(bars: list[dict[str, Any]], count: int) -> ForeignFlowPeriod:
            subset = bars[:count]
            net_s = sum(_to_int(b.get("netForeignShares"), 0) for b in subset)
            net_v = sum(
                _to_float(
                    b.get("netForeignValue"),
                    float(_to_int(b.get("netForeignShares"), 0) * _to_float(b.get("close"), 0.0)),
                )
                for b in subset
            )
            return ForeignFlowPeriod(net_shares=net_s, net_value_idr=net_v)

        w1 = sum_period(items, 5)
        m1 = sum_period(items, 20)
        m3 = sum_period(items, 60)

        # Evaluate foreign accumulation status
        if w1.net_shares > 10_000_000 and m1.net_shares > 20_000_000:
            status = "STRONG_ACCUMULATION"
        elif w1.net_shares > 0:
            status = "ACCUMULATION"
        elif w1.net_shares < -10_000_000 and m1.net_shares < -20_000_000:
            status = "STRONG_DISTRIBUTION"
        elif w1.net_shares < 0:
            status = "DISTRIBUTION"
        else:
            status = "NEUTRAL"

        recent_series = [
            {
                "date": str(b.get("date") or ""),
                "net_shares": _to_int(b.get("netForeignShares"), 0),
                "close": _to_float(b.get("close"), 0.0),
            }
            for b in items[:7]
        ]

        ff_domain = ForeignFlowDomain(
            today_1d=today_1d,
            weekly_1w=w1,
            monthly_1m=m1,
            three_month_3m=m3,
            foreign_status=status,
            recent_daily_series=recent_series,
        )

        return hist_domain, ff_domain

    @staticmethod
    def normalize_broker_flow(raw: dict[str, Any]) -> BrokerFlowDomain:
        raw = EvidenceNormalizer._unwrap(raw)
        buyers_raw = raw.get("buyers") or []
        sellers_raw = raw.get("sellers") or []

        buyers: list[BrokerItem] = []
        sellers: list[BrokerItem] = []

        total_buy_lots = sum(_to_int(b.get("lots"), 0) for b in buyers_raw)
        total_sell_lots = sum(_to_int(s.get("lots"), 0) for s in sellers_raw)

        for b in buyers_raw:
            lots = _to_int(b.get("lots"), 0)
            share = round(lots / total_buy_lots * 100, 1) if total_buy_lots > 0 else 0.0
            buyers.append(
                BrokerItem(
                    broker=str(b.get("broker") or ""),
                    lots=lots,
                    value_idr=_to_float(b.get("value"), 0.0),
                    avg_price=_to_float(b.get("averagePrice") or b.get("avg_price"), 0.0),
                    market_share_percent=share,
                )
            )

        for s in sellers_raw:
            lots = _to_int(s.get("lots"), 0)
            share = round(lots / total_sell_lots * 100, 1) if total_sell_lots > 0 else 0.0
            sellers.append(
                BrokerItem(
                    broker=str(s.get("broker") or ""),
                    lots=lots,
                    value_idr=_to_float(s.get("value"), 0.0),
                    avg_price=_to_float(s.get("averagePrice") or s.get("avg_price"), 0.0),
                    market_share_percent=share,
                )
            )

        top3_buy_concentration = sum(b.market_share_percent or 0.0 for b in buyers[:3])
        top3_sell_concentration = sum(s.market_share_percent or 0.0 for s in sellers[:3])

        if top3_buy_concentration > 60.0 and (top3_buy_concentration - top3_sell_concentration) > 15.0:
            bandar_status = "BIG_ACCUMULATION"
        elif top3_buy_concentration > 50.0 and top3_buy_concentration > top3_sell_concentration:
            bandar_status = "ACCUMULATION"
        elif top3_sell_concentration > 60.0 and (top3_sell_concentration - top3_buy_concentration) > 15.0:
            bandar_status = "BIG_DISTRIBUTION"
        elif top3_sell_concentration > 50.0:
            bandar_status = "DISTRIBUTION"
        else:
            bandar_status = "NEUTRAL"

        return BrokerFlowDomain(
            date=raw.get("date") or datetime.now(JAKARTA_TZ).strftime("%Y-%m-%d"),
            is_net=bool(raw.get("net", True)),
            top3_buyer_concentration_percent=round(top3_buy_concentration, 1),
            top3_seller_concentration_percent=round(top3_sell_concentration, 1),
            bandar_status=bandar_status,
            top_buyers=buyers[:5],
            top_sellers=sellers[:5],
        )

    @staticmethod
    def normalize_market_context(raw: dict[str, Any]) -> MarketContextDomain:
        raw = EvidenceNormalizer._unwrap(raw)
        items = raw.get("data") or raw.get("items") or []
        ihsg = next((i for i in items if i.get("IndexCode") == "COMPOSITE" or i.get("code") == "COMPOSITE"), None)
        if not ihsg and items:
            ihsg = items[0]

        price = _to_optional_float(ihsg.get("Close") or ihsg.get("close")) if ihsg else None
        prev = _to_optional_float(ihsg.get("Previous") or ihsg.get("previous")) or price if ihsg else None
        change_pct = round(((price - prev) / prev * 100), 2) if price and prev and prev > 0 else 0.0

        trend = "BULLISH" if change_pct > 0.2 else ("BEARISH" if change_pct < -0.2 else "NEUTRAL")

        return MarketContextDomain(
            index_code="COMPOSITE",
            index_name="IHSG",
            index_price=price,
            index_change_percent=change_pct,
            index_trend=trend,
        )

    @classmethod
    def assemble_snapshot(
        cls,
        session_id: uuid.UUID | str,
        symbol: str,
        quote_raw: dict[str, Any],
        orderbook_raw: dict[str, Any],
        history_raw: dict[str, Any],
        broker_raw: dict[str, Any],
        index_raw: dict[str, Any],
        stockbit_chart_raw: dict[str, Any] | None = None,
        snapshot_type: str = "INITIAL",
        sequence_number: int = 1,
        providers_used: dict[str, str] | None = None,
    ) -> EvidenceSnapshotSchema:
        """Assemble all normalized domains into one authoritative EvidenceSnapshotSchema."""
        now_wib = datetime.now(JAKARTA_TZ)
        snapshot_id = f"SNP-{now_wib.strftime('%Y%m%d')}-{symbol.upper()}-{sequence_number:03d}"

        quote = cls.normalize_quote(quote_raw, stockbit_chart=stockbit_chart_raw)
        orderbook = cls.normalize_orderbook(orderbook_raw)
        history, foreign_flow = cls.normalize_history_and_foreign_flow(history_raw)
        broker_flow = cls.normalize_broker_flow(broker_raw)
        market_ctx = cls.normalize_market_context(index_raw)

        # Fallback for quote price if after-hours or missing in quote endpoint
        if quote.last_price <= 0:
            if orderbook.best_bid > 0:
                quote.last_price = orderbook.best_bid
            elif history.recent_bars and history.recent_bars[0].close > 0:
                quote.last_price = history.recent_bars[0].close
                quote.open = history.recent_bars[0].open or quote.last_price
                quote.high = max(history.recent_bars[0].high or quote.last_price, quote.high)
                quote.low = min(history.recent_bars[0].low or quote.last_price, quote.low) if quote.low > 0 else (history.recent_bars[0].low or quote.last_price)
                if quote.volume_shares <= 0:
                    quote.volume_shares = history.recent_bars[0].volume
                    quote.volume_lots = quote.volume_shares // 100
                if quote.value_idr <= 0:
                    quote.value_idr = history.recent_bars[0].value or (quote.volume_shares * quote.last_price)

            if quote.previous_close <= 0 and len(history.recent_bars) > 1:
                quote.previous_close = history.recent_bars[1].close
            if quote.previous_close > 0:
                quote.change = quote.last_price - quote.previous_close
                quote.change_percent = round((quote.change / quote.previous_close * 100), 2)

        return EvidenceSnapshotSchema(
            snapshot_id=snapshot_id,
            session_id=str(session_id),
            symbol=symbol.upper(),
            market="IDX",
            captured_at=now_wib.isoformat(),
            snapshot_type=snapshot_type,
            sequence_number=sequence_number,
            providers_used=providers_used or {
                "quote": "PLUANG",
                "orderbook": "PLUANG",
                "historical_ohlcv": "IDX",
                "foreign_flow": "IDX",
                "broker_flow": "PLUANG",
                "market_context": "IDX",
            },
            completeness_status="COMPLETE",
            quote=quote,
            orderbook=orderbook,
            historical_ohlcv=history,
            foreign_flow=foreign_flow,
            broker_flow=broker_flow,
            market_context=market_ctx,
        )
