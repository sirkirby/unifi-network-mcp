"""Access device mutation serializers.

Phase 6 PR4 Task A — the read serializer (``AccessDeviceSerializer``)
moved to a Strawberry type in ``unifi_api.graphql.types.access.devices``.
The ``access_list_devices`` / ``access_get_device`` tools are listed in
``PHASE6_TYPE_MIGRATED_TOOLS`` and dispatched via the type_registry by
both the REST routes and the action endpoint.

This module now only ships ``AccessDeviceMutationAckSerializer`` for the
``access_reboot_device`` preview-and-confirm tool, which still flows
through the manager's preview path and produces a dict ack.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "access_reboot_device": {"kind": RenderKind.DETAIL},
    },
)
class AccessDeviceMutationAckSerializer(Serializer):
    """DETAIL ack for ``access_reboot_device``. Preview/apply both return
    dicts; pass through. Bool coerces to ``{"success": bool}``."""

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if obj is None:
            return {"success": False}
        return {"result": str(obj)}
