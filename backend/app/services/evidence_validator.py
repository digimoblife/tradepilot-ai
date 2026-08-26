"""Evidence Validator service for TradePilot AI.

Validates the integrity, completeness, and freshness of EvidenceSnapshotSchema
to prevent LLM hallucination and enforce deterministic product rules.
"""

from __future__ import annotations

from typing import NamedTuple
from app.api.schemas.evidence_snapshot import EvidenceSnapshotSchema


class ValidationResult(NamedTuple):
    is_valid: bool
    completeness_status: str  # "COMPLETE" | "PARTIAL" | "FAILED"
    critical_errors: list[str]
    warnings: list[str]


class EvidenceValidator:
    """Deterministic validation rules for System-Acquired Evidence."""

    MIN_HISTORY_DAYS = 30  # Minimum 30 trading days for basic analysis

    @classmethod
    def validate_snapshot(cls, snapshot: EvidenceSnapshotSchema) -> ValidationResult:
        critical_errors: list[str] = []
        warnings: list[str] = []

        # 1. Validate Quote
        if snapshot.quote.last_price <= 0:
            critical_errors.append("Harga terkini (last_price) tidak valid atau 0.")
        if snapshot.quote.low > snapshot.quote.high:
            critical_errors.append("Rentang harga harian tidak valid (Low > High).")

        # 2. Validate Orderbook
        if not snapshot.orderbook.bids and not snapshot.orderbook.asks:
            warnings.append("Orderbook kosong (kemungkinan sesi pre-market atau saham suspensi).")
        elif snapshot.orderbook.best_bid <= 0 or snapshot.orderbook.best_ask <= 0:
            warnings.append("Best Bid atau Best Ask tidak terdeteksi.")
        elif snapshot.orderbook.best_bid > snapshot.orderbook.best_ask:
            warnings.append("Best Bid > Best Ask (kemungkinan fase call auction / pre-closing).")

        # 3. Validate Historical OHLCV
        if snapshot.historical_ohlcv.horizon_days < cls.MIN_HISTORY_DAYS:
            if snapshot.historical_ohlcv.horizon_days == 0:
                critical_errors.append("Data riwayat harga (OHLCV) kosong dari bursa.")
            else:
                warnings.append(
                    f"Riwayat harga terbatas ({snapshot.historical_ohlcv.horizon_days} hari bursa, kemungkinan saham baru IPO)."
                )

        # 4. Validate Foreign Flow
        if not snapshot.foreign_flow.today_1d or snapshot.foreign_flow.today_1d.net_shares == 0:
            warnings.append("Data akumulasi asing hari ini netral atau belum terupdate.")

        # 5. Validate Broker Summary
        if not snapshot.broker_flow.top_buyers and not snapshot.broker_flow.top_sellers:
            warnings.append("Data broker summary hari ini belum dirilis oleh bursa.")

        # Determine final status
        if critical_errors:
            return ValidationResult(
                is_valid=False,
                completeness_status="FAILED",
                critical_errors=critical_errors,
                warnings=warnings,
            )
        elif warnings:
            return ValidationResult(
                is_valid=True,
                completeness_status="PARTIAL",
                critical_errors=[],
                warnings=warnings,
            )
        else:
            return ValidationResult(
                is_valid=True,
                completeness_status="COMPLETE",
                critical_errors=[],
                warnings=[],
            )
