"""Tests for DeviceManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager
from unifi_access_mcp.managers.device_manager import DeviceManager
from unifi_core.exceptions import UniFiConnectionError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cm_api():
    cm = AccessConnectionManager(host="192.168.1.1", username="", password="", api_key="test-key")
    cm._api_client_available = True
    cm._api_client = AsyncMock()
    return cm


@pytest.fixture
def cm_proxy():
    cm = AccessConnectionManager(host="192.168.1.1", username="admin", password="secret")
    cm._proxy_available = True
    cm._proxy_session = MagicMock()
    return cm


@pytest.fixture
def cm_none():
    return AccessConnectionManager(host="192.168.1.1", username="", password="")


@pytest.fixture
def device_mgr_api(cm_api):
    return DeviceManager(cm_api)


@pytest.fixture
def device_mgr_proxy(cm_proxy):
    return DeviceManager(cm_proxy)


@pytest.fixture
def device_mgr_none(cm_none):
    return DeviceManager(cm_none)


# ---------------------------------------------------------------------------
# list_devices
# ---------------------------------------------------------------------------


class TestListDevices:
    @pytest.mark.asyncio
    async def test_list_devices_api(self, device_mgr_api, cm_api):
        mock_device = MagicMock()
        mock_device.id = "dev-1"
        mock_device.name = "Hub Pro"
        mock_device.type = "hub"
        mock_device.connected = True
        mock_device.firmware_version = "2.1.0"

        cm_api._api_client.get_devices = AsyncMock(return_value=[mock_device])

        devices = await device_mgr_api.list_devices()

        assert len(devices) == 1
        assert devices[0]["id"] == "dev-1"
        assert devices[0]["name"] == "Hub Pro"
        assert devices[0]["connected"] is True

    @pytest.mark.asyncio
    async def test_list_devices_proxy(self, device_mgr_proxy, cm_proxy):
        """list_devices uses devices/topology4 via proxy."""
        expected = [{"id": "dev-2", "name": "Reader G2"}]
        with patch.object(cm_proxy, "proxy_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": expected}
            devices = await device_mgr_proxy.list_devices()
        assert devices == expected
        mock_req.assert_awaited_once_with("GET", "devices/topology4")

    @pytest.mark.asyncio
    async def test_list_devices_no_auth(self, device_mgr_none):
        with pytest.raises(UniFiConnectionError, match="No auth path"):
            await device_mgr_none.list_devices()


# ---------------------------------------------------------------------------
# get_device
# ---------------------------------------------------------------------------


class TestGetDevice:
    @pytest.mark.asyncio
    async def test_get_device_api(self, device_mgr_api, cm_api):
        mock_device = MagicMock()
        mock_device.id = "dev-1"
        mock_device.name = "Hub Pro"
        mock_device.type = "hub"
        mock_device.connected = True
        mock_device.firmware_version = "2.1.0"
        mock_device.mac = "AA:BB:CC:DD:EE:FF"
        mock_device.ip = "192.168.1.100"

        cm_api._api_client.get_device = AsyncMock(return_value=mock_device)

        detail = await device_mgr_api.get_device("dev-1")

        assert detail["id"] == "dev-1"
        assert detail["mac"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_get_device_proxy(self, device_mgr_proxy, cm_proxy):
        """get_device filters from topology4 response by ID."""
        topology = [
            {"id": "dev-1", "name": "Hub Pro"},
            {"id": "dev-2", "name": "Reader G2", "type": "reader"},
        ]
        with patch.object(cm_proxy, "proxy_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": topology}
            detail = await device_mgr_proxy.get_device("dev-2")
        assert detail == {"id": "dev-2", "name": "Reader G2", "type": "reader"}
        mock_req.assert_awaited_once_with("GET", "devices/topology4")

    @pytest.mark.asyncio
    async def test_get_device_proxy_not_found(self, device_mgr_proxy, cm_proxy):
        """get_device raises ValueError when device ID not found in topology."""
        with patch.object(cm_proxy, "proxy_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"data": [{"id": "other-dev"}]}
            with pytest.raises(ValueError, match="Device not found"):
                await device_mgr_proxy.get_device("missing-dev")

    @pytest.mark.asyncio
    async def test_get_device_empty_id(self, device_mgr_api):
        with pytest.raises(ValueError, match="device_id is required"):
            await device_mgr_api.get_device("")

    @pytest.mark.asyncio
    async def test_get_device_no_auth(self, device_mgr_none):
        with pytest.raises(UniFiConnectionError, match="No auth path"):
            await device_mgr_none.get_device("dev-1")


# ---------------------------------------------------------------------------
# reboot_device (preview)
# ---------------------------------------------------------------------------


class TestRebootDevice:
    @pytest.mark.asyncio
    async def test_reboot_device_preview_api(self, device_mgr_api, cm_api):
        mock_device = MagicMock()
        mock_device.id = "dev-1"
        mock_device.name = "Hub Pro"
        mock_device.type = "hub"
        mock_device.connected = True
        mock_device.firmware_version = "2.1.0"
        mock_device.mac = "AA:BB:CC:DD:EE:FF"
        mock_device.ip = "192.168.1.100"

        cm_api._api_client.get_device = AsyncMock(return_value=mock_device)

        preview = await device_mgr_api.reboot_device("dev-1")

        assert preview["device_id"] == "dev-1"
        assert preview["device_name"] == "Hub Pro"
        assert preview["proposed_changes"]["action"] == "reboot"

    @pytest.mark.asyncio
    async def test_reboot_device_empty_id(self, device_mgr_api):
        with pytest.raises(ValueError, match="device_id is required"):
            await device_mgr_api.reboot_device("")


# ---------------------------------------------------------------------------
# apply_reboot_device
# ---------------------------------------------------------------------------


class TestApplyRebootDevice:
    @pytest.mark.asyncio
    async def test_apply_reboot_success(self, device_mgr_proxy, cm_proxy):
        with patch.object(cm_proxy, "proxy_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {}
            result = await device_mgr_proxy.apply_reboot_device("dev-1")
        assert result["result"] == "success"
        assert result["action"] == "reboot"
        mock_req.assert_awaited_once_with("POST", "devices/dev-1/reboot")

    @pytest.mark.asyncio
    async def test_apply_reboot_no_proxy(self, device_mgr_none):
        with pytest.raises(UniFiConnectionError, match="No proxy session"):
            await device_mgr_none.apply_reboot_device("dev-1")
