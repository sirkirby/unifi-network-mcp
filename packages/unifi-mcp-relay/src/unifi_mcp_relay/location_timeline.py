"""Cross-product location timeline tool for the relay sidecar.

Fans out event queries to all connected servers via the ToolForwarder,
merges results into a single time-sorted timeline, and returns a unified
response. This tool is only available in relay mode — local/stdio mode
uses the single-product event timeline from unifi-mcp-shared.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from unifi_mcp_shared.event_timeline import NormalizedEvent, filter_by_area, merge_timelines

logger = logging.getLogger("unifi-mcp-relay")


def validate_timeline_input(
    *,
    start_time: str,
    end_time: str,
    location_id: str | None = None,
    is_relay_mode: bool = True,
) -> list[str]:
    """Validate timeline tool input parameters.

    Returns list of error messages (empty if valid).
    """
    errors: list[str] = []

    if not start_time:
        errors.append("start_time is required")
    if not end_time:
        errors.append("end_time is required")

    parsed_start = None
    parsed_end = None

    if start_time:
        try:
            parsed_start = datetime.fromisoformat(start_time)
        except ValueError:
            errors.append(f"start_time is not valid ISO 8601: '{start_time}'")

    if end_time:
        try:
            parsed_end = datetime.fromisoformat(end_time)
        except ValueError:
            errors.append(f"end_time is not valid ISO 8601: '{end_time}'")

    if parsed_start and parsed_end and parsed_end <= parsed_start:
        errors.append("end_time must be after start_time")

    if location_id and not is_relay_mode:
        errors.append(
            "location_id is only meaningful in relay mode. "
            "Omit this parameter for local connections."
        )

    return errors


def build_timeline_summary(events: list[NormalizedEvent]) -> dict[str, Any]:
    """Build summary statistics from a list of events."""
    if not events:
        return {
            "total_events": 0,
            "by_product": {},
            "by_type": {},
            "by_location": {},
        }

    by_product = Counter(e.product for e in events)
    by_type = Counter(e.event_type for e in events)
    by_location = Counter(
        e.location_id for e in events if e.location_id is not None
    )

    summary: dict[str, Any] = {
        "total_events": len(events),
        "by_product": dict(by_product),
        "by_type": dict(by_type),
        "by_location": dict(by_location),
        "time_range": {
            "start": events[0].timestamp.isoformat(),
            "end": events[-1].timestamp.isoformat(),
        },
    }

    return summary


def build_timeline_response(
    events: list[NormalizedEvent],
) -> dict[str, Any]:
    """Build the final tool response from merged events."""
    return {
        "success": True,
        "data": {
            "timeline": [e.to_dict() for e in events],
            "summary": build_timeline_summary(events),
        },
    }
