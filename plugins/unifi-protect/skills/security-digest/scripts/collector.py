#!/usr/bin/env python3
"""Security digest event collector daemon.

Polls MCP servers at regular intervals, stores events in SQLite
for later digest generation. Designed to run as a background daemon
started by start-collector.sh.

Usage:
    python collector.py --state-dir DIR --poll-interval 10 --servers protect,network --timeout 1800
"""
import argparse
import asyncio
import json
import logging
import os
import signal
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add the scripts directory to sys.path for sibling imports.
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from config import get_server_url  # noqa: E402
from mcp_client import MCPClient, MCPConnectionError, MCPToolError  # noqa: E402

logger = logging.getLogger("security-digest-collector")

# ── Database setup ──────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    server TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    details TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'low',
    buffered_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_server ON events(server);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
"""


def init_db(state_dir: str | Path) -> sqlite3.Connection:
    """Create or open the events database and ensure schema exists."""
    db_path = Path(state_dir) / "events.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def insert_events(conn: sqlite3.Connection, events: list[dict[str, Any]]) -> int:
    """Insert events, deduplicating by ID. Returns count of new events inserted."""
    if not events:
        return 0
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    for evt in events:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO events (id, server, event_type, timestamp, details, severity, buffered_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    evt["id"],
                    evt["server"],
                    evt["event_type"],
                    evt["timestamp"],
                    json.dumps(evt.get("details", {})),
                    evt.get("severity", "low"),
                    now,
                ),
            )
            if conn.total_changes:
                inserted += 1
        except sqlite3.IntegrityError:
            pass  # Duplicate — expected
    conn.commit()
    return inserted


def count_events(conn: sqlite3.Connection) -> int:
    """Return the total number of events in the database."""
    cursor = conn.execute("SELECT COUNT(*) FROM events")
    return cursor.fetchone()[0]


# ── Event classification ────────────────────────────────────────────────────


def classify_severity(event_type: str, details: dict, timestamp_str: str) -> str:
    """Classify event severity based on type, details, and time of day.

    Follows the severity model:
    - High: person at unusual hours, access denied, forced open, IPS alerts
    - Medium: vehicle, package, door held, new devices
    - Low: animal, routine motion, informational
    """
    hour = _extract_hour(timestamp_str)
    is_night = hour < 6 or hour >= 22

    # Protect events
    if event_type == "person":
        return "high" if is_night else "medium"
    if event_type == "vehicle":
        return "medium" if is_night else "low"
    if event_type == "animal":
        return "low"
    if event_type == "package":
        return "medium"
    if event_type == "licenseplate":
        return "medium"
    if event_type in ("ring",):
        return "medium" if is_night else "low"
    if event_type in ("sensorAlarm", "sensorOpened"):
        return "high" if is_night else "medium"
    if event_type == "motion":
        return "low"
    if event_type == "smartDetectZone":
        return "low"

    # Access events
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

    # Network events
    if event_type.startswith("EVT_IPS_"):
        return "high"
    if event_type == "EVT_AD_LoginFailed":
        return "medium"
    if event_type.endswith("_Disconnected"):
        return "medium" if is_night else "low"
    if event_type.startswith("EVT_WU_Connected") or event_type.startswith("EVT_WG_Connected"):
        # New device connections
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
        return 12  # Default to noon if can't parse
    except (ValueError, IndexError):
        return 12


# ── MCP polling ─────────────────────────────────────────────────────────────


async def poll_protect(client: MCPClient) -> list[dict[str, Any]]:
    """Poll UniFi Protect MCP server for recent events."""
    events = []
    try:
        result = await client.call_tool("protect_recent_events", {})
        if result.get("success") and result.get("data"):
            raw_events = result["data"] if isinstance(result["data"], list) else [result["data"]]
            for evt in raw_events:
                event_type = evt.get("type", evt.get("event_type", "motion"))
                ts = evt.get("start", evt.get("timestamp", datetime.now(timezone.utc).isoformat()))
                event_id = evt.get("id", f"protect-{ts}-{event_type}")
                severity = classify_severity(event_type, evt, ts)
                events.append({
                    "id": event_id,
                    "server": "protect",
                    "event_type": event_type,
                    "timestamp": ts,
                    "details": evt,
                    "severity": severity,
                })
    except (MCPConnectionError, MCPToolError) as e:
        logger.warning("Failed to poll Protect: %s", e)
    except Exception:
        logger.exception("Unexpected error polling Protect")
    return events


async def poll_access(client: MCPClient) -> list[dict[str, Any]]:
    """Poll UniFi Access MCP server for recent events."""
    events = []
    try:
        result = await client.call_tool("access_recent_events", {})
        if result.get("success") and result.get("data"):
            raw_events = result["data"] if isinstance(result["data"], list) else [result["data"]]
            for evt in raw_events:
                event_type = evt.get("type", evt.get("event_type", "ACCESS_GRANT"))
                ts = evt.get("timestamp", datetime.now(timezone.utc).isoformat())
                event_id = evt.get("id", f"access-{ts}-{event_type}")
                severity = classify_severity(event_type, evt, ts)
                events.append({
                    "id": event_id,
                    "server": "access",
                    "event_type": event_type,
                    "timestamp": ts,
                    "details": evt,
                    "severity": severity,
                })
    except (MCPConnectionError, MCPToolError) as e:
        logger.warning("Failed to poll Access: %s", e)
    except Exception:
        logger.exception("Unexpected error polling Access")
    return events


async def poll_network(client: MCPClient) -> list[dict[str, Any]]:
    """Poll UniFi Network MCP server for alarms and events."""
    events = []
    try:
        result = await client.call_tool("unifi_list_alarms", {})
        if result.get("success") and result.get("data"):
            raw_alarms = result["data"] if isinstance(result["data"], list) else [result["data"]]
            for alarm in raw_alarms:
                event_type = alarm.get("key", "alarm")
                ts = alarm.get("time", alarm.get("timestamp", datetime.now(timezone.utc).isoformat()))
                # Normalize epoch timestamps
                if isinstance(ts, (int, float)):
                    ts = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                event_id = alarm.get("_id", alarm.get("id", f"network-{ts}-{event_type}"))
                severity = classify_severity(event_type, alarm, ts)
                events.append({
                    "id": event_id,
                    "server": "network",
                    "event_type": event_type,
                    "timestamp": ts,
                    "details": alarm,
                    "severity": severity,
                })
    except (MCPConnectionError, MCPToolError) as e:
        logger.warning("Failed to poll Network: %s", e)
    except Exception:
        logger.exception("Unexpected error polling Network")
    return events


# ── Main loop ───────────────────────────────────────────────────────────────


async def run_collector(
    state_dir: str,
    poll_interval: int,
    servers: list[str],
    timeout: int,
) -> None:
    """Main collector loop. Polls servers and stores events until timeout."""
    conn = init_db(state_dir)
    logger.info("Collector started: state_dir=%s poll=%ds servers=%s timeout=%ds", state_dir, poll_interval, servers, timeout)

    # Build MCP clients for requested servers
    clients: dict[str, MCPClient] = {}
    for server in servers:
        try:
            url = get_server_url(server)
            clients[server] = MCPClient(url, timeout=15.0)
        except ValueError as e:
            logger.warning("Skipping unknown server %s: %s", server, e)

    start_time = time.monotonic()
    shutdown = asyncio.Event()

    def handle_signal(signum, frame):
        logger.info("Received signal %d, shutting down", signum)
        shutdown.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        while not shutdown.is_set():
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                logger.info("Timeout reached (%.0fs), shutting down", elapsed)
                break

            # Poll all configured servers
            all_events: list[dict[str, Any]] = []

            poll_tasks = []
            if "protect" in clients:
                poll_tasks.append(("protect", poll_protect(clients["protect"])))
            if "access" in clients:
                poll_tasks.append(("access", poll_access(clients["access"])))
            if "network" in clients:
                poll_tasks.append(("network", poll_network(clients["network"])))

            for server_name, coro in poll_tasks:
                try:
                    events = await coro
                    all_events.extend(events)
                except Exception:
                    logger.exception("Error polling %s", server_name)

            # Insert into DB
            if all_events:
                new_count = insert_events(conn, all_events)
                total = count_events(conn)
                if new_count > 0:
                    logger.info("Buffered %d new events (%d total)", new_count, total)

            # Wait for next poll interval or shutdown
            try:
                await asyncio.wait_for(shutdown.wait(), timeout=poll_interval)
                break  # shutdown was set
            except asyncio.TimeoutError:
                pass  # Normal — poll interval elapsed

    finally:
        # Close MCP clients
        for client in clients.values():
            try:
                await client.close()
            except Exception:
                pass
        conn.close()
        logger.info("Collector stopped. Database at %s/events.db", state_dir)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Security digest event collector daemon")
    parser.add_argument("--state-dir", default=".claude/unifi-skills", help="State directory for events.db and PID file")
    parser.add_argument("--poll-interval", type=int, default=10, help="Seconds between polls (default: 10)")
    parser.add_argument("--servers", default="protect,network", help="Comma-separated server list (default: protect,network)")
    parser.add_argument("--timeout", type=int, default=1800, help="Auto-exit after N seconds (default: 1800 = 30 min)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the collector daemon."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    args = parse_args(argv)
    servers = [s.strip() for s in args.servers.split(",") if s.strip()]

    Path(args.state_dir).mkdir(parents=True, exist_ok=True)

    asyncio.run(run_collector(
        state_dir=args.state_dir,
        poll_interval=args.poll_interval,
        servers=servers,
        timeout=args.timeout,
    ))


if __name__ == "__main__":
    main()
