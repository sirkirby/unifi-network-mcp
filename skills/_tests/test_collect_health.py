"""Tests for collect-health.py script."""
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# The script lives in the plugin's scripts/ directory — add it to sys.path for import.
_scripts_dir = Path(__file__).resolve().parent.parent.parent / (
    "plugins/unifi-network/skills/network-health-check/scripts"
)
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

# Import the module by filename (collect-health.py has a hyphen).
import importlib.util

_spec = importlib.util.spec_from_file_location("collect_health", _scripts_dir / "collect-health.py")
collect_health_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collect_health_mod)
# Register so unittest.mock.patch() can resolve "collect_health.MCPClient".
sys.modules["collect_health"] = collect_health_mod

# Pull out the names we need.
parse_args = collect_health_mod.parse_args
collect_health = collect_health_mod.collect_health
main = collect_health_mod.main
format_human = collect_health_mod.format_human
diff_against_baseline = collect_health_mod.diff_against_baseline
load_baseline = collect_health_mod.load_baseline
save_baseline = collect_health_mod.save_baseline
_parse_devices = collect_health_mod._parse_devices
_parse_health = collect_health_mod._parse_health
_parse_alarms = collect_health_mod._parse_alarms
_parse_system = collect_health_mod._parse_system
_determine_status = collect_health_mod._determine_status
_build_recommendations = collect_health_mod._build_recommendations


# ── Argument parsing tests ───────────────────────────────────────────────────


class TestParseArgs:
    def test_defaults(self):
        args = parse_args([])
        assert args.mcp_url is None
        assert args.output_format == "json"
        assert args.state_dir is None

    def test_mcp_url(self):
        args = parse_args(["--mcp-url", "http://myhost:4000"])
        assert args.mcp_url == "http://myhost:4000"

    def test_format_json(self):
        args = parse_args(["--format", "json"])
        assert args.output_format == "json"

    def test_format_human(self):
        args = parse_args(["--format", "human"])
        assert args.output_format == "human"

    def test_state_dir(self):
        args = parse_args(["--state-dir", "/tmp/my-state"])
        assert args.state_dir == "/tmp/my-state"

    def test_all_args(self):
        args = parse_args(["--mcp-url", "http://x:1234", "--format", "human", "--state-dir", "/tmp/s"])
        assert args.mcp_url == "http://x:1234"
        assert args.output_format == "human"
        assert args.state_dir == "/tmp/s"


# ── Parsing helper tests ────────────────────────────────────────────────────


class TestParseDevices:
    def test_empty(self):
        result = _parse_devices(None)
        assert result["total"] == 0
        assert result["offline_devices"] == []

    def test_all_online(self):
        devices = [{"state": 1, "name": "AP1", "mac": "aa:bb:cc:dd:ee:01"}]
        result = _parse_devices(devices)
        assert result["online"] == 1
        assert result["offline"] == 0

    def test_mixed_states(self):
        devices = [
            {"state": 1, "name": "AP1", "mac": "aa:bb:cc:dd:ee:01"},
            {"state": 0, "name": "Switch1", "mac": "aa:bb:cc:dd:ee:02", "model": "USW-24"},
            {"state": 6, "name": "AP2", "mac": "aa:bb:cc:dd:ee:03"},
            {"state": 5, "name": "GW", "mac": "aa:bb:cc:dd:ee:04"},
        ]
        result = _parse_devices(devices)
        assert result["total"] == 4
        assert result["online"] == 1
        assert result["offline"] == 1
        assert result["upgrading"] == 1
        assert result["other"] == 1
        assert len(result["offline_devices"]) == 1
        assert result["offline_devices"][0]["name"] == "Switch1"

    def test_string_state_labels(self):
        devices = [
            {"status": "online", "name": "AP1", "mac": "m1"},
            {"status": "offline", "name": "AP2", "mac": "m2"},
        ]
        result = _parse_devices(devices)
        assert result["online"] == 1
        assert result["offline"] == 1


class TestParseHealth:
    def test_empty(self):
        assert _parse_health(None) == {}

    def test_normal(self):
        data = [
            {"subsystem": "wan", "status": "ok"},
            {"subsystem": "lan", "status": "ok"},
            {"subsystem": "wlan", "status": "warning"},
        ]
        result = _parse_health(data)
        assert result == {"wan": "ok", "lan": "ok", "wlan": "warning"}

    def test_single_dict(self):
        result = _parse_health({"subsystem": "wan", "status": "error"})
        assert result == {"wan": "error"}


