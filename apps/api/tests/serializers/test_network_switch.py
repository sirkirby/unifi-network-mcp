"""Switch + device cluster serializer unit tests (Phase 4A PR1 Cluster 1)."""

from unifi_api.serializers._registry import (
    serializer_registry_singleton,
    discover_serializers,
)


def _registry():
    discover_serializers(manifest_tool_names=set())
    return serializer_registry_singleton()


# ---- switch.py ----


def test_port_profile_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_list_port_profiles")
    sample = {
        "_id": "pp1",
        "name": "All-Tagged",
        "native_networkconf_id": "net1",
        "tagged_networkconf_ids": ["net2"],
        "poe_mode": "auto",
        "isolation": False,
    }
    out = s.serialize(sample)
    assert out["id"] == "pp1"
    assert out["name"] == "All-Tagged"
    assert out["poe_mode"] == "auto"
    assert out["tagged_networkconf_ids"] == ["net2"]


def test_port_profile_detail_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_port_profile_details")
    sample = {"_id": "pp2", "name": "Voice", "poe_mode": "passive"}
    out = s.serialize_action(sample, tool_name="unifi_get_port_profile_details")
    assert out["success"] is True
    assert out["data"]["id"] == "pp2"
    assert out["data"]["name"] == "Voice"
    assert out["render_hint"]["kind"] == "detail"


def test_switch_ports_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_switch_ports")
    sample = {
        "name": "USW-24",
        "model": "US24P250",
        "port_overrides": [
            {"port_idx": 1, "name": "Trunk", "portconf_id": "pp1", "poe_mode": "auto"},
            {"port_idx": 2, "name": "Voice", "portconf_id": "pp2"},
        ],
    }
    out = s.serialize_action(sample, tool_name="unifi_get_switch_ports")
    assert out["success"] is True
    assert out["data"]["name"] == "USW-24"
    assert len(out["data"]["port_overrides"]) == 2
    assert out["data"]["port_overrides"][0]["port_idx"] == 1
    assert out["render_hint"]["kind"] == "detail"


def test_port_stats_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_port_stats")
    sample = {
        "name": "USW-24",
        "model": "US24P250",
        "port_table": [
            {
                "port_idx": 1,
                "tx_bytes": 1000,
                "rx_bytes": 2000,
                "tx_packets": 5,
                "rx_packets": 10,
                "speed": 1000,
                "enable": True,
            }
        ],
    }
    out = s.serialize_action(sample, tool_name="unifi_get_port_stats")
    assert out["success"] is True
    assert out["data"]["name"] == "USW-24"
    assert out["data"]["port_table"][0]["tx_bytes"] == 1000
    assert out["render_hint"]["kind"] == "detail"


def test_switch_capabilities_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_switch_capabilities")
    sample = {
        "name": "USW-24",
        "model": "US24P250",
        "switch_caps": {"max_aggregate_sessions": 8, "max_mirror_sessions": 1},
        "stp_version": "rstp",
        "stp_priority": "32768",
        "jumboframe_enabled": False,
    }
    out = s.serialize_action(sample, tool_name="unifi_get_switch_capabilities")
    assert out["success"] is True
    assert out["data"]["name"] == "USW-24"
    assert out["data"]["stp_version"] == "rstp"
    assert out["data"]["jumboframe_enabled"] is False
    assert out["render_hint"]["kind"] == "detail"


def test_switch_mutation_ack_bool() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_update_switch_stp")
    out = s.serialize_action(True, tool_name="unifi_update_switch_stp")
    assert out["success"] is True
    assert out["data"] == {"success": True}
    assert out["render_hint"]["kind"] == "detail"


def test_switch_mutation_ack_dict_passthrough() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_create_port_profile")
    out = s.serialize_action({"_id": "pp9", "name": "New"}, tool_name="unifi_create_port_profile")
    assert out["success"] is True
    assert out["data"]["_id"] == "pp9"
    assert out["render_hint"]["kind"] == "detail"


# ---- devices.py extensions ----


def test_device_radio_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_device_radio")
    sample = {
        "mac": "11:22:33:44:55:66",
        "name": "AP1",
        "model": "U6-Pro",
        "radios": [
            {"name": "wifi0", "radio": "ng", "channel": 6, "tx_power": 17, "ht": 20},
            {"name": "wifi1", "radio": "na", "channel": 36, "tx_power": 23, "ht": 80},
        ],
    }
    out = s.serialize_action(sample, tool_name="unifi_get_device_radio")
    assert out["success"] is True
    assert out["data"]["mac"] == "11:22:33:44:55:66"
    assert len(out["data"]["radios"]) == 2
    assert out["render_hint"]["kind"] == "detail"


