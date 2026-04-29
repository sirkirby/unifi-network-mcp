"""Access user serializer.

``SystemManager.list_users`` returns dicts shaped by the proxy
``users`` endpoint. There is no per-user GET tool in the Access manifest
today, so we register the LIST tool and both LIST + DETAIL resources
(detail is reachable via the resources endpoint by id).

Name handling: prefer the explicit ``name`` field, otherwise stitch
``first_name`` + ``last_name`` together.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _name(obj: Any) -> str | None:
    name = _get(obj, "name")
    if name:
        return name
    first = _get(obj, "first_name") or ""
    last = _get(obj, "last_name") or ""
    full = f"{first} {last}".strip()
    return full or None


@register_serializer(
    tools={
        "access_list_users": {"kind": RenderKind.LIST},
    },
    resources=[
        (("access", "users"), {"kind": RenderKind.LIST}),
        (("access", "users/{id}"), {"kind": RenderKind.DETAIL}),
    ],
)
class UserSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "employee_id", "status", "role"]
    sort_default = "name"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "name": _name(obj),
            "employee_id": _get(obj, "employee_id"),
            "status": _get(obj, "status"),
            "role": _get(obj, "role"),
            "created_at": _get(obj, "created_at"),
        }
