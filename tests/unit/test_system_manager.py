"""Tests for SystemManager.get_network_health() response handling."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestGetNetworkHealth:
    """Tests for SystemManager.get_network_health().

    Unlike other /stat/* endpoints that wrap a single dict in a list,
    /stat/health returns a multi-element list (one dict per subsystem).
    """

    @pytest.fixture
    def mock_connection(self):
        """Create a mock ConnectionManager."""
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        conn.get_cached = MagicMock(return_value=None)
        conn._update_cache = MagicMock()
        return conn

    @pytest.fixture
    def system_manager(self, mock_connection):
        """Create a SystemManager with mocked connection."""
        from src.managers.system_manager import SystemManager

        return SystemManager(mock_connection)

    @pytest.mark.asyncio
    async def test_multi_element_list(self, system_manager, mock_connection):
        """Test that a multi-element list is returned in full (no truncation)."""
        health_data = [
            {"subsystem": "wan", "status": "ok", "num_gw": 1},
            {"subsystem": "wlan", "status": "ok", "num_ap": 3},
            {"subsystem": "lan", "status": "ok", "num_sw": 2},
        ]
        mock_connection.request.return_value = health_data

        result = await system_manager.get_network_health()

        assert result == health_data
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_single_element_list(self, system_manager, mock_connection):
        """Test that a single-element list is returned as-is (not unwrapped)."""
        mock_connection.request.return_value = [{"subsystem": "wan", "status": "ok"}]

        result = await system_manager.get_network_health()

        assert result == [{"subsystem": "wan", "status": "ok"}]
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_dict_response_wrapped(self, system_manager, mock_connection):
        """Test that a dict response is normalized to a single-element list."""
        mock_connection.request.return_value = {"subsystem": "wan", "status": "ok"}

        result = await system_manager.get_network_health()

        assert result == [{"subsystem": "wan", "status": "ok"}]
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_empty_list(self, system_manager, mock_connection):
        """Test that an empty list returns an empty list."""
        mock_connection.request.return_value = []

        result = await system_manager.get_network_health()

        assert result == []

    @pytest.mark.asyncio
    async def test_none_response(self, system_manager, mock_connection):
        """Test that a None response returns an empty list."""
        mock_connection.request.return_value = None

        result = await system_manager.get_network_health()

        assert result == []

    @pytest.mark.asyncio
    async def test_exception(self, system_manager, mock_connection):
        """Test that an exception returns an empty list."""
        mock_connection.request.side_effect = Exception("Network error")

        result = await system_manager.get_network_health()

        assert result == []
        mock_connection.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit(self, system_manager, mock_connection):
        """Test that cached data is returned without making a request."""
        cached_data = [{"subsystem": "wan", "status": "ok"}]
        mock_connection.get_cached.return_value = cached_data

        result = await system_manager.get_network_health()

        assert result == cached_data
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_populates(self, system_manager, mock_connection):
        """Test that a cache miss fetches data and populates the cache."""
        health_data = [{"subsystem": "wan"}, {"subsystem": "wlan"}]
        mock_connection.request.return_value = health_data

        result = await system_manager.get_network_health()

        assert result == health_data
        mock_connection._update_cache.assert_called_once_with("health_default", health_data, timeout=10)
