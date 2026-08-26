"""ZAPI HTTP Client module for TradePilot AI market data ingestion."""

from __future__ import annotations

import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class ZapiClientError(Exception):
    """Base error for ZAPI client."""
    pass


class ZapiClient:
    """Async HTTP client for ZAPI (https://api.zpi.web.id)."""

    def __init__(self, base_url: str = "https://api.zpi.web.id", api_key: str = "", timeout_seconds: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json",
            "User-Agent": "TradePilot-AI/2.0",
        }

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform an authenticated GET request to ZAPI."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        # Filter out None values in params
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.get(url, params=clean_params, headers=self._headers)
                if response.status_code == 429:
                    logger.warning("ZAPI Rate limit hit (429) on %s", endpoint)
                    raise ZapiClientError(f"ZAPI Rate Limit Exceeded (429) on {endpoint}")
                if response.status_code >= 400:
                    logger.error("ZAPI Error %s on %s: %s", response.status_code, endpoint, response.text)
                    raise ZapiClientError(f"ZAPI Error {response.status_code}: {response.text}")
                
                json_data = response.json()
                if isinstance(json_data, dict):
                    if "data" in json_data and isinstance(json_data["data"], (dict, list)):
                        return json_data["data"] if isinstance(json_data["data"], dict) else {"items": json_data["data"]}
                    if "content" in json_data and isinstance(json_data["content"], (dict, list)):
                        return json_data["content"] if isinstance(json_data["content"], dict) else {"items": json_data["content"]}
                return json_data
            except httpx.RequestError as exc:
                logger.error("ZAPI Network/Timeout exception on %s: %s", endpoint, exc)
                raise ZapiClientError(f"ZAPI Network Error: {exc}") from exc
