#!/usr/bin/env python3
"""Compare two firewall configuration snapshots.

Usage:
    python diff-policies.py [--current FILE] [--previous FILE] [--state-dir DIR]
    python diff-policies.py --state-dir DIR  # auto-loads two most recent snapshots
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Allow importing sibling modules when run as a script.
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from config import get_state_dir  # noqa: E402

SNAPSHOTS_SUBDIR = "firewall-snapshots"


# -- Argument parsing ----------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two firewall snapshots.")
    parser.add_argument(
        "--current",
        default=None,
        help="Path to the current (newer) snapshot JSON file",
    )
    parser.add_argument(
        "--previous",
        default=None,
        help="Path to the previous (older) snapshot JSON file",
    )
    parser.add_argument(
        "--state-dir",
        default=None,
        help="Directory containing firewall-snapshots/ (auto-loads two most recent)",
    )
    return parser.parse_args(argv)


# -- Snapshot loading ----------------------------------------------------------


def load_snapshot(path: Path) -> dict:
    """Load a snapshot JSON file."""
    return json.loads(path.read_text())


def find_recent_snapshots(state_dir: Path) -> list[Path]:
    """Return snapshot files sorted by name (oldest first)."""
    d = state_dir / SNAPSHOTS_SUBDIR
    if not d.exists():
        return []
    return sorted(d.glob("*.json"))


def load_snapshot_pair(
    current_path: str | None,
    previous_path: str | None,
    state_dir: Path,
) -> tuple[dict, dict]:
    """Load two snapshots — from explicit paths or auto-discover from state_dir.

    Returns (previous, current) dicts.

    Raises:
        SystemExit: if fewer than two snapshots are available.
    """
    if current_path and previous_path:
        return load_snapshot(Path(previous_path)), load_snapshot(Path(current_path))

    files = find_recent_snapshots(state_dir)
    if len(files) < 2:
        print(
            json.dumps({
                "success": False,
                "error": "Need at least two snapshots to compare. "
                f"Found {len(files)} in {state_dir / SNAPSHOTS_SUBDIR}.",
            }),
        )
        sys.exit(1)

    previous = load_snapshot(files[-2])
    current = load_snapshot(files[-1])
    return previous, current


# -- Diff helpers --------------------------------------------------------------


def _key_by(items: list[dict], key: str) -> dict[str, dict]:
    """Index a list of dicts by a key field."""
    result = {}
    for item in items:
        k = item.get(key)
        if k is not None:
            result[str(k)] = item
    return result


def _diff_field(old_val: Any, new_val: Any) -> dict | None:
    """Return a change record if values differ, else None."""
    if old_val == new_val:
        return None
    return {"old": old_val, "new": new_val}


def _diff_dicts(old: dict, new: dict, skip_keys: set[str] | None = None) -> dict[str, dict]:
    """Field-level diff of two dicts. Returns {field: {old, new}} for changed fields."""
    skip = skip_keys or set()
    changes: dict[str, dict] = {}
    all_keys = set(old.keys()) | set(new.keys())
    for k in sorted(all_keys - skip):
        change = _diff_field(old.get(k), new.get(k))
        if change is not None:
            changes[k] = change
    return changes


def diff_collection(
    previous_items: list[dict],
    current_items: list[dict],
    id_key: str,
    name_key: str = "name",
) -> dict[str, Any]:
    """Compare two lists of objects by ID, return structured diff.

    Returns:
        {
            "added": [...],
            "removed": [...],
            "modified": [...],
            "unchanged_count": int
        }
    """
    prev_by_id = _key_by(previous_items, id_key)
    curr_by_id = _key_by(current_items, id_key)

    prev_ids = set(prev_by_id.keys())
    curr_ids = set(curr_by_id.keys())

    added = []
    for aid in sorted(curr_ids - prev_ids):
        item = curr_by_id[aid]
        added.append({
            "id": aid,
            "name": item.get(name_key, ""),
            "details": item,
        })

    removed = []
    for rid in sorted(prev_ids - curr_ids):
        item = prev_by_id[rid]
        removed.append({
            "id": rid,
            "name": item.get(name_key, ""),
            "details": item,
        })

    modified = []
    unchanged = 0
    for cid in sorted(prev_ids & curr_ids):
        changes = _diff_dicts(prev_by_id[cid], curr_by_id[cid])
        if changes:
            modified.append({
                "id": cid,
                "name": curr_by_id[cid].get(name_key, prev_by_id[cid].get(name_key, "")),
                "changes": changes,
            })
        else:
            unchanged += 1

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged_count": unchanged,
    }


# -- Top-level diff builder ----------------------------------------------------


# Map of snapshot key -> (id field used for matching, display name key)
COLLECTION_CONFIG = {
    "policies": ("id", "name"),
    "networks": ("_id", "name"),
    "zones": ("_id", "name"),
    "firewall_groups": ("_id", "name"),
}


def diff_snapshots(previous: dict, current: dict) -> dict[str, Any]:
    """Compare two full snapshots, returning a structured diff report."""
    result: dict[str, Any] = {
        "previous_timestamp": previous.get("timestamp", "unknown"),
        "current_timestamp": current.get("timestamp", "unknown"),
    }

    for collection_key, (id_key, name_key) in COLLECTION_CONFIG.items():
        prev_items = previous.get(collection_key, [])
        curr_items = current.get(collection_key, [])
        result[collection_key] = diff_collection(prev_items, curr_items, id_key, name_key)

    # Compute overall summary.
    total_added = sum(len(result[k]["added"]) for k in COLLECTION_CONFIG)
    total_removed = sum(len(result[k]["removed"]) for k in COLLECTION_CONFIG)
    total_modified = sum(len(result[k]["modified"]) for k in COLLECTION_CONFIG)
    total_unchanged = sum(result[k]["unchanged_count"] for k in COLLECTION_CONFIG)

    result["summary"] = {
        "total_added": total_added,
        "total_removed": total_removed,
        "total_modified": total_modified,
        "total_unchanged": total_unchanged,
        "has_changes": (total_added + total_removed + total_modified) > 0,
    }

    return result


# -- Entry point ---------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    state_dir = Path(args.state_dir) if args.state_dir else get_state_dir()

    previous, current = load_snapshot_pair(args.current, args.previous, state_dir)
    report = diff_snapshots(previous, current)

    print(json.dumps({"success": True, **report}, indent=2))


if __name__ == "__main__":
    main()
