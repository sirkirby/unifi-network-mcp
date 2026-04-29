"""Network sessions / wifi-details serializer unit tests (Phase 4A PR1 Cluster 6)."""

from unifi_api.serializers._registry import (
    discover_serializers,
    serializer_registry_singleton,
)


def _registry():
    discover_serializers(manifest_tool_names=set())
    return serializer_registry_singleton()


def test_client_sessions_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_client_sessions")
    sample = [
        {
            "mac": "aa:bb:cc:dd:ee:ff",
            "hostname": "laptop",
            "ap_mac": "11:22:33:44:55:66",
            "essid": "MyWiFi",
            "assoc_time": 1714000000,
            "disassoc_time": 1714003600,
            "duration": 3600,
        }
    ]
    out = s.serialize_action(sample, tool_name="unifi_get_client_sessions")
    assert out["render_hint"]["kind"] == "list"
    item = out["data"][0]
    assert item["mac"] == "aa:bb:cc:dd:ee:ff"
    assert item["hostname"] == "laptop"
    assert item["ap"] == "11:22:33:44:55:66"
    assert item["ssid"] == "MyWiFi"
    assert item["connected_at"] == 1714000000
    assert item["disconnected_at"] == 1714003600
    assert item["duration"] == 3600


def test_client_wifi_details_detail_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_client_wifi_details")
    sample = {
        "mac": "aa:bb:cc:dd:ee:ff",
        "essid": "MyWiFi",
        "ap_mac": "11:22:33:44:55:66",
        "signal": -55,
        "tx_rate": 866000,
        "rx_rate": 433000,
        "channel": 36,
    }
    out = s.serialize_action(sample, tool_name="unifi_get_client_wifi_details")
    assert out["render_hint"]["kind"] == "detail"
    assert out["data"]["mac"] == "aa:bb:cc:dd:ee:ff"
    assert out["data"]["ssid"] == "MyWiFi"
    assert out["data"]["ap"] == "11:22:33:44:55:66"
    assert out["data"]["signal"] == -55
    assert out["data"]["tx_rate"] == 866000
    assert out["data"]["rx_rate"] == 433000
    assert out["data"]["channel"] == 36


def test_client_wifi_details_handles_none() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_client_wifi_details")
    out = s.serialize_action(None, tool_name="unifi_get_client_wifi_details")
    assert out["render_hint"]["kind"] == "detail"
    assert out["data"] == {}
