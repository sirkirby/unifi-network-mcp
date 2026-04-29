"""Static + active + traffic route serializers (Phase 4A PR1 Cluster 3).

Three managers feed this module:

* ``RoutingManager`` — ``get_routes()`` / ``get_route_details()`` /
  ``get_active_routes()``. Static routes use the V1 ``/rest/routing``
  endpoint with hyphen-prefixed fields (``static-route_network``,
  ``static-route_nexthop``, ``static-route_distance``). Active routes come
  from the undocumented ``/stat/routing`` endpoint and may include nh
  (next-hop) sublists, ``pfx`` (prefix), ``metric``, and ``t`` (type).
* ``TrafficRouteManager`` — V2 ``/trafficroutes``. Returns ``List[Dict]``.
  Note: traffic routes use ``description`` for the human-readable name and
  ``matching_target`` (DOMAIN/IP/REGION) for what triggers the route.
* Cross-cutting mutation ack covering all CUD entry points across both.

``unifi_create_route`` is from RoutingManager; ``unifi_update_traffic_route``
and ``unifi_toggle_traffic_route`` are from TrafficRouteManager — all return
``bool`` (or in the case of create, an ``Optional[Dict]``).
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


def _summarize_targets(value: Any) -> Any:
    """Collapse a list of target dicts to either a count or the raw list."""
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return value


@register_serializer(
    tools={
        "unifi_list_routes": {"kind": RenderKind.LIST},
        "unifi_get_route_details": {"kind": RenderKind.DETAIL},
    },
)
class RouteSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "target_subnet", "gateway", "distance", "enabled"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "target_subnet": _get(obj, "static-route_network")
            or _get(obj, "target_subnet")
            or _get(obj, "network"),
            "gateway": _get(obj, "static-route_nexthop")
            or _get(obj, "gateway")
            or _get(obj, "nexthop"),
            "distance": _get(obj, "static-route_distance")
            or _get(obj, "distance"),
            "enabled": bool(_get(obj, "enabled", True)),
        }


@register_serializer(
    tools={
        "unifi_list_active_routes": {"kind": RenderKind.LIST},
    },
)
class ActiveRouteSerializer(Serializer):
    primary_key = "target_subnet"
    display_columns = ["target_subnet", "gateway", "interface", "distance"]

    @staticmethod
    def serialize(obj) -> dict:
        # /stat/routing returns nh as a list of {via, intf} dicts; pluck the
        # first to populate gateway/interface. Falls through cleanly when the
        # endpoint emits a flatter shape.
        nh_list = _get(obj, "nh") or []
        first_nh: dict[str, Any] = nh_list[0] if isinstance(nh_list, list) and nh_list else {}
        return {
            "target_subnet": _get(obj, "pfx")
            or _get(obj, "target_subnet")
            or _get(obj, "network"),
            "gateway": first_nh.get("via")
            or _get(obj, "gateway")
            or _get(obj, "nexthop"),
            "interface": first_nh.get("intf")
            or _get(obj, "interface")
            or _get(obj, "intf"),
            "distance": _get(obj, "metric") or _get(obj, "distance"),
        }


@register_serializer(
    tools={
        "unifi_list_traffic_routes": {"kind": RenderKind.LIST},
        "unifi_get_traffic_route_details": {"kind": RenderKind.DETAIL},
    },
)
class TrafficRouteSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "matching_target", "next_hop", "enabled"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "description") or _get(obj, "name"),
            "matching_target": _get(obj, "matching_target"),
            "source_targets": _summarize_targets(_get(obj, "target_devices")),
            "destination_targets": _summarize_targets(
                _get(obj, "domains")
                or _get(obj, "ip_addresses")
                or _get(obj, "ip_ranges")
                or _get(obj, "regions")
            ),
            "next_hop": _get(obj, "next_hop") or _get(obj, "network_id"),
            "enabled": bool(_get(obj, "enabled", True)),
        }


@register_serializer(
    tools={
        "unifi_create_route": {"kind": RenderKind.DETAIL},
        "unifi_update_route": {"kind": RenderKind.DETAIL},
        "unifi_update_traffic_route": {"kind": RenderKind.DETAIL},
        "unifi_toggle_traffic_route": {"kind": RenderKind.DETAIL},
    },
)
class RouteMutationAckSerializer(Serializer):
    """DETAIL ack for static + traffic route mutations.

    ``create_route`` returns the created dict; the rest return ``bool``."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        raw = getattr(obj, "raw", None)
        if isinstance(raw, dict):
            return raw
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
