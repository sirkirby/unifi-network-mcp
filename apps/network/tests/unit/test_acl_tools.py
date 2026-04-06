"""Tests for ACL rule tool functions.

Tests the source_macs/destination_macs convenience params and the
flattened-to-nested translation in create and update paths.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("UNIFI_HOST", "127.0.0.1")
os.environ.setdefault("UNIFI_USERNAME", "test")
os.environ.setdefault("UNIFI_PASSWORD", "test")


SAMPLE_RULE = {
    "_id": "rule001",
    "name": "Test Rule",
    "acl_index": 5,
    "action": "ALLOW",
    "enabled": True,
    "mac_acl_network_id": "net001",
    "traffic_source": {
        "type": "CLIENT_MAC",
        "specific_mac_addresses": ["aa:bb:cc:dd:ee:ff"],
        "ips_or_subnets": [],
        "network_ids": [],
        "ports": [],
    },
    "traffic_destination": {
        "type": "CLIENT_MAC",
        "specific_mac_addresses": [],
        "ips_or_subnets": [],
        "network_ids": [],
        "ports": [],
    },
}


class TestCreateAclRule:
    """Test create_acl_rule with convenience MAC params."""

    @pytest.mark.asyncio
    async def test_source_macs_builds_traffic_source(self):
        """source_macs param builds the nested traffic_source dict correctly."""
        with patch("unifi_network_mcp.tools.acl.acl_manager") as mock_mgr:
            mock_mgr.create_acl_rule = AsyncMock(return_value=SAMPLE_RULE)

            from unifi_network_mcp.tools.acl import create_acl_rule

            result = await create_acl_rule(
                name="Test",
                acl_index=5,
                action="ALLOW",
                mac_acl_network_id="net001",
                source_macs=["aa:bb:cc:dd:ee:ff"],
                destination_macs=[],
                confirm=True,
            )

        assert result["success"] is True
        # Verify the manager received the nested structure
        call_args = mock_mgr.create_acl_rule.call_args[0][0]
        assert call_args["traffic_source"]["specific_mac_addresses"] == ["aa:bb:cc:dd:ee:ff"]
        assert call_args["traffic_destination"]["specific_mac_addresses"] == []

    @pytest.mark.asyncio
    async def test_source_macs_overrides_traffic_source_dict(self):
        """source_macs takes precedence over traffic_source dict when both provided."""
        with patch("unifi_network_mcp.tools.acl.acl_manager") as mock_mgr:
            mock_mgr.create_acl_rule = AsyncMock(return_value=SAMPLE_RULE)

            from unifi_network_mcp.tools.acl import create_acl_rule

            result = await create_acl_rule(
                name="Test",
                acl_index=5,
                action="ALLOW",
                mac_acl_network_id="net001",
                source_macs=["11:22:33:44:55:66"],
                traffic_source={
                    "type": "CLIENT_MAC",
                    "specific_mac_addresses": ["aa:bb:cc:dd:ee:ff"],
                },
                confirm=True,
            )

        assert result["success"] is True
        call_args = mock_mgr.create_acl_rule.call_args[0][0]
        # source_macs wins over traffic_source
        assert call_args["traffic_source"]["specific_mac_addresses"] == ["11:22:33:44:55:66"]

    @pytest.mark.asyncio
    async def test_backward_compat_traffic_source_dict(self):
        """traffic_source dict still works when source_macs is not provided."""
        with patch("unifi_network_mcp.tools.acl.acl_manager") as mock_mgr:
            mock_mgr.create_acl_rule = AsyncMock(return_value=SAMPLE_RULE)

            from unifi_network_mcp.tools.acl import create_acl_rule

            result = await create_acl_rule(
                name="Test",
                acl_index=5,
                action="ALLOW",
                mac_acl_network_id="net001",
                traffic_source={
                    "type": "CLIENT_MAC",
                    "specific_mac_addresses": ["aa:bb:cc:dd:ee:ff"],
                    "ips_or_subnets": [],
                    "network_ids": [],
                    "ports": [],
                },
                confirm=True,
            )

        assert result["success"] is True
        call_args = mock_mgr.create_acl_rule.call_args[0][0]
        assert call_args["traffic_source"]["specific_mac_addresses"] == ["aa:bb:cc:dd:ee:ff"]

    @pytest.mark.asyncio
    async def test_no_macs_defaults_to_any(self):
        """Omitting both source_macs and traffic_source defaults to ANY (empty list)."""
        with patch("unifi_network_mcp.tools.acl.acl_manager") as mock_mgr:
            mock_mgr.create_acl_rule = AsyncMock(return_value=SAMPLE_RULE)

            from unifi_network_mcp.tools.acl import create_acl_rule

            result = await create_acl_rule(
                name="Block All",
                acl_index=99,
                action="BLOCK",
                mac_acl_network_id="net001",
                confirm=True,
            )

        assert result["success"] is True
        call_args = mock_mgr.create_acl_rule.call_args[0][0]
        assert call_args["traffic_source"]["specific_mac_addresses"] == []
        assert call_args["traffic_destination"]["specific_mac_addresses"] == []

    @pytest.mark.asyncio
    async def test_preview_includes_macs(self):
        """Preview mode shows the resolved MAC addresses in the rule data."""
        from unifi_network_mcp.tools.acl import create_acl_rule

        result = await create_acl_rule(
            name="Test Preview",
            acl_index=5,
            action="ALLOW",
            mac_acl_network_id="net001",
            source_macs=["aa:bb:cc:dd:ee:ff"],
            confirm=False,
        )

        assert result["success"] is True
        assert result.get("requires_confirmation") is True
        preview_data = result.get("preview", {}).get("will_create", {})
        assert preview_data["traffic_source"]["specific_mac_addresses"] == ["aa:bb:cc:dd:ee:ff"]


class TestUpdateAclRule:
    """Test update_acl_rule flattened field translation."""

    @pytest.mark.asyncio
    async def test_source_macs_translated_to_traffic_source(self):
        """source_macs in rule_data is translated to nested traffic_source before validation."""
        with patch("unifi_network_mcp.tools.acl.acl_manager") as mock_mgr:
            mock_mgr.get_acl_rule_by_id = AsyncMock(return_value=SAMPLE_RULE)
            mock_mgr.update_acl_rule = AsyncMock(return_value=True)

            from unifi_network_mcp.tools.acl import update_acl_rule

            result = await update_acl_rule(
                rule_id="rule001",
                rule_data={"source_macs": ["11:22:33:44:55:66"]},
                confirm=True,
            )

        assert result["success"] is True
        call_args = mock_mgr.update_acl_rule.call_args[0]
        update_data = call_args[1]
        assert "traffic_source" in update_data
        assert update_data["traffic_source"]["specific_mac_addresses"] == ["11:22:33:44:55:66"]
        assert "source_macs" not in update_data

    @pytest.mark.asyncio
    async def test_destination_macs_translated_to_traffic_destination(self):
        """destination_macs in rule_data is translated to nested traffic_destination."""
        with patch("unifi_network_mcp.tools.acl.acl_manager") as mock_mgr:
            mock_mgr.get_acl_rule_by_id = AsyncMock(return_value=SAMPLE_RULE)
            mock_mgr.update_acl_rule = AsyncMock(return_value=True)

            from unifi_network_mcp.tools.acl import update_acl_rule

            result = await update_acl_rule(
                rule_id="rule001",
                rule_data={"destination_macs": ["aa:bb:cc:dd:ee:ff"]},
                confirm=True,
            )

        assert result["success"] is True
        call_args = mock_mgr.update_acl_rule.call_args[0]
        update_data = call_args[1]
        assert "traffic_destination" in update_data
        assert update_data["traffic_destination"]["specific_mac_addresses"] == ["aa:bb:cc:dd:ee:ff"]
        assert "destination_macs" not in update_data
