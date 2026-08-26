"""IDX (Bursa Efek Indonesia) Provider Adapter for ZAPI."""

from __future__ import annotations

from typing import Any
from app.services.market_data.zapi_client import ZapiClient


class IdxProvider:
    """Provider wrapper for IDX endpoints on ZAPI."""

    def __init__(self, client: ZapiClient) -> None:
        self.client = client

    async def get_stock_history(self, symbol: str, length: int = 130, from_date: str | None = None, to_date: str | None = None) -> dict[str, Any]:
        """Fetch historical daily OHLCV and daily foreign net data from IDX."""
        params: dict[str, Any] = {
            "code": symbol.upper(),
            "length": length,
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return await self.client.get("/v1/finance:idx/stock-history", params)

    async def get_stock_summary(self, symbol: str, date: str | None = None) -> dict[str, Any]:
        """Fetch official stock summary from IDX."""
        params: dict[str, Any] = {"code": symbol.upper(), "length": 5}
        if date:
            params["date"] = date
        return await self.client.get("/v1/finance:idx/stock-summary", params)

    async def get_foreign_flow(self, symbol: str, date: str | None = None) -> dict[str, Any]:
        """Fetch daily foreign flow ranked table from IDX."""
        params: dict[str, Any] = {"code": symbol.upper(), "length": 5}
        if date:
            params["date"] = date
        return await self.client.get("/v1/finance:idx/foreign-flow", params)

    async def get_index_summary(self, date: str | None = None) -> dict[str, Any]:
        """Fetch composite index (IHSG) and sector summary from IDX."""
        params: dict[str, Any] = {"length": 20}
        if date:
            params["date"] = date
        return await self.client.get("/v1/finance:idx/index-summary", params)
