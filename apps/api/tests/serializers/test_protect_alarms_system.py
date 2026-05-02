"""Protect alarms + system serializer tests (Phase 4A PR2 Cluster 3).

Manager + tool methods covered:
  - ``AlarmManager.get_arm_state`` -> dict; tool wraps as
    ``{armed, status, active_profile_id, active_profile_name, armed_at, ...,
       breach_event_count, profile_count}``
  - ``AlarmManager.list_arm_profiles`` -> list[dict]; tool wraps as
    ``{profiles: [...], count: N}`` (wrapper dict at serializer boundary)
  - ``AlarmManager.arm`` / ``disarm`` -> dict (preview or result; pass-through)
  - ``SystemManager.get_system_info`` -> nested dict (id/name/model/version/storage/...)
  - ``SystemManager.get_health`` -> nested dict (cpu/memory/storage/...)
  - ``SystemManager.list_viewers`` -> list[dict]; tool wraps as
    ``{viewers: [...], count: N}`` (wrapper dict at serializer boundary)
  - ``SystemManager.get_firmware_status`` -> dict with ``nvr``, ``devices``, totals

Notes on shape divergence from the plan spec (recorded in commit body):
  * ``protect_alarm_list_profiles`` and ``protect_list_viewers`` are wrapped by
    the tool layer in ``{profiles|viewers, count}``, so we register DETAIL
    pass-through serializers (mirroring ``protect_recent_events`` from Cluster 2).
  * Profile entries are ``id, name, record_everything, activation_delay_ms,
    schedule_count, automation_count`` — not ``schedule, trigger_camera_ids``.
  * Health is nested ``cpu/memory/storage`` — not flat ``status,
    storage_used_pct, num_*``.
  * Firmware status returns ``nvr``, ``devices``, ``total_devices``,
    ``devices_with_updates`` — not ``current_version, latest_version, ...``.
"""

from unifi_api.serializers._registry import (
    discover_serializers,
    serializer_registry_singleton,
)


def _registry():
    discover_serializers(manifest_tool_names=set())
    return serializer_registry_singleton()


# ---- alarms.py ----


def test_alarm_status_serializer_shape() -> None:
    """Phase 6 PR3 Task B — projection moved to a Strawberry type. Same dict
    shape contract as the old serializer; verified via Type.to_dict()."""
    from unifi_api.graphql.types.protect.alarms import AlarmStatus

    sample = {
        "armed": True,
        "status": "active",
        "active_profile_id": "p1",
        "active_profile_name": "Night",
        "armed_at": "2026-04-29T08:00:00+00:00",
        "will_be_armed_at": None,
        "breach_detected_at": None,
        "breach_event_count": 0,
        "profile_count": 3,
    }
    out = AlarmStatus.from_manager_output(sample).to_dict()
    assert out["armed"] is True
    assert out["status"] == "active"
    assert out["active_profile_id"] == "p1"
    assert out["active_profile_name"] == "Night"
    assert out["breach_event_count"] == 0
    assert AlarmStatus.render_hint("detail")["kind"] == "detail"


def test_alarm_list_profiles_serializer_shape() -> None:
    """Phase 6 PR3 Task B — projection moved to a Strawberry type. The
    wrapper type ``AlarmProfileList`` carries the {profiles, count} action-
    endpoint payload; ``AlarmProfile`` carries each per-row REST projection.
    """
    from unifi_api.graphql.types.protect.alarms import (
        AlarmProfile,
        AlarmProfileList,
    )

    # Tool layer wraps manager list in {profiles, count} dict.
    sample = {
        "profiles": [
            {
                "id": "p1",
                "name": "Night",
                "record_everything": False,
                "activation_delay_ms": 30000,
                "schedule_count": 1,
                "automation_count": 2,
            },
            {
                "id": "p2",
                "name": "Vacation",
                "record_everything": True,
                "activation_delay_ms": 0,
                "schedule_count": 0,
                "automation_count": 1,
            },
        ],
        "count": 2,
    }
    out = AlarmProfileList.from_manager_output(sample).to_dict()
    assert out["count"] == 2
    assert out["profiles"][0]["id"] == "p1"
    assert out["profiles"][0]["name"] == "Night"
    assert out["profiles"][1]["activation_delay_ms"] == 0
    assert AlarmProfileList.render_hint("detail")["kind"] == "detail"

    # REST per-row projection passes profile dicts through unchanged.
    row = AlarmProfile.from_manager_output(sample["profiles"][0]).to_dict()
    assert row["id"] == "p1"
    assert row["record_everything"] is False
    assert row["activation_delay_ms"] == 30000
    assert AlarmProfile.render_hint("list")["primary_key"] == "id"

    # Bare list coerces to a wrapper.
    bare = AlarmProfileList.from_manager_output(sample["profiles"]).to_dict()
    assert bare["count"] == 2
    assert bare["profiles"][0]["id"] == "p1"


