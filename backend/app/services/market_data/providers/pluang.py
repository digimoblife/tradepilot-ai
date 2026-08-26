"""Pluang Provider Adapter for ZAPI."""

from __future__ import annotations

from typing import Any
from app.services.market_data.zapi_client import ZapiClient


class PluangProvider:
    """Provider wrapper for Pluang endpoints on ZAPI."""

    def __init__(self, client: ZapiClient) -> None:
        self.client = client

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Fetch current stock quote from Pluang."""
        return await self.client.get("/v1/finance:pluang/quote", {"code": symbol.upper()})

    async def get_orderbook(self, symbol: str) -> dict[str, Any]:
        """Fetch live bid/ask orderbook depth from Pluang."""
        return await self.client.get("/v1/finance:pluang/orderbook", {"code": symbol.upper()})

    async def get_broker_summary(
        self, symbol: str, start_date: str | None = None, end_date: str | None = None, net: bool = True
    ) -> dict[str, Any]:
        """Fetch broker summary / bandarmology from Pluang."""
        params: dict[str, Any] = {
            "code": symbol.upper(),
            "net": "true" if net else "false",
        }
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return await self.client.get("/v1/finance:pluang/broker-summary", params)

    async def get_chart_intraday(self, symbol: str) -> dict[str, Any]:
        """Fetch 5-min intraday candles from Pluang."""
        return await self.client.get("/v1/finance:pluang/chart", {"code": symbol.upper()})
