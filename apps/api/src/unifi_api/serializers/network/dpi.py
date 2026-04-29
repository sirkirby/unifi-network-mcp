"""DPI application + category serializers (Phase 4A PR1 Cluster 4).

``DpiManager`` reaches the official integration API and returns paginated
wrapper dicts (``{"data": [...], "totalCount", "offset", "limit"}``).
The DPI tool layer unwraps to a bare list for the action layer, so this
serializer expects a list of dicts; if the wrapper itself slips through
the registry will emit a sensible single-record DETAIL of the wrapper
metadata, but the LIST flow only ever sees the items.

Each application carries an ``id`` (compound:
``(category_id << 16) | app_id``), a ``name``, and (often) a
``categoryId`` linking it to a DPI category. Categories carry just
``id`` + ``name``.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "unifi_list_dpi_applications": {"kind": RenderKind.LIST},
    },
)
class DpiApplicationSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "category_id"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        # DPI ids can be 0 (e.g. category 0 = Instant messengers); avoid the
        # ``a or b`` pattern that collapses 0 → None.
        ident = _get(obj, "id")
        if ident is None:
            ident = _get(obj, "_id")
        cat = _get(obj, "categoryId")
        if cat is None:
            cat = _get(obj, "category_id")
        return {
            "id": ident,
            "name": _get(obj, "name"),
            "category_id": cat,
        }


@register_serializer(
    tools={
        "unifi_list_dpi_categories": {"kind": RenderKind.LIST},
    },
)
class DpiCategorySerializer(Serializer):
    primary_key = "id"
    display_columns = ["name"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        ident = _get(obj, "id")
        if ident is None:
            ident = _get(obj, "_id")
        return {
            "id": ident,
            "name": _get(obj, "name"),
        }
