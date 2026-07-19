"""Evidence test factory."""

from __future__ import annotations

import copy
from typing import Mapping

from tests.factories.deep_merge import deep_merge

EVIDENCE_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
SESSION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

_BASE = {
    "evidence_id": EVIDENCE_ID,
    "session_id": SESSION_ID,
    "evidence_type": "ORDERBOOK_SCREENSHOT",
    "uploaded_at": "2026-07-18T09:35:00+07:00",
    "market_timestamp": "2026-07-18T09:30:00+07:00",
    "file_reference": f"trade-sessions/{SESSION_ID}/evidence/"
    "bbri_orderbook_morning_2026-07-18.png",
    "file_name": "bbri_orderbook_morning_2026-07-18.png",
    "mime_type": "image/png",
    "file_size_bytes": 245760,
    "image_width": 1080,
    "image_height": 1920,
    "checksum_sha256": "a" * 64,
    "usability": "READABLE",
    "extraction_status": "NOT_REQUESTED",
    "is_active": True,
    "superseded_by": None,
    "extracted_facts": [],
    "user_note": None,
    "limitations": [],
}


def make_evidence(*, overrides: Mapping[str, object] | None = None) -> dict[str, object]:
    """Return a deterministic Evidence dict."""
    base = copy.deepcopy(_BASE)
    if overrides:
        return deep_merge(base, overrides)
    return base
