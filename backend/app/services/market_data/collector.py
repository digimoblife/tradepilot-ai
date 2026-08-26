"""Market Data Collector orchestrator for TradePilot AI.

Coordinates parallel acquisition from ZAPI providers (Pluang, IDX, Stockbit),
handles graceful fallback, normalizes payloads, and runs validation rules.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.api.schemas.evidence_snapshot import EvidenceSnapshotSchema
from app.config import AppConfig
from app.services.evidence_normalizer import EvidenceNormalizer
from app.services.evidence_validator import EvidenceValidator, ValidationResult
from app.services.market_data.providers.idx import IdxProvider
from app.services.market_data.providers.pluang import PluangProvider
from app.services.market_data.providers.stockbit import StockbitProvider
from app.services.market_data.zapi_client import ZapiClient

logger = logging.getLogger(__name__)


class MarketDataCollector:
    """Orchestrator for acquiring complete market evidence."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = ZapiClient(
            base_url=config.zapi_base_url,
            api_key=config.zapi_api_key,
            timeout_seconds=float(config.zapi_timeout_seconds),
        )
        self.pluang = PluangProvider(self.client)
        self.idx = IdxProvider(self.client)
        self.stockbit = StockbitProvider(self.client)

    async def acquire_snapshot(
        self,
        session_id: uuid.UUID | str,
        symbol: str,
        snapshot_type: str = "INITIAL",
        sequence_number: int = 1,
    ) -> tuple[EvidenceSnapshotSchema, ValidationResult]:
        """Fetch all evidence domains concurrently and return assembled snapshot + validation result."""
        symbol = symbol.upper()
        logger.info("Acquiring %s market data snapshot for %s (Session: %s)", snapshot_type, symbol, session_id)

        providers_used: dict[str, str] = {
            "quote": "PLUANG",
            "orderbook": "PLUANG",
            "historical_ohlcv": "IDX",
            "foreign_flow": "IDX",
            "broker_flow": "PLUANG",
            "market_context": "IDX",
        }

        # 1. Execute concurrent requests
        results = await asyncio.gather(
            self.pluang.get_quote(symbol),
            self.pluang.get_orderbook(symbol),
            self.idx.get_stock_history(symbol, length=130),
            self.pluang.get_broker_summary(symbol),
            self.idx.get_index_summary(),
            return_exceptions=True,
        )

        quote_res, orderbook_res, history_res, broker_res, index_res = results

        # 2. Handle Fallbacks
        # Fallback for Quote if Pluang fails
        if isinstance(quote_res, Exception) or not quote_res:
            logger.warning("Pluang quote failed for %s, falling back to IDX: %s", symbol, quote_res)
            try:
                quote_res = await self.idx.get_stock_summary(symbol)
                providers_used["quote"] = "IDX"
            except Exception as exc:
                logger.error("IDX quote fallback also failed: %s", exc)
                quote_res = {}

        # Fallback for Orderbook if Pluang fails
        if isinstance(orderbook_res, Exception) or not orderbook_res:
            logger.warning("Pluang orderbook failed for %s: %s", symbol, orderbook_res)
            orderbook_res = {}

        # Fallback for History if IDX fails
        if isinstance(history_res, Exception) or not history_res:
            logger.warning("IDX history failed for %s: %s", symbol, history_res)
            history_res = {}

        # Fallback for Broker Summary if Pluang fails
        if isinstance(broker_res, Exception) or not broker_res:
            logger.warning("Pluang broker summary failed for %s, trying IDX fallback: %s", symbol, broker_res)
            try:
                broker_res = await self.idx.get_foreign_flow(symbol)  # or IDX broker summary
                providers_used["broker_flow"] = "IDX"
            except Exception:
                broker_res = {}

        # Fallback for Index summary
        if isinstance(index_res, Exception) or not index_res:
            index_res = {}

        # 3. Assemble Snapshot
        snapshot = EvidenceNormalizer.assemble_snapshot(
            session_id=session_id,
            symbol=symbol,
            quote_raw=quote_res if isinstance(quote_res, dict) else {},
            orderbook_raw=orderbook_res if isinstance(orderbook_res, dict) else {},
            history_raw=history_res if isinstance(history_res, dict) else {},
            broker_raw=broker_res if isinstance(broker_res, dict) else {},
            index_raw=index_res if isinstance(index_res, dict) else {},
            snapshot_type=snapshot_type,
            sequence_number=sequence_number,
            providers_used=providers_used,
        )

        # 4. Validate Snapshot
        val_result = EvidenceValidator.validate_snapshot(snapshot)
        snapshot.completeness_status = val_result.completeness_status

        return snapshot, val_result