def test_lldp_neighbors_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_lldp_neighbors")
    sample = {
        "name": "USW-24",
        "model": "US24P250",
        "lldp_table": [
            {
                "local_port_idx": 1,
                "chassis_id": "aa:bb:cc:dd:ee:ff",
                "port_id": "Gi1/0/1",
                "system_name": "neighbor-sw",
                "capabilities": ["bridge"],
            }
        ],
    }
    out = s.serialize_action(sample, tool_name="unifi_get_lldp_neighbors")
    assert out["success"] is True
    assert out["data"]["lldp_table"][0]["chassis_id"] == "aa:bb:cc:dd:ee:ff"
    assert out["render_hint"]["kind"] == "detail"


def test_rogue_ap_serializer_shape() -> None:
    reg = _registry()
    s_unknown = reg.serializer_for_tool("unifi_list_rogue_aps")
    s_known = reg.serializer_for_tool("unifi_list_known_rogue_aps")
    sample = [
        {
            "bssid": "aa:bb:cc:11:22:33",
            "essid": "EvilTwin",
            "channel": 11,
            "rssi": -55,
            "last_seen": 1700000000,
            "is_rogue": True,
        }
    ]
    out = s_unknown.serialize_action(sample, tool_name="unifi_list_rogue_aps")
    assert out["success"] is True
    assert out["data"][0]["bssid"] == "aa:bb:cc:11:22:33"
    assert out["data"][0]["ssid"] == "EvilTwin"
    assert out["data"][0]["is_known"] is False
    assert out["render_hint"]["kind"] == "list"

    out2 = s_known.serialize_action(sample, tool_name="unifi_list_known_rogue_aps")
    assert out2["data"][0]["is_known"] is True


def test_rf_scan_result_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_rf_scan_results")
    sample = [
        {
            "bssid": "aa:bb:cc:11:22:33",
            "essid": "Neighbor",
            "channel": 6,
            "rssi": -70,
            "ts": 1700000000,
        }
    ]
    out = s.serialize_action(sample, tool_name="unifi_get_rf_scan_results")
    assert out["success"] is True
    assert out["data"][0]["bssid"] == "aa:bb:cc:11:22:33"
    assert out["data"][0]["channel"] == 6
    assert out["render_hint"]["kind"] == "list"


def test_available_channel_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_list_available_channels")
    sample = [{"channel": 36, "freq": 5180, "ht": 80, "allowed": True}]
    out = s.serialize_action(sample, tool_name="unifi_list_available_channels")
    assert out["success"] is True
    assert out["data"][0]["channel"] == 36
    assert out["data"][0]["frequency_mhz"] == 5180
    assert out["data"][0]["width_mhz"] == 80
    assert out["render_hint"]["kind"] == "list"


def test_speedtest_status_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_speedtest_status")
    sample = {
        "status_download": 500.5,
        "status_upload": 50.1,
        "latency": 12,
        "rundate": 1700000000,
        "status": 0,
    }
    out = s.serialize_action(sample, tool_name="unifi_get_speedtest_status")
    assert out["success"] is True
    assert out["data"]["download_mbps"] == 500.5
    assert out["data"]["upload_mbps"] == 50.1
    assert out["data"]["latency_ms"] == 12
    assert out["render_hint"]["kind"] == "detail"


def test_device_mutation_ack_bool() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_reboot_device")
    out = s.serialize_action(True, tool_name="unifi_reboot_device")
    assert out["success"] is True
    assert out["data"] == {"success": True}
    assert out["render_hint"]["kind"] == "detail"


def test_device_mutation_ack_dispatches_for_all_mutations() -> None:
    """Every mutation tool registered should resolve via the registry."""
    reg = _registry()
    for tool in (
        "unifi_adopt_device",
        "unifi_force_provision_device",
        "unifi_locate_device",
        "unifi_reboot_device",
        "unifi_rename_device",
        "unifi_set_device_led",
        "unifi_set_site_leds",
        "unifi_toggle_device",
        "unifi_trigger_rf_scan",
        "unifi_trigger_speedtest",
        "unifi_update_device_radio",
        "unifi_upgrade_device",
        "unifi_create_port_profile",
        "unifi_update_port_profile",
        "unifi_delete_port_profile",
        "unifi_set_switch_port_profile",
        "unifi_configure_port_aggregation",
        "unifi_configure_port_mirror",
        "unifi_power_cycle_port",
        "unifi_set_jumbo_frames",
        "unifi_update_switch_stp",
    ):
        s = reg.serializer_for_tool(tool)
        out = s.serialize_action(True, tool_name=tool)
        assert out["render_hint"]["kind"] == "detail"
