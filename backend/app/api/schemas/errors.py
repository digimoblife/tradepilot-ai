"""Unified API error response schema (TP-1007)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
