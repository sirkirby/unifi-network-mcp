#!/usr/bin/env python3
"""Copy shared skill modules into each skill's scripts/ directory.

Ensures each skill is self-contained for plugin marketplace distribution.
Source of truth: skills/_shared/mcp_client.py, skills/_shared/config.py

Usage:
    python skills/_build/sync_shared.py [--check]

Flags:
    --check   Dry-run mode: report drift without modifying files (exit 1 if drift found)
"""
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SHARED_DIR = REPO_ROOT / "skills" / "_shared"
PLUGINS_DIR = REPO_ROOT / "plugins"

SHARED_FILES = ["mcp_client.py", "config.py", "requirements.txt"]


def find_skill_script_dirs() -> list[Path]:
    """Find all skill scripts/ directories that should receive shared files."""
    dirs = []
    for plugin_dir in PLUGINS_DIR.iterdir():
        if not plugin_dir.is_dir():
            continue
        skills_dir = plugin_dir / "skills"
        if not skills_dir.exists():
            continue
        for skill_dir in skills_dir.iterdir():
            scripts_dir = skill_dir / "scripts"
            if scripts_dir.is_dir():
                dirs.append(scripts_dir)
    return dirs


def sync(check_only: bool = False) -> bool:
    """Sync shared files to all skill scripts/ directories."""
    target_dirs = find_skill_script_dirs()
    if not target_dirs:
        print("No skill scripts/ directories found. Nothing to sync.")
        return True

    all_in_sync = True
    for target_dir in target_dirs:
        for filename in SHARED_FILES:
            src = SHARED_DIR / filename
            dst = target_dir / filename
            if not src.exists():
                print(f"WARNING: Source {src} does not exist, skipping")
                continue
            if dst.exists() and src.read_text() == dst.read_text():
                continue
            all_in_sync = False
            rel_dst = dst.relative_to(REPO_ROOT)
            if check_only:
                print(f"DRIFT: {rel_dst} differs from source")
            else:
                shutil.copy2(src, dst)
                print(f"SYNCED: {rel_dst}")

    if check_only and not all_in_sync:
        print("\nRun 'make sync-skills' to fix drift.")
        return False
    if all_in_sync:
        print("All shared files in sync.")
    return True


if __name__ == "__main__":
    check_only = "--check" in sys.argv
    success = sync(check_only=check_only)
    sys.exit(0 if success else 1)
