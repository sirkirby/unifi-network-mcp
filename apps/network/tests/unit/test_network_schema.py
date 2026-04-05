"""Tests for NETWORK_SCHEMA and NETWORK_UPDATE_SCHEMA validation.

Verifies DHCP, DNS, multicast, and network feature fields
are accepted or rejected correctly by the validator.
"""

import pytest

from unifi_network_mcp.validator_registry import UniFiValidatorRegistry


class TestNetworkUpdateSchema:
    """Tests for network_update schema validation."""

    def test_dhcpd_fields_accepted(self):
        """Test DHCP server fields pass validation."""
        is_valid, error_msg, data = UniFiValidatorRegistry.validate(
            "network_update",
            {
                "dhcpd_enabled": True,
                "dhcpd_start": "10.0.0.100",
                "dhcpd_stop": "10.0.0.200",
                "dhcpd_leasetime": 86400,
            },
        )
        assert is_valid
        assert data["dhcpd_enabled"] is True
        assert data["dhcpd_leasetime"] == 86400

    def test_dhcpd_leasetime_minimum(self):
        """Test dhcpd_leasetime rejects values below minimum."""
        is_valid, error_msg, _ = UniFiValidatorRegistry.validate(
            "network_update",
            {"dhcpd_leasetime": 10},
        )
        assert not is_valid
        assert "minimum" in error_msg.lower() or "10" in error_msg

    def test_dhcpd_dns_fields_accepted(self):
        """Test DHCP DNS option fields pass validation."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {
                "dhcpd_dns_enabled": True,
                "dhcpd_dns_1": "1.1.1.1",
                "dhcpd_dns_2": "8.8.8.8",
            },
        )
        assert is_valid
        assert data["dhcpd_dns_1"] == "1.1.1.1"

    def test_dhcpd_ntp_fields_accepted(self):
        """Test DHCP NTP option fields pass validation."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {
                "dhcpd_ntp_enabled": True,
                "dhcpd_ntp_1": "pool.ntp.org",
            },
        )
        assert is_valid

    def test_dhcpd_wins_fields_accepted(self):
        """Test DHCP WINS option fields pass validation."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {
                "dhcpd_wins_enabled": True,
                "dhcpd_wins_1": "10.0.0.10",
            },
        )
        assert is_valid

    def test_dhcp_security_fields_accepted(self):
        """Test DHCP security fields pass validation."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {
                "dhcpguard_enabled": True,
                "dhcpd_conflict_checking": True,
                "dhcp_relay_enabled": False,
            },
        )
        assert is_valid

    def test_domain_name_accepted(self):
        """Test domain_name field passes validation."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {"domain_name": "example.com"},
        )
        assert is_valid
        assert data["domain_name"] == "example.com"

    def test_network_feature_fields_accepted(self):
        """Test network feature fields pass validation."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {
                "network_isolation_enabled": True,
                "internet_access_enabled": False,
                "upnp_lan_enabled": True,
            },
        )
        assert is_valid

    def test_igmp_fields_accepted(self):
        """Test IGMP/multicast fields pass validation."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {
                "igmp_snooping": True,
                "igmp_flood_unknown_multicast": False,
                "mdns_enabled": True,
            },
        )
        assert is_valid

    def test_igmp_querier_requires_switch_mac(self):
        """Test igmp_querier_switches rejects entries without switch_mac."""
        is_valid, error_msg, _ = UniFiValidatorRegistry.validate(
            "network_update",
            {"igmp_querier_switches": [{"querier_address": "10.0.0.1"}]},
        )
        assert not is_valid
        assert "switch_mac" in error_msg

    def test_wrong_type_rejected(self):
        """Test wrong types are rejected."""
        is_valid, error_msg, _ = UniFiValidatorRegistry.validate(
            "network_update",
            {"dhcpd_enabled": "yes"},
        )
        assert not is_valid
        assert "type" in error_msg.lower()

    def test_partial_update_accepted(self):
        """Test single field update passes (no required fields on update schema)."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {"domain_name": "new.example.com"},
        )
        assert is_valid
        assert len(data) == 1

    def test_pxe_boot_fields_accepted(self):
        """Test PXE/TFTP boot fields pass validation.

        Note: dhcpd_tftp_server is DHCP option 150 (Cisco TFTP, independent).
        PXE boot uses dhcpd_boot_server (BOOTP siaddr) + dhcpd_boot_filename.
        """
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {
                "dhcpd_boot_enabled": True,
                "dhcpd_boot_server": "10.0.0.5",
                "dhcpd_boot_filename": "pxelinux.0",
                "dhcpd_tftp_server": "10.0.0.6",
            },
        )
        assert is_valid
        assert set(data.keys()) == {
            "dhcpd_boot_enabled",
            "dhcpd_boot_server",
            "dhcpd_boot_filename",
            "dhcpd_tftp_server",
        }

    def test_dhcpd_unifi_controller_accepted(self):
        """Test UniFi controller DHCP option passes validation."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {"dhcpd_unifi_controller": "192.168.1.1"},
        )
        assert is_valid

    def test_dhcpguard_with_trusted_ip_accepted(self):
        """Test dhcpguard_enabled with required dhcpd_ip_1 trusted server."""
        is_valid, _, data = UniFiValidatorRegistry.validate(
            "network_update",
            {"dhcpguard_enabled": True, "dhcpd_ip_1": "192.168.1.1"},
        )
        assert is_valid
        assert data["dhcpguard_enabled"] is True
        assert data["dhcpd_ip_1"] == "192.168.1.1"
