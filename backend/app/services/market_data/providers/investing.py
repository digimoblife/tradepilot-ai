"""Investing Provider Adapter for ZAPI."""

from __future__ import annotations

from typing import Any

from app.services.market_data.zapi_client import ZapiClient


class InvestingProvider:
    """Provider wrapper for Investing endpoints on ZAPI."""

    def __init__(self, client: ZapiClient) -> None:
        self.client = client
        self._pair_cache: dict[str, int] = {}

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Fetch stock quote & fundamental data from Investing.

        Resolves the exact Indonesian instrument (pairId) first to prevent
        collisions with global tickers (e.g. BBCA on NYSE ETF vs BBCA on IDX).
        """
        sym = symbol.upper()
        pair_id = self._pair_cache.get(sym)

        if pair_id is None:
            try:
                search_res = await self.client.get(
                    "/v1/finance:investing/search", {"q": sym}
                )
                quotes = search_res.get("quotes", [])
                for q in quotes:
                    if q.get("symbol") == sym:
                        country = str(q.get("country") or "").lower()
                        exchange = str(q.get("exchange") or "").lower()
                        item_type = str(q.get("type") or "").lower()
                        if (
                            "indonesia" in country
                            or "jakarta" in exchange
                            or "jakarta" in item_type
                        ):
                            pair_id = q.get("pairId")
                            if pair_id:
                                self._pair_cache[sym] = pair_id
                            break
            except Exception:
                # If search fails, fallback to standard symbol query
                pair_id = None

        params: dict[str, Any] = {"query": sym}
        if pair_id:
            params["pairId"] = pair_id

        return await self.client.get("/v1/finance:investing/quote", params)

