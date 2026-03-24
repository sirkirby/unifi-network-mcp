"""Tests for the cross-product location timeline tool."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from unifi_mcp_relay.location_timeline import (
    build_timeline_response,
    build_timeline_summary,
    validate_timeline_input,
)
from unifi_mcp_shared.event_timeline import NormalizedEvent


class TestValidateTimelineInput:
    """Test input validation for the timeline tool."""

    def test_valid_input(self):
        errors = validate_timeline_input(
            start_time="2026-03-24T00:00:00Z",
            end_time="2026-03-24T23:59:59Z",
        )
        assert errors == []

    def test_missing_start_time(self):
        errors = validate_timeline_input(start_time="", end_time="2026-03-24T23:59:59Z")
        assert any("start_time" in e for e in errors)

    def test_end_before_start(self):
        errors = validate_timeline_input(
            start_time="2026-03-24T23:59:59Z",
            end_time="2026-03-24T00:00:00Z",
        )
        assert any("before" in e.lower() or "after" in e.lower() for e in errors)

    def test_invalid_iso_format(self):
        errors = validate_timeline_input(
            start_time="not-a-date",
            end_time="2026-03-24T23:59:59Z",
        )
        assert any("start_time" in e for e in errors)

    def test_location_id_in_local_mode_returns_error(self):
        errors = validate_timeline_input(
            start_time="2026-03-24T00:00:00Z",
            end_time="2026-03-24T23:59:59Z",
            location_id="loc_123",
            is_relay_mode=False,
        )
        assert any("relay" in e.lower() for e in errors)

    def test_location_id_in_relay_mode_ok(self):
        errors = validate_timeline_input(
            start_time="2026-03-24T00:00:00Z",
            end_time="2026-03-24T23:59:59Z",
            location_id="loc_123",
            is_relay_mode=True,
        )
        assert errors == []


class TestBuildTimelineSummary:
    """Test summary generation from events."""

    def test_empty_events(self):
        summary = build_timeline_summary([])
        assert summary["total_events"] == 0
        assert summary["by_location"] == {}

    def test_counts_by_product(self):
        events = [
            NormalizedEvent(
                timestamp=datetime(2026, 3, 24, 1, 0, tzinfo=timezone.utc),
                product="network", event_type="a", summary="a",
            ),
            NormalizedEvent(
                timestamp=datetime(2026, 3, 24, 2, 0, tzinfo=timezone.utc),
                product="network", event_type="b", summary="b",
            ),
            NormalizedEvent(
                timestamp=datetime(2026, 3, 24, 3, 0, tzinfo=timezone.utc),
                product="protect", event_type="c", summary="c",
            ),
        ]
        summary = build_timeline_summary(events)
        assert summary["by_product"]["network"] == 2
        assert summary["by_product"]["protect"] == 1

    def test_counts_by_location(self):
        events = [
            NormalizedEvent(
                timestamp=datetime(2026, 3, 24, 1, 0, tzinfo=timezone.utc),
                product="network", event_type="a", summary="a",
                location_id="loc_1", location_name="Home",
            ),
            NormalizedEvent(
                timestamp=datetime(2026, 3, 24, 2, 0, tzinfo=timezone.utc),
                product="protect", event_type="b", summary="b",
                location_id="loc_2", location_name="Office",
            ),
        ]
        summary = build_timeline_summary(events)
        assert summary["by_location"]["loc_1"] == 1
        assert summary["by_location"]["loc_2"] == 1


class TestBuildTimelineResponse:
    """Test final response construction."""

    def test_success_response_shape(self):
        events = [
            NormalizedEvent(
                timestamp=datetime(2026, 3, 24, 1, 0, tzinfo=timezone.utc),
                product="network", event_type="a", summary="a",
            ),
        ]
        response = build_timeline_response(events)
        assert response["success"] is True
        assert "timeline" in response["data"]
        assert "summary" in response["data"]
        assert len(response["data"]["timeline"]) == 1
