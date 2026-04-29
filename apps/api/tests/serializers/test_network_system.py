"""Network system cluster serializer unit tests (Phase 4A PR1 Cluster 6).

Covers alarms (LIST), backups (LIST), system info / network health /
site settings / SNMP settings / event types / autobackup settings (DETAIL),
top clients (LIST), client sessions (LIST), client wifi details (DETAIL),
speedtest results (LIST), and mutation acks for archive/backup/autobackup
operations.
"""

from unifi_api.serializers._registry import (
    discover_serializers,
    serializer_registry_singleton,
)


def _registry():
    discover_serializers(manifest_tool_names=set())
    return serializer_registry_singleton()


# ---- Alarms ----


def test_alarm_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_list_alarms")
    sample = [
        {"_id": "al1", "key": "EVT_FW_Block", "msg": "Blocked", "archived": False, "time": 1714000000}
    ]
    out = s.serialize_action(sample, tool_name="unifi_list_alarms")
    assert out["success"] is True
    assert out["render_hint"]["kind"] == "list"
    item = out["data"][0]
    assert item["id"] == "al1"
    assert item["key"] == "EVT_FW_Block"
    assert item["msg"] == "Blocked"
    assert item["archived"] is False
    assert item["time"] == 1714000000


# ---- Backups ----


def test_backup_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_list_backups")
    sample = [{"_id": "b1", "filename": "auto-2026-04-29.unf", "size": 12345, "time": 1714000000}]
    out = s.serialize_action(sample, tool_name="unifi_list_backups")
    assert out["render_hint"]["kind"] == "list"
    item = out["data"][0]
    assert item["id"] == "b1"
    assert item["filename"] == "auto-2026-04-29.unf"
    assert item["size"] == 12345
    assert item["created_at"] == 1714000000


# ---- System info ----


def test_system_info_detail_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_system_info")
    sample = {
        "name": "UniFi Controller",
        "version": "8.1.113",
        "hostname": "unifi.local",
        "uptime": 86400,
        "num_devices": 12,
        "num_clients": 47,
    }
    out = s.serialize_action(sample, tool_name="unifi_get_system_info")
    assert out["render_hint"]["kind"] == "detail"
    assert out["data"]["name"] == "UniFi Controller"
    assert out["data"]["version"] == "8.1.113"
    assert out["data"]["uptime"] == 86400
    assert out["data"]["num_devices"] == 12


# ---- Network health (manager returns list of subsystems) ----


def test_network_health_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_network_health")
    sample = [
        {"subsystem": "wan", "status": "ok", "num_user": 5, "num_guest": 1, "num_iot": 2, "rx_bytes-r": 100, "tx_bytes-r": 200},
        {"subsystem": "wlan", "status": "ok", "num_user": 8},
    ]
    out = s.serialize_action(sample, tool_name="unifi_get_network_health")
    assert out["render_hint"]["kind"] == "list"
    assert out["data"][0]["subsystem"] == "wan"
    assert out["data"][0]["status"] == "ok"
    assert out["data"][0]["num_user"] == 5
    assert out["data"][1]["subsystem"] == "wlan"


# ---- Site settings (DETAIL) ----


def test_site_settings_detail_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_site_settings")
    sample = {"_id": "site_id_1", "name": "default", "role": "admin", "country": 840}
    out = s.serialize_action(sample, tool_name="unifi_get_site_settings")
    assert out["render_hint"]["kind"] == "detail"
    assert out["data"]["site_id"] == "site_id_1"
    assert out["data"]["name"] == "default"
    assert out["data"]["country"] == 840


# ---- SNMP settings (manager returns list[dict]) ----


def test_snmp_settings_detail_first_item_unwrap() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_snmp_settings")
    sample = [{"enabled": True, "community": "public", "port": 161, "version": "v2c", "key": "snmp"}]
    out = s.serialize_action(sample, tool_name="unifi_get_snmp_settings")
    assert out["render_hint"]["kind"] == "detail"
    assert out["data"]["enabled"] is True
    assert out["data"]["community"] == "public"
    assert out["data"]["port"] == 161
    assert out["data"]["version"] == "v2c"


# ---- Event types ----


def test_event_types_detail_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_event_types")
    sample = [
        {"prefix": "EVT_WU_", "description": "Wireless user events"},
        {"prefix": "EVT_SW_", "description": "Switch events"},
    ]
    out = s.serialize_action(sample, tool_name="unifi_get_event_types")
    assert out["render_hint"]["kind"] == "detail"
    assert out["data"]["event_types"][0]["prefix"] == "EVT_WU_"
    assert out["data"]["event_types"][1]["prefix"] == "EVT_SW_"


# ---- Auto-backup settings ----


def test_autobackup_settings_detail_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_autobackup_settings")
    sample = {"enabled": True, "schedule": "daily", "max_count": 10}
    out = s.serialize_action(sample, tool_name="unifi_get_autobackup_settings")
    assert out["render_hint"]["kind"] == "detail"
    assert out["data"]["enabled"] is True
    assert out["data"]["schedule"] == "daily"
    assert out["data"]["max_count"] == 10


# ---- Top clients ----


def test_top_clients_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_top_clients")
    sample = [
        {"mac": "aa:bb:cc:dd:ee:ff", "name": "laptop", "rx_bytes": 100, "tx_bytes": 200, "total_bytes": 300}
    ]
    out = s.serialize_action(sample, tool_name="unifi_get_top_clients")
    assert out["render_hint"]["kind"] == "list"
    item = out["data"][0]
    assert item["mac"] == "aa:bb:cc:dd:ee:ff"
    assert item["hostname"] == "laptop"
    assert item["rx_bytes"] == 100
    assert item["tx_bytes"] == 200
    assert item["total_bytes"] == 300


# ---- Speedtest ----


def test_speedtest_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_speedtest_results")
    sample = [
        {"time": 1714000000, "xput_download": 500.5, "xput_upload": 50.1, "latency": 12}
    ]
    out = s.serialize_action(sample, tool_name="unifi_get_speedtest_results")
    assert out["render_hint"]["kind"] == "list"
    item = out["data"][0]
    assert item["timestamp"] == 1714000000
    assert item["download_mbps"] == 500.5
    assert item["upload_mbps"] == 50.1
    assert item["latency_ms"] == 12


# ---- System mutation acks ----


def test_system_mutation_acks_dispatch() -> None:
    reg = _registry()
    for tool in (
        "unifi_archive_alarm",
        "unifi_archive_all_alarms",
        "unifi_create_backup",
        "unifi_delete_backup",
        "unifi_update_autobackup_settings",
    ):
        s = reg.serializer_for_tool(tool)
        out = s.serialize_action(True, tool_name=tool)
        assert out["render_hint"]["kind"] == "detail"
        assert out["data"]["success"] is True


def test_create_backup_returns_dict_passthrough() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_create_backup")
    sample = {"filename": "backup.unf", "url": "/dl/backup/backup.unf"}
    out = s.serialize_action(sample, tool_name="unifi_create_backup")
    assert out["data"]["filename"] == "backup.unf"
