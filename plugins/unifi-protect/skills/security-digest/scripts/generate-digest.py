#!/usr/bin/env python3
"""Generate a security digest from collected events or live MCP queries.

Mode 1 (rich): Reads from SQLite events.db if collector has been running
Mode 2 (fallback): Calls MCP tools directly with time range filters

Usage:
    python generate-digest.py [--mcp-url URL] [--range overnight|today|recent|24h] [--format json|human] [--state-dir DIR]
"""
import argparse
import asyncio
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Add the scripts directory to sys.path for sibling imports.
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from config import get_server_url  # noqa: E402
from mcp_client import MCPClient, MCPConnectionError, MCPToolError  # noqa: E402

logger = logging.getLogger("security-digest")

# ── Time range helpers ──────────────────────────────────────────────────────

TIME_RANGES = {
    "overnight": 12,  # last 12 hours (6pm-6am window)
    "today": None,  # since midnight — computed dynamically
    "recent": 4,  # last 4 hours
    "24h": 24,  # full 24 hours
}


def compute_time_range(range_name: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Compute start and end datetimes for a named time range.

    Returns (start, end) as timezone-aware UTC datetimes.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if range_name == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now

    hours = TIME_RANGES.get(range_name)
    if hours is None:
        hours = 12  # fallback to overnight
    return now - timedelta(hours=hours), now


# ── SQLite reader (rich mode) ──────────────────────────────────────────────


def query_events_from_db(
    db_path: Path, start: datetime, end: datetime
) -> list[dict[str, Any]]:
    """Query events from SQLite database within the time range."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            "SELECT id, server, event_type, timestamp, details, severity, buffered_at "
            "FROM events WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
            (start.isoformat(), end.isoformat()),
        )
        rows = cursor.fetchall()
        events = []
        for row in rows:
            evt = dict(row)
            try:
                evt["details"] = json.loads(evt["details"])
            except (json.JSONDecodeError, TypeError):
                evt["details"] = {}
            events.append(evt)
        return events
    finally:
        conn.close()


def has_recent_data(db_path: Path, max_age_minutes: int = 60) -> bool:
    """Check if the database has events buffered within the last N minutes."""
    if not db_path.exists():
        return False

    conn = sqlite3.connect(str(db_path))
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).isoformat()
        cursor = conn.execute("SELECT COUNT(*) FROM events WHERE buffered_at >= ?", (cutoff,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception:
        return False
    finally:
        conn.close()


# ── MCP fallback mode ─────────────────────────────────────────────────────


async def fetch_protect_events(client: MCPClient, start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Fetch events from Protect MCP server."""
    events = []
    calls = [
        ("protect_list_events", {"start": start.isoformat(), "end": end.isoformat()}),
        ("protect_list_smart_detections", {"start": start.isoformat(), "end": end.isoformat()}),
    ]
    try:
        results = await client.call_tools_parallel(calls)
        for result in results:
            if result.get("success") and result.get("data"):
                raw = result["data"] if isinstance(result["data"], list) else [result["data"]]
                for evt in raw:
                    event_type = evt.get("type", evt.get("event_type", "motion"))
                    ts = evt.get("start", evt.get("timestamp", start.isoformat()))
                    event_id = evt.get("id", f"protect-{ts}-{event_type}")
                    events.append({
                        "id": event_id,
                        "server": "protect",
                        "event_type": event_type,
                        "timestamp": ts,
                        "details": evt,
                        "severity": _classify_severity(event_type, evt, ts),
                    })
    except (MCPConnectionError, MCPToolError) as e:
        logger.warning("Protect unavailable: %s", e)
    return events


async def fetch_access_events(client: MCPClient, start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Fetch events from Access MCP server."""
    events = []
    try:
        result = await client.call_tool("access_list_events", {"start": start.isoformat(), "end": end.isoformat()})
        if result.get("success") and result.get("data"):
            raw = result["data"] if isinstance(result["data"], list) else [result["data"]]
            for evt in raw:
                event_type = evt.get("type", evt.get("event_type", "ACCESS_GRANT"))
                ts = evt.get("timestamp", start.isoformat())
                event_id = evt.get("id", f"access-{ts}-{event_type}")
                events.append({
                    "id": event_id,
                    "server": "access",
                    "event_type": event_type,
                    "timestamp": ts,
                    "details": evt,
                    "severity": _classify_severity(event_type, evt, ts),
                })
    except (MCPConnectionError, MCPToolError) as e:
        logger.warning("Access unavailable: %s", e)
    return events


async def fetch_network_events(client: MCPClient, start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Fetch events and alarms from Network MCP server."""
    events = []
    calls = [
        ("unifi_list_alarms", {}),
        ("unifi_list_events", {"start": start.isoformat(), "end": end.isoformat()}),
    ]
    try:
        results = await client.call_tools_parallel(calls)
        for result in results:
            if result.get("success") and result.get("data"):
                raw = result["data"] if isinstance(result["data"], list) else [result["data"]]
                for evt in raw:
                    event_type = evt.get("key", evt.get("type", "event"))
                    ts = evt.get("time", evt.get("timestamp", start.isoformat()))
                    if isinstance(ts, (int, float)):
                        ts = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                    event_id = evt.get("_id", evt.get("id", f"network-{ts}-{event_type}"))
                    events.append({
                        "id": event_id,
                        "server": "network",
                        "event_type": event_type,
                        "timestamp": ts,
                        "details": evt,
                        "severity": _classify_severity(event_type, evt, ts),
                    })
    except (MCPConnectionError, MCPToolError) as e:
        logger.warning("Network unavailable: %s", e)
    return events


async def fetch_all_events_fallback(start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Fetch events from all available MCP servers (fallback mode)."""
    events: list[dict[str, Any]] = []

    # Try each server independently — missing servers are fine
    servers = {
        "protect": fetch_protect_events,
        "access": fetch_access_events,
        "network": fetch_network_events,
    }

    for server_name, fetch_fn in servers.items():
        try:
            url = get_server_url(server_name)
            async with MCPClient(url, timeout=15.0) as client:
                server_events = await fetch_fn(client, start, end)
                events.extend(server_events)
        except Exception as e:
            logger.debug("Server %s unavailable: %s", server_name, e)

    return events


# ── Severity classification (shared with collector.py) ─────────────────────


def _classify_severity(event_type: str, details: dict, timestamp_str: str) -> str:
    """Classify event severity based on type, details, and time of day."""
    hour = _extract_hour(timestamp_str)
    is_night = hour < 6 or hour >= 22

    # Protect
    if event_type == "person":
        return "high" if is_night else "medium"
    if event_type == "vehicle":
        return "medium" if is_night else "low"
    if event_type == "animal":
        return "low"
    if event_type == "package":
        return "medium"
    if event_type in ("ring",):
        return "medium" if is_night else "low"
    if event_type in ("sensorAlarm", "sensorOpened"):
        return "high" if is_night else "medium"
    if event_type in ("motion", "smartDetectZone"):
        return "low"

    # Access
    if event_type in ("ACCESS_DENY", "CREDENTIAL_EXPIRED", "ANTI_PASSBACK"):
        return "high"
    if event_type == "SCHEDULE_DENY":
        return "medium"
    if event_type == "DOOR_FORCED_OPEN":
        return "high"
    if event_type == "DOOR_HELD_OPEN":
        return "medium" if is_night else "low"
    if event_type in ("ACCESS_GRANT", "VISITOR_GRANT", "REMOTE_UNLOCK"):
        return "medium" if is_night else "low"

    # Network
    if event_type.startswith("EVT_IPS_"):
        return "high"
    if event_type == "EVT_AD_LoginFailed":
        return "medium"
    if event_type.endswith("_Disconnected"):
        return "medium" if is_night else "low"

    # Network alarms
    if details.get("severity") == "critical":
        return "high"
    if details.get("severity") in ("high", "medium"):
        return "medium"

    return "low"


def _extract_hour(timestamp_str: str) -> int:
    """Extract hour from an ISO-8601 timestamp string."""
    try:
        if "T" in timestamp_str:
            time_part = timestamp_str.split("T")[1]
            return int(time_part[:2])
        return 12
    except (ValueError, IndexError):
        return 12


# ── Correlation engine ─────────────────────────────────────────────────────

CORRELATION_WINDOW_SECONDS = {
    "CORR-01": 120,   # 2 minutes: motion at door camera without badge-in
    "CORR-02": 300,   # 5 minutes: new network device + motion
    "CORR-03": 180,   # 3 minutes: access denied + continued motion
}


def run_correlations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run all correlation rules across events.

    Returns a list of correlation findings.
    """
    correlations = []

    correlations.extend(_corr_01_motion_without_badge(events))
    correlations.extend(_corr_02_new_device_with_motion(events))
    correlations.extend(_corr_03_access_denied_with_motion(events))

    return correlations


def _parse_timestamp(ts: str) -> datetime | None:
    """Parse an ISO-8601 timestamp string to datetime."""
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _events_within_window(evt_a: dict, evt_b: dict, window_seconds: int) -> bool:
    """Check if two events occurred within a time window."""
    ts_a = _parse_timestamp(evt_a["timestamp"])
    ts_b = _parse_timestamp(evt_b["timestamp"])
    if ts_a is None or ts_b is None:
        return False
    return abs((ts_a - ts_b).total_seconds()) <= window_seconds


def _corr_01_motion_without_badge(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """CORR-01: Motion at door camera without badge-in within 2 minutes.

    Looks for Protect person/motion events near a door camera that
    don't have a corresponding Access grant event.
    """
    correlations = []
    window = CORRELATION_WINDOW_SECONDS["CORR-01"]

    # Get motion/person events from Protect
    motion_events = [
        e for e in events
        if e["server"] == "protect" and e["event_type"] in ("person", "motion", "smartDetectZone")
    ]

    # Get successful access events
    access_grants = [
        e for e in events
        if e["server"] == "access" and e["event_type"] in ("ACCESS_GRANT", "VISITOR_GRANT", "REMOTE_UNLOCK")
    ]

    for motion in motion_events:
        # Check if any access grant happened within the window
        has_badge = any(
            _events_within_window(motion, grant, window)
            for grant in access_grants
        )
        if not has_badge and access_grants is not None:
            # Only flag if Access server is present (we have some access events or this is from collector with access configured)
            # To avoid false positives when Access isn't connected, check if we have ANY access events
            if len([e for e in events if e["server"] == "access"]) > 0:
                correlations.append({
                    "rule": "CORR-01",
                    "description": "Motion detected near door without corresponding badge-in",
                    "severity": "high",
                    "events": [motion["id"]],
                    "timestamp": motion["timestamp"],
                    "details": {
                        "motion_type": motion["event_type"],
                        "window_seconds": window,
                    },
                })

    return correlations


def _corr_02_new_device_with_motion(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """CORR-02: New network device + motion within 5 minutes.

    A new device appearing on the network near the time of a
    person detection could indicate an intruder with a device.
    """
    correlations = []
    window = CORRELATION_WINDOW_SECONDS["CORR-02"]

    # Network client connection events
    new_devices = [
        e for e in events
        if e["server"] == "network"
        and e["event_type"] in ("EVT_WU_Connected", "EVT_WG_Connected")
    ]

    # Protect person detections
    person_events = [
        e for e in events
        if e["server"] == "protect" and e["event_type"] == "person"
    ]

    for device_evt in new_devices:
        for person_evt in person_events:
            if _events_within_window(device_evt, person_evt, window):
                correlations.append({
                    "rule": "CORR-02",
                    "description": "New device on network near time of person detection",
                    "severity": "high",
                    "events": [device_evt["id"], person_evt["id"]],
                    "timestamp": device_evt["timestamp"],
                    "details": {
                        "device_event": device_evt["event_type"],
                        "window_seconds": window,
                    },
                })
                break  # One correlation per device event

    return correlations


def _corr_03_access_denied_with_motion(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """CORR-03: Access denied + continued motion within 3 minutes.

    Someone was denied access but motion continues, suggesting
    they may be trying alternate entry points.
    """
    correlations = []
    window = CORRELATION_WINDOW_SECONDS["CORR-03"]

    # Access denied events
    denied = [
        e for e in events
        if e["server"] == "access"
        and e["event_type"] in ("ACCESS_DENY", "CREDENTIAL_EXPIRED", "SCHEDULE_DENY")
    ]

    # Protect motion/person events
    motion_events = [
        e for e in events
        if e["server"] == "protect" and e["event_type"] in ("person", "motion")
    ]

    for deny_evt in denied:
        deny_ts = _parse_timestamp(deny_evt["timestamp"])
        if deny_ts is None:
            continue

        # Look for motion AFTER the denial within the window
        for motion_evt in motion_events:
            motion_ts = _parse_timestamp(motion_evt["timestamp"])
            if motion_ts is None:
                continue
            delta = (motion_ts - deny_ts).total_seconds()
            if 0 < delta <= window:
                correlations.append({
                    "rule": "CORR-03",
                    "description": "Access denied followed by continued motion",
                    "severity": "high",
                    "events": [deny_evt["id"], motion_evt["id"]],
                    "timestamp": deny_evt["timestamp"],
                    "details": {
                        "deny_type": deny_evt["event_type"],
                        "motion_type": motion_evt["event_type"],
                        "delay_seconds": delta,
                        "window_seconds": window,
                    },
                })
                break  # One correlation per denial

    return correlations


# ── Activity counting ──────────────────────────────────────────────────────


def compute_activity_counts(events: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Compute activity counts grouped by server."""
    counts: dict[str, dict[str, int]] = {
        "protect": {"total": 0, "person": 0, "vehicle": 0, "animal": 0, "package": 0, "motion": 0},
        "access": {"total": 0, "granted": 0, "denied": 0},
        "network": {"total": 0, "alarms": 0, "client_events": 0},
    }

    for evt in events:
        server = evt["server"]
        if server not in counts:
            counts[server] = {"total": 0}
        counts[server]["total"] += 1

        et = evt["event_type"]

        if server == "protect":
            if et == "person":
                counts[server]["person"] += 1
            elif et == "vehicle":
                counts[server]["vehicle"] += 1
            elif et == "animal":
                counts[server]["animal"] += 1
            elif et == "package":
                counts[server]["package"] += 1
            elif et in ("motion", "smartDetectZone"):
                counts[server]["motion"] += 1

        elif server == "access":
            if et in ("ACCESS_GRANT", "VISITOR_GRANT", "REMOTE_UNLOCK"):
                counts[server]["granted"] += 1
            elif et in ("ACCESS_DENY", "CREDENTIAL_EXPIRED", "SCHEDULE_DENY", "ANTI_PASSBACK"):
                counts[server]["denied"] += 1

        elif server == "network":
            if et.startswith("EVT_"):
                if "Connected" in et or "Disconnected" in et:
                    counts[server]["client_events"] += 1
                else:
                    counts[server]["alarms"] += 1
            else:
                counts[server]["alarms"] += 1

    return counts


# ── Notable event extraction ───────────────────────────────────────────────

NOTABLE_EVENT_TYPES = {
    "person", "vehicle", "package", "sensorAlarm", "sensorOpened", "ring",
    "ACCESS_DENY", "CREDENTIAL_EXPIRED", "DOOR_FORCED_OPEN", "DOOR_HELD_OPEN",
    "SCHEDULE_DENY", "ANTI_PASSBACK",
    "EVT_IPS_IpsAlert", "EVT_IPS_IpsBlock", "EVT_AD_LoginFailed",
}


def extract_notable_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract events worth human attention."""
    notable = []
    for evt in events:
        if evt["severity"] in ("high", "medium") or evt["event_type"] in NOTABLE_EVENT_TYPES:
            description = _describe_event(evt)
            recommendations = _recommend_for_event(evt)
            notable.append({
                "time": _format_time(evt["timestamp"]),
                "description": description,
                "sources": [evt["server"]],
                "severity": evt["severity"],
                "correlation": None,
                "event_type": evt["event_type"],
                "recommendations": recommendations,
            })
    # Sort by timestamp
    notable.sort(key=lambda e: e["time"])
    return notable


def _describe_event(evt: dict[str, Any]) -> str:
    """Generate a human-readable description of an event."""
    et = evt["event_type"]
    details = evt.get("details", {})

    # Protect events
    if et == "person":
        camera = details.get("camera_name", details.get("camera_id", "camera"))
        return f"Person detected at {camera}"
    if et == "vehicle":
        camera = details.get("camera_name", details.get("camera_id", "camera"))
        return f"Vehicle detected at {camera}"
    if et == "package":
        camera = details.get("camera_name", details.get("camera_id", "camera"))
        return f"Package detected at {camera}"
    if et == "ring":
        return "Doorbell ring"
    if et == "sensorAlarm":
        return f"Sensor alarm triggered"
    if et == "sensorOpened":
        return f"Door/window sensor opened"

    # Access events
    if et == "ACCESS_DENY":
        door = details.get("door_name", "door")
        user = details.get("user_display_name", "unknown")
        return f"Access denied at {door} for {user}"
    if et == "DOOR_FORCED_OPEN":
        door = details.get("door_name", "door")
        return f"Door forced open: {door}"
    if et == "DOOR_HELD_OPEN":
        door = details.get("door_name", "door")
        return f"Door held open: {door}"
    if et == "CREDENTIAL_EXPIRED":
        return "Expired credential presented"
    if et == "SCHEDULE_DENY":
        return "Access attempted outside allowed hours"
    if et == "ANTI_PASSBACK":
        return "Anti-passback violation detected"

    # Network events
    if et.startswith("EVT_IPS_"):
        msg = details.get("msg", "IPS alert")
        return f"IPS: {msg}"
    if et == "EVT_AD_LoginFailed":
        return "Controller login failure"
    if et.endswith("_Disconnected"):
        device = details.get("ap_name", details.get("msg", et))
        return f"Device disconnected: {device}"

    # Fallback
    msg = details.get("msg", details.get("message", et))
    return str(msg)


def _recommend_for_event(evt: dict[str, Any]) -> list[str]:
    """Generate recommendations for a notable event."""
    et = evt["event_type"]
    recs = []

    if et == "person" and evt["severity"] == "high":
        recs.append("Review camera footage")
    if et == "DOOR_FORCED_OPEN":
        recs.append("Inspect door hardware")
        recs.append("Review camera footage at door")
    if et == "ACCESS_DENY":
        recs.append("Verify badge holder credentials")
    if et.startswith("EVT_IPS_"):
        recs.append("Review IPS alert details and source IP")
    if et == "EVT_AD_LoginFailed":
        recs.append("Check for brute-force attempts")
    if et.endswith("_Disconnected"):
        recs.append("Check device power and connectivity")

    return recs


def _format_time(timestamp_str: str) -> str:
    """Format a timestamp to a readable time string."""
    try:
        if "T" in timestamp_str:
            time_part = timestamp_str.split("T")[1]
            return time_part[:8]  # HH:MM:SS
    except (IndexError, ValueError):
        pass
    return timestamp_str


# ── Digest summary ─────────────────────────────────────────────────────────


def determine_status(notable_events: list, correlations: list) -> str:
    """Determine overall digest status: clear, notable, or alert."""
    high_count = sum(1 for e in notable_events if e["severity"] == "high")
    high_count += sum(1 for c in correlations if c["severity"] == "high")

    if high_count > 0 or len(correlations) > 0:
        return "alert"
    if len(notable_events) > 0:
        return "notable"
    return "clear"


def generate_summary(status: str, notable_events: list, activity_counts: dict) -> str:
    """Generate a one-line summary for the digest."""
    total = sum(c.get("total", 0) for c in activity_counts.values())

    if status == "clear":
        return f"Quiet period with {total} routine events and nothing notable."
    if status == "notable":
        return f"{len(notable_events)} notable event(s) detected across {total} total events."
    # alert
    high = sum(1 for e in notable_events if e["severity"] == "high")
    return f"Alert: {high} high-severity event(s) among {len(notable_events)} notable events."


def build_recommendations(notable_events: list, correlations: list) -> list[str]:
    """Build top-level recommendations from notable events and correlations."""
    recs: list[str] = []

    if not notable_events and not correlations:
        recs.append("No action needed — all clear.")
        return recs

    # Aggregate per-event recommendations
    seen = set()
    for evt in notable_events:
        for rec in evt.get("recommendations", []):
            if rec not in seen:
                recs.append(rec)
                seen.add(rec)

    for corr in correlations:
        rule = corr["rule"]
        if rule == "CORR-01":
            rec = "Review footage at entry points for unauthorized access"
        elif rule == "CORR-02":
            rec = "Identify new network device and verify authorization"
        elif rule == "CORR-03":
            rec = "Check entry points — access was denied but motion continued"
        else:
            rec = f"Investigate correlation: {corr['description']}"
        if rec not in seen:
            recs.append(rec)
            seen.add(rec)

    return recs


# ── Main digest generation ─────────────────────────────────────────────────


async def generate_digest(
    state_dir: str | Path,
    range_name: str = "overnight",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Generate the security digest.

    Auto-selects rich mode (from collector DB) or fallback mode (live MCP queries).
    """
    state_dir = Path(state_dir)
    start, end = compute_time_range(range_name, now)

    db_path = state_dir / "events.db"
    use_collector = db_path.exists() and has_recent_data(db_path)

    if use_collector:
        mode = "collector"
        events = query_events_from_db(db_path, start, end)
    else:
        mode = "fallback"
        events = await fetch_all_events_fallback(start, end)

    # De-duplicate by event ID
    seen_ids: set[str] = set()
    unique_events: list[dict[str, Any]] = []
    for evt in events:
        if evt["id"] not in seen_ids:
            seen_ids.add(evt["id"])
            unique_events.append(evt)

    events = unique_events

    # Run analysis
    notable_events = extract_notable_events(events)
    correlations = run_correlations(events)
    activity_counts = compute_activity_counts(events)
    status = determine_status(notable_events, correlations)
    summary = generate_summary(status, notable_events, activity_counts)
    recommendations = build_recommendations(notable_events, correlations)

    return {
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "time_range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "name": range_name,
        },
        "mode": mode,
        "summary": summary,
        "status": status,
        "notable_events": notable_events,
        "correlations": correlations,
        "activity_counts": activity_counts,
        "recommendations": recommendations,
    }


# ── Human-readable formatting ──────────────────────────────────────────────


def format_human(result: dict[str, Any]) -> str:
    """Format digest result as human-readable text."""
    lines = []
    tr = result["time_range"]
    lines.append(f"## Security Digest — {tr.get('name', 'custom')} ({tr['start'][:16]} to {tr['end'][:16]})")
    lines.append("")
    lines.append(f"**Mode:** {result['mode']}")
    lines.append(f"**Status:** {result['status'].upper()}")
    lines.append("")
    lines.append(f"### Summary")
    lines.append(result["summary"])
    lines.append("")

    if result["notable_events"]:
        lines.append("### Notable Events")
        for evt in result["notable_events"]:
            lines.append(f"**{evt['time']}** — {evt['description']}")
            lines.append(f"  Source: {', '.join(evt['sources'])} | Severity: {evt['severity']}")
            if evt.get("recommendations"):
                for rec in evt["recommendations"]:
                    lines.append(f"  - {rec}")
            lines.append("")

    if result["correlations"]:
        lines.append("### Correlations")
        for corr in result["correlations"]:
            lines.append(f"**{corr['rule']}** — {corr['description']}")
            lines.append(f"  Severity: {corr['severity']}")
            lines.append("")

    lines.append("### Activity Counts")
    lines.append("| Source | Total | Notable |")
    lines.append("|--------|-------|---------|")
    ac = result["activity_counts"]
    p = ac.get("protect", {})
    lines.append(f"| Protect | {p.get('total', 0)} | person={p.get('person', 0)} vehicle={p.get('vehicle', 0)} |")
    a = ac.get("access", {})
    lines.append(f"| Access | {a.get('total', 0)} | denied={a.get('denied', 0)} |")
    n = ac.get("network", {})
    lines.append(f"| Network | {n.get('total', 0)} | alarms={n.get('alarms', 0)} |")
    lines.append("")

    if result["recommendations"]:
        lines.append("### Recommendations")
        for rec in result["recommendations"]:
            lines.append(f"- {rec}")

    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate a security digest")
    parser.add_argument("--mcp-url", default=None, help="MCP server URL (fallback mode)")
    parser.add_argument(
        "--range", dest="time_range", default="overnight",
        choices=["overnight", "today", "recent", "24h"],
        help="Time range for the digest (default: overnight)",
    )
    parser.add_argument(
        "--format", dest="output_format", default="json",
        choices=["json", "human"],
        help="Output format (default: json)",
    )
    parser.add_argument("--state-dir", default=None, help="State directory containing events.db")
    return parser.parse_args(argv)


async def async_main(argv: list[str] | None = None) -> dict[str, Any]:
    """Async entry point."""
    args = parse_args(argv)

    state_dir = args.state_dir
    if state_dir is None:
        import os
        state_dir = os.environ.get("UNIFI_SKILLS_STATE_DIR", ".claude/unifi-skills")

    Path(state_dir).mkdir(parents=True, exist_ok=True)

    result = await generate_digest(
        state_dir=state_dir,
        range_name=args.time_range,
    )

    if args.output_format == "human":
        print(format_human(result))
    else:
        print(json.dumps(result, indent=2))

    return result


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    asyncio.run(async_main(argv))


if __name__ == "__main__":
    main()
