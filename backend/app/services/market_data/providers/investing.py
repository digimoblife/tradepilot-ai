"""Investing Provider Adapter for ZAPI."""

from __future__ import annotations

from typing import Any

from app.services.market_data.zapi_client import ZapiClient


class InvestingProvider:
    """Provider wrapper for Investing endpoints on ZAPI."""

    def __init__(self, client: ZapiClient) -> None:
        self.client = client

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Fetch stock quote & fundamental data from Investing."""
        return await self.client.get("/v1/finance:investing/quote", {"query": symbol.upper()})
