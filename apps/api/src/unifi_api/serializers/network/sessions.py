"""Client sessions and wifi-details serializers (Phase 4A PR1 Cluster 6).

- ``unifi_get_client_sessions`` (LIST) — historical association sessions
  with ``connected_at``/``disconnected_at`` and duration.
- ``unifi_get_client_wifi_details`` (DETAIL) — current WiFi parameters for
  a specific client (signal, rates, channel).
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


@register_serializer(
    tools={
        "unifi_get_client_sessions": {"kind": RenderKind.LIST},
    },
)
class ClientSessionSerializer(Serializer):
    primary_key = "connected_at"
    sort_default = "connected_at:desc"
    display_columns = ["mac", "hostname", "ssid", "connected_at", "duration"]

    @staticmethod
    def serialize(record) -> dict:
        if not isinstance(record, dict):
            return {}
        return {
            "mac": _get(record, "mac"),
            "hostname": _get(record, "hostname", "name"),
            "ap": _get(record, "ap", "ap_mac"),
            "ssid": _get(record, "essid", "ssid"),
            "connected_at": _get(record, "assoc_time", "connected_at", "first_seen"),
            "disconnected_at": _get(record, "disassoc_time", "disconnected_at", "last_seen"),
            "duration": _get(record, "duration"),
        }


@register_serializer(
    tools={
        "unifi_get_client_wifi_details": {"kind": RenderKind.DETAIL},
    },
)
class ClientWifiDetailsSerializer(Serializer):
    @staticmethod
    def serialize(obj) -> dict:
        if obj is None:
            return {}
        if not isinstance(obj, dict):
            raw = getattr(obj, "raw", None)
            obj = raw if isinstance(raw, dict) else {}
        return {
            "mac": _get(obj, "mac"),
            "ssid": _get(obj, "essid", "ssid"),
            "ap": _get(obj, "ap_mac", "ap"),
            "signal": _get(obj, "signal", "rssi"),
            "tx_rate": _get(obj, "tx_rate"),
            "rx_rate": _get(obj, "rx_rate"),
            "channel": _get(obj, "channel"),
        }
