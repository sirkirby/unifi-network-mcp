"""Tests for the EventManager class.

Tests both the v2 system-log API (modern controllers) and the legacy
/stat/event API (older controllers).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestEventManagerV2:
    """Tests for the EventManager using the v2 system-log API."""

    @pytest.fixture
    def mock_connection(self):
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        return conn

    @pytest.fixture
    def event_manager(self, mock_connection):
        from unifi_core.network.managers.event_manager import EventManager

        mgr = EventManager(mock_connection)
        mgr._use_v2 = True  # Force v2 mode
        return mgr

    @pytest.mark.asyncio
    async def test_get_events_returns_list(self, event_manager, mock_connection):
        mock_connection.request.return_value = [
            {
                "data": [
                    {"id": "evt1", "event": "CLIENT_CONNECTED_WIRED", "category": "CLIENT_DEVICES"},
                    {"id": "evt2", "event": "CLIENT_DISCONNECTED_WIRELESS", "category": "CLIENT_DEVICES"},
                ],
                "total_element_count": 2,
            }
        ]
        events = await event_manager.get_events(within=24, limit=100)
        assert len(events) == 2
        assert events[0]["id"] == "evt1"

    @pytest.mark.asyncio
    async def test_get_events_with_search_text(self, event_manager, mock_connection):
        mock_connection.request.return_value = [{"data": [], "total_element_count": 0}]
        await event_manager.get_events(event_type="CLIENT_CONNECTED")
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.data["searchText"] == "CLIENT_CONNECTED"

    @pytest.mark.asyncio
    async def test_get_events_uses_timestamp_range(self, event_manager, mock_connection):
        mock_connection.request.return_value = [{"data": [], "total_element_count": 0}]
        await event_manager.get_events(within=48)
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert "timestampFrom" in api_request.data
        assert "timestampTo" in api_request.data
        assert api_request.data["timestampTo"] > api_request.data["timestampFrom"]

    @pytest.mark.asyncio
    async def test_get_events_handles_error(self, event_manager, mock_connection):
        mock_connection.request.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            await event_manager.get_events()

    @pytest.mark.asyncio
    async def test_get_alarms_v2(self, event_manager, mock_connection):
        mock_connection.request.return_value = [
            {
                "data": [
                    {"id": "alm1", "event": "THREAT_DETECTED", "severity": "VERY_HIGH"},
                ],
                "total_element_count": 1,
            }
        ]
        alarms = await event_manager.get_alarms()
        assert len(alarms) == 1
        assert alarms[0]["severity"] == "VERY_HIGH"

    @pytest.mark.asyncio
    async def test_get_alarms_v2_limit(self, event_manager, mock_connection):
        mock_data = [{"id": f"alm{i}"} for i in range(200)]
        mock_connection.request.return_value = [{"data": mock_data, "total_element_count": 200}]
        alarms = await event_manager.get_alarms(limit=50)
        assert len(alarms) == 50


class TestEventManagerLegacy:
    """Tests for the EventManager using the legacy /stat/event API."""

    @pytest.fixture
    def mock_connection(self):
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        return conn

    @pytest.fixture
    def event_manager(self, mock_connection):
        from unifi_core.network.managers.event_manager import EventManager

        mgr = EventManager(mock_connection)
        mgr._use_v2 = False  # Force legacy mode
        return mgr

    @pytest.mark.asyncio
    async def test_get_events_returns_list(self, event_manager, mock_connection):
        mock_events = [
            {"_id": "evt1", "msg": "Client connected", "time": 1700000000},
            {"_id": "evt2", "msg": "Client disconnected", "time": 1700000100},
        ]
        mock_connection.request.return_value = mock_events
        events = await event_manager.get_events(within=24, limit=100)
        assert len(events) == 2
        assert events[0]["_id"] == "evt1"

    @pytest.mark.asyncio
    async def test_get_events_with_type_filter(self, event_manager, mock_connection):
        mock_connection.request.return_value = []
        await event_manager.get_events(event_type="EVT_SW_")
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.data["type"] == "EVT_SW_"

    @pytest.mark.asyncio
    async def test_get_events_respects_limit(self, event_manager, mock_connection):
        mock_connection.request.return_value = []
        await event_manager.get_events(limit=5000)
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.data["_limit"] == 3000

    @pytest.mark.asyncio
    async def test_get_events_handles_dict_response(self, event_manager, mock_connection):
        mock_connection.request.return_value = {"data": [{"_id": "evt1"}], "meta": {"rc": "ok"}}
        events = await event_manager.get_events()
        assert len(events) == 1
        assert events[0]["_id"] == "evt1"

    @pytest.mark.asyncio
    async def test_get_events_handles_error(self, event_manager, mock_connection):
        mock_connection.request.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            await event_manager.get_events()

    @pytest.mark.asyncio
    async def test_get_alarms_returns_list(self, event_manager, mock_connection):
        mock_alarms = [
            {"_id": "alm1", "msg": "High CPU usage", "severity": "warning"},
            {"_id": "alm2", "msg": "Device offline", "severity": "critical"},
        ]
        mock_connection.request.return_value = mock_alarms
        alarms = await event_manager.get_alarms()
        assert len(alarms) == 2

    @pytest.mark.asyncio
    async def test_get_alarms_archived_parameter(self, event_manager, mock_connection):
        mock_connection.request.return_value = []
        await event_manager.get_alarms(archived=True)
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert "archived=true" in api_request.path

    @pytest.mark.asyncio
    async def test_get_alarms_limit(self, event_manager, mock_connection):
        mock_alarms = [{"_id": f"alm{i}"} for i in range(200)]
        mock_connection.request.return_value = mock_alarms
        alarms = await event_manager.get_alarms(limit=50)
        assert len(alarms) == 50


class TestEventManagerCommon:
    """Tests for shared EventManager functionality."""

    @pytest.fixture
    def mock_connection(self):
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        return conn

    @pytest.fixture
    def event_manager(self, mock_connection):
        from unifi_core.network.managers.event_manager import EventManager

        return EventManager(mock_connection)

    def test_get_event_type_prefixes(self, event_manager):
        prefixes = event_manager.get_event_type_prefixes()
        assert len(prefixes) > 0
        assert any(p["prefix"] == "EVT_SW_" for p in prefixes)
        assert any(p["prefix"] == "EVT_AP_" for p in prefixes)
        assert all("description" in p for p in prefixes)

    def test_get_event_categories(self, event_manager):
        categories = event_manager.get_event_categories()
        assert len(categories) > 0
        assert any(c["category"] == "SECURITY" for c in categories)
        assert all("description" in c for c in categories)

    @pytest.mark.asyncio
    async def test_archive_alarm_success(self, event_manager, mock_connection):
        mock_connection.request.return_value = {}
        result = await event_manager.archive_alarm("alarm123")
        assert result is True
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.data["cmd"] == "archive-alarm"

    @pytest.mark.asyncio
    async def test_archive_alarm_failure(self, event_manager, mock_connection):
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await event_manager.archive_alarm("alarm123")

    @pytest.mark.asyncio
    async def test_archive_all_alarms_success(self, event_manager, mock_connection):
        mock_connection.request.return_value = {}
        result = await event_manager.archive_all_alarms()
        assert result is True

    @pytest.mark.asyncio
    async def test_archive_all_alarms_failure(self, event_manager, mock_connection):
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await event_manager.archive_all_alarms()

    @pytest.mark.asyncio
    async def test_auto_detect_v2(self, event_manager, mock_connection):
        """Test that v2 API is detected when system-log/count succeeds."""
        mock_connection.request.return_value = {"count": 100}
        await event_manager._ensure_api_version()
        assert event_manager._use_v2 is True

    @pytest.mark.asyncio
    async def test_auto_detect_legacy(self, event_manager, mock_connection):
        """Test that legacy API is used when system-log/count fails."""
        mock_connection.request.side_effect = Exception("404")
        await event_manager._ensure_api_version()
        assert event_manager._use_v2 is False
