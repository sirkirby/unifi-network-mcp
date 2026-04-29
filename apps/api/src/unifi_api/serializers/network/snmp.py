"""SNMP settings serializer (Phase 4A PR1 Cluster 5).

The SNMP tool exposes only a single mutation
(``unifi_update_snmp_settings``); reads are not currently surfaced as
tools. This serializer provides a passthrough DETAIL ack with bool
coercion to match the established mutation-ack pattern.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "unifi_update_snmp_settings": {"kind": RenderKind.DETAIL},
    },
)
class SnmpMutationAckSerializer(Serializer):
    """DETAIL ack for SNMP settings update.

    Manager returns ``bool`` on success; passes through dict payloads
    unchanged for any future detail-style responses."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        raw = getattr(obj, "raw", None)
        if isinstance(raw, dict):
            return raw
        if obj is None:
            return {"success": False}
        return {"result": str(obj)}
