"""Network stats cluster serializer unit tests (Phase 4A PR1 Cluster 6).

Covers TIMESERIES tools (per-point shape: {ts, ...metrics}) plus a small
number of stats tools whose AST-captured manager method returns a single
dict and therefore lands as DETAIL instead of TIMESERIES (device_stats,
client_stats, dpi_stats).
"""

from unifi_api.serializers._registry import (
    discover_serializers,
    serializer_registry_singleton,
)


def _registry():
    discover_serializers(manifest_tool_names=set())
    return serializer_registry_singleton()


# ---- TIMESERIES (list-returning manager methods) ----


def test_timeseries_serializer_normalizes_seconds_to_ms() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_dashboard")
    sample = [
        {"time": 1714000000, "rx_bytes": 1024, "tx_bytes": 2048},
        {"time": 1714000300, "rx_bytes": 4096, "tx_bytes": 8192},
    ]
    out = s.serialize_action(sample, tool_name="unifi_get_dashboard")
    assert out["success"] is True
    assert out["render_hint"]["kind"] == "timeseries"
    assert out["data"][0]["ts"] == 1714000000 * 1000
    assert out["data"][0]["rx_bytes"] == 1024
    assert out["data"][1]["ts"] == 1714000300 * 1000
    assert "time" not in out["data"][0]


def test_timeseries_serializer_passes_ms_through() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_network_stats")
    sample = [{"ts": 1714000000123, "wan_rx": 100}]
    out = s.serialize_action(sample, tool_name="unifi_get_network_stats")
    assert out["data"][0]["ts"] == 1714000000123
    assert out["data"][0]["wan_rx"] == 100


def test_timeseries_dispatches_for_all_list_returning_stats_tools() -> None:
    reg = _registry()
    for tool in (
        "unifi_get_dashboard",
        "unifi_get_network_stats",
        "unifi_get_gateway_stats",
        "unifi_get_client_dpi_traffic",
        "unifi_get_site_dpi_traffic",
    ):
        s = reg.serializer_for_tool(tool)
        out = s.serialize_action([{"time": 1, "v": 2}], tool_name=tool)
        assert out["render_hint"]["kind"] == "timeseries"


# ---- TIMESERIES stats (PR4 dispatch override now points at list-returning
# stats_manager.get_device_stats / get_client_stats) ----


def test_device_stats_timeseries_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_device_stats")
    sample = [
        {"time": 1_700_000_000, "rx_bytes": 1, "tx_bytes": 2},
        {"time": 1_700_000_300, "rx_bytes": 3, "tx_bytes": 4},
    ]
    out = s.serialize_action(sample, tool_name="unifi_get_device_stats")
    assert out["success"] is True
    assert out["render_hint"]["kind"] == "timeseries"
    assert isinstance(out["data"], list) and len(out["data"]) == 2
    assert out["data"][0]["ts"] == 1_700_000_000_000  # seconds → ms


def test_client_stats_timeseries_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_client_stats")
    sample = [{"timestamp": 1_700_000_000_000, "tx_bytes": 100}]
    out = s.serialize_action(sample, tool_name="unifi_get_client_stats")
    assert out["render_hint"]["kind"] == "timeseries"
    assert out["data"][0]["ts"] == 1_700_000_000_000
    assert out["data"][0]["tx_bytes"] == 100


def test_dpi_stats_detail_serializer_shape() -> None:
    """get_dpi_stats returns dict {applications: [...], categories: [...]}."""
    reg = _registry()
    s = reg.serializer_for_tool("unifi_get_dpi_stats")
    sample = {"applications": [{"name": "Netflix"}], "categories": [{"name": "Streaming"}]}
    out = s.serialize_action(sample, tool_name="unifi_get_dpi_stats")
    assert out["render_hint"]["kind"] == "detail"
    assert out["data"]["applications"][0]["name"] == "Netflix"
    assert out["data"]["categories"][0]["name"] == "Streaming"