class TestParseAlarms:
    def test_empty(self):
        result = _parse_alarms(None)
        assert result == {"total": 0, "critical": 0, "warning": 0}

    def test_mixed(self):
        alarms = [
            {"severity": "critical", "msg": "AP lost contact"},
            {"severity": "warning", "msg": "High utilization"},
            {"severity": "informational", "msg": "Firmware update available"},
        ]
        result = _parse_alarms(alarms)
        assert result["total"] == 3
        assert result["critical"] == 1
        assert result["warning"] == 1


class TestParseSystem:
    def test_normal(self):
        result = _parse_system({"version": "8.1.113", "uptime": 86400})
        assert result == {"version": "8.1.113", "uptime": 86400}

    def test_none(self):
        result = _parse_system(None)
        assert result["version"] == "unknown"


# ── Status determination tests ───────────────────────────────────────────────


class TestDetermineStatus:
    def test_healthy(self):
        assert _determine_status({"wan": "ok", "lan": "ok"}, {"offline": 0}, {"total": 0}) == "healthy"

    def test_critical_from_health_error(self):
        assert _determine_status({"wan": "error"}, {"offline": 0}, {"total": 0}) == "critical"

    def test_critical_from_offline_device(self):
        assert _determine_status({"wan": "ok"}, {"offline": 1}, {"total": 0}) == "critical"

    def test_warning_from_health(self):
        assert _determine_status({"wan": "warning"}, {"offline": 0}, {"total": 0}) == "warning"

    def test_warning_from_alarms(self):
        assert _determine_status({"wan": "ok"}, {"offline": 0}, {"total": 2}) == "warning"


# ── Baseline diffing tests ───────────────────────────────────────────────────


class TestDiffBaseline:
    def test_first_run_no_baseline(self):
        changes = diff_against_baseline({"offline_devices": [], "alarms": {}, "health": {}}, None)
        assert any("First run" in c for c in changes)

    def test_no_changes(self):
        state = {"offline_devices": [], "alarms": {"total": 0}, "health": {"wan": "ok"}}
        changes = diff_against_baseline(state, state)
        assert changes == ["No changes since last run."]

    def test_new_offline_device(self):
        baseline = {"offline_devices": [], "alarms": {"total": 0}, "health": {"wan": "ok"}}
        current = {
            "offline_devices": [{"name": "Switch1", "mac": "aa:bb:cc:dd:ee:02"}],
            "alarms": {"total": 0},
            "health": {"wan": "ok"},
        }
        changes = diff_against_baseline(current, baseline)
        assert any("OFFLINE" in c and "Switch1" in c for c in changes)

    def test_device_came_online(self):
        baseline = {
            "offline_devices": [{"name": "Switch1", "mac": "aa:bb:cc:dd:ee:02"}],
            "alarms": {"total": 0},
            "health": {"wan": "ok"},
        }
        current = {"offline_devices": [], "alarms": {"total": 0}, "health": {"wan": "ok"}}
        changes = diff_against_baseline(current, baseline)
        assert any("ONLINE" in c and "Switch1" in c for c in changes)

    def test_new_alarms(self):
        baseline = {"offline_devices": [], "alarms": {"total": 1}, "health": {}}
        current = {"offline_devices": [], "alarms": {"total": 3}, "health": {}}
        changes = diff_against_baseline(current, baseline)
        assert any("2 new alarm" in c for c in changes)

    def test_subsystem_status_change(self):
        baseline = {"offline_devices": [], "alarms": {"total": 0}, "health": {"wan": "ok", "wlan": "ok"}}
        current = {"offline_devices": [], "alarms": {"total": 0}, "health": {"wan": "ok", "wlan": "warning"}}
        changes = diff_against_baseline(current, baseline)
        assert any("wlan" in c and "ok" in c and "warning" in c for c in changes)


# ── Baseline file I/O tests ──────────────────────────────────────────────────


class TestBaselineIO:
    def test_load_missing(self, tmp_path):
        assert load_baseline(tmp_path) is None

    def test_save_and_load(self, tmp_path):
        data = {"health": {"wan": "ok"}, "offline_devices": [], "alarms": {"total": 0}}
        save_baseline(tmp_path, data)
        loaded = load_baseline(tmp_path)
        assert loaded == data

    def test_load_corrupted(self, tmp_path):
        (tmp_path / "health-baseline.json").write_text("not json!")
        assert load_baseline(tmp_path) is None


# ── Health data collection (async, mocked MCP) ──────────────────────────────


def _make_mock_client(tool_results: dict, ready: bool = True):
    """Create a mock MCPClient that returns canned results."""
    client = AsyncMock()
    client.check_ready = AsyncMock(return_value=ready)
    client.get_setup_error = AsyncMock(return_value={
        "success": False,
        "error": "setup_required",
        "message": "MCP server not reachable.",
    })

    async def fake_parallel(calls):
        return [tool_results.get(name, {"success": False, "error": f"{name} not mocked"}) for name, _ in calls]

    client.call_tools_parallel = AsyncMock(side_effect=fake_parallel)

    # Support async context manager.
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


