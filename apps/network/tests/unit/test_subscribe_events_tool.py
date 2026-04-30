"""Tests for unifi_subscribe_events and unifi_recent_events MCP tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_event_manager():
    """Patch the network event_manager singleton accessor."""
    mgr = MagicMock()
    with patch(
        "unifi_network_mcp.tools.events._get_event_manager",
        return_value=mgr,
    ):
        yield mgr


class TestUnifiRecentEvents:
    @pytest.mark.asyncio
    async def test_unifi_recent_events_returns_buffered(self, mock_event_manager):
        from unifi_network_mcp.tools.events import unifi_recent_events

        mock_event_manager.get_recent_from_buffer.return_value = [
            {"key": "EVT_WU_Connected", "msg": "client x connected"},
            {"key": "EVT_WU_Disconnected", "msg": "client x disconnected"},
        ]
        mock_event_manager.buffer_size = 7

        result = await unifi_recent_events()

        assert result["count"] == 2
        assert result["buffer_size"] == 7
        assert len(result["events"]) == 2

    @pytest.mark.asyncio
    async def test_unifi_recent_events_passes_filters(self, mock_event_manager):
        from unifi_network_mcp.tools.events import unifi_recent_events

        mock_event_manager.get_recent_from_buffer.return_value = []
        mock_event_manager.buffer_size = 0

        await unifi_recent_events(event_type="EVT_WU_", mac="aa:bb:cc:dd:ee:ff", limit=5)

        mock_event_manager.get_recent_from_buffer.assert_called_once_with(
            event_type="EVT_WU_",
            mac="aa:bb:cc:dd:ee:ff",
            limit=5,
        )


class TestUnifiSubscribeEvents:
    @pytest.mark.asyncio
    async def test_unifi_subscribe_events_returns_handle_dict(self, mock_event_manager):
        from unifi_network_mcp.tools.events import unifi_subscribe_events

        mock_event_manager.buffer_size = 12
        result = await unifi_subscribe_events()

        assert result["resource_uri"] == "unifi://network/events"
        assert result["summary_uri"] == "unifi://network/events/recent"
        assert result["buffer_size"] == 12
        assert "instructions" in result
