"""Deep merge utility for update operations.

Used by all fetch-merge-put manager methods to preserve nested
sub-object fields when applying partial updates.
"""

from typing import Any, Dict


def deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *updates* into *base*, returning a new dict.

    - Dict values are merged recursively (preserving sibling keys).
    - All other types (lists, scalars, None) replace the base value.

    Args:
        base: The existing object state.
        updates: Partial updates to apply on top.

    Returns:
        A new dict with updates merged in.
    """
    merged = base.copy()
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
