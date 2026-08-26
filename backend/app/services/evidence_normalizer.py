"""Evidence Normalizer service for TradePilot AI.

Transforms raw heterogeneous JSON responses from ZAPI providers (Pluang, IDX, Stockbit)
into standard canonical EvidenceSnapshot objects.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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


class EvidenceNormalizer:
    """Normalizes raw provider payloads into canonical EvidenceSnapshotSchema."""

    @staticmethod
    def _unwrap(raw: dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw, dict) and "data" in raw and isinstance(raw["data"], dict):
            return raw["data"]
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def normalize_quote(raw: dict[str, Any], provider: str = "PLUANG") -> QuoteDomain:
        raw = EvidenceNormalizer._unwrap(raw)
        stats = raw.get("keyStats") or {}
        
        # Try extracting price from multiple known fields
        last_price_str = raw.get("lastPrice") or raw.get("Close") or raw.get("close") or raw.get("price") or stats.get("iep") or raw.get("highestIndicativePrice") or 0
        if isinstance(last_price_str, str):
            last_price_str = last_price_str.replace(",", "")
        last_price = float(last_price_str or 0)

        previous_close = float(raw.get("previousClose") or raw.get("Previous") or raw.get("previous") or last_price)
        change = float(raw.get("change") or raw.get("Change") or (last_price - previous_close))
        change_pct = float(raw.get("changePercent") or raw.get("percentage") or ((change / previous_close * 100) if previous_close else 0))
        open_price = float(raw.get("openPrice") or raw.get("OpenPrice") or raw.get("open") or last_price)
        high_price = float(raw.get("highPrice") or raw.get("High") or raw.get("high") or raw.get("highestIndicativePrice") or last_price)
        low_price = float(raw.get("lowPrice") or raw.get("Low") or raw.get("low") or last_price)
        volume_shares = int(raw.get("volume") or raw.get("Volume") or 0)
        volume_lots = volume_shares // 100 if volume_shares > 0 else 0
        value_idr = float(raw.get("value") or raw.get("Value") or (volume_shares * last_price))
        freq = int(raw.get("frequency") or raw.get("Frequency") or 0)

        pe = float(raw["pe"]) if raw.get("pe") is not None else None
        pbv = float(raw["pbv"]) if raw.get("pbv") is not None else None
        mcap = float(raw.get("marketCap") or raw.get("MarketCapital") or 0) or None

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

        bids = [OrderbookLevel(price=float(b.get("price") or 0), lots=int(b.get("lots") or 0)) for b in raw_bids if b.get("price")]
        asks = [OrderbookLevel(price=float(a.get("price") or 0), lots=int(a.get("lots") or 0)) for a in raw_asks if a.get("price")]

        best_bid = float(raw.get("bestBid") or (bids[0].price if bids else 0))
        best_ask = float(raw.get("bestAsk") or (asks[0].price if asks else 0))
        spread = best_ask - best_bid if best_ask and best_bid else 0
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
        # Usually API returns newest first (index 0 = today), so reverse for technical computation
        bars_chronological = list(reversed(items)) if items else []

        parsed_bars: list[HistoricalBar] = []
        for b in items[:15]:  # Keep recent 15 bars for prompt presentation
            parsed_bars.append(
                HistoricalBar(
                    date=str(b.get("date") or b.get("Date") or ""),
                    open=float(b.get("open") or b.get("OpenPrice") or 0),
                    high=float(b.get("high") or b.get("High") or 0),
                    low=float(b.get("low") or b.get("Low") or 0),
                    close=float(b.get("close") or b.get("Close") or 0),
                    volume=int(b.get("volume") or b.get("Volume") or 0),
                    value=float(b.get("value") or b.get("Value") or 0),
                    net_foreign_shares=int(b.get("netForeignShares") or 0) if b.get("netForeignShares") is not None else None,
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
        today_net_shares = int(today_bar.get("netForeignShares") or 0)
        today_net_val = float(today_bar.get("netForeignValue") or (today_net_shares * (today_bar.get("close") or 0)))
        today_buy_shares = int(today_bar.get("foreignBuyShares") or 0) if today_bar.get("foreignBuyShares") else None
        today_sell_shares = int(today_bar.get("foreignSellShares") or 0) if today_bar.get("foreignSellShares") else None

        today_1d = ForeignFlowPeriod(
            net_shares=today_net_shares,
            net_value_idr=today_net_val,
            buy_shares=today_buy_shares,
            sell_shares=today_sell_shares,
        )

        def sum_period(bars: list[dict[str, Any]], count: int) -> ForeignFlowPeriod:
            subset = bars[:count]
            net_s = sum(int(b.get("netForeignShares") or 0) for b in subset)
            net_v = sum(float(b.get("netForeignValue") or (int(b.get("netForeignShares") or 0) * (b.get("close") or 0))) for b in subset)
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
            {"date": b.get("date"), "net_shares": b.get("netForeignShares", 0), "close": b.get("close", 0)}
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

        total_buy_lots = sum(int(b.get("lots") or 0) for b in buyers_raw)
        total_sell_lots = sum(int(s.get("lots") or 0) for s in sellers_raw)

        for b in buyers_raw:
            lots = int(b.get("lots") or 0)
            share = round(lots / total_buy_lots * 100, 1) if total_buy_lots > 0 else 0.0
            buyers.append(
                BrokerItem(
                    broker=str(b.get("broker") or ""),
                    lots=lots,
                    value_idr=float(b.get("value") or 0),
                    avg_price=float(b.get("averagePrice") or b.get("avg_price") or 0),
                    market_share_percent=share,
                )
            )

        for s in sellers_raw:
            lots = int(s.get("lots") or 0)
            share = round(lots / total_sell_lots * 100, 1) if total_sell_lots > 0 else 0.0
            sellers.append(
                BrokerItem(
                    broker=str(s.get("broker") or ""),
                    lots=lots,
                    value_idr=float(s.get("value") or 0),
                    avg_price=float(s.get("averagePrice") or s.get("avg_price") or 0),
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

        price = float(ihsg.get("Close") or ihsg.get("close") or 0) if ihsg else None
        prev = float(ihsg.get("Previous") or ihsg.get("previous") or price) if ihsg else None
        change_pct = round(((price - prev) / prev * 100), 2) if price and prev else 0.0

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
        snapshot_type: str = "INITIAL",
        sequence_number: int = 1,
        providers_used: dict[str, str] | None = None,
    ) -> EvidenceSnapshotSchema:
        """Assemble all normalized domains into one authoritative EvidenceSnapshotSchema."""
        now_wib = datetime.now(JAKARTA_TZ)
        snapshot_id = f"SNP-{now_wib.strftime('%Y%m%d')}-{symbol.upper()}-{sequence_number:03d}"

        quote = cls.normalize_quote(quote_raw)
        orderbook = cls.normalize_orderbook(orderbook_raw)
        history, foreign_flow = cls.normalize_history_and_foreign_flow(history_raw)
        broker_flow = cls.normalize_broker_flow(broker_raw)
        market_ctx = cls.normalize_market_context(index_raw)

        # Fallback for quote price if after-hours or missing in quote endpoint
        if quote.last_price <= 0:
            if history.recent_bars and history.recent_bars[0].close > 0:
                quote.last_price = history.recent_bars[0].close
                quote.open = history.recent_bars[0].open or quote.last_price
                quote.high = max(history.recent_bars[0].high or quote.last_price, quote.high)
                quote.low = min(history.recent_bars[0].low or quote.last_price, quote.low) if quote.low > 0 else (history.recent_bars[0].low or quote.last_price)
                if quote.volume_shares <= 0:
                    quote.volume_shares = history.recent_bars[0].volume
                    quote.volume_lots = quote.volume_shares // 100
                if quote.value_idr <= 0:
                    quote.value_idr = history.recent_bars[0].value or (quote.volume_shares * quote.last_price)
            elif orderbook.best_bid > 0:
                quote.last_price = orderbook.best_bid

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
