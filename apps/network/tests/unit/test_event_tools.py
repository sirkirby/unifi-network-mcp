"""Tests for event/alarm tool confirmation previews."""

import os

import pytest

os.environ.setdefault("UNIFI_HOST", "127.0.0.1")
os.environ.setdefault("UNIFI_USERNAME", "test")
os.environ.setdefault("UNIFI_PASSWORD", "test")


@pytest.mark.asyncio
async def test_archive_alarm_preview_requires_confirmation():
    from unifi_network_mcp.tools.events import archive_alarm

    result = await archive_alarm(alarm_id="alarm123", confirm=False)

    assert result["success"] is True
    assert result["requires_confirmation"] is True
    assert result["resource_type"] == "alarm"
    assert result["resource_id"] == "alarm123"
    assert result["preview"]["proposed"]["archived"] is True


@pytest.mark.asyncio
async def test_archive_all_alarms_preview_requires_confirmation():
    from unifi_network_mcp.tools.events import archive_all_alarms

    result = await archive_all_alarms(confirm=False)

    assert result["success"] is True
    assert result["requires_confirmation"] is True
    assert result["resource_type"] == "alarm_collection"
    assert result["resource_id"] == "all_active_alarms"
    assert result["preview"]["proposed"]["archived"] is True
