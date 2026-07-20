"""Tests for Context Summary Validator (TP-0311)."""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from app.validation.context_summary import (
    CONTEXT_ENTRY_MISMATCH,
    CONTEXT_ORIGINAL_QUANTITY_MISMATCH,
    CONTEXT_PENDING_PROPOSAL_ACTIVATED,
    CONTEXT_REMAINING_QUANTITY_MISMATCH,
    CONTEXT_STALE,
    ContextSummaryValidationResult,
    validate_context_summary,
)

CANONICAL = {
    "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "ticker": "BBRI",
    "position": {
        "entry_price": 2800,
        "original_quantity": 100,
        "remaining_quantity": 50,
        "active_stop_loss": 2840,
        "active_target": 2920,
        "position_status": "PARTIALLY_CLOSED",
    },
}

CTG = {
    "source_cutoff_timestamp": "2026-07-17T14:10:00+07:00",
    "current_position": {
        "entry_price": 2800,
        "original_quantity": 100,
        "remaining_quantity": 50,
    },
    "active_levels": {
        "active_stop_loss": {"price": 2840, "label": "Active stop", "summary": ""},
        "active_target": {"price": 2920, "label": "Active target", "summary": ""},
        "proposed_stop_loss": None,
        "proposed_target": None,
    },
}

# Context cutoff = 2026-07-17T14:10:00+07:00 = 2026-07-17T07:10:00Z
REQUIRED_TS = datetime(2026, 7, 17, 7, 10, 0, tzinfo=timezone.utc)


def _expect(result: ContextSummaryValidationResult, code: str) -> None:
    assert not result.valid, f"Expected {code} but result is valid"
    codes = {i.code for i in result.issues}
    assert code in codes, f"Expected code {code!r} not in {codes}"


# ===================================================================


class TestEntry:
    def test_matching(self) -> None:
        assert validate_context_summary(CTG, CANONICAL).valid

    def test_altered(self) -> None:
        p = {**CTG, "current_position": {**CTG["current_position"], "entry_price": 999}}
        _expect(validate_context_summary(p, CANONICAL), CONTEXT_ENTRY_MISMATCH)

    def test_float_accepted_as_mismatch(self) -> None:
        p = {**CTG, "current_position": {**CTG["current_position"], "entry_price": 2800.5}}
        _expect(validate_context_summary(p, CANONICAL), CONTEXT_ENTRY_MISMATCH)


class TestOriginalQuantity:
    def test_matching(self) -> None:
        assert validate_context_summary(CTG, CANONICAL).valid

    def test_altered(self) -> None:
        p = {**CTG, "current_position": {**CTG["current_position"], "original_quantity": 999}}
        _expect(validate_context_summary(p, CANONICAL), CONTEXT_ORIGINAL_QUANTITY_MISMATCH)


class TestRemainingQuantity:
    def test_matching(self) -> None:
        assert validate_context_summary(CTG, CANONICAL).valid

    def test_altered(self) -> None:
        p = {**CTG, "current_position": {**CTG["current_position"], "remaining_quantity": 999}}
        _expect(validate_context_summary(p, CANONICAL), CONTEXT_REMAINING_QUANTITY_MISMATCH)


class TestPendingProposals:
    def test_no_proposals_ok(self) -> None:
        assert validate_context_summary(CTG, CANONICAL).valid

    def test_proposal_differs_from_active_valid(self) -> None:
        """A proposed stop may differ from active stop while remaining pending."""
        p = {
            **CTG,
            "active_levels": {
                **CTG["active_levels"],
                "proposed_stop_loss": {"price": 2800, "label": "Proposed stop", "summary": ""},
            },
        }
        assert validate_context_summary(p, CANONICAL).valid

    def test_proposal_activated_invalid(self) -> None:
        """Proposed stop presented as active when canonical hasn't changed."""
        p = {
            **CTG,
            "active_levels": {
                **CTG["active_levels"],
                "active_stop_loss": {"price": 2800, "label": "Active stop", "summary": ""},
                "proposed_stop_loss": {"price": 2800, "label": "Proposed stop", "summary": ""},
            },
        }
        _expect(validate_context_summary(p, CANONICAL), CONTEXT_PENDING_PROPOSAL_ACTIVATED)

    def test_proposed_target_activated_invalid(self) -> None:
        p = {
            **CTG,
            "active_levels": {
                **CTG["active_levels"],
                "active_target": {"price": 3000, "label": "Active target", "summary": ""},
                "proposed_target": {"price": 3000, "label": "Proposed target", "summary": ""},
            },
        }
        _expect(validate_context_summary(p, CANONICAL), CONTEXT_PENDING_PROPOSAL_ACTIVATED)


class TestCutoff:
    def test_equal(self) -> None:
        assert validate_context_summary(
            CTG, CANONICAL, required_cutoff_timestamp=REQUIRED_TS
        ).valid

    def test_newer(self) -> None:
        """Required cutoff before context cutoff → not stale."""
        ts = datetime(2026, 7, 17, 6, 0, 0, tzinfo=timezone.utc)
        assert validate_context_summary(CTG, CANONICAL, required_cutoff_timestamp=ts).valid

    def test_stale(self) -> None:
        """Required cutoff after context cutoff → stale."""
        ts = datetime(2026, 7, 17, 8, 0, 0, tzinfo=timezone.utc)
        _expect(
            validate_context_summary(CTG, CANONICAL, required_cutoff_timestamp=ts), CONTEXT_STALE
        )

    def test_invalid_timestamp(self) -> None:
        p = {**CTG, "source_cutoff_timestamp": "not-a-timestamp"}
        r = validate_context_summary(p, CANONICAL)
        assert not r.valid

    def test_cross_offset_comparison(self) -> None:
        """Context in +07:00, required in UTC, same instant."""
        ts = datetime(2026, 7, 17, 7, 10, 0, tzinfo=timezone.utc)
        assert validate_context_summary(CTG, CANONICAL, required_cutoff_timestamp=ts).valid


class TestImmutability:
    def test_ctx_unchanged(self) -> None:
        p = {**CTG, "current_position": {**CTG["current_position"], "entry_price": 999}}
        before = copy.deepcopy(p)
        validate_context_summary(p, CANONICAL)
        assert p == before

    def test_canonical_unchanged(self) -> None:
        c = {**CANONICAL, "position": {**CANONICAL["position"]}}
        p = {**CTG, "current_position": {**CTG["current_position"], "entry_price": 999}}
        before = copy.deepcopy(c)
        validate_context_summary(p, c)
        assert c == before


class TestMultiError:
    def test_multiple_errors(self) -> None:
        p = {
            **CTG,
            "current_position": {
                **CTG["current_position"],
                "entry_price": 999,
                "original_quantity": 999,
            },
        }
        r = validate_context_summary(p, CANONICAL)
        assert not r.valid
        assert len(r.issues) >= 2

    def test_deterministic_ordering(self) -> None:
        p = {
            **CTG,
            "current_position": {
                **CTG["current_position"],
                "entry_price": 999,
                "original_quantity": 999,
            },
        }
        r1 = validate_context_summary(p, CANONICAL)
        r2 = validate_context_summary(p, CANONICAL)
        assert r1.issues == r2.issues
