"""Tests for Alembic migration graph single head reconciliation."""

import os
from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_CFG = "alembic.ini"


def test_alembic_has_exactly_one_head() -> None:
    """Verify that Alembic script directory has exactly one canonical head."""
    config = Config(ALEMBIC_CFG)
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()
    assert len(heads) == 1, f"Expected 1 Alembic head, found {len(heads)}: {heads}"
    head_rev = heads[0]
    assert head_rev == "7f716a66f99b", f"Expected head 7f716a66f99b, found {head_rev}"


def test_merge_revision_parents() -> None:
    """Verify that merge revision 7f716a66f99b merges e1f2a3b4c5d6 and a1b2c3d4e5f6."""
    config = Config(ALEMBIC_CFG)
    script = ScriptDirectory.from_config(config)

    merge_script = script.get_revision("7f716a66f99b")
    assert merge_script is not None, "Merge revision 7f716a66f99b not found"
    
    down_revisions = merge_script.down_revision
    if isinstance(down_revisions, str):
        down_revisions = (down_revisions,)
    
    assert set(down_revisions) == {"e1f2a3b4c5d6", "a1b2c3d4e5f6"}, (
        f"Expected down_revisions {{'e1f2a3b4c5d6', 'a1b2c3d4e5f6'}}, got {down_revisions}"
    )
