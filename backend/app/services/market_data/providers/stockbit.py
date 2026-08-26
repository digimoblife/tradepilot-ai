"""Stockbit Provider Adapter for ZAPI."""

from __future__ import annotations

from typing import Any
from app.services.market_data.zapi_client import ZapiClient


class StockbitProvider:
    """Provider wrapper for Stockbit endpoints on ZAPI."""

    def __init__(self, client: ZapiClient) -> None:
        self.client = client

    async def get_symbol(self, symbol: str) -> dict[str, Any]:
        """Fetch symbol overview from Stockbit."""
        return await self.client.get("/v1/finance:stockbit/symbol", {"symbol": symbol.upper()})

    async def get_chart(self, symbol: str, count: int = 100) -> dict[str, Any]:
        """Fetch 1-minute intraday price series from Stockbit."""
        return await self.client.get("/v1/finance:stockbit/chart", {"symbol": symbol.upper(), "count": count})
