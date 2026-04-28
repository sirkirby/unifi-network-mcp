"""Tests for the OonManager class.

This module tests OON (Object-Oriented Network) policy operations.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestOonManager:
    """Tests for the OonManager class."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock ConnectionManager."""
        conn = MagicMock()
        conn.site = "default"
        conn.request = AsyncMock()
        conn.get_cached = MagicMock(return_value=None)
        conn._update_cache = MagicMock()
        conn._invalidate_cache = MagicMock()
        conn.ensure_connected = AsyncMock(return_value=True)
        return conn

    @pytest.fixture
    def oon_manager(self, mock_connection):
        """Create an OonManager with mocked connection."""
        from unifi_core.network.managers.oon_manager import OonManager

        return OonManager(mock_connection)

    # ---- get_oon_policies ----

    @pytest.mark.asyncio
    async def test_get_oon_policies_returns_list(self, oon_manager, mock_connection):
        """Test get_oon_policies returns a list of policies."""
        mock_policies = [
            {"id": "p1", "name": "Bedtime", "enabled": True},
            {"id": "p2", "name": "App Block", "enabled": True},
        ]
        mock_connection.request.return_value = mock_policies

        policies = await oon_manager.get_oon_policies()

        assert len(policies) == 2
        assert policies[0]["name"] == "Bedtime"
        mock_connection._update_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_oon_policies_uses_cache(self, oon_manager, mock_connection):
        """Test get_oon_policies returns cached data when available."""
        cached = [{"id": "cached", "name": "Cached Policy"}]
        mock_connection.get_cached.return_value = cached

        policies = await oon_manager.get_oon_policies()

        assert policies == cached
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_oon_policies_handles_error(self, oon_manager, mock_connection):
        """Test get_oon_policies returns empty list on error."""
        mock_connection.request.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            await oon_manager.get_oon_policies()

    @pytest.mark.asyncio
    async def test_get_oon_policies_handles_404(self, oon_manager, mock_connection):
        """Test get_oon_policies returns empty list on 404 (unsupported controller)."""
        mock_connection.request.side_effect = Exception("404 Not Found")

        # 404 is a legitimate fallback path: returns empty list when the
        # controller does not support OON policies. Other errors raise.
        result = await oon_manager.get_oon_policies()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_oon_policies_not_connected(self, oon_manager, mock_connection):
        """Test get_oon_policies returns empty list when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await oon_manager.get_oon_policies()

        mock_connection.request.assert_not_called()

    # ---- get_oon_policy_by_id ----

    @pytest.mark.asyncio
    async def test_get_oon_policy_by_id_found(self, oon_manager, mock_connection):
        """Test get_oon_policy_by_id returns policy when found."""
        mock_connection.request.return_value = {"id": "p1", "name": "Test Policy"}

        policy = await oon_manager.get_oon_policy_by_id("p1")

        assert policy is not None
        assert policy["name"] == "Test Policy"

    @pytest.mark.asyncio
    async def test_get_oon_policy_by_id_not_connected(self, oon_manager, mock_connection):
        """Test get_oon_policy_by_id returns None when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await oon_manager.get_oon_policy_by_id("p1")

    @pytest.mark.asyncio
    async def test_get_oon_policy_by_id_handles_error(self, oon_manager, mock_connection):
        """Test get_oon_policy_by_id returns None on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await oon_manager.get_oon_policy_by_id("p1")

    # ---- create_oon_policy ----

    @pytest.mark.asyncio
    async def test_create_oon_policy_success(self, oon_manager, mock_connection):
        """Test create_oon_policy with valid data."""
        policy_data = {
            "name": "New Policy",
            "enabled": True,
            "target_type": "CLIENTS",
            "targets": ["aa:bb:cc:dd:ee:ff"],
        }
        mock_connection.request.return_value = {"id": "new1", **policy_data}

        result = await oon_manager.create_oon_policy(policy_data)

        assert result is not None
        assert result["id"] == "new1"
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_create_oon_policy_strips_id(self, oon_manager, mock_connection):
        """Test create_oon_policy strips _id and id from data."""
        policy_data = {"_id": "old1", "id": "old1", "name": "Test", "enabled": True}
        mock_connection.request.return_value = {"id": "new1", "name": "Test"}

        await oon_manager.create_oon_policy(policy_data)

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert "_id" not in api_request.data
        assert "id" not in api_request.data

    @pytest.mark.asyncio
    async def test_create_oon_policy_normalizes_client_targets(self, oon_manager, mock_connection):
        """Test create_oon_policy sends controller target objects."""
        policy_data = {
            "name": "Test",
            "enabled": False,
            "target_type": "CLIENTS",
            "targets": ["aa:bb:cc:dd:ee:ff", {"type": "MAC", "id": "11:22:33:44:55:66"}],
            "secure": {"enabled": False, "internet": {"mode": "TURN_OFF_INTERNET"}},
        }
        mock_connection.request.return_value = {"id": "new1", "name": "Test"}

        await oon_manager.create_oon_policy(policy_data)

        api_request = mock_connection.request.call_args[0][0]
        assert api_request.data["targets"] == [
            {"type": "MAC", "value": "aa:bb:cc:dd:ee:ff"},
            {"type": "MAC", "value": "11:22:33:44:55:66"},
        ]

    @pytest.mark.asyncio
    async def test_create_oon_policy_normalizes_group_targets(self, oon_manager, mock_connection):
        """Test create_oon_policy maps group IDs to network group targets."""
        policy_data = {
            "name": "Test",
            "enabled": False,
            "target_type": "GROUPS",
            "targets": ["group-1"],
            "secure": {"enabled": False, "internet": {"mode": "TURN_OFF_INTERNET"}},
        }
        mock_connection.request.return_value = {"id": "new1", "name": "Test"}

        await oon_manager.create_oon_policy(policy_data)

        api_request = mock_connection.request.call_args[0][0]
        assert api_request.data["targets"] == [{"type": "NETWORK_GROUP_ID", "value": "group-1"}]

    @pytest.mark.asyncio
    async def test_create_oon_policy_normalizes_secure_shorthand(self, oon_manager, mock_connection):
        """Test create_oon_policy sends required nested secure fields."""
        policy_data = {
            "name": "Test",
            "enabled": False,
            "target_type": "CLIENTS",
            "targets": ["aa:bb:cc:dd:ee:ff"],
            "secure": {"internet_access_enabled": False, "apps": []},
        }
        mock_connection.request.return_value = {"id": "new1", "name": "Test"}

        await oon_manager.create_oon_policy(policy_data)

        api_request = mock_connection.request.call_args[0][0]
        assert api_request.data["secure"] == {
            "enabled": True,
            "internet": {"mode": "TURN_OFF_INTERNET"},
        }

    @pytest.mark.asyncio
    async def test_create_oon_policy_disables_empty_secure_shorthand(self, oon_manager, mock_connection):
        """Test empty secure shorthand becomes a disabled draft config."""
        policy_data = {
            "name": "Test",
            "enabled": False,
            "target_type": "CLIENTS",
            "targets": ["aa:bb:cc:dd:ee:ff"],
            "secure": {"internet_access_enabled": True, "apps": []},
        }
        mock_connection.request.return_value = {"id": "new1", "name": "Test"}

        await oon_manager.create_oon_policy(policy_data)

        api_request = mock_connection.request.call_args[0][0]
        assert api_request.data["secure"] == {
            "enabled": False,
            "internet": {"mode": "TURN_OFF_INTERNET"},
        }

    @pytest.mark.asyncio
    async def test_create_oon_policy_missing_name(self, oon_manager, mock_connection):
        """Test create_oon_policy returns None when name is missing."""
        result = await oon_manager.create_oon_policy({"enabled": True})

        assert result is None
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_oon_policy_not_connected(self, oon_manager, mock_connection):
        """Test create_oon_policy returns None when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await oon_manager.create_oon_policy({"name": "Test"})

    @pytest.mark.asyncio
    async def test_create_oon_policy_handles_data_wrapper(self, oon_manager, mock_connection):
        """Test create_oon_policy handles response with data key."""
        mock_connection.request.return_value = {"data": {"id": "new1", "name": "Test"}}

        result = await oon_manager.create_oon_policy({"name": "Test"})

        assert result == {"id": "new1", "name": "Test"}

    @pytest.mark.asyncio
    async def test_create_oon_policy_handles_error(self, oon_manager, mock_connection):
        """Test create_oon_policy returns None on API error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await oon_manager.create_oon_policy({"name": "Test"})

    # ---- update_oon_policy ----

    @pytest.mark.asyncio
    async def test_update_oon_policy_success(self, oon_manager, mock_connection):
        """Test update_oon_policy with valid data."""
        existing = {"id": "p1", "name": "Original", "enabled": True}
        mock_connection.request.side_effect = [
            existing,  # GET
            {},  # PUT
        ]

        result = await oon_manager.update_oon_policy("p1", {"name": "Updated"})

        assert result is True
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_update_oon_policy_not_connected(self, oon_manager, mock_connection):
        """Test update_oon_policy returns False when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await oon_manager.update_oon_policy("p1", {"name": "Test"})

    @pytest.mark.asyncio
    async def test_update_oon_policy_handles_error(self, oon_manager, mock_connection):
        """Test update_oon_policy returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await oon_manager.update_oon_policy("p1", {"name": "Test"})

    @pytest.mark.asyncio
    async def test_update_oon_policy_fetches_and_merges(self, oon_manager, mock_connection):
        """Test update_oon_policy fetches current policy, merges, PUTs full object."""
        existing_policy = {
            "id": "p1",
            "name": "Kids Bedtime",
            "enabled": True,
            "target_type": "CLIENTS",
            "targets": ["aa:bb:cc:dd:ee:ff"],
            "secure": {"internet_access_enabled": True},
            "qos": {"mode": "OFF"},
            "route": {"mode": "OFF"},
        }
        mock_connection.request.side_effect = [
            existing_policy,  # GET
            {},  # PUT
        ]

        result = await oon_manager.update_oon_policy("p1", {"name": "Kids Bedtime v2", "enabled": False})

        assert result is True
        put_call = mock_connection.request.call_args_list[1]
        put_request = put_call[0][0]
        assert put_request.method == "put"
        assert put_request.data["name"] == "Kids Bedtime v2"
        assert put_request.data["enabled"] is False
        assert put_request.data["targets"] == ["aa:bb:cc:dd:ee:ff"]
        assert put_request.data["secure"] == {"internet_access_enabled": True}

    @pytest.mark.asyncio
    async def test_update_oon_policy_not_found(self, oon_manager, mock_connection):
        """Test update_oon_policy returns False when policy not found."""
        mock_connection.request.side_effect = Exception("Not found")

        with pytest.raises(Exception):
            await oon_manager.update_oon_policy("nonexistent", {"name": "Test"})

    @pytest.mark.asyncio
    async def test_update_oon_policy_empty_update(self, oon_manager, mock_connection):
        """Test update_oon_policy with empty data is a no-op."""
        result = await oon_manager.update_oon_policy("p1", {})

        assert result is True
        mock_connection.request.assert_not_called()

    # ---- toggle_oon_policy ----

    @pytest.mark.asyncio
    async def test_toggle_oon_policy_enables(self, oon_manager, mock_connection):
        """Test toggle_oon_policy enables a disabled policy."""
        mock_connection.request.side_effect = [
            {"id": "p1", "name": "Test", "enabled": False},  # get
            {},  # put
        ]

        result = await oon_manager.toggle_oon_policy("p1")

        assert result is True

    @pytest.mark.asyncio
    async def test_toggle_oon_policy_disables(self, oon_manager, mock_connection):
        """Test toggle_oon_policy disables an enabled policy."""
        mock_connection.request.side_effect = [
            {"id": "p1", "name": "Test", "enabled": True},  # get
            {},  # put
        ]

        result = await oon_manager.toggle_oon_policy("p1")

        assert result is False

    @pytest.mark.asyncio
    async def test_toggle_oon_policy_not_connected(self, oon_manager, mock_connection):
        """Test toggle_oon_policy returns None when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await oon_manager.toggle_oon_policy("p1")

        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_toggle_oon_policy_not_found(self, oon_manager, mock_connection):
        """Test toggle_oon_policy returns None when policy not found."""
        mock_connection.request.return_value = None

        result = await oon_manager.toggle_oon_policy("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_toggle_oon_policy_invalidates_cache(self, oon_manager, mock_connection):
        """Test toggle_oon_policy invalidates cache."""
        mock_connection.request.side_effect = [
            {"id": "p1", "enabled": True},
            {},
        ]

        await oon_manager.toggle_oon_policy("p1")

        mock_connection._invalidate_cache.assert_called()

    # ---- delete_oon_policy ----

    @pytest.mark.asyncio
    async def test_delete_oon_policy_success(self, oon_manager, mock_connection):
        """Test delete_oon_policy with valid ID."""
        mock_connection.request.return_value = {}

        result = await oon_manager.delete_oon_policy("p1")

        assert result is True
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_delete_oon_policy_not_connected(self, oon_manager, mock_connection):
        """Test delete_oon_policy returns False when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await oon_manager.delete_oon_policy("p1")

    @pytest.mark.asyncio
    async def test_delete_oon_policy_handles_error(self, oon_manager, mock_connection):
        """Test delete_oon_policy returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await oon_manager.delete_oon_policy("p1")

    # ---- API path verification ----

    @pytest.mark.asyncio
    async def test_list_uses_plural_path(self, oon_manager, mock_connection):
        """Test get_oon_policies uses plural path."""
        mock_connection.request.return_value = []

        await oon_manager.get_oon_policies()

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/object-oriented-network-configs"

    @pytest.mark.asyncio
    async def test_get_by_id_uses_singular_path(self, oon_manager, mock_connection):
        """Test get_oon_policy_by_id uses singular path."""
        mock_connection.request.return_value = {"id": "p1"}

        await oon_manager.get_oon_policy_by_id("p1")

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/object-oriented-network-config/p1"

    @pytest.mark.asyncio
    async def test_create_uses_singular_path(self, oon_manager, mock_connection):
        """Test create_oon_policy uses singular POST path."""
        mock_connection.request.return_value = {"id": "new1"}

        await oon_manager.create_oon_policy({"name": "Test"})

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/object-oriented-network-config"
        assert api_request.method == "post"

    @pytest.mark.asyncio
    async def test_update_uses_singular_path(self, oon_manager, mock_connection):
        """Test update_oon_policy uses singular PUT path."""
        existing = {"id": "p1", "name": "Original"}
        mock_connection.request.side_effect = [
            existing,  # GET
            {},  # PUT
        ]

        await oon_manager.update_oon_policy("p1", {"name": "Updated"})

        put_call = mock_connection.request.call_args_list[1]
        api_request = put_call[0][0]
        assert api_request.path == "/object-oriented-network-config/p1"
        assert api_request.method == "put"

    @pytest.mark.asyncio
    async def test_delete_uses_singular_path(self, oon_manager, mock_connection):
        """Test delete_oon_policy uses singular DELETE path."""
        mock_connection.request.return_value = {}

        await oon_manager.delete_oon_policy("p1")

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/object-oriented-network-config/p1"
        assert api_request.method == "delete"
