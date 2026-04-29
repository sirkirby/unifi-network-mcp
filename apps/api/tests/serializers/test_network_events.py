"""Network events cluster serializer unit tests (Phase 4A PR1 Cluster 6).

Covers EVENT_LOG tools (`unifi_list_events`, `unifi_get_alerts`,
`unifi_get_anomalies`, `unifi_get_ips_events`).
"""

from unifi_api.serializers._registry import (
    discover_serializers,
    serializer_registry_singleton,
)


def _registry():
    discover_serializers(manifest_tool_names=set())
    return serializer_registry_singleton()


def test_event_log_serializer_basic_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_list_events")
    sample = [
        {
            "_id": "evt1",
            "key": "EVT_WU_Connected",
            "msg": "Client connected",
            "time": 1714000000000,
            "user": "aa:bb:cc:dd:ee:ff",
            "ip": "10.0.0.5",
        }
    ]
    out = s.serialize_action(sample, tool_name="unifi_list_events")
    assert out["success"] is True
    assert out["render_hint"]["kind"] == "event_log"
    assert out["render_hint"]["sort_default"] == "time:desc"
    item = out["data"][0]
    assert item["id"] == "evt1"
    assert item["key"] == "EVT_WU_Connected"
    assert item["msg"] == "Client connected"
    assert item["time"] == 1714000000000
    assert item["mac"] == "aa:bb:cc:dd:ee:ff"
    assert item["ip"] == "10.0.0.5"


def test_event_log_severity_passthrough() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_alerts")
    sample = [{"_id": "a1", "key": "EVT_AD_Login", "msg": "x", "severity": "warn", "time": 100}]
    out = s.serialize_action(sample, tool_name="unifi_get_alerts")
    assert out["data"][0]["severity"] == "warn"
    assert out["data"][0]["id"] == "a1"


def test_event_log_dispatches_for_all_event_tools() -> None:
    reg = _registry()
    for tool in (
        "unifi_list_events",
        "unifi_get_alerts",
        "unifi_get_anomalies",
        "unifi_get_ips_events",
    ):
        s = reg.serializer_for_tool(tool)
        out = s.serialize_action([], tool_name=tool)
        assert out["render_hint"]["kind"] == "event_log"
