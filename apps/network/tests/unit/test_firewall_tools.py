"""Tests for firewall tool enhancements: zone-based targeting, auto-detection, and delete tool."""

import copy
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("UNIFI_HOST", "127.0.0.1")
os.environ.setdefault("UNIFI_USERNAME", "test")
os.environ.setdefault("UNIFI_PASSWORD", "test")


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_LEGACY_POLICY_RAW = {
    "_id": "pol_legacy_001",
    "name": "Block Xbox LAN Out",
    "enabled": True,
    "action": "drop",
    "index": 2010,
    "ruleset": "LAN_OUT",
    "description": "Block Xbox from WAN",
    "predefined": False,
}

SAMPLE_ZONE_POLICY_RAW = {
    "_id": "pol_zone_001",
    "name": "Allow IoT to HomeAssistant",
    "enabled": True,
    "action": "ALLOW",
    "index": 3000,
    "predefined": False,
    "protocol": "all",
    "ip_version": "BOTH",
    "logging": False,
    "connection_state_type": "ALL",
    "source": {
        "zone_id": "internal-zone-id",
        "matching_target": "NETWORK",
        "matching_target_type": "OBJECT",
        "network_ids": ["iot-network-id"],
    },
    "destination": {
        "zone_id": "internal-zone-id",
        "matching_target": "IP",
        "matching_target_type": "SPECIFIC",
        "ips": ["192.168.1.100"],
    },
}


def _make_policy(raw: dict):
    """Create a mock FirewallPolicy with the given raw dict."""
    policy = MagicMock()
    policy.raw = copy.deepcopy(raw)
    policy.id = raw["_id"]
    policy.enabled = raw.get("enabled", True)
    policy.predefined = raw.get("predefined", False)
    return policy


# ---------------------------------------------------------------------------
# list_firewall_policies — v2 targeting fields
# ---------------------------------------------------------------------------


class TestListFirewallPolicies:
    """Test that list_firewall_policies includes zone-based targeting fields."""

    @pytest.mark.asyncio
    async def test_legacy_policy_includes_ruleset(self):
        """Legacy policies with ruleset should include it in the output."""
        mock_policy = _make_policy(SAMPLE_LEGACY_POLICY_RAW)
        mock_conn = MagicMock()
        mock_conn.site = "default"

        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.get_firewall_policies = AsyncMock(return_value=[mock_policy])
            mock_fm._connection = mock_conn

            from unifi_network_mcp.tools.firewall import list_firewall_policies

            result = await list_firewall_policies(include_predefined=False)

        assert result["success"] is True
        assert result["count"] == 1
        policy = result["policies"][0]
        assert policy["ruleset"] == "LAN_OUT"
        assert "source" not in policy
        assert "destination" not in policy

    @pytest.mark.asyncio
    async def test_zone_policy_includes_targeting(self):
        """Zone-based policies should include source/destination targeting details."""
        mock_policy = _make_policy(SAMPLE_ZONE_POLICY_RAW)
        mock_conn = MagicMock()
        mock_conn.site = "default"

        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.get_firewall_policies = AsyncMock(return_value=[mock_policy])
            mock_fm._connection = mock_conn

            from unifi_network_mcp.tools.firewall import list_firewall_policies

            result = await list_firewall_policies(include_predefined=False)

        assert result["success"] is True
        policy = result["policies"][0]
        # Should NOT have ruleset (zone-based policy)
        assert "ruleset" not in policy
        # Should have source/destination targeting
        assert policy["source"]["zone_id"] == "internal-zone-id"
        assert policy["source"]["matching_target"] == "NETWORK"
        assert policy["source"]["matching_target_type"] == "OBJECT"
        assert policy["source"]["network_ids"] == ["iot-network-id"]
        assert policy["destination"]["matching_target"] == "IP"
        assert policy["destination"]["ips"] == ["192.168.1.100"]


# ---------------------------------------------------------------------------
# create_firewall_policy — auto-detection
# ---------------------------------------------------------------------------


