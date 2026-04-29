"""Network misc cluster serializer unit tests (Phase 4A PR1 Cluster 5).

Covers port forwards (LIST + DETAIL + mutation ack), vouchers (LIST + DETAIL
+ mutation ack), and SNMP settings mutation ack. The hotspot category in
the manifest currently contains only voucher tools — there are no
non-voucher hotspot tools to serialize.
"""

from unifi_api.serializers._registry import (
    discover_serializers,
    serializer_registry_singleton,
)


def _registry():
    discover_serializers(manifest_tool_names=set())
    return serializer_registry_singleton()


# ---- Port forwards ----


def test_port_forward_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_list_port_forwards")
    sample = [
        {
            "_id": "pf1",
            "name": "Web",
            "enabled": True,
            "fwd_protocol": "tcp",
            "dst_port": "443",
            "fwd_port": "443",
            "src": "any",
            "log": False,
        }
    ]
    out = s.serialize_action(sample, tool_name="unifi_list_port_forwards")
    assert out["success"] is True
    assert out["data"][0]["id"] == "pf1"
    assert out["data"][0]["name"] == "Web"
    assert out["data"][0]["enabled"] is True
    assert out["data"][0]["fwd_protocol"] == "tcp"
    assert out["data"][0]["dst_port"] == "443"
    assert out["data"][0]["fwd_port"] == "443"
    assert out["data"][0]["src"] == "any"
    assert out["data"][0]["log"] is False
    assert out["render_hint"]["kind"] == "list"


def test_port_forward_detail_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_port_forward")
    sample = {
        "_id": "pf2",
        "name": "SSH",
        "enabled": False,
        "fwd_protocol": "tcp",
        "dst_port": "22",
        "fwd_port": "22",
    }
    out = s.serialize_action(sample, tool_name="unifi_get_port_forward")
    assert out["success"] is True
    assert out["data"]["id"] == "pf2"
    assert out["data"]["name"] == "SSH"
    assert out["data"]["enabled"] is False
    assert out["render_hint"]["kind"] == "detail"


def test_port_forward_mutation_ack_dispatches_for_all_mutations() -> None:
    reg = _registry()
    for tool in (
        "unifi_create_port_forward",
        "unifi_create_simple_port_forward",
        "unifi_update_port_forward",
        "unifi_toggle_port_forward",
    ):
        s = reg.serializer_for_tool(tool)
        out = s.serialize_action(True, tool_name=tool)
        assert out["render_hint"]["kind"] == "detail"


# ---- Vouchers ----


def test_voucher_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_list_vouchers")
    sample = [
        {
            "_id": "v1",
            "code": "12345-67890",
            "status": "VALID_MULTI",
            "duration": 1440,
            "qos_overwrite": False,
            "create_time": 1714000000,
            "used_at": None,
        }
    ]
    out = s.serialize_action(sample, tool_name="unifi_list_vouchers")
    assert out["success"] is True
    assert out["data"][0]["id"] == "v1"
    assert out["data"][0]["code"] == "12345-67890"
    assert out["data"][0]["status"] == "VALID_MULTI"
    assert out["data"][0]["duration"] == 1440
    assert out["data"][0]["qos_overwrite"] is False
    assert out["data"][0]["created_at"] == 1714000000
    assert out["render_hint"]["kind"] == "list"


def test_voucher_detail_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_voucher_details")
    sample = {
        "_id": "v2",
        "code": "abcde-fghij",
        "status": "USED_MULTIPLE",
        "duration": 60,
        "qos_overwrite": True,
        "create_time": 1714111111,
        "end_time": 1714222222,
    }
    out = s.serialize_action(sample, tool_name="unifi_get_voucher_details")
    assert out["success"] is True
    assert out["data"]["id"] == "v2"
    assert out["data"]["code"] == "abcde-fghij"
    assert out["data"]["status"] == "USED_MULTIPLE"
    assert out["data"]["qos_overwrite"] is True
    assert out["render_hint"]["kind"] == "detail"


def test_voucher_mutation_ack_dispatches_for_all_mutations() -> None:
    reg = _registry()
    for tool in ("unifi_create_voucher", "unifi_revoke_voucher"):
        s = reg.serializer_for_tool(tool)
        out = s.serialize_action(True, tool_name=tool)
        assert out["render_hint"]["kind"] == "detail"


# ---- SNMP settings ----


def test_snmp_mutation_ack_dispatches() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_update_snmp_settings")
    out = s.serialize_action(True, tool_name="unifi_update_snmp_settings")
    assert out["render_hint"]["kind"] == "detail"
    assert out["data"]["success"] is True
