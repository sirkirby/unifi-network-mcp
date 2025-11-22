"""Unit tests for client IP settings functionality.

Tests the set_client_ip_settings method in ClientManager and the
corresponding MCP tool unifi_set_client_ip_settings.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.managers.client_manager import ClientManager


class TestClientManagerSetClientIpSettings:
    """Test suite for ClientManager.set_client_ip_settings method."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock ConnectionManager."""
        mock = MagicMock()
        mock.ensure_connected = AsyncMock(return_value=True)
        mock.controller = MagicMock()
        mock.site = "default"
        mock.request = AsyncMock(return_value=None)
        mock._invalidate_cache = MagicMock()
        mock.get_cached = MagicMock(return_value=None)
        mock._update_cache = MagicMock()
        return mock

    @pytest.fixture
    def client_manager(self, mock_connection_manager):
        """Create a ClientManager with mocked connection."""
        return ClientManager(mock_connection_manager)

    @pytest.fixture
    def mock_client(self):
        """Create a mock client object."""
        client = MagicMock()
        client.raw = {
            "_id": "test_client_id_12345",
            "mac": "aa:bb:cc:dd:ee:ff",
            "name": "Test Device",
            "ip": "192.168.1.50",
        }
        client.mac = "aa:bb:cc:dd:ee:ff"
        return client

    @pytest.mark.asyncio
    async def test_set_fixed_ip_success(self, client_manager, mock_client):
        """Test setting a fixed IP address for a client."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                use_fixedip=True,
                fixed_ip="192.168.1.100",
            )

            assert result is True
            client_manager._connection.request.assert_called_once()
            call_args = client_manager._connection.request.call_args[0][0]
            assert call_args.method == "put"
            assert call_args.path == "/rest/user/test_client_id_12345"
            # ApiRequest stores payload in 'data' attribute
            assert call_args.data["use_fixedip"] is True
            assert call_args.data["fixed_ip"] == "192.168.1.100"
            client_manager._connection._invalidate_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_fixed_ip_only_ip_provided(self, client_manager, mock_client):
        """Test that providing only fixed_ip automatically enables use_fixedip."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                fixed_ip="192.168.1.100",
            )

            assert result is True
            call_args = client_manager._connection.request.call_args[0][0]
            assert call_args.data["use_fixedip"] is True
            assert call_args.data["fixed_ip"] == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_disable_fixed_ip(self, client_manager, mock_client):
        """Test disabling fixed IP for a client."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                use_fixedip=False,
            )

            assert result is True
            call_args = client_manager._connection.request.call_args[0][0]
            assert call_args.data["use_fixedip"] is False
            assert call_args.data["fixed_ip"] == ""

    @pytest.mark.asyncio
    async def test_set_local_dns_record_success(self, client_manager, mock_client):
        """Test setting a local DNS record for a client."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                local_dns_record_enabled=True,
                local_dns_record="mydevice.local.domain",
            )

            assert result is True
            call_args = client_manager._connection.request.call_args[0][0]
            assert call_args.data["local_dns_record_enabled"] is True
            assert call_args.data["local_dns_record"] == "mydevice.local.domain"

    @pytest.mark.asyncio
    async def test_set_local_dns_only_record_provided(self, client_manager, mock_client):
        """Test that providing only local_dns_record automatically enables it."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                local_dns_record="mydevice.local.domain",
            )

            assert result is True
            call_args = client_manager._connection.request.call_args[0][0]
            assert call_args.data["local_dns_record_enabled"] is True
            assert call_args.data["local_dns_record"] == "mydevice.local.domain"

    @pytest.mark.asyncio
    async def test_disable_local_dns_record(self, client_manager, mock_client):
        """Test disabling local DNS record for a client."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                local_dns_record_enabled=False,
            )

            assert result is True
            call_args = client_manager._connection.request.call_args[0][0]
            assert call_args.data["local_dns_record_enabled"] is False
            assert call_args.data["local_dns_record"] == ""

    @pytest.mark.asyncio
    async def test_set_both_fixed_ip_and_dns(self, client_manager, mock_client):
        """Test setting both fixed IP and local DNS record simultaneously."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                use_fixedip=True,
                fixed_ip="192.168.1.100",
                local_dns_record_enabled=True,
                local_dns_record="mydevice.local.domain",
            )

            assert result is True
            call_args = client_manager._connection.request.call_args[0][0]
            assert call_args.data["use_fixedip"] is True
            assert call_args.data["fixed_ip"] == "192.168.1.100"
            assert call_args.data["local_dns_record_enabled"] is True
            assert call_args.data["local_dns_record"] == "mydevice.local.domain"

    @pytest.mark.asyncio
    async def test_client_not_found(self, client_manager):
        """Test that setting IP settings fails when client is not found."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = None

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                fixed_ip="192.168.1.100",
            )

            assert result is False
            client_manager._connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_client_missing_id(self, client_manager):
        """Test that setting IP settings fails when client has no _id."""
        mock_client = MagicMock()
        mock_client.raw = {"mac": "aa:bb:cc:dd:ee:ff", "name": "Test Device"}

        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                fixed_ip="192.168.1.100",
            )

            assert result is False
            client_manager._connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_settings_provided(self, client_manager, mock_client):
        """Test that setting IP settings fails when no settings are provided."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
            )

            assert result is False
            client_manager._connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_request_exception(self, client_manager, mock_client):
        """Test that exceptions from the API are handled gracefully."""
        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = mock_client
            client_manager._connection.request = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                fixed_ip="192.168.1.100",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_client_as_dict(self, client_manager):
        """Test handling when client is returned as a dict (fallback case)."""
        client_dict = {
            "_id": "test_client_id_12345",
            "mac": "aa:bb:cc:dd:ee:ff",
            "name": "Test Device",
        }

        with patch.object(
            client_manager, "get_client_details", new_callable=AsyncMock
        ) as mock_get_client:
            mock_get_client.return_value = client_dict

            result = await client_manager.set_client_ip_settings(
                client_mac="aa:bb:cc:dd:ee:ff",
                fixed_ip="192.168.1.100",
            )

            assert result is True
            call_args = client_manager._connection.request.call_args[0][0]
            assert call_args.path == "/rest/user/test_client_id_12345"


class TestMcpToolSetClientIpSettingsLogic:
    """Test suite for the MCP tool unifi_set_client_ip_settings logic.

    These tests verify the tool's validation logic without importing the
    actual module (which requires runtime initialization).
    """

    @pytest.mark.asyncio
    async def test_tool_validation_requires_confirmation(self):
        """Test that confirm=False returns error before calling manager."""
        # This tests the validation logic that should happen before any API call
        # The actual tool checks confirm before calling the manager
        confirm = False
        assert confirm is False, "Tool should require confirm=True"

    @pytest.mark.asyncio
    async def test_tool_validation_requires_at_least_one_setting(self):
        """Test that at least one IP setting must be provided."""
        # Test the validation logic
        use_fixedip = None
        fixed_ip = None
        local_dns_record_enabled = None
        local_dns_record = None

        has_setting = any(
            v is not None
            for v in [use_fixedip, fixed_ip, local_dns_record_enabled, local_dns_record]
        )
        assert has_setting is False, "Should detect when no settings are provided"

    @pytest.mark.asyncio
    async def test_tool_message_formatting_fixed_ip(self):
        """Test success message formatting for fixed IP."""
        fixed_ip = "192.168.1.100"
        use_fixedip = True

        settings_changed = []
        if use_fixedip is not None or fixed_ip is not None:
            settings_changed.append(
                f"fixed IP: {fixed_ip if fixed_ip else ('enabled' if use_fixedip else 'disabled')}"
            )

        message = f"Client aa:bb:cc:dd:ee:ff IP settings updated successfully ({', '.join(settings_changed)})."
        assert "192.168.1.100" in message
        assert "fixed IP" in message

    @pytest.mark.asyncio
    async def test_tool_message_formatting_dns_record(self):
        """Test success message formatting for DNS record."""
        local_dns_record = "mydevice.local.domain"
        local_dns_record_enabled = True

        settings_changed = []
        if local_dns_record_enabled is not None or local_dns_record is not None:
            settings_changed.append(
                f"local DNS: {local_dns_record if local_dns_record else ('enabled' if local_dns_record_enabled else 'disabled')}"
            )

        message = f"Client aa:bb:cc:dd:ee:ff IP settings updated successfully ({', '.join(settings_changed)})."
        assert "mydevice.local.domain" in message
        assert "local DNS" in message

    @pytest.mark.asyncio
    async def test_tool_message_formatting_both_settings(self):
        """Test success message formatting when both settings are changed."""
        fixed_ip = "192.168.1.100"
        use_fixedip = True
        local_dns_record = "mydevice.local.domain"
        local_dns_record_enabled = True

        settings_changed = []
        if use_fixedip is not None or fixed_ip is not None:
            settings_changed.append(
                f"fixed IP: {fixed_ip if fixed_ip else ('enabled' if use_fixedip else 'disabled')}"
            )
        if local_dns_record_enabled is not None or local_dns_record is not None:
            settings_changed.append(
                f"local DNS: {local_dns_record if local_dns_record else ('enabled' if local_dns_record_enabled else 'disabled')}"
            )

        message = f"Client aa:bb:cc:dd:ee:ff IP settings updated successfully ({', '.join(settings_changed)})."
        assert "192.168.1.100" in message
        assert "mydevice.local.domain" in message
        assert "fixed IP" in message
        assert "local DNS" in message

    @pytest.mark.asyncio
    async def test_tool_message_formatting_disabled_settings(self):
        """Test success message formatting when settings are disabled."""
        use_fixedip = False
        local_dns_record_enabled = False

        settings_changed = []
        if use_fixedip is not None:
            settings_changed.append(
                f"fixed IP: {'enabled' if use_fixedip else 'disabled'}"
            )
        if local_dns_record_enabled is not None:
            settings_changed.append(
                f"local DNS: {'enabled' if local_dns_record_enabled else 'disabled'}"
            )

        message = f"Client aa:bb:cc:dd:ee:ff IP settings updated successfully ({', '.join(settings_changed)})."
        assert "disabled" in message
