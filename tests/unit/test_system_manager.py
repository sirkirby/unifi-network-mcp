"""Tests for the SystemManager class.

This module tests system info, controller status, and firmware update
operations — specifically the list-response handling that was fixed in PR #76.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestGetSystemInfo:
    """Tests for SystemManager.get_system_info()."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock ConnectionManager."""
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        conn.get_cached = MagicMock(return_value=None)
        conn._update_cache = MagicMock()
        conn._invalidate_cache = MagicMock()
        return conn

    @pytest.fixture
    def system_manager(self, mock_connection):
        """Create a SystemManager with mocked connection."""
        from src.managers.system_manager import SystemManager

        return SystemManager(mock_connection)

    @pytest.mark.asyncio
    async def test_list_response(self, system_manager, mock_connection):
        """Test that a list response is unwrapped to its first element."""
        mock_connection.request.return_value = [{"version": "8.6.9", "uptime": 12345}]

        result = await system_manager.get_system_info()

        assert result == {"version": "8.6.9", "uptime": 12345}
        mock_connection._update_cache.assert_called_once()
        cached_value = mock_connection._update_cache.call_args[0][1]
        assert cached_value == {"version": "8.6.9", "uptime": 12345}

    @pytest.mark.asyncio
    async def test_dict_response(self, system_manager, mock_connection):
        """Test that a dict response is returned as-is."""
        mock_connection.request.return_value = {"version": "8.6.9"}

        result = await system_manager.get_system_info()

        assert result == {"version": "8.6.9"}

    @pytest.mark.asyncio
    async def test_empty_list(self, system_manager, mock_connection):
        """Test that an empty list returns an empty dict."""
        mock_connection.request.return_value = []

        result = await system_manager.get_system_info()

        assert result == {}

    @pytest.mark.asyncio
    async def test_none_response(self, system_manager, mock_connection):
        """Test that a None response returns an empty dict."""
        mock_connection.request.return_value = None

        result = await system_manager.get_system_info()

        assert result == {}

    @pytest.mark.asyncio
    async def test_exception(self, system_manager, mock_connection):
        """Test that an exception returns an empty dict."""
        mock_connection.request.side_effect = Exception("Network error")

        result = await system_manager.get_system_info()

        assert result == {}
        mock_connection.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit(self, system_manager, mock_connection):
        """Test that cached data is returned without making a request."""
        cached_data = {"version": "8.6.9", "uptime": 99999}
        mock_connection.get_cached.return_value = cached_data

        result = await system_manager.get_system_info()

        assert result == cached_data
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_populates(self, system_manager, mock_connection):
        """Test that a cache miss fetches data and populates the cache."""
        mock_connection.request.return_value = [{"version": "8.6.9"}]

        result = await system_manager.get_system_info()

        assert result == {"version": "8.6.9"}
        mock_connection._update_cache.assert_called_once_with("system_info_default", {"version": "8.6.9"}, timeout=15)


class TestGetControllerStatus:
    """Tests for SystemManager.get_controller_status()."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock ConnectionManager."""
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        conn.get_cached = MagicMock(return_value=None)
        conn._update_cache = MagicMock()
        conn._invalidate_cache = MagicMock()
        return conn

    @pytest.fixture
    def system_manager(self, mock_connection):
        """Create a SystemManager with mocked connection."""
        from src.managers.system_manager import SystemManager

        return SystemManager(mock_connection)

    @pytest.mark.asyncio
    async def test_list_response(self, system_manager, mock_connection):
        """Test that a list response is unwrapped to its first element."""
        mock_connection.request.return_value = [{"status": "ok"}]

        result = await system_manager.get_controller_status()

        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_dict_response(self, system_manager, mock_connection):
        """Test that a dict response is returned as-is."""
        mock_connection.request.return_value = {"status": "ok"}

        result = await system_manager.get_controller_status()

        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_empty_list(self, system_manager, mock_connection):
        """Test that an empty list returns an empty dict."""
        mock_connection.request.return_value = []

        result = await system_manager.get_controller_status()

        assert result == {}

    @pytest.mark.asyncio
    async def test_none_response(self, system_manager, mock_connection):
        """Test that a None response returns an empty dict."""
        mock_connection.request.return_value = None

        result = await system_manager.get_controller_status()

        assert result == {}

    @pytest.mark.asyncio
    async def test_exception(self, system_manager, mock_connection):
        """Test that an exception returns an empty dict."""
        mock_connection.request.side_effect = Exception("API error")

        result = await system_manager.get_controller_status()

        assert result == {}


class TestCheckFirmwareUpdates:
    """Tests for SystemManager.check_firmware_updates()."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock ConnectionManager."""
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        conn.get_cached = MagicMock(return_value=None)
        conn._update_cache = MagicMock()
        conn._invalidate_cache = MagicMock()
        return conn

    @pytest.fixture
    def system_manager(self, mock_connection):
        """Create a SystemManager with mocked connection."""
        from src.managers.system_manager import SystemManager

        return SystemManager(mock_connection)

    @pytest.mark.asyncio
    async def test_list_response(self, system_manager, mock_connection):
        """Test that a list response is unwrapped to its first element."""
        mock_connection.request.return_value = [{"firmware_version": "7.1.68", "device_type": "U7PG2"}]

        result = await system_manager.check_firmware_updates()

        assert result == {"firmware_version": "7.1.68", "device_type": "U7PG2"}

    @pytest.mark.asyncio
    async def test_dict_response(self, system_manager, mock_connection):
        """Test that a dict response is returned as-is."""
        mock_connection.request.return_value = {"firmware_version": "7.1.68"}

        result = await system_manager.check_firmware_updates()

        assert result == {"firmware_version": "7.1.68"}

    @pytest.mark.asyncio
    async def test_empty_list(self, system_manager, mock_connection):
        """Test that an empty list returns an empty dict."""
        mock_connection.request.return_value = []

        result = await system_manager.check_firmware_updates()

        assert result == {}

    @pytest.mark.asyncio
    async def test_none_response(self, system_manager, mock_connection):
        """Test that a None response returns an empty dict."""
        mock_connection.request.return_value = None

        result = await system_manager.check_firmware_updates()

        assert result == {}

    @pytest.mark.asyncio
    async def test_exception(self, system_manager, mock_connection):
        """Test that an exception returns an empty dict."""
        mock_connection.request.side_effect = Exception("Timeout")

        result = await system_manager.check_firmware_updates()

        assert result == {}