class TestCreateFirewallPolicyAutoDetect:
    """Test that create_firewall_policy auto-detects legacy vs zone-based format."""

    @pytest.mark.asyncio
    async def test_legacy_format_detected_by_ruleset(self):
        """Policy with 'ruleset' key should use legacy schema validation."""
        legacy_data = {
            "name": "Test Block",
            "ruleset": "LAN_OUT",
            "action": "drop",
            "index": 2000,
        }
        created_raw = {**legacy_data, "_id": "new_001"}
        mock_created = MagicMock()
        mock_created.raw = created_raw

        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.create_firewall_policy = AsyncMock(return_value=mock_created)

            from unifi_network_mcp.tools.firewall import create_firewall_policy

            result = await create_firewall_policy(policy_data=legacy_data, confirm=True)

        assert result["success"] is True
        assert result["policy_id"] == "new_001"

    @pytest.mark.asyncio
    async def test_zone_format_detected_by_source_zone_id(self):
        """Policy with source/destination zone_id should use v2 schema validation."""
        zone_data = {
            "name": "Allow IoT",
            "action": "ALLOW",
            "source": {
                "zone_id": "internal",
                "matching_target": "ANY",
            },
            "destination": {
                "zone_id": "internal",
                "matching_target": "IP",
                "matching_target_type": "SPECIFIC",
                "ips": ["10.0.0.1"],
            },
        }
        created_raw = {**zone_data, "_id": "new_002"}
        mock_created = MagicMock()
        mock_created.raw = created_raw

        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.create_firewall_policy = AsyncMock(return_value=mock_created)

            from unifi_network_mcp.tools.firewall import create_firewall_policy

            result = await create_firewall_policy(policy_data=zone_data, confirm=True)

        assert result["success"] is True
        assert result["policy_id"] == "new_002"

    @pytest.mark.asyncio
    async def test_zone_format_detected_by_uppercase_action(self):
        """Uppercase ALLOW/BLOCK/REJECT action should trigger zone-based detection."""
        zone_data = {
            "name": "Block Zone",
            "action": "BLOCK",
            "source": {"zone_id": "internal", "matching_target": "ANY"},
            "destination": {"zone_id": "wan", "matching_target": "ANY"},
        }
        created_raw = {**zone_data, "_id": "new_003"}
        mock_created = MagicMock()
        mock_created.raw = created_raw

        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.create_firewall_policy = AsyncMock(return_value=mock_created)

            from unifi_network_mcp.tools.firewall import create_firewall_policy

            result = await create_firewall_policy(policy_data=zone_data, confirm=True)

        assert result["success"] is True


# ---------------------------------------------------------------------------
# create_firewall_policy — zone targeting validation
# ---------------------------------------------------------------------------


class TestCreateZoneTargetingValidation:
    """Test matching_target_type validation for zone-based policies."""

    @pytest.mark.asyncio
    async def test_missing_matching_target_type_for_ip(self):
        """IP targeting without matching_target_type should fail with helpful error."""
        zone_data = {
            "name": "Bad IP policy",
            "action": "ALLOW",
            "source": {"zone_id": "internal", "matching_target": "ANY"},
            "destination": {
                "zone_id": "internal",
                "matching_target": "IP",
                # missing matching_target_type and ips
            },
        }

        from unifi_network_mcp.tools.firewall import create_firewall_policy

        result = await create_firewall_policy(policy_data=zone_data, confirm=True)

        assert result["success"] is False
        assert "matching_target_type" in result["error"]
        assert "SPECIFIC" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_matching_target_type_for_network(self):
        """Network targeting without matching_target_type should fail with helpful error."""
        zone_data = {
            "name": "Bad network policy",
            "action": "BLOCK",
            "source": {
                "zone_id": "internal",
                "matching_target": "NETWORK",
                # missing matching_target_type
            },
            "destination": {"zone_id": "wan", "matching_target": "ANY"},
        }

        from unifi_network_mcp.tools.firewall import create_firewall_policy

        result = await create_firewall_policy(policy_data=zone_data, confirm=True)

        assert result["success"] is False
        assert "matching_target_type" in result["error"]
        assert "OBJECT" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_ips_for_ip_targeting(self):
        """IP targeting with matching_target_type but no ips should fail."""
        zone_data = {
            "name": "No IPs",
            "action": "ALLOW",
            "source": {"zone_id": "internal", "matching_target": "ANY"},
            "destination": {
                "zone_id": "internal",
                "matching_target": "IP",
                "matching_target_type": "SPECIFIC",
                # missing ips
            },
        }

        from unifi_network_mcp.tools.firewall import create_firewall_policy

        result = await create_firewall_policy(policy_data=zone_data, confirm=True)

        assert result["success"] is False
        assert "ips" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_network_ids_for_network_targeting(self):
        """Network targeting without network_ids should fail."""
        zone_data = {
            "name": "No Network IDs",
            "action": "BLOCK",
            "source": {
                "zone_id": "internal",
                "matching_target": "NETWORK",
                "matching_target_type": "OBJECT",
                # missing network_ids
            },
            "destination": {"zone_id": "wan", "matching_target": "ANY"},
        }

        from unifi_network_mcp.tools.firewall import create_firewall_policy

        result = await create_firewall_policy(policy_data=zone_data, confirm=True)

        assert result["success"] is False
        assert "network_ids" in result["error"]


# ---------------------------------------------------------------------------
# update_firewall_policy — v2 field acceptance
# ---------------------------------------------------------------------------


