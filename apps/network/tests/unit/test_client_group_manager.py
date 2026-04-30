"""Tests for the ClientGroupManager class.

This module tests client group (network member group) operations.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestClientGroupManager:
    """Tests for the ClientGroupManager class."""

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
    def client_group_manager(self, mock_connection):
        """Create a ClientGroupManager with mocked connection."""
        from unifi_core.network.managers.client_group_manager import ClientGroupManager

        return ClientGroupManager(mock_connection)

    # ---- get_client_groups ----

    @pytest.mark.asyncio
    async def test_get_client_groups_returns_list(self, client_group_manager, mock_connection):
        """Test get_client_groups returns a list of groups."""
        mock_groups = [
            {"id": "g1", "name": "Kids Everything", "type": "CLIENTS", "members": ["aa:bb:cc:dd:ee:ff"]},
            {"id": "g2", "name": "Adults", "type": "CLIENTS", "members": ["11:22:33:44:55:66"]},
        ]
        mock_connection.request.return_value = mock_groups

        groups = await client_group_manager.get_client_groups()

        assert len(groups) == 2
        assert groups[0]["name"] == "Kids Everything"
        mock_connection._update_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_groups_uses_cache(self, client_group_manager, mock_connection):
        """Test get_client_groups returns cached data when available."""
        cached = [{"id": "cached", "name": "Cached Group"}]
        mock_connection.get_cached.return_value = cached

        groups = await client_group_manager.get_client_groups()

        assert groups == cached
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_client_groups_handles_error(self, client_group_manager, mock_connection):
        """Test get_client_groups returns empty list on error."""
        mock_connection.request.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            await client_group_manager.get_client_groups()

    @pytest.mark.asyncio
    async def test_get_client_groups_not_connected(self, client_group_manager, mock_connection):
        """Test get_client_groups returns empty list when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await client_group_manager.get_client_groups()

        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_client_groups_handles_dict_response(self, client_group_manager, mock_connection):
        """Test get_client_groups handles dict response with data key."""
        mock_connection.request.return_value = {"data": [{"id": "g1", "name": "Group"}]}

        groups = await client_group_manager.get_client_groups()

        assert len(groups) == 1

    # ---- get_client_group_by_id ----

    @pytest.mark.asyncio
    async def test_get_client_group_by_id_found(self, client_group_manager, mock_connection):
        """Test get_client_group_by_id returns group when found."""
        mock_connection.request.return_value = {"id": "g1", "name": "Test Group", "members": []}

        group = await client_group_manager.get_client_group_by_id("g1")

        assert group is not None
        assert group["name"] == "Test Group"

    @pytest.mark.asyncio
    async def test_get_client_group_by_id_not_connected(self, client_group_manager, mock_connection):
        """Test get_client_group_by_id returns None when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await client_group_manager.get_client_group_by_id("g1")

    @pytest.mark.asyncio
    async def test_get_client_group_by_id_handles_error(self, client_group_manager, mock_connection):
        """Test get_client_group_by_id returns None on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await client_group_manager.get_client_group_by_id("g1")

    # ---- create_client_group ----

    @pytest.mark.asyncio
    async def test_create_client_group_success(self, client_group_manager, mock_connection):
        """Test create_client_group with valid data."""
        group_data = {
            "name": "New Group",
            "members": ["aa:bb:cc:dd:ee:ff"],
            "type": "CLIENTS",
        }
        mock_connection.request.return_value = {"id": "new1", **group_data}

        result = await client_group_manager.create_client_group(group_data)

        assert result is not None
        assert result["id"] == "new1"
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_create_client_group_missing_required_keys(self, client_group_manager, mock_connection):
        """Test create_client_group returns None when required keys are missing."""
        result = await client_group_manager.create_client_group({"name": "Incomplete"})

        assert result is None
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_client_group_not_connected(self, client_group_manager, mock_connection):
        """Test create_client_group returns None when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(Exception):
            await client_group_manager.create_client_group(
                {
                    "name": "Test",
                    "members": [],
                    "type": "CLIENTS",
                }
            )

    @pytest.mark.asyncio
    async def test_create_client_group_handles_error(self, client_group_manager, mock_connection):
        """Test create_client_group returns None on API error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await client_group_manager.create_client_group(
                {
                    "name": "Test",
                    "members": [],
                    "type": "CLIENTS",
                }
            )

    @pytest.mark.asyncio
    async def test_create_client_group_handles_data_wrapper(self, client_group_manager, mock_connection):
        """Test create_client_group handles response with data key."""
        mock_connection.request.return_value = {"data": {"id": "new1", "name": "Test"}}

        result = await client_group_manager.create_client_group(
            {
                "name": "Test",
                "members": [],
                "type": "CLIENTS",
            }
        )

        assert result == {"id": "new1", "name": "Test"}

    # ---- update_client_group ----

    @pytest.mark.asyncio
    async def test_update_client_group_success(self, client_group_manager, mock_connection):
        """Test update_client_group with valid data."""
        existing = {"id": "g1", "name": "Original", "members": [], "type": "CLIENTS"}
        mock_connection.request.side_effect = [
            existing,  # GET
            {},  # PUT
        ]

        result = await client_group_manager.update_client_group("g1", {"name": "Updated"})

        assert result["name"] == "Updated"
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_update_client_group_not_connected(self, client_group_manager, mock_connection):
        """Test update_client_group returns False when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await client_group_manager.update_client_group("g1", {"name": "Test"})

    @pytest.mark.asyncio
    async def test_update_client_group_handles_error(self, client_group_manager, mock_connection):
        """Test update_client_group returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await client_group_manager.update_client_group("g1", {"name": "Test"})

    @pytest.mark.asyncio
    async def test_update_client_group_fetches_and_merges(self, client_group_manager, mock_connection):
        """Test update_client_group fetches current group, merges, PUTs full object."""
        existing_group = {
            "id": "g1",
            "name": "IoT Devices",
            "members": ["aa:bb:cc:dd:ee:ff"],
            "type": "CLIENTS",
        }
        mock_connection.request.side_effect = [
            existing_group,  # GET
            {},  # PUT
        ]

        result = await client_group_manager.update_client_group("g1", {"name": "Smart Home Devices"})

        assert result["name"] == "Smart Home Devices"
        put_call = mock_connection.request.call_args_list[1]
        put_request = put_call[0][0]
        assert put_request.method == "put"
        assert put_request.data["name"] == "Smart Home Devices"
        assert put_request.data["members"] == ["aa:bb:cc:dd:ee:ff"]
        assert put_request.data["type"] == "CLIENTS"

    @pytest.mark.asyncio
    async def test_update_client_group_not_found(self, client_group_manager, mock_connection):
        """Test update_client_group raises UniFiNotFoundError when group missing."""
        from unifi_core.exceptions import UniFiNotFoundError

        # First call: by-id GET → None; second call: list fallback also empty.
        mock_connection.request.side_effect = [None, []]

        with pytest.raises(UniFiNotFoundError):
            await client_group_manager.update_client_group("nonexistent", {"name": "Test"})

    @pytest.mark.asyncio
    async def test_update_client_group_empty_update(self, client_group_manager, mock_connection):
        """Test update_client_group with empty data returns existing without PUT."""
        existing = {"id": "g1", "name": "Original"}
        mock_connection.request.return_value = existing

        result = await client_group_manager.update_client_group("g1", {})

        assert result == existing
        # Only the GET (existence check) ran; no PUT.
        assert mock_connection.request.call_count == 1

    # ---- delete_client_group ----

    @pytest.mark.asyncio
    async def test_delete_client_group_success(self, client_group_manager, mock_connection):
        """Test delete_client_group with valid ID."""
        mock_connection.request.return_value = {}

        result = await client_group_manager.delete_client_group("g1")

        assert result is True
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_delete_client_group_not_connected(self, client_group_manager, mock_connection):
        """Test delete_client_group returns False when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await client_group_manager.delete_client_group("g1")

    @pytest.mark.asyncio
    async def test_delete_client_group_handles_error(self, client_group_manager, mock_connection):
        """Test delete_client_group returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await client_group_manager.delete_client_group("g1")

    # ---- API path verification ----

    @pytest.mark.asyncio
    async def test_list_uses_correct_path(self, client_group_manager, mock_connection):
        """Test get_client_groups calls the correct API endpoint."""
        mock_connection.request.return_value = []

        await client_group_manager.get_client_groups()

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/network-members-groups"

    @pytest.mark.asyncio
    async def test_get_by_id_uses_correct_path(self, client_group_manager, mock_connection):
        """Test get_client_group_by_id calls the correct API endpoint."""
        mock_connection.request.return_value = {"id": "g1"}

        await client_group_manager.get_client_group_by_id("g1")

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/network-members-group/g1"

    @pytest.mark.asyncio
    async def test_create_uses_correct_path_and_method(self, client_group_manager, mock_connection):
        """Test create_client_group uses POST to the correct endpoint."""
        mock_connection.request.return_value = {"id": "new1"}

        await client_group_manager.create_client_group(
            {
                "name": "Test",
                "members": [],
                "type": "CLIENTS",
            }
        )

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/network-members-group"
        assert api_request.method == "post"

    @pytest.mark.asyncio
    async def test_update_uses_correct_path_and_method(self, client_group_manager, mock_connection):
        """Test update_client_group uses PUT to the correct endpoint."""
        existing = {"id": "g1", "name": "Original", "members": [], "type": "CLIENTS"}
        mock_connection.request.side_effect = [
            existing,  # GET
            {},  # PUT
        ]

        await client_group_manager.update_client_group("g1", {"name": "Updated"})

        put_call = mock_connection.request.call_args_list[1]
        api_request = put_call[0][0]
        assert api_request.path == "/network-members-group/g1"
        assert api_request.method == "put"

    @pytest.mark.asyncio
    async def test_delete_uses_correct_path_and_method(self, client_group_manager, mock_connection):
        """Test delete_client_group uses DELETE to the correct endpoint."""
        mock_connection.request.return_value = {}

        await client_group_manager.delete_client_group("g1")

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/network-members-group/g1"
        assert api_request.method == "delete"