HEALTHY_TOOL_RESULTS = {
    "unifi_get_system_info": {"success": True, "data": {"version": "8.1.113", "uptime": 172800}},
    "unifi_get_network_health": {
        "success": True,
        "data": [
            {"subsystem": "wan", "status": "ok"},
            {"subsystem": "lan", "status": "ok"},
            {"subsystem": "wlan", "status": "ok"},
            {"subsystem": "vpn", "status": "ok"},
        ],
    },
    "unifi_list_devices": {
        "success": True,
        "data": [
            {"name": "Gateway", "mac": "aa:00:00:00:00:01", "state": 1, "model": "UDM-Pro"},
            {"name": "AP-LR", "mac": "aa:00:00:00:00:02", "state": 1, "model": "U6-LR"},
            {"name": "Switch24", "mac": "aa:00:00:00:00:03", "state": 1, "model": "USW-24-POE"},
        ],
    },
    "unifi_list_alarms": {"success": True, "data": []},
}


@pytest.mark.asyncio
async def test_collect_health_healthy(tmp_path):
    """Test full collection with a healthy network."""
    mock_client = _make_mock_client(HEALTHY_TOOL_RESULTS)

    with patch(f"{collect_health_mod.__name__}.MCPClient", return_value=mock_client):
        result = await collect_health("http://localhost:3000", tmp_path)

    assert result["success"] is True
    assert result["status"] == "healthy"
    assert result["system"]["version"] == "8.1.113"
    assert result["devices"]["total"] == 3
    assert result["devices"]["online"] == 3
    assert result["devices"]["offline"] == 0
    assert result["alarms"]["total"] == 0
    assert result["offline_devices"] == []
    assert "timestamp" in result
    assert len(result["recommendations"]) > 0


@pytest.mark.asyncio
async def test_collect_health_with_issues(tmp_path):
    """Test collection with offline devices and alarms."""
    results = {
        "unifi_get_system_info": {"success": True, "data": {"version": "8.1.113", "uptime": 3600}},
        "unifi_get_network_health": {
            "success": True,
            "data": [
                {"subsystem": "wan", "status": "ok"},
                {"subsystem": "lan", "status": "warning"},
                {"subsystem": "wlan", "status": "error"},
            ],
        },
        "unifi_list_devices": {
            "success": True,
            "data": [
                {"name": "Gateway", "mac": "aa:00:00:00:00:01", "state": 1},
                {"name": "AP-Down", "mac": "aa:00:00:00:00:02", "state": 0, "model": "U6-LR"},
            ],
        },
        "unifi_list_alarms": {
            "success": True,
            "data": [
                {"severity": "critical", "msg": "AP lost contact"},
                {"severity": "warning", "msg": "High CPU"},
            ],
        },
    }
    mock_client = _make_mock_client(results)

    with patch(f"{collect_health_mod.__name__}.MCPClient", return_value=mock_client):
        result = await collect_health("http://localhost:3000", tmp_path)

    assert result["success"] is True
    assert result["status"] == "critical"
    assert result["devices"]["offline"] == 1
    assert result["alarms"]["critical"] == 1
    assert len(result["offline_devices"]) == 1
    assert result["offline_devices"][0]["name"] == "AP-Down"


@pytest.mark.asyncio
async def test_collect_health_setup_required(tmp_path):
    """Test that unreachable server returns setup_required error."""
    mock_client = _make_mock_client({}, ready=False)

    with patch(f"{collect_health_mod.__name__}.MCPClient", return_value=mock_client):
        result = await collect_health("http://localhost:3000", tmp_path)

    assert result["success"] is False
    assert result["error"] == "setup_required"


@pytest.mark.asyncio
async def test_collect_health_saves_baseline(tmp_path):
    """Test that running the collector saves a baseline file."""
    mock_client = _make_mock_client(HEALTHY_TOOL_RESULTS)

    with patch(f"{collect_health_mod.__name__}.MCPClient", return_value=mock_client):
        await collect_health("http://localhost:3000", tmp_path)

    baseline_path = tmp_path / "health-baseline.json"
    assert baseline_path.exists()
    baseline = json.loads(baseline_path.read_text())
    assert "health" in baseline
    assert "offline_devices" in baseline


