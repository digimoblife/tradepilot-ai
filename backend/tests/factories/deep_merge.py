"""Safe nested dictionary merge for fixture overrides."""

from __future__ import annotations

import copy
from typing import Mapping


def deep_merge(base: Mapping[str, object], overrides: Mapping[str, object]) -> dict[str, object]:
    """Return a new dict merging *overrides* into a deep copy of *base*.

    - Nested ``Mapping`` values are recursively merged.
    - Scalar and list values from *overrides* replace the base value directly.
    - ``None`` in an override value explicitly sets the field to ``None``.
    - Neither *base* nor *overrides* is mutated.
    """
    result = copy.deepcopy(base)
    for key, val in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, Mapping):
            merged: dict[str, object] = deep_merge(result[key], val)  # type: ignore[arg-type]
            result[key] = merged
        else:
            result[key] = copy.deepcopy(val)
    return result