class TestUpdateFirewallPolicyV2Fields:
    """Test that update_firewall_policy accepts zone-based fields."""

    @pytest.mark.asyncio
    async def test_v2_fields_pass_through(self):
        """Update with source/destination should bypass legacy validation."""
        mock_policy = _make_policy(SAMPLE_ZONE_POLICY_RAW)
        updated_raw = copy.deepcopy(SAMPLE_ZONE_POLICY_RAW)
        updated_raw["action"] = "BLOCK"
        updated_raw["source"]["zone_id"] = "wan"
        updated_raw["source"]["matching_target"] = "ANY"
        mock_updated = _make_policy(updated_raw)

        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.get_firewall_policies = AsyncMock(side_effect=[[mock_policy], [mock_updated]])
            mock_fm.update_firewall_policy = AsyncMock(return_value=True)

            from unifi_network_mcp.tools.firewall import update_firewall_policy

            result = await update_firewall_policy(
                policy_id="pol_zone_001",
                update_data={
                    "action": "BLOCK",
                    "source": {"zone_id": "wan", "matching_target": "ANY"},
                },
                confirm=True,
            )

        assert result["success"] is True
        assert "action" in result["updated_fields"]
        assert "source" in result["updated_fields"]

    @pytest.mark.asyncio
    async def test_action_normalization_uppercase(self):
        """Uppercase actions should be accepted and normalized."""
        mock_policy = _make_policy(SAMPLE_ZONE_POLICY_RAW)

        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.get_firewall_policies = AsyncMock(return_value=[mock_policy])

            from unifi_network_mcp.tools.firewall import update_firewall_policy

            # Preview mode to test normalization without calling manager
            result = await update_firewall_policy(
                policy_id="pol_zone_001",
                update_data={"action": "REJECT", "ip_version": "IPv4"},
                confirm=False,
            )

        assert result["success"] is True
        assert result.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_invalid_action_rejected(self):
        """Invalid action values should be rejected."""
        from unifi_network_mcp.tools.firewall import update_firewall_policy

        result = await update_firewall_policy(
            policy_id="pol_001",
            update_data={"action": "INVALID"},
            confirm=True,
        )

        assert result["success"] is False
        assert "Invalid action" in result["error"]

    @pytest.mark.asyncio
    async def test_update_detects_silently_discarded_change(self):
        """Post-update verification should catch when controller ignores a field."""
        mock_policy = _make_policy(SAMPLE_ZONE_POLICY_RAW)
        # Simulate controller ignoring the logging change (returns original value)
        unchanged_raw = copy.deepcopy(SAMPLE_ZONE_POLICY_RAW)
        mock_unchanged = _make_policy(unchanged_raw)

        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.get_firewall_policies = AsyncMock(side_effect=[[mock_policy], [mock_unchanged]])
            mock_fm.update_firewall_policy = AsyncMock(return_value=True)

            from unifi_network_mcp.tools.firewall import update_firewall_policy

            result = await update_firewall_policy(
                policy_id="pol_zone_001",
                update_data={"logging": True},
                confirm=True,
            )

        assert result["success"] is False
        assert "logging" in result["error"]
        assert "did not apply" in result["error"]


# ---------------------------------------------------------------------------
# delete_firewall_policy
# ---------------------------------------------------------------------------


class TestDeleteFirewallPolicy:
    """Test the new delete_firewall_policy tool."""

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """Confirmed delete should call manager and return success."""
        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.delete_firewall_policy = AsyncMock(return_value=True)

            from unifi_network_mcp.tools.firewall import delete_firewall_policy

            result = await delete_firewall_policy(policy_id="pol_001", confirm=True)

        assert result["success"] is True
        assert "deleted successfully" in result["message"]
        mock_fm.delete_firewall_policy.assert_called_once_with("pol_001")

    @pytest.mark.asyncio
    async def test_delete_preview(self):
        """Unconfirmed delete should return a preview."""
        from unifi_network_mcp.tools.firewall import delete_firewall_policy

        result = await delete_firewall_policy(policy_id="pol_001", confirm=False)

        assert result["success"] is True
        assert result.get("requires_confirmation") is True

    @pytest.mark.asyncio
    async def test_delete_manager_failure(self):
        """Delete should return error when manager returns False."""
        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.delete_firewall_policy = AsyncMock(return_value=False)

            from unifi_network_mcp.tools.firewall import delete_firewall_policy

            result = await delete_firewall_policy(policy_id="pol_001", confirm=True)

        assert result["success"] is False
        assert "Failed to delete" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_exception_handled(self):
        """Delete should catch exceptions and return clean error."""
        with patch("unifi_network_mcp.tools.firewall.firewall_manager") as mock_fm:
            mock_fm.delete_firewall_policy = AsyncMock(side_effect=Exception("Connection refused"))

            from unifi_network_mcp.tools.firewall import delete_firewall_policy

            result = await delete_firewall_policy(policy_id="pol_001", confirm=True)

        assert result["success"] is False
        assert "Connection refused" in result["error"]
