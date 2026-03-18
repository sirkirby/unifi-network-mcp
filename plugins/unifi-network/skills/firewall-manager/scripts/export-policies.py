#!/usr/bin/env python3
"""Export complete firewall configuration as a portable JSON snapshot.

Calls firewall tools in parallel, saves timestamped snapshot.

Usage:
    python export-policies.py [--mcp-url URL] [--state-dir DIR]
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow importing sibling modules when run as a script.
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from config import get_server_url, get_state_dir  # noqa: E402
from mcp_client import MCPClient, MCPConnectionError, MCPToolError  # noqa: E402

logger = logging.getLogger("export-policies")

SNAPSHOTS_SUBDIR = "firewall-snapshots"


# -- Argument parsing ----------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export UniFi firewall configuration via MCP.")
    parser.add_argument(
        "--mcp-url",
        default=None,
        help="MCP server URL (default: auto-detect from env / localhost:3000)",
    )
    parser.add_argument(
        "--state-dir",
        default=None,
        help="Directory for snapshot storage (default: auto-detect)",
    )
    return parser.parse_args(argv)


# -- Data extraction helpers ---------------------------------------------------


def _extract_list(result: dict, key: str) -> list:
    """Extract a list payload from an MCP tool result by key."""
    if not result.get("success", False):
        return []
    val = result.get(key, result.get("data"))
    if isinstance(val, list):
        return val
    return []


# -- Snapshot I/O --------------------------------------------------------------


def snapshot_dir(state_dir: Path) -> Path:
    """Return the snapshots subdirectory, creating it if needed."""
    d = state_dir / SNAPSHOTS_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_snapshot(state_dir: Path, snapshot: dict) -> Path:
    """Write snapshot JSON to a timestamped file and return the path."""
    d = snapshot_dir(state_dir)
    ts = snapshot.get("timestamp", datetime.now(timezone.utc).isoformat())
    safe_ts = ts.replace(":", "-").replace("+", "_")
    filename = f"{safe_ts}.json"
    path = d / filename
    path.write_text(json.dumps(snapshot, indent=2))
    return path


def list_snapshots(state_dir: Path) -> list[Path]:
    """Return snapshot files sorted by name (oldest first)."""
    d = state_dir / SNAPSHOTS_SUBDIR
    if not d.exists():
        return []
    files = sorted(d.glob("*.json"))
    return files


# -- Main async logic ----------------------------------------------------------


async def export_policies(mcp_url: str, state_dir: Path) -> dict[str, Any]:
    """Connect to MCP, gather firewall data, build and save a snapshot."""
    async with MCPClient(mcp_url) as client:
        # Check readiness.
        ready = await client.check_ready("unifi_tool_index")
        if not ready:
            return await client.get_setup_error()

        # Step 1: Collect bulk data in parallel.
        try:
            results = await client.call_tools_parallel([
                ("unifi_list_firewall_policies", {}),
                ("unifi_list_firewall_zones", {}),
                ("unifi_list_networks", {}),
                ("unifi_list_ip_groups", {}),
            ])
        except (MCPConnectionError, MCPToolError) as e:
            return {"success": False, "error": f"Failed to collect firewall data: {e}"}

        policies_result, zones_result, networks_result, ip_groups_result = results

        policies = _extract_list(policies_result, "policies")
        zones = _extract_list(zones_result, "zones")
        networks = _extract_list(networks_result, "networks")
        ip_groups = _extract_list(ip_groups_result, "ip_groups")

        # Step 2: Fetch details for each policy.
        detailed_policies: list[dict] = []
        for p in policies:
            pid = p.get("id")
            if not pid:
                detailed_policies.append(p)
                continue
            try:
                detail_result = await client.call_tool(
                    "unifi_get_firewall_policy_details", {"policy_id": pid}
                )
                if detail_result.get("success"):
                    detail = detail_result.get("details", detail_result.get("data", {}))
                    # Merge summary fields for completeness.
                    detail.setdefault("id", pid)
                    detail.setdefault("name", p.get("name"))
                    detail.setdefault("enabled", p.get("enabled"))
                    detail.setdefault("action", p.get("action"))
                    detail.setdefault("rule_index", p.get("rule_index"))
                    detail.setdefault("ruleset", p.get("ruleset"))
                    detailed_policies.append(detail)
                else:
                    # Fall back to summary if details unavailable.
                    detailed_policies.append(p)
            except (MCPConnectionError, MCPToolError):
                logger.warning("Failed to fetch details for policy %s, using summary", pid)
                detailed_policies.append(p)

        # Step 3: Build snapshot.
        timestamp = datetime.now(timezone.utc).isoformat()
        snapshot = {
            "timestamp": timestamp,
            "policies": detailed_policies,
            "zones": zones,
            "networks": networks,
            "ip_groups": ip_groups,
        }

        # Step 4: Save to disk.
        path = save_snapshot(state_dir, snapshot)
        logger.info("Snapshot saved to %s", path)

        return {
            "success": True,
            "snapshot": snapshot,
            "file": str(path),
            "summary": {
                "policies": len(detailed_policies),
                "zones": len(zones),
                "networks": len(networks),
                "ip_groups": len(ip_groups),
            },
        }


# -- Entry point ---------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    mcp_url = args.mcp_url or get_server_url("network")
    state_dir = Path(args.state_dir) if args.state_dir else get_state_dir(ensure=True)

    result = asyncio.run(export_policies(mcp_url, state_dir))

    print(json.dumps(result, indent=2))

    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    main()
