"""System / alarms / backups / settings serializers (Phase 4A PR1 Cluster 6).

Covers:
- LIST: ``unifi_list_alarms``, ``unifi_list_backups``, ``unifi_get_top_clients``,
  ``unifi_get_speedtest_results``, ``unifi_get_network_health`` (manager
  returns multi-element list of subsystems).
- DETAIL: ``unifi_get_system_info``, ``unifi_get_site_settings``,
  ``unifi_get_snmp_settings`` (manager returns ``list[dict]``; serializer
  unwraps the first item), ``unifi_get_event_types`` (list of prefix
  descriptors wrapped under ``event_types`` key for stable shape),
  ``unifi_get_autobackup_settings``.
- DETAIL passthrough+bool coercion (mutation acks):
  ``unifi_archive_alarm``, ``unifi_archive_all_alarms``,
  ``unifi_create_backup``, ``unifi_delete_backup``,
  ``unifi_update_autobackup_settings``.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj, *keys, default=None):
    if not isinstance(obj, dict):
        return default
    for k in keys:
        v = obj.get(k)
        if v is not None:
            return v
    return default


# ---- Alarms (LIST) ----


@register_serializer(
    tools={
        "unifi_list_alarms": {"kind": RenderKind.LIST},
    },
)
class AlarmSerializer(Serializer):
    primary_key = "id"
    sort_default = "time:desc"
    display_columns = ["time", "key", "msg", "archived"]

    @staticmethod
    def serialize(record) -> dict:
        if not isinstance(record, dict):
            return {"id": None}
        return {
            "id": _get(record, "_id", "id"),
            "key": _get(record, "key", "event_type"),
            "msg": _get(record, "msg", "message"),
            "archived": bool(record.get("archived", False)),
            "time": _get(record, "time", "timestamp"),
        }


# ---- Backups (LIST) ----


@register_serializer(
    tools={
        "unifi_list_backups": {"kind": RenderKind.LIST},
    },
)
class BackupSerializer(Serializer):
    primary_key = "id"
    display_columns = ["filename", "size", "created_at"]

    @staticmethod
    def serialize(record) -> dict:
        if not isinstance(record, dict):
            return {"id": None}
        return {
            "id": _get(record, "_id", "id"),
            "filename": _get(record, "filename", "name"),
            "size": _get(record, "size"),
            "created_at": _get(record, "time", "created_at", "timestamp"),
        }


# ---- System info (DETAIL) ----


@register_serializer(
    tools={
        "unifi_get_system_info": {"kind": RenderKind.DETAIL},
    },
)
class SystemInfoSerializer(Serializer):
    @staticmethod
    def serialize(obj) -> dict:
        if not isinstance(obj, dict):
            return {}
        return {
            "name": _get(obj, "name", "controller_name"),
            "version": _get(obj, "version", "build"),
            "hostname": _get(obj, "hostname", "host"),
            "uptime": _get(obj, "uptime"),
            "num_devices": _get(obj, "num_devices"),
            "num_clients": _get(obj, "num_clients"),
        }


# ---- Network health (LIST — manager returns multiple subsystems) ----


@register_serializer(
    tools={
        "unifi_get_network_health": {"kind": RenderKind.LIST},
    },
)
class NetworkHealthSerializer(Serializer):
    primary_key = "subsystem"
    display_columns = ["subsystem", "status", "num_user", "rx_bytes", "tx_bytes"]

    @staticmethod
    def serialize(record) -> dict:
        if not isinstance(record, dict):
            return {}
        return {
            "subsystem": _get(record, "subsystem"),
            "status": _get(record, "status"),
            "num_user": _get(record, "num_user"),
            "num_guest": _get(record, "num_guest"),
            "num_iot": _get(record, "num_iot"),
            "rx_bytes": _get(record, "rx_bytes-r", "rx_bytes"),
            "tx_bytes": _get(record, "tx_bytes-r", "tx_bytes"),
        }


# ---- Site settings (DETAIL) ----


@register_serializer(
    tools={
        "unifi_get_site_settings": {"kind": RenderKind.DETAIL},
    },
)
class SiteSettingsSerializer(Serializer):
    @staticmethod
    def serialize(obj) -> dict:
        if not isinstance(obj, dict):
            return {}
        return {
            "site_id": _get(obj, "_id", "site_id"),
            "name": _get(obj, "name"),
            "role": _get(obj, "role"),
            "country": _get(obj, "country"),
        }


# ---- SNMP settings (DETAIL — manager returns list[dict], unwrap first) ----


@register_serializer(
    tools={
        "unifi_get_snmp_settings": {"kind": RenderKind.DETAIL},
    },
)
class SnmpSettingsSerializer(Serializer):
    @staticmethod
    def serialize(obj) -> dict:
        # Manager returns list[dict]; serializer unwraps first item.
        if isinstance(obj, list):
            obj = obj[0] if obj else {}
        if not isinstance(obj, dict):
            return {}
        return {
            "enabled": bool(obj.get("enabled", False)),
            "community": _get(obj, "community", default=""),
            "port": _get(obj, "port"),
            "version": _get(obj, "version"),
        }


# ---- Event types (DETAIL — wrap list under stable key) ----


@register_serializer(
    tools={
        "unifi_get_event_types": {"kind": RenderKind.DETAIL},
    },
)
class EventTypesSerializer(Serializer):
    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, list):
            return {"event_types": [e for e in obj if isinstance(e, dict)]}
        if isinstance(obj, dict):
            # Already shaped {prefix: descriptor} or wrapping list.
            inner = obj.get("event_types")
            if isinstance(inner, list):
                return {"event_types": inner}
            return {"event_types": [obj]}
        return {"event_types": []}


# ---- Auto-backup settings (DETAIL) ----


@register_serializer(
    tools={
        "unifi_get_autobackup_settings": {"kind": RenderKind.DETAIL},
    },
)
class AutoBackupSettingsSerializer(Serializer):
    @staticmethod
    def serialize(obj) -> dict:
        if not isinstance(obj, dict):
            return {}
        return {
            "enabled": bool(obj.get("enabled", False)),
            "schedule": _get(obj, "schedule", "cron"),
            "max_count": _get(obj, "max_count", "max_backups"),
        }


# ---- Top clients (LIST) ----


@register_serializer(
    tools={
        "unifi_get_top_clients": {"kind": RenderKind.LIST},
    },
)
class TopClientsSerializer(Serializer):
    primary_key = "mac"
    sort_default = "total_bytes:desc"
    display_columns = ["mac", "hostname", "total_bytes"]

    @staticmethod
    def serialize(record) -> dict:
        if not isinstance(record, dict):
            return {"mac": None}
        return {
            "mac": _get(record, "mac"),
            "hostname": _get(record, "name", "hostname"),
            "tx_bytes": _get(record, "tx_bytes"),
            "rx_bytes": _get(record, "rx_bytes"),
            "total_bytes": _get(record, "total_bytes", "bytes"),
        }


# ---- Speedtest results (LIST) ----


@register_serializer(
    tools={
        "unifi_get_speedtest_results": {"kind": RenderKind.LIST},
    },
)
class SpeedtestResultSerializer(Serializer):
    sort_default = "timestamp:desc"
    display_columns = ["timestamp", "download_mbps", "upload_mbps", "latency_ms"]

    @staticmethod
    def serialize(record) -> dict:
        if not isinstance(record, dict):
            return {}
        return {
            "timestamp": _get(record, "time", "timestamp"),
            "download_mbps": _get(record, "xput_download", "download_mbps"),
            "upload_mbps": _get(record, "xput_upload", "upload_mbps"),
            "latency_ms": _get(record, "latency", "latency_ms"),
        }


# ---- Mutation acks (DETAIL passthrough + bool coercion) ----


@register_serializer(
    tools={
        "unifi_archive_alarm": {"kind": RenderKind.DETAIL},
        "unifi_archive_all_alarms": {"kind": RenderKind.DETAIL},
        "unifi_create_backup": {"kind": RenderKind.DETAIL},
        "unifi_delete_backup": {"kind": RenderKind.DETAIL},
        "unifi_update_autobackup_settings": {"kind": RenderKind.DETAIL},
    },
)
class SystemMutationAckSerializer(Serializer):
    """DETAIL ack for system mutations.

    Managers return ``bool`` (archive/delete/update) or ``Optional[Dict]``
    (``create_backup``). Bool maps to ``{"success": <bool>}``; dicts pass
    through; ``None`` maps to ``{"success": False}``.
    """

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if obj is None:
            return {"success": False}
        raw = getattr(obj, "raw", None)
        if isinstance(raw, dict):
            return raw
        return {"result": str(obj)}
