"""Access credential serializer.

``CredentialManager.list_credentials`` / ``get_credential`` return plain
dicts as supplied by the proxy/API path. Field names follow the
controller's snake-case convention.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "access_list_credentials": {"kind": RenderKind.LIST},
        "access_get_credential": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("access", "credentials"), {"kind": RenderKind.LIST}),
        (("access", "credentials/{id}"), {"kind": RenderKind.DETAIL}),
    ],
)
class CredentialSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["user_id", "type", "status", "expiry"]
    sort_default = "user_id"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "user_id": _get(obj, "user_id"),
            "type": _get(obj, "type"),
            "status": _get(obj, "status"),
            "expiry": _get(obj, "expiry"),
            "last_used": _get(obj, "last_used"),
        }
