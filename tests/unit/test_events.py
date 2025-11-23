"""Unit tests for event log functionality.

Tests the EventManager methods for viewing events and alarms.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.managers.event_manager import EventManager


class TestEventManagerGetEvents:
    """Test suite for EventManager.get_events method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.ensure_connected = AsyncMock(return_value=True)
        mock.controller = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def event_manager(self, mock_connection_manager):
        """Create an EventManager with mocked connection."""
        return EventManager(mock_connection_manager)

    @pytest.fixture
    def sample_events(self):
        """Sample event data returned by the API."""
        return [
            {
                "_id": "event_id_1",
                "key": "EVT_WU_Connected",
                "time": 1705320600000,
                "msg": "User[aa:bb:cc:dd:ee:ff] has connected to AP[Test AP]",
                "subsystem": "wlan",
                "user": "aa:bb:cc:dd:ee:ff",
                "ap": "Test AP",
                "ssid": "MyNetwork",
                "site_id": "site123",
            },
            {
                "_id": "event_id_2",
                "key": "EVT_SW_PortUp",
                "time": 1705320500000,
                "msg": "Port 1 on Switch[Test Switch] is now up",
                "subsystem": "lan",
                "site_id": "site123",
            },
        ]

    @pytest.mark.asyncio
    async def test_get_events_success(self, event_manager, sample_events):
        """Test successfully getting events."""
        event_manager._connection.request = AsyncMock(return_value=sample_events)

        result = await event_manager.get_events()

        assert len(result) == 2
        assert result[0]["key"] == "EVT_WU_Connected"
        assert result[1]["key"] == "EVT_SW_PortUp"

    @pytest.mark.asyncio
    async def test_get_events_with_filter(self, event_manager, sample_events):
        """Test getting events with type filter."""
        filtered_events = [sample_events[0]]  # Only WLAN event
        event_manager._connection.request = AsyncMock(return_value=filtered_events)

        result = await event_manager.get_events(event_type="EVT_WU_")

        assert len(result) == 1
        assert result[0]["key"] == "EVT_WU_Connected"

        # Verify the request included the type filter
        call_args = event_manager._connection.request.call_args[0][0]
        assert call_args.data["type"] == "EVT_WU_"

    @pytest.mark.asyncio
    async def test_get_events_with_limit(self, event_manager):
        """Test getting events with custom limit."""
        event_manager._connection.request = AsyncMock(return_value=[])

        await event_manager.get_events(limit=50, within=12)

        call_args = event_manager._connection.request.call_args[0][0]
        assert call_args.data["_limit"] == 50
        assert call_args.data["within"] == 12

    @pytest.mark.asyncio
    async def test_get_events_limit_capped(self, event_manager):
        """Test that event limit is capped at 3000."""
        event_manager._connection.request = AsyncMock(return_value=[])

        await event_manager.get_events(limit=5000)

        call_args = event_manager._connection.request.call_args[0][0]
        assert call_args.data["_limit"] == 3000

    @pytest.mark.asyncio
    async def test_get_events_empty(self, event_manager):
        """Test getting events when none exist."""
        event_manager._connection.request = AsyncMock(return_value=[])

        result = await event_manager.get_events()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_events_api_error(self, event_manager):
        """Test handling API errors gracefully."""
        event_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await event_manager.get_events()

        assert result == []


class TestEventManagerGetAlarms:
    """Test suite for EventManager.get_alarms method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.ensure_connected = AsyncMock(return_value=True)
        mock.controller = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def event_manager(self, mock_connection_manager):
        """Create an EventManager with mocked connection."""
        return EventManager(mock_connection_manager)

    @pytest.fixture
    def sample_alarms(self):
        """Sample alarm data returned by the API."""
        return [
            {
                "_id": "alarm_id_1",
                "key": "EVT_AP_Disconnected",
                "time": 1705320600000,
                "msg": "AP[Test AP] has disconnected",
                "archived": False,
                "site_id": "site123",
            },
            {
                "_id": "alarm_id_2",
                "key": "EVT_SW_HighCPU",
                "time": 1705320500000,
                "msg": "Switch[Test Switch] CPU usage is high",
                "archived": False,
                "site_id": "site123",
            },
        ]

    @pytest.mark.asyncio
    async def test_get_alarms_success(self, event_manager, sample_alarms):
        """Test successfully getting alarms."""
        event_manager._connection.request = AsyncMock(return_value=sample_alarms)

        result = await event_manager.get_alarms()

        assert len(result) == 2
        assert result[0]["key"] == "EVT_AP_Disconnected"

    @pytest.mark.asyncio
    async def test_get_alarms_with_limit(self, event_manager, sample_alarms):
        """Test getting alarms with limit applied."""
        event_manager._connection.request = AsyncMock(return_value=sample_alarms)

        result = await event_manager.get_alarms(limit=1)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_alarms_api_error(self, event_manager):
        """Test handling API errors gracefully."""
        event_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await event_manager.get_alarms()

        assert result == []


class TestEventManagerArchiveAlarm:
    """Test suite for EventManager.archive_alarm method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def event_manager(self, mock_connection_manager):
        """Create an EventManager with mocked connection."""
        return EventManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_archive_alarm_success(self, event_manager):
        """Test successfully archiving an alarm."""
        result = await event_manager.archive_alarm("alarm_id_1")

        assert result is True
        call_args = event_manager._connection.request.call_args[0][0]
        assert call_args.data["cmd"] == "archive-alarm"
        assert call_args.data["_id"] == "alarm_id_1"

    @pytest.mark.asyncio
    async def test_archive_alarm_api_error(self, event_manager):
        """Test handling API errors during alarm archiving."""
        event_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await event_manager.archive_alarm("alarm_id_1")

        assert result is False


class TestEventManagerArchiveAllAlarms:
    """Test suite for EventManager.archive_all_alarms method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def event_manager(self, mock_connection_manager):
        """Create an EventManager with mocked connection."""
        return EventManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_archive_all_alarms_success(self, event_manager):
        """Test successfully archiving all alarms."""
        result = await event_manager.archive_all_alarms()

        assert result is True
        call_args = event_manager._connection.request.call_args[0][0]
        assert call_args.data["cmd"] == "archive-all-alarms"

    @pytest.mark.asyncio
    async def test_archive_all_alarms_api_error(self, event_manager):
        """Test handling API errors during archive all."""
        event_manager._connection.request = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await event_manager.archive_all_alarms()

        assert result is False


class TestEventManagerGetEventTypes:
    """Test suite for EventManager.get_event_types method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.site = "default"
        return mock

    @pytest.fixture
    def event_manager(self, mock_connection_manager):
        """Create an EventManager with mocked connection."""
        return EventManager(mock_connection_manager)

    @pytest.mark.asyncio
    async def test_get_event_types(self, event_manager):
        """Test getting event type prefixes."""
        result = await event_manager.get_event_types()

        assert isinstance(result, list)
        assert len(result) > 0
        assert "EVT_SW_" in result
        assert "EVT_AP_" in result
        assert "EVT_WU_" in result