@pytest.mark.asyncio
async def test_collect_health_diffs_baseline(tmp_path):
    """Test that second run detects changes from baseline."""
    # First run: all healthy.
    mock_client = _make_mock_client(HEALTHY_TOOL_RESULTS)
    with patch(f"{collect_health_mod.__name__}.MCPClient", return_value=mock_client):
        first = await collect_health("http://localhost:3000", tmp_path)

    assert any("First run" in c for c in first["changes_since_last_run"])

    # Second run: a device went offline.
    results_with_offline = dict(HEALTHY_TOOL_RESULTS)
    results_with_offline["unifi_list_devices"] = {
        "success": True,
        "data": [
            {"name": "Gateway", "mac": "aa:00:00:00:00:01", "state": 1, "model": "UDM-Pro"},
            {"name": "AP-LR", "mac": "aa:00:00:00:00:02", "state": 0, "model": "U6-LR"},
            {"name": "Switch24", "mac": "aa:00:00:00:00:03", "state": 1, "model": "USW-24-POE"},
        ],
    }
    mock_client2 = _make_mock_client(results_with_offline)
    with patch(f"{collect_health_mod.__name__}.MCPClient", return_value=mock_client2):
        second = await collect_health("http://localhost:3000", tmp_path)

    assert any("OFFLINE" in c and "AP-LR" in c for c in second["changes_since_last_run"])


@pytest.mark.asyncio
async def test_collect_health_tool_error_result(tmp_path):
    """Test handling of tool calls that return error responses."""
    results = {
        "unifi_get_system_info": {"success": False, "error": "Connection timed out"},
        "unifi_get_network_health": {"success": True, "data": []},
        "unifi_list_devices": {"success": True, "data": []},
        "unifi_list_alarms": {"success": True, "data": []},
    }
    mock_client = _make_mock_client(results)

    with patch(f"{collect_health_mod.__name__}.MCPClient", return_value=mock_client):
        result = await collect_health("http://localhost:3000", tmp_path)

    # Should still succeed overall — failed tool yields "unknown" values.
    assert result["success"] is True
    assert result["system"]["version"] == "unknown"


# ── JSON output structure validation ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_output_structure(tmp_path):
    """Validate that output has all required top-level keys."""
    mock_client = _make_mock_client(HEALTHY_TOOL_RESULTS)

    with patch(f"{collect_health_mod.__name__}.MCPClient", return_value=mock_client):
        result = await collect_health("http://localhost:3000", tmp_path)

    required_keys = {
        "success",
        "timestamp",
        "status",
        "system",
        "health",
        "devices",
        "alarms",
        "changes_since_last_run",
        "offline_devices",
        "recommendations",
    }
    assert required_keys.issubset(set(result.keys()))

    # Validate nested structures.
    assert isinstance(result["system"], dict)
    assert "version" in result["system"]
    assert "uptime" in result["system"]

    assert isinstance(result["health"], dict)

    devs = result["devices"]
    for key in ("total", "online", "offline", "upgrading", "other"):
        assert key in devs

    alarms = result["alarms"]
    for key in ("total", "critical", "warning"):
        assert key in alarms

    assert isinstance(result["changes_since_last_run"], list)
    assert isinstance(result["offline_devices"], list)
    assert isinstance(result["recommendations"], list)


# ── Human-readable format tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_human_format(tmp_path):
    """Test human-readable output contains expected sections."""
    mock_client = _make_mock_client(HEALTHY_TOOL_RESULTS)

    with patch(f"{collect_health_mod.__name__}.MCPClient", return_value=mock_client):
        result = await collect_health("http://localhost:3000", tmp_path)

    text = format_human(result)
    assert "Network Health Report" in text
    assert "HEALTHY" in text
    assert "8.1.113" in text
    assert "Recommendations" in text


# ── Recommendations tests ────────────────────────────────────────────────────


class TestRecommendations:
    def test_healthy_network(self):
        recs = _build_recommendations({"wan": "ok", "lan": "ok"}, {"offline": 0, "upgrading": 0}, {"total": 0, "critical": 0, "warning": 0})
        assert any("healthy" in r.lower() for r in recs)

    def test_wan_down(self):
        recs = _build_recommendations({"wan": "error"}, {"offline": 0, "upgrading": 0}, {"total": 0, "critical": 0, "warning": 0})
        assert any("WAN" in r for r in recs)

    def test_offline_devices(self):
        recs = _build_recommendations({"wan": "ok"}, {"offline": 2, "upgrading": 0}, {"total": 0, "critical": 0, "warning": 0})
        assert any("2 device" in r for r in recs)

    def test_critical_alarms(self):
        recs = _build_recommendations({"wan": "ok"}, {"offline": 0, "upgrading": 0}, {"total": 1, "critical": 1, "warning": 0})
        assert any("critical" in r.lower() for r in recs)
