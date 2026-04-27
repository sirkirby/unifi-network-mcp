"""Tests for device management commands (locate, force provision).

Tests the locate_device and force_provision methods on DeviceManager.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from unifi_network_mcp.managers.device_manager import DeviceManager


class TestDeviceCommands:
    """Tests for device command methods in DeviceManager."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock ConnectionManager."""
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        return conn

    @pytest.fixture
    def device_manager(self, mock_connection):
        """Create a DeviceManager with mocked connection."""
        return DeviceManager(mock_connection)

    # ---- locate_device ----

    @pytest.mark.asyncio
    async def test_locate_device_enable(self, device_manager, mock_connection):
        """Test locate_device sends set-locate command."""
        mock_connection.request.return_value = {}

        result = await device_manager.locate_device("aa:bb:cc:dd:ee:ff", True)

        assert result is True
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/cmd/devmgr"
        assert api_request.data["cmd"] == "set-locate"
        assert api_request.data["mac"] == "aa:bb:cc:dd:ee:ff"

    @pytest.mark.asyncio
    async def test_locate_device_disable(self, device_manager, mock_connection):
        """Test locate_device sends unset-locate command."""
        mock_connection.request.return_value = {}

        result = await device_manager.locate_device("aa:bb:cc:dd:ee:ff", False)

        assert result is True
        call_args = mock_connection.request.call_args
        assert call_args[0][0].data["cmd"] == "unset-locate"

    @pytest.mark.asyncio
    async def test_locate_device_handles_error(self, device_manager, mock_connection):
        """Test locate_device returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await device_manager.locate_device("aa:bb:cc:dd:ee:ff", True)
    # ---- force_provision ----

    @pytest.mark.asyncio
    async def test_force_provision_success(self, device_manager, mock_connection):
        """Test force_provision sends correct command."""
        mock_connection.request.return_value = {}

        result = await device_manager.force_provision("aa:bb:cc:dd:ee:ff")

        assert result is True
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/cmd/devmgr"
        assert api_request.data["cmd"] == "force-provision"
        assert api_request.data["mac"] == "aa:bb:cc:dd:ee:ff"

    @pytest.mark.asyncio
    async def test_force_provision_handles_error(self, device_manager, mock_connection):
        """Test force_provision returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await device_manager.force_provision("aa:bb:cc:dd:ee:ff")
