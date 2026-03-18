#!/usr/bin/env python3
"""Collect network health data via MCP tools.

Calls unifi_get_system_info, unifi_get_network_health, unifi_list_devices,
and unifi_list_alarms in parallel. Compares to stored baseline and reports
changes. Outputs structured JSON.

Usage:
    python collect-health.py [--mcp-url URL] [--format json|human] [--state-dir DIR]
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow importing sibling modules when run as a script.
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from config import get_server_url, get_state_dir  # noqa: E402
from mcp_client import MCPClient, MCPConnectionError, MCPToolError  # noqa: E402

logger = logging.getLogger("collect-health")

BASELINE_FILENAME = "health-baseline.json"

# ── Argument parsing ─────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect UniFi network health data via MCP.")
    parser.add_argument(
        "--mcp-url",
        default=None,
        help="MCP server URL (default: auto-detect from env / localhost:3000)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "human"],
        default="json",
        dest="output_format",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--state-dir",
        default=None,
        help="Directory for baseline state files (default: auto-detect)",
    )
    return parser.parse_args(argv)


# ── Result parsing helpers ───────────────────────────────────────────────────


def _extract_data(result: dict) -> dict | list | None:
    """Extract the data payload from an MCP tool result."""
    if not result.get("success", False):
        return None
    return result.get("data")


def _parse_devices(device_data) -> dict:
    """Parse device list into summary counts and offline list."""
    if not device_data or not isinstance(device_data, list):
        return {"total": 0, "online": 0, "offline": 0, "upgrading": 0, "other": 0, "offline_devices": []}

    total = len(device_data)
    online = 0
    offline = 0
    upgrading = 0
    other = 0
    offline_devices = []

    for dev in device_data:
        state = dev.get("state", dev.get("status", 0))
        # Normalise: the tool may return a string label or an int code.
        if isinstance(state, str):
            state = state.lower()
        if state in (1, "online", "connected"):
            online += 1
        elif state in (0, "offline", "disconnected"):
            offline += 1
            offline_devices.append({
                "name": dev.get("name", "unknown"),
                "mac": dev.get("mac", "unknown"),
                "model": dev.get("model", ""),
                "last_seen": dev.get("last_seen", ""),
            })
        elif state in (6, "upgrading"):
            upgrading += 1
        else:
            other += 1

    return {
        "total": total,
        "online": online,
        "offline": offline,
        "upgrading": upgrading,
        "other": other,
        "offline_devices": offline_devices,
    }


def _parse_health(health_data) -> dict:
    """Extract per-subsystem status from network health data."""
    subsystems = {}
    if not health_data:
        return subsystems

    items = health_data if isinstance(health_data, list) else [health_data]
    for item in items:
        subsystem = item.get("subsystem", "")
        status = item.get("status", "unknown")
        if subsystem:
            subsystems[subsystem] = status
    return subsystems


def _parse_alarms(alarm_data) -> dict:
    """Count alarms by severity."""
    if not alarm_data or not isinstance(alarm_data, list):
        return {"total": 0, "critical": 0, "warning": 0}

    critical = 0
    warning = 0
    for alarm in alarm_data:
        sev = str(alarm.get("severity", "")).lower()
        if sev == "critical":
            critical += 1
        elif sev in ("warning", "warn"):
            warning += 1
    return {"total": len(alarm_data), "critical": critical, "warning": warning}


def _parse_system(system_data) -> dict:
    """Extract version and uptime from system info."""
    if not system_data or not isinstance(system_data, dict):
        return {"version": "unknown", "uptime": "unknown"}
    return {
        "version": system_data.get("version", "unknown"),
        "uptime": system_data.get("uptime", "unknown"),
    }


# ── Overall status determination ─────────────────────────────────────────────


def _determine_status(health: dict, devices: dict, alarms: dict) -> str:
    """Determine overall status: healthy, warning, or critical."""
    # Critical if any subsystem is in error or any device offline.
    for status in health.values():
        if status == "error":
            return "critical"
    if devices.get("offline", 0) > 0:
        return "critical"

    # Warning if any subsystem warns or alarms present.
    for status in health.values():
        if status == "warning":
            return "warning"
    if alarms.get("total", 0) > 0:
        return "warning"

    return "healthy"


# ── Baseline diffing ─────────────────────────────────────────────────────────


def load_baseline(state_dir: Path) -> dict | None:
    baseline_path = state_dir / BASELINE_FILENAME
    if not baseline_path.exists():
        return None
    try:
        return json.loads(baseline_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def save_baseline(state_dir: Path, data: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = state_dir / BASELINE_FILENAME
    baseline_path.write_text(json.dumps(data, indent=2))


def diff_against_baseline(current: dict, baseline: dict | None) -> list[str]:
    """Compute human-readable list of changes since last run."""
    if baseline is None:
        return ["First run — no previous baseline to compare against."]

    changes: list[str] = []

    # Device state changes.
    prev_offline_macs = {d["mac"] for d in baseline.get("offline_devices", [])}
    curr_offline_macs = {d["mac"] for d in current.get("offline_devices", [])}
    newly_offline = curr_offline_macs - prev_offline_macs
    came_online = prev_offline_macs - curr_offline_macs

    prev_offline_by_mac = {d["mac"]: d for d in baseline.get("offline_devices", [])}
    curr_offline_by_mac = {d["mac"]: d for d in current.get("offline_devices", [])}

    for mac in newly_offline:
        dev = curr_offline_by_mac.get(mac, {})
        changes.append(f"Device went OFFLINE: {dev.get('name', mac)}")
    for mac in came_online:
        dev = prev_offline_by_mac.get(mac, {})
        changes.append(f"Device came ONLINE: {dev.get('name', mac)}")

    # New alarms.
    prev_alarm_count = baseline.get("alarms", {}).get("total", 0)
    curr_alarm_count = current.get("alarms", {}).get("total", 0)
    if curr_alarm_count > prev_alarm_count:
        changes.append(f"New alarms detected: {curr_alarm_count - prev_alarm_count} new alarm(s)")

    # Subsystem status changes.
    prev_health = baseline.get("health", {})
    curr_health = current.get("health", {})
    for subsystem in set(list(prev_health.keys()) + list(curr_health.keys())):
        old_status = prev_health.get(subsystem, "unknown")
        new_status = curr_health.get(subsystem, "unknown")
        if old_status != new_status:
            changes.append(f"Subsystem '{subsystem}' changed: {old_status} -> {new_status}")

    if not changes:
        changes.append("No changes since last run.")

    return changes


# ── Recommendations ──────────────────────────────────────────────────────────


def _build_recommendations(health: dict, devices: dict, alarms: dict) -> list[str]:
    """Generate actionable recommendations based on current state."""
    recs: list[str] = []

    if health.get("wan") == "error":
        recs.append("WAN is down — check ISP status and gateway device.")
    if health.get("lan") == "error":
        recs.append("LAN subsystem error — check core switch connectivity and STP.")
    if health.get("wlan") in ("error", "warning"):
        recs.append("WLAN issues detected — check AP status and channel interference.")
    if health.get("vpn") == "error":
        recs.append("VPN subsystem error — check tunnel configuration and remote sites.")

    if devices.get("offline", 0) > 0:
        recs.append(f"{devices['offline']} device(s) offline — check power and uplink cables.")
    if devices.get("upgrading", 0) > 0:
        recs.append(f"{devices['upgrading']} device(s) upgrading — wait for firmware update to complete.")

    if alarms.get("critical", 0) > 0:
        recs.append(f"{alarms['critical']} critical alarm(s) — review and resolve immediately.")
    elif alarms.get("warning", 0) > 0:
        recs.append(f"{alarms['warning']} warning alarm(s) — review when convenient.")

    if not recs:
        recs.append("Network is healthy. No action needed.")

    return recs


# ── Human-readable output ────────────────────────────────────────────────────


def format_human(report: dict) -> str:
    """Render report dict as a human-readable string."""
    lines: list[str] = []
    lines.append("=== Network Health Report ===")
    lines.append(f"Status: {report['status'].upper()}")
    lines.append(f"Timestamp: {report['timestamp']}")
    lines.append("")

    sys_info = report.get("system", {})
    lines.append(f"Controller: v{sys_info.get('version', '?')}  Uptime: {sys_info.get('uptime', '?')}")
    lines.append("")

    lines.append("-- Subsystem Health --")
    for sub, status in report.get("health", {}).items():
        lines.append(f"  {sub}: {status}")
    lines.append("")

    devs = report.get("devices", {})
    lines.append(f"-- Devices ({devs.get('online', 0)}/{devs.get('total', 0)} online) --")
    if devs.get("offline", 0):
        lines.append(f"  Offline: {devs['offline']}")
    if devs.get("upgrading", 0):
        lines.append(f"  Upgrading: {devs['upgrading']}")
    lines.append("")

    alarms_info = report.get("alarms", {})
    lines.append(f"-- Alarms ({alarms_info.get('total', 0)}) --")
    if alarms_info.get("critical", 0):
        lines.append(f"  Critical: {alarms_info['critical']}")
    if alarms_info.get("warning", 0):
        lines.append(f"  Warning: {alarms_info['warning']}")
    lines.append("")

    changes = report.get("changes_since_last_run", [])
    if changes:
        lines.append("-- Changes Since Last Run --")
        for c in changes:
            lines.append(f"  - {c}")
        lines.append("")

    recs = report.get("recommendations", [])
    if recs:
        lines.append("-- Recommendations --")
        for i, r in enumerate(recs, 1):
            lines.append(f"  {i}. {r}")

    return "\n".join(lines)


# ── Main async logic ─────────────────────────────────────────────────────────


async def collect_health(mcp_url: str, state_dir: Path) -> dict:
    """Connect to MCP, gather health data, diff against baseline, return report."""
    async with MCPClient(mcp_url) as client:
        # Check readiness.
        ready = await client.check_ready("unifi_tool_index")
        if not ready:
            return await client.get_setup_error()

        # Collect all data in parallel.
        results = await client.call_tools_parallel([
            ("unifi_get_system_info", {}),
            ("unifi_get_network_health", {}),
            ("unifi_list_devices", {}),
            ("unifi_list_alarms", {}),
        ])

        system_result, health_result, devices_result, alarms_result = results

        # Parse each result.
        system_info = _parse_system(_extract_data(system_result))
        health = _parse_health(_extract_data(health_result))
        device_summary = _parse_devices(_extract_data(devices_result))
        alarm_summary = _parse_alarms(_extract_data(alarms_result))

        # Determine overall status.
        status = _determine_status(health, device_summary, alarm_summary)

        # Build the core report (used for both output and baseline saving).
        report_core = {
            "health": health,
            "devices": {
                "total": device_summary["total"],
                "online": device_summary["online"],
                "offline": device_summary["offline"],
                "upgrading": device_summary["upgrading"],
                "other": device_summary["other"],
            },
            "alarms": alarm_summary,
            "offline_devices": device_summary["offline_devices"],
        }

        # Diff against baseline.
        baseline = load_baseline(state_dir)
        changes = diff_against_baseline(report_core, baseline)

        # Save current state as new baseline.
        save_baseline(state_dir, report_core)

        # Build recommendations.
        recommendations = _build_recommendations(health, device_summary, alarm_summary)

        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "system": system_info,
            "health": health,
            "devices": report_core["devices"],
            "alarms": alarm_summary,
            "changes_since_last_run": changes,
            "offline_devices": device_summary["offline_devices"],
            "recommendations": recommendations,
        }


# ── Entry point ──────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    mcp_url = args.mcp_url or get_server_url("network")
    state_dir = Path(args.state_dir) if args.state_dir else get_state_dir(ensure=True)

    report = asyncio.run(collect_health(mcp_url, state_dir))

    if args.output_format == "human":
        print(format_human(report))
    else:
        print(json.dumps(report, indent=2))

    # Exit with non-zero if unhealthy or setup required.
    if not report.get("success", False):
        sys.exit(1)
    if report.get("status") == "critical":
        sys.exit(2)


if __name__ == "__main__":
    main()
