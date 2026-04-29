"""Stats serializers (Phase 4A PR1 Cluster 6).

TIMESERIES tools share a per-point shape — `{ts: <ms>, ...metrics}` — locked
in spec §5 (amended April 29, 2026). Window/step metadata moves to
`render_hint`, not `data`, to fit Phase 3's `serialize_action` contract
(TIMESERIES iterates `serialize` per item, same as EVENT_LOG).

A handful of nominally-stats tools are registered as DETAIL because the
AST-captured manager method returns a single dict rather than a list:

- ``unifi_get_device_stats`` → ``device_manager.get_device_details`` (dict)
- ``unifi_get_client_stats`` → ``client_manager.get_client_details`` (dict)
- ``unifi_get_dpi_stats`` → ``stats_manager.get_dpi_stats`` (Dict[str, List])

For these, fields are passed through and curated to the keys most relevant
for stats consumption. Phase 5 (which fixes the AST limitation) can revisit
whether dedicated stats endpoints exist.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _normalize_ts(point: dict) -> int:
    ts = point.get("ts") or point.get("time") or point.get("timestamp") or 0
    if ts and ts < 10_000_000_000:  # likely seconds → ms
        ts = ts * 1000
    return ts


@register_serializer(
    tools={
        "unifi_get_dashboard": {"kind": RenderKind.TIMESERIES},
        "unifi_get_network_stats": {"kind": RenderKind.TIMESERIES},
        "unifi_get_gateway_stats": {"kind": RenderKind.TIMESERIES},
        "unifi_get_client_dpi_traffic": {"kind": RenderKind.TIMESERIES},
        "unifi_get_site_dpi_traffic": {"kind": RenderKind.TIMESERIES},
    },
)
class TimeseriesSerializer(Serializer):
    """Serialize a single point: ``{ts: <ms>, ...metric_keys}``.

    Window/step metadata lives in ``render_hint``; per spec §5 the
    serialized ``data`` is ``list[point]``.
    """

    sort_default = "ts:desc"

    @staticmethod
    def serialize(point) -> dict:
        if not isinstance(point, dict):
            return {"ts": 0}
        ts = _normalize_ts(point)
        return {
            "ts": ts,
            **{k: v for k, v in point.items() if k not in ("time", "timestamp", "ts")},
        }


@register_serializer(
    tools={
        "unifi_get_device_stats": {"kind": RenderKind.DETAIL},
        "unifi_get_client_stats": {"kind": RenderKind.DETAIL},
    },
)
class StatsDetailSerializer(Serializer):
    """Detail serializer for stats tools whose AST-captured manager method
    returns a single dict (e.g. ``get_device_details``)."""

    @staticmethod
    def serialize(obj) -> dict:
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return dict(obj)
        raw = getattr(obj, "raw", None)
        if isinstance(raw, dict):
            return dict(raw)
        return {"value": str(obj)}


@register_serializer(
    tools={
        "unifi_get_dpi_stats": {"kind": RenderKind.DETAIL},
    },
)
class DpiStatsSerializer(Serializer):
    """``get_dpi_stats`` returns ``{applications: [...], categories: [...]}``."""

    @staticmethod
    def serialize(obj) -> dict:
        if not isinstance(obj, dict):
            return {"applications": [], "categories": []}

        def _itemize(items):
            out = []
            for it in items or []:
                if isinstance(it, dict):
                    out.append(it)
                else:
                    raw = getattr(it, "raw", None)
                    if isinstance(raw, dict):
                        out.append(dict(raw))
            return out

        return {
            "applications": _itemize(obj.get("applications")),
            "categories": _itemize(obj.get("categories")),
        }
