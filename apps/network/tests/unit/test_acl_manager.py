"""Tests for the AclManager class.

This module tests MAC ACL rule operations (Policy Engine).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestAclManager:
    """Tests for the AclManager class."""

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
    def acl_manager(self, mock_connection):
        """Create an AclManager with mocked connection."""
        from unifi_network_mcp.managers.acl_manager import AclManager

        return AclManager(mock_connection)

    # ---- get_acl_rules ----

    @pytest.mark.asyncio
    async def test_get_acl_rules_returns_list(self, acl_manager, mock_connection):
        """Test get_acl_rules returns a list of rules."""
        mock_rules = [
            {"_id": "r1", "name": "Allow A", "action": "ALLOW", "mac_acl_network_id": "net1"},
            {"_id": "r2", "name": "Block All", "action": "BLOCK", "mac_acl_network_id": "net1"},
        ]
        mock_connection.request.return_value = mock_rules

        rules = await acl_manager.get_acl_rules()

        assert len(rules) == 2
        assert rules[0]["name"] == "Allow A"
        mock_connection._update_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_acl_rules_filters_by_network(self, acl_manager, mock_connection):
        """Test get_acl_rules filters by network_id."""
        mock_rules = [
            {"_id": "r1", "name": "Rule Net1", "mac_acl_network_id": "net1"},
            {"_id": "r2", "name": "Rule Net2", "mac_acl_network_id": "net2"},
            {"_id": "r3", "name": "Rule Net1 Again", "mac_acl_network_id": "net1"},
        ]
        mock_connection.request.return_value = mock_rules

        rules = await acl_manager.get_acl_rules(network_id="net1")

        assert len(rules) == 2
        assert all(r["mac_acl_network_id"] == "net1" for r in rules)

    @pytest.mark.asyncio
    async def test_get_acl_rules_uses_cache(self, acl_manager, mock_connection):
        """Test get_acl_rules returns cached data when available."""
        cached = [{"_id": "cached", "name": "Cached Rule"}]
        mock_connection.get_cached.return_value = cached

        rules = await acl_manager.get_acl_rules()

        assert rules == cached
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_acl_rules_handles_error(self, acl_manager, mock_connection):
        """Test get_acl_rules returns empty list on error."""
        mock_connection.request.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            await acl_manager.get_acl_rules()

    @pytest.mark.asyncio
    async def test_get_acl_rules_not_connected(self, acl_manager, mock_connection):
        """Test get_acl_rules returns empty list when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await acl_manager.get_acl_rules()

        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_acl_rules_handles_dict_response(self, acl_manager, mock_connection):
        """Test get_acl_rules handles dict response with data key."""
        mock_connection.request.return_value = {"data": [{"_id": "r1", "name": "Rule"}]}

        rules = await acl_manager.get_acl_rules()

        assert len(rules) == 1

    # ---- get_acl_rule_by_id ----

    @pytest.mark.asyncio
    async def test_get_acl_rule_by_id_found(self, acl_manager, mock_connection):
        """Test get_acl_rule_by_id returns rule when found via list-then-filter."""
        mock_connection.request.return_value = [
            {"_id": "r1", "name": "Test Rule"},
            {"_id": "r2", "name": "Other Rule"},
        ]

        rule = await acl_manager.get_acl_rule_by_id("r1")

        assert rule is not None
        assert rule["name"] == "Test Rule"

    @pytest.mark.asyncio
    async def test_get_acl_rule_by_id_not_found(self, acl_manager, mock_connection):
        """Test get_acl_rule_by_id returns None when ID not in list."""
        mock_connection.request.return_value = [{"_id": "r1", "name": "Test Rule"}]

        rule = await acl_manager.get_acl_rule_by_id("nonexistent")

        assert rule is None

    @pytest.mark.asyncio
    async def test_get_acl_rule_by_id_not_connected(self, acl_manager, mock_connection):
        """Test get_acl_rule_by_id returns None when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await acl_manager.get_acl_rule_by_id("r1")

    @pytest.mark.asyncio
    async def test_get_acl_rule_by_id_handles_error(self, acl_manager, mock_connection):
        """Test get_acl_rule_by_id returns None on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await acl_manager.get_acl_rule_by_id("r1")

    # ---- create_acl_rule ----

    @pytest.mark.asyncio
    async def test_create_acl_rule_success(self, acl_manager, mock_connection):
        """Test create_acl_rule with valid data."""
        rule_data = {
            "name": "New Rule",
            "acl_index": 5,
            "action": "ALLOW",
            "mac_acl_network_id": "net1",
            "type": "MAC",
            "traffic_source": {"type": "CLIENT_MAC", "specific_mac_addresses": ["aa:bb:cc:dd:ee:ff"]},
            "traffic_destination": {"type": "CLIENT_MAC", "specific_mac_addresses": []},
        }
        mock_connection.request.return_value = {"_id": "new1", **rule_data}

        result = await acl_manager.create_acl_rule(rule_data)

        assert result is not None
        assert result["_id"] == "new1"
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_create_acl_rule_missing_required_keys(self, acl_manager, mock_connection):
        """Test create_acl_rule returns None when required keys are missing."""
        result = await acl_manager.create_acl_rule({"name": "Incomplete"})

        assert result is None
        mock_connection.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_acl_rule_not_connected(self, acl_manager, mock_connection):
        """Test create_acl_rule returns None when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(Exception):
            await acl_manager.create_acl_rule(
                {
                    "name": "Test",
                    "acl_index": 0,
                    "action": "ALLOW",
                    "mac_acl_network_id": "net1",
                    "type": "MAC",
                }
            )

    @pytest.mark.asyncio
    async def test_create_acl_rule_handles_error(self, acl_manager, mock_connection):
        """Test create_acl_rule returns None on API error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await acl_manager.create_acl_rule(
                {
                    "name": "Test",
                    "acl_index": 0,
                    "action": "ALLOW",
                    "mac_acl_network_id": "net1",
                    "type": "MAC",
                }
            )

    @pytest.mark.asyncio
    async def test_create_acl_rule_handles_data_wrapper(self, acl_manager, mock_connection):
        """Test create_acl_rule handles response with data key."""
        mock_connection.request.return_value = {"data": {"_id": "new1", "name": "Test"}}

        result = await acl_manager.create_acl_rule(
            {
                "name": "Test",
                "acl_index": 0,
                "action": "ALLOW",
                "mac_acl_network_id": "net1",
                "type": "MAC",
            }
        )

        assert result == {"_id": "new1", "name": "Test"}

    # ---- update_acl_rule ----

    @pytest.mark.asyncio
    async def test_update_acl_rule_success(self, acl_manager, mock_connection):
        """Test update_acl_rule with valid data."""
        existing_rule = {"_id": "r1", "name": "Original"}
        mock_connection.request.side_effect = [
            [existing_rule],  # LIST (for get_acl_rule_by_id)
            {},  # PUT (update)
        ]

        result = await acl_manager.update_acl_rule("r1", {"_id": "r1", "name": "Updated"})

        assert result is True
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_update_acl_rule_not_connected(self, acl_manager, mock_connection):
        """Test update_acl_rule returns False when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await acl_manager.update_acl_rule("r1", {"name": "Test"})

    @pytest.mark.asyncio
    async def test_update_acl_rule_handles_error(self, acl_manager, mock_connection):
        """Test update_acl_rule returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await acl_manager.update_acl_rule("r1", {"name": "Test"})

    @pytest.mark.asyncio
    async def test_update_acl_rule_fetches_and_merges(self, acl_manager, mock_connection):
        """Test update_acl_rule fetches current rule, merges updates, PUTs full object."""
        existing_rule = {
            "_id": "r1",
            "name": "Original",
            "acl_index": 5,
            "action": "ALLOW",
            "enabled": True,
            "mac_acl_network_id": "net1",
            "type": "MAC",
            "traffic_source": {"type": "CLIENT_MAC", "specific_mac_addresses": []},
            "traffic_destination": {"type": "CLIENT_MAC", "specific_mac_addresses": []},
        }
        mock_connection.request.side_effect = [
            [existing_rule],  # LIST (for get_acl_rule_by_id)
            {},  # PUT (update)
        ]

        result = await acl_manager.update_acl_rule("r1", {"name": "Renamed", "enabled": False})

        assert result is True
        # Verify PUT was called with merged data
        put_call = mock_connection.request.call_args_list[1]
        put_request = put_call[0][0]
        assert put_request.method == "put"
        assert put_request.data["name"] == "Renamed"
        assert put_request.data["enabled"] is False
        # Original fields preserved
        assert put_request.data["acl_index"] == 5
        assert put_request.data["action"] == "ALLOW"
        assert put_request.data["mac_acl_network_id"] == "net1"

    @pytest.mark.asyncio
    async def test_update_acl_rule_not_found(self, acl_manager, mock_connection):
        """Test update_acl_rule returns False when rule not found."""
        mock_connection.request.return_value = []

        result = await acl_manager.update_acl_rule("nonexistent", {"name": "Test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_update_acl_rule_empty_update(self, acl_manager, mock_connection):
        """Test update_acl_rule with empty update data returns True (no-op)."""
        result = await acl_manager.update_acl_rule("r1", {})

        assert result is True
        mock_connection.request.assert_not_called()

    # ---- delete_acl_rule ----

    @pytest.mark.asyncio
    async def test_delete_acl_rule_success(self, acl_manager, mock_connection):
        """Test delete_acl_rule with valid ID."""
        mock_connection.request.return_value = {}

        result = await acl_manager.delete_acl_rule("r1")

        assert result is True
        mock_connection._invalidate_cache.assert_called()

    @pytest.mark.asyncio
    async def test_delete_acl_rule_not_connected(self, acl_manager, mock_connection):
        """Test delete_acl_rule returns False when not connected."""
        mock_connection.ensure_connected.return_value = False

        with pytest.raises(ConnectionError, match="Not connected to controller"):
            await acl_manager.delete_acl_rule("r1")

    @pytest.mark.asyncio
    async def test_delete_acl_rule_handles_error(self, acl_manager, mock_connection):
        """Test delete_acl_rule returns False on error."""
        mock_connection.request.side_effect = Exception("API error")

        with pytest.raises(Exception):
            await acl_manager.delete_acl_rule("r1")

    # ---- API path verification ----

    @pytest.mark.asyncio
    async def test_list_uses_correct_path(self, acl_manager, mock_connection):
        """Test get_acl_rules calls the correct API endpoint."""
        mock_connection.request.return_value = []

        await acl_manager.get_acl_rules()

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/acl-rules"

    @pytest.mark.asyncio
    async def test_get_by_id_uses_list_endpoint(self, acl_manager, mock_connection):
        """Test get_acl_rule_by_id uses list-then-filter (GET /acl-rules/{id} returns 405)."""
        mock_connection.request.return_value = [{"_id": "r1"}]

        await acl_manager.get_acl_rule_by_id("r1")

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/acl-rules"

    @pytest.mark.asyncio
    async def test_create_uses_correct_path_and_method(self, acl_manager, mock_connection):
        """Test create_acl_rule uses POST to the correct endpoint."""
        mock_connection.request.return_value = {"_id": "new1"}

        await acl_manager.create_acl_rule(
            {
                "name": "Test",
                "acl_index": 0,
                "action": "ALLOW",
                "mac_acl_network_id": "net1",
                "type": "MAC",
            }
        )

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/acl-rules"
        assert api_request.method == "post"

    @pytest.mark.asyncio
    async def test_update_uses_correct_path_and_method(self, acl_manager, mock_connection):
        """Test update_acl_rule uses PUT to the correct endpoint."""
        existing_rule = {"_id": "r1", "name": "Original"}
        mock_connection.request.side_effect = [
            [existing_rule],  # LIST (for get_acl_rule_by_id)
            {},  # PUT (update)
        ]

        await acl_manager.update_acl_rule("r1", {"name": "Updated"})

        # call_args returns the most recent call, which is the PUT
        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/acl-rules/r1"
        assert api_request.method == "put"

    @pytest.mark.asyncio
    async def test_delete_uses_correct_path_and_method(self, acl_manager, mock_connection):
        """Test delete_acl_rule uses DELETE to the correct endpoint."""
        mock_connection.request.return_value = {}

        await acl_manager.delete_acl_rule("r1")

        call_args = mock_connection.request.call_args
        api_request = call_args[0][0]
        assert api_request.path == "/acl-rules/r1"
        assert api_request.method == "delete"