def test_alarm_mutation_ack_arm() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("protect_alarm_arm")
    sample = {
        "armed": True,
        "profile_id": "p1",
        "profile_name": "Night",
    }
    out = s.serialize_action(sample, tool_name="protect_alarm_arm")
    assert out["success"] is True
    assert out["data"]["armed"] is True
    assert out["data"]["profile_id"] == "p1"
    assert out["render_hint"]["kind"] == "detail"


def test_alarm_mutation_ack_disarm_idempotent() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("protect_alarm_disarm")
    sample = {"armed": False, "already_disarmed": True}
    out = s.serialize_action(sample, tool_name="protect_alarm_disarm")
    assert out["success"] is True
    assert out["data"]["armed"] is False
    assert out["data"]["already_disarmed"] is True
    assert out["render_hint"]["kind"] == "detail"


# ---- system.py ----


def test_system_info_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("protect_get_system_info")
    sample = {
        "id": "nvr-1",
        "name": "Home NVR",
        "model": "UNVR",
        "hardware_platform": "UNVR",
        "firmware_version": "4.0.0",
        "version": "4.0.0",
        "host": "192.0.2.10",
        "mac": "AA:BB:CC:DD:EE:FF",
        "uptime_seconds": 12345,
        "up_since": "2026-04-25T00:00:00+00:00",
        "is_updating": False,
        "storage": {
            "utilization_pct": 42.5,
            "recording_space_total_bytes": 10_000_000_000,
            "recording_space_used_bytes": 4_250_000_000,
        },
        "camera_count": 5,
        "light_count": 0,
        "sensor_count": 1,
        "viewer_count": 1,
        "chime_count": 0,
    }
    out = s.serialize_action(sample, tool_name="protect_get_system_info")
    assert out["success"] is True
    assert out["data"]["id"] == "nvr-1"
    assert out["data"]["model"] == "UNVR"
    assert out["data"]["camera_count"] == 5
    assert out["data"]["storage"]["utilization_pct"] == 42.5
    assert out["render_hint"]["kind"] == "detail"


def test_health_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("protect_get_health")
    sample = {
        "cpu": {"average_load": 1.2, "temperature_c": 45.0},
        "memory": {"available_bytes": 1_000_000, "free_bytes": 500_000, "total_bytes": 4_000_000},
        "storage": {
            "available_bytes": 5_000_000_000,
            "size_bytes": 10_000_000_000,
            "used_bytes": 5_000_000_000,
            "is_recycling": False,
            "type": "hdd",
        },
        "is_updating": False,
        "uptime_seconds": 99999,
    }
    out = s.serialize_action(sample, tool_name="protect_get_health")
    assert out["success"] is True
    assert out["data"]["cpu"]["temperature_c"] == 45.0
    assert out["data"]["memory"]["total_bytes"] == 4_000_000
    assert out["data"]["storage"]["is_recycling"] is False
    assert out["render_hint"]["kind"] == "detail"


def test_firmware_status_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("protect_get_firmware_status")
    sample = {
        "nvr": {
            "id": "nvr-1",
            "name": "Home NVR",
            "current_firmware": "4.0.0",
            "version": "4.0.0",
            "is_updating": False,
            "is_protect_updatable": True,
            "is_ucore_updatable": False,
            "last_device_fw_check": "2026-04-29T07:00:00+00:00",
        },
        "devices": [
            {
                "id": "cam1",
                "name": "Front Door",
                "type": "camera",
                "model": "G4",
                "current_firmware": "4.61.0",
                "latest_firmware": "4.62.0",
                "update_available": True,
                "is_updating": False,
            }
        ],
        "total_devices": 1,
        "devices_with_updates": 1,
    }
    out = s.serialize_action(sample, tool_name="protect_get_firmware_status")
    assert out["success"] is True
    assert out["data"]["nvr"]["id"] == "nvr-1"
    assert out["data"]["devices_with_updates"] == 1
    assert out["data"]["devices"][0]["update_available"] is True
    assert out["render_hint"]["kind"] == "detail"


def test_list_viewers_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("protect_list_viewers")
    # Tool layer wraps manager list in {viewers, count} dict.
    sample = {
        "viewers": [
            {
                "id": "viewer-1",
                "name": "Living Room",
                "type": "viewport",
                "mac": "11:22:33:44:55:66",
                "host": "192.0.2.20",
                "firmware_version": "2.0.0",
                "is_connected": True,
                "is_updating": False,
                "uptime_seconds": 3600,
                "state": "CONNECTED",
                "software_version": "2.0.0",
                "liveview_id": "lv-1",
            }
        ],
        "count": 1,
    }
    out = s.serialize_action(sample, tool_name="protect_list_viewers")
    assert out["success"] is True
    assert out["data"]["count"] == 1
    assert out["data"]["viewers"][0]["id"] == "viewer-1"
    assert out["data"]["viewers"][0]["liveview_id"] == "lv-1"
    assert out["render_hint"]["kind"] == "detail"
