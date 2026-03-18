"""Tests for security digest collector and digest generator."""
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# ── Import collector module ─────────────────────────────────────────────────

_scripts_dir = Path(__file__).resolve().parent.parent.parent / (
    "plugins/unifi-protect/skills/security-digest/scripts"
)
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import importlib.util

# Import collector.py
_collector_spec = importlib.util.spec_from_file_location("collector", _scripts_dir / "collector.py")
collector_mod = importlib.util.module_from_spec(_collector_spec)
_collector_spec.loader.exec_module(collector_mod)
sys.modules["collector"] = collector_mod

# Import generate-digest.py
_digest_spec = importlib.util.spec_from_file_location("generate_digest", _scripts_dir / "generate-digest.py")
digest_mod = importlib.util.module_from_spec(_digest_spec)
_digest_spec.loader.exec_module(digest_mod)
sys.modules["generate_digest"] = digest_mod

# Pull out the names we need from collector
init_db = collector_mod.init_db
insert_events = collector_mod.insert_events
count_events = collector_mod.count_events
classify_severity = collector_mod.classify_severity
parse_args_collector = collector_mod.parse_args

# Pull out the names we need from digest generator
compute_time_range = digest_mod.compute_time_range
query_events_from_db = digest_mod.query_events_from_db
has_recent_data = digest_mod.has_recent_data
run_correlations = digest_mod.run_correlations
_corr_01_motion_without_badge = digest_mod._corr_01_motion_without_badge
_corr_02_new_device_with_motion = digest_mod._corr_02_new_device_with_motion
_corr_03_access_denied_with_motion = digest_mod._corr_03_access_denied_with_motion
compute_activity_counts = digest_mod.compute_activity_counts
extract_notable_events = digest_mod.extract_notable_events
determine_status = digest_mod.determine_status
generate_summary = digest_mod.generate_summary
build_recommendations = digest_mod.build_recommendations
generate_digest = digest_mod.generate_digest
format_human = digest_mod.format_human
parse_args_digest = digest_mod.parse_args
_classify_severity = digest_mod._classify_severity
_parse_timestamp = digest_mod._parse_timestamp
_events_within_window = digest_mod._events_within_window


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_event(
    event_id: str = "evt-1",
    server: str = "protect",
    event_type: str = "motion",
    timestamp: str = "2026-03-18T03:00:00+00:00",
    details: dict | None = None,
    severity: str = "low",
) -> dict:
    return {
        "id": event_id,
        "server": server,
        "event_type": event_type,
        "timestamp": timestamp,
        "details": details or {},
        "severity": severity,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════════════════════
# COLLECTOR TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestCollectorDB:
    """Test SQLite schema creation and basic operations."""

    def test_init_db_creates_file(self, tmp_path):
        conn = init_db(tmp_path)
        assert (tmp_path / "events.db").exists()
        conn.close()

    def test_init_db_creates_schema(self, tmp_path):
        conn = init_db(tmp_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_init_db_idempotent(self, tmp_path):
        """Calling init_db twice should not error."""
        conn1 = init_db(tmp_path)
        conn1.close()
        conn2 = init_db(tmp_path)
        conn2.close()

    def test_insert_events_basic(self, tmp_path):
        conn = init_db(tmp_path)
        events = [_make_event("e1"), _make_event("e2")]
        inserted = insert_events(conn, events)
        assert count_events(conn) == 2
        conn.close()

    def test_insert_events_dedup(self, tmp_path):
        """Duplicate IDs should be ignored."""
        conn = init_db(tmp_path)
        events = [_make_event("e1"), _make_event("e1")]
        insert_events(conn, events)
        assert count_events(conn) == 1
        conn.close()

    def test_insert_events_across_batches(self, tmp_path):
        """Dedup works across separate insert calls."""
        conn = init_db(tmp_path)
        insert_events(conn, [_make_event("e1")])
        insert_events(conn, [_make_event("e1"), _make_event("e2")])
        assert count_events(conn) == 2
        conn.close()

    def test_insert_events_empty_list(self, tmp_path):
        conn = init_db(tmp_path)
        inserted = insert_events(conn, [])
        assert inserted == 0
        assert count_events(conn) == 0
        conn.close()

    def test_count_events_empty(self, tmp_path):
        conn = init_db(tmp_path)
        assert count_events(conn) == 0
        conn.close()


class TestCollectorSeverity:
    """Test the classify_severity function."""

    def test_person_at_night(self):
        assert classify_severity("person", {}, "2026-03-18T02:00:00+00:00") == "high"

    def test_person_during_day(self):
        assert classify_severity("person", {}, "2026-03-18T14:00:00+00:00") == "medium"

    def test_vehicle_at_night(self):
        assert classify_severity("vehicle", {}, "2026-03-18T23:00:00+00:00") == "medium"

    def test_vehicle_during_day(self):
        assert classify_severity("vehicle", {}, "2026-03-18T12:00:00+00:00") == "low"

    def test_animal_always_low(self):
        assert classify_severity("animal", {}, "2026-03-18T03:00:00+00:00") == "low"
        assert classify_severity("animal", {}, "2026-03-18T14:00:00+00:00") == "low"

    def test_package(self):
        assert classify_severity("package", {}, "2026-03-18T14:00:00+00:00") == "medium"

    def test_access_deny(self):
        assert classify_severity("ACCESS_DENY", {}, "2026-03-18T14:00:00+00:00") == "high"

    def test_door_forced_open(self):
        assert classify_severity("DOOR_FORCED_OPEN", {}, "2026-03-18T14:00:00+00:00") == "high"

    def test_ips_alert(self):
        assert classify_severity("EVT_IPS_IpsAlert", {}, "2026-03-18T14:00:00+00:00") == "high"

    def test_network_alarm_critical(self):
        assert classify_severity("alarm", {"severity": "critical"}, "2026-03-18T14:00:00+00:00") == "high"

    def test_motion_always_low(self):
        assert classify_severity("motion", {}, "2026-03-18T03:00:00+00:00") == "low"

    def test_sensor_alarm_at_night(self):
        assert classify_severity("sensorAlarm", {}, "2026-03-18T03:00:00+00:00") == "high"

    def test_sensor_alarm_during_day(self):
        assert classify_severity("sensorAlarm", {}, "2026-03-18T14:00:00+00:00") == "medium"


class TestCollectorParseArgs:
    """Test collector argument parsing."""

    def test_defaults(self):
        args = parse_args_collector([])
        assert args.state_dir == ".claude/unifi-skills"
        assert args.poll_interval == 10
        assert args.servers == "protect,network"
        assert args.timeout == 1800

    def test_custom_args(self):
        args = parse_args_collector([
            "--state-dir", "/tmp/test",
            "--poll-interval", "30",
            "--servers", "protect,access,network",
            "--timeout", "3600",
        ])
        assert args.state_dir == "/tmp/test"
        assert args.poll_interval == 30
        assert args.servers == "protect,access,network"
        assert args.timeout == 3600


# ══════════════════════════════════════════════════════════════════════════════
# DIGEST GENERATOR TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestTimeRange:
    """Test time range computation."""

    def test_overnight(self):
        now = datetime(2026, 3, 18, 6, 0, 0, tzinfo=timezone.utc)
        start, end = compute_time_range("overnight", now)
        assert end == now
        assert start == now - timedelta(hours=12)

    def test_today(self):
        now = datetime(2026, 3, 18, 14, 30, 0, tzinfo=timezone.utc)
        start, end = compute_time_range("today", now)
        assert end == now
        assert start.hour == 0
        assert start.minute == 0

    def test_recent(self):
        now = datetime(2026, 3, 18, 14, 0, 0, tzinfo=timezone.utc)
        start, end = compute_time_range("recent", now)
        assert end == now
        assert start == now - timedelta(hours=4)

    def test_24h(self):
        now = datetime(2026, 3, 18, 14, 0, 0, tzinfo=timezone.utc)
        start, end = compute_time_range("24h", now)
        assert end == now
        assert start == now - timedelta(hours=24)

    def test_unknown_range_defaults_to_12h(self):
        now = datetime(2026, 3, 18, 14, 0, 0, tzinfo=timezone.utc)
        start, end = compute_time_range("bogus", now)
        assert end == now
        assert start == now - timedelta(hours=12)


class TestDigestParseArgs:
    """Test digest generator argument parsing."""

    def test_defaults(self):
        args = parse_args_digest([])
        assert args.mcp_url is None
        assert args.time_range == "overnight"
        assert args.output_format == "json"
        assert args.state_dir is None

    def test_custom_args(self):
        args = parse_args_digest([
            "--mcp-url", "http://x:3001",
            "--range", "today",
            "--format", "human",
            "--state-dir", "/tmp/digest",
        ])
        assert args.mcp_url == "http://x:3001"
        assert args.time_range == "today"
        assert args.output_format == "human"
        assert args.state_dir == "/tmp/digest"


class TestDBReader:
    """Test SQLite query functions for digest generation."""

    def test_query_events_from_db_empty(self, tmp_path):
        conn = init_db(tmp_path)
        conn.close()
        start = datetime(2026, 3, 17, 18, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 18, 6, 0, 0, tzinfo=timezone.utc)
        events = query_events_from_db(tmp_path / "events.db", start, end)
        assert events == []

    def test_query_events_filters_by_time(self, tmp_path):
        conn = init_db(tmp_path)
        events = [
            _make_event("e1", timestamp="2026-03-18T01:00:00+00:00"),
            _make_event("e2", timestamp="2026-03-18T05:00:00+00:00"),
            _make_event("e3", timestamp="2026-03-18T12:00:00+00:00"),  # Outside range
        ]
        insert_events(conn, events)
        conn.close()

        start = datetime(2026, 3, 18, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 18, 6, 0, 0, tzinfo=timezone.utc)
        result = query_events_from_db(tmp_path / "events.db", start, end)
        assert len(result) == 2

    def test_query_events_returns_parsed_details(self, tmp_path):
        conn = init_db(tmp_path)
        events = [_make_event("e1", details={"camera_id": "cam-1"})]
        insert_events(conn, events)
        conn.close()

        start = datetime(2026, 3, 17, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 19, 0, 0, 0, tzinfo=timezone.utc)
        result = query_events_from_db(tmp_path / "events.db", start, end)
        assert result[0]["details"]["camera_id"] == "cam-1"

    def test_has_recent_data_true(self, tmp_path):
        conn = init_db(tmp_path)
        insert_events(conn, [_make_event("e1")])
        conn.close()
        assert has_recent_data(tmp_path / "events.db", max_age_minutes=60) is True

    def test_has_recent_data_no_db(self, tmp_path):
        assert has_recent_data(tmp_path / "events.db") is False

    def test_query_nonexistent_db(self, tmp_path):
        start = datetime(2026, 3, 17, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 19, 0, 0, 0, tzinfo=timezone.utc)
        result = query_events_from_db(tmp_path / "nonexistent.db", start, end)
        assert result == []


# ── Correlation rule tests ──────────────────────────────────────────────────


class TestCorrelationCORR01:
    """CORR-01: Motion at door camera without badge-in within 2 minutes."""

    def test_motion_with_no_access_events(self):
        """If no Access events exist, don't flag — server may not be connected."""
        events = [
            _make_event("m1", server="protect", event_type="person", timestamp="2026-03-18T03:00:00+00:00"),
        ]
        corrs = _corr_01_motion_without_badge(events)
        assert len(corrs) == 0

    def test_motion_without_badge(self):
        """Motion at door with access server present but no badge-in should flag."""
        events = [
            _make_event("m1", server="protect", event_type="person", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("a1", server="access", event_type="ACCESS_DENY", timestamp="2026-03-18T02:50:00+00:00"),
        ]
        corrs = _corr_01_motion_without_badge(events)
        assert len(corrs) == 1
        assert corrs[0]["rule"] == "CORR-01"

    def test_motion_with_badge(self):
        """Motion with a nearby badge-in should NOT flag."""
        events = [
            _make_event("m1", server="protect", event_type="person", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("a1", server="access", event_type="ACCESS_GRANT", timestamp="2026-03-18T03:01:00+00:00"),
        ]
        corrs = _corr_01_motion_without_badge(events)
        assert len(corrs) == 0

    def test_motion_badge_outside_window(self):
        """Badge-in too far from motion should still flag."""
        events = [
            _make_event("m1", server="protect", event_type="person", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("a1", server="access", event_type="ACCESS_GRANT", timestamp="2026-03-18T03:10:00+00:00"),
        ]
        corrs = _corr_01_motion_without_badge(events)
        assert len(corrs) == 1


class TestCorrelationCORR02:
    """CORR-02: New network device + motion within 5 minutes."""

    def test_new_device_with_person(self):
        events = [
            _make_event("n1", server="network", event_type="EVT_WU_Connected", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("p1", server="protect", event_type="person", timestamp="2026-03-18T03:02:00+00:00"),
        ]
        corrs = _corr_02_new_device_with_motion(events)
        assert len(corrs) == 1
        assert corrs[0]["rule"] == "CORR-02"

    def test_new_device_no_person(self):
        events = [
            _make_event("n1", server="network", event_type="EVT_WU_Connected", timestamp="2026-03-18T03:00:00+00:00"),
        ]
        corrs = _corr_02_new_device_with_motion(events)
        assert len(corrs) == 0

    def test_new_device_person_outside_window(self):
        events = [
            _make_event("n1", server="network", event_type="EVT_WU_Connected", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("p1", server="protect", event_type="person", timestamp="2026-03-18T03:10:00+00:00"),
        ]
        corrs = _corr_02_new_device_with_motion(events)
        assert len(corrs) == 0

    def test_wired_device_with_person(self):
        events = [
            _make_event("n1", server="network", event_type="EVT_WG_Connected", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("p1", server="protect", event_type="person", timestamp="2026-03-18T03:03:00+00:00"),
        ]
        corrs = _corr_02_new_device_with_motion(events)
        assert len(corrs) == 1


class TestCorrelationCORR03:
    """CORR-03: Access denied + continued motion within 3 minutes."""

    def test_denied_then_motion(self):
        events = [
            _make_event("a1", server="access", event_type="ACCESS_DENY", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("m1", server="protect", event_type="person", timestamp="2026-03-18T03:01:30+00:00"),
        ]
        corrs = _corr_03_access_denied_with_motion(events)
        assert len(corrs) == 1
        assert corrs[0]["rule"] == "CORR-03"

    def test_denied_no_motion(self):
        events = [
            _make_event("a1", server="access", event_type="ACCESS_DENY", timestamp="2026-03-18T03:00:00+00:00"),
        ]
        corrs = _corr_03_access_denied_with_motion(events)
        assert len(corrs) == 0

    def test_denied_motion_before_denial(self):
        """Motion before denial should NOT flag (we want continued motion after)."""
        events = [
            _make_event("m1", server="protect", event_type="motion", timestamp="2026-03-18T02:59:00+00:00"),
            _make_event("a1", server="access", event_type="ACCESS_DENY", timestamp="2026-03-18T03:00:00+00:00"),
        ]
        corrs = _corr_03_access_denied_with_motion(events)
        assert len(corrs) == 0

    def test_denied_motion_outside_window(self):
        events = [
            _make_event("a1", server="access", event_type="ACCESS_DENY", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("m1", server="protect", event_type="person", timestamp="2026-03-18T03:05:00+00:00"),
        ]
        corrs = _corr_03_access_denied_with_motion(events)
        assert len(corrs) == 0

    def test_schedule_deny_with_motion(self):
        events = [
            _make_event("a1", server="access", event_type="SCHEDULE_DENY", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("m1", server="protect", event_type="motion", timestamp="2026-03-18T03:02:00+00:00"),
        ]
        corrs = _corr_03_access_denied_with_motion(events)
        assert len(corrs) == 1


class TestRunCorrelations:
    """Test the combined correlation runner."""

    def test_no_events(self):
        assert run_correlations([]) == []

    def test_multiple_rules_fire(self):
        events = [
            # CORR-01: person with no badge (access server present via deny)
            _make_event("m1", server="protect", event_type="person", timestamp="2026-03-18T03:00:00+00:00"),
            _make_event("a1", server="access", event_type="ACCESS_DENY", timestamp="2026-03-18T02:50:00+00:00"),
            # CORR-03: denied + motion after
            _make_event("m2", server="protect", event_type="motion", timestamp="2026-03-18T02:51:00+00:00"),
        ]
        corrs = run_correlations(events)
        rules = {c["rule"] for c in corrs}
        # CORR-01 should fire for m1 (no grant near it)
        assert "CORR-01" in rules
        # CORR-03 should fire for a1 + m2
        assert "CORR-03" in rules


# ── Activity counting tests ─────────────────────────────────────────────────


class TestActivityCounts:
    def test_empty(self):
        counts = compute_activity_counts([])
        assert counts["protect"]["total"] == 0
        assert counts["access"]["total"] == 0
        assert counts["network"]["total"] == 0

    def test_mixed_events(self):
        events = [
            _make_event("e1", server="protect", event_type="person"),
            _make_event("e2", server="protect", event_type="vehicle"),
            _make_event("e3", server="protect", event_type="motion"),
            _make_event("e4", server="access", event_type="ACCESS_GRANT"),
            _make_event("e5", server="access", event_type="ACCESS_DENY"),
            _make_event("e6", server="network", event_type="EVT_WU_Connected"),
            _make_event("e7", server="network", event_type="alarm"),
        ]
        counts = compute_activity_counts(events)
        assert counts["protect"]["total"] == 3
        assert counts["protect"]["person"] == 1
        assert counts["protect"]["vehicle"] == 1
        assert counts["protect"]["motion"] == 1
        assert counts["access"]["total"] == 2
        assert counts["access"]["granted"] == 1
        assert counts["access"]["denied"] == 1
        assert counts["network"]["total"] == 2
        assert counts["network"]["client_events"] == 1
        assert counts["network"]["alarms"] == 1


# ── Notable events tests ───────────────────────────────────────────────────


class TestNotableEvents:
    def test_empty(self):
        assert extract_notable_events([]) == []

    def test_high_severity_included(self):
        events = [
            _make_event("e1", event_type="person", severity="high", timestamp="2026-03-18T03:00:00+00:00"),
        ]
        notable = extract_notable_events(events)
        assert len(notable) == 1
        assert notable[0]["severity"] == "high"

    def test_low_routine_excluded(self):
        events = [
            _make_event("e1", event_type="motion", severity="low", timestamp="2026-03-18T14:00:00+00:00"),
        ]
        notable = extract_notable_events(events)
        assert len(notable) == 0

    def test_notable_type_included_regardless_of_severity(self):
        """Events like ACCESS_DENY are always notable."""
        events = [
            _make_event("e1", server="access", event_type="ACCESS_DENY", severity="high",
                        timestamp="2026-03-18T14:00:00+00:00"),
        ]
        notable = extract_notable_events(events)
        assert len(notable) == 1


# ── Status determination tests ──────────────────────────────────────────────


class TestDetermineStatus:
    def test_clear(self):
        assert determine_status([], []) == "clear"

    def test_notable(self):
        notable = [{"severity": "medium"}]
        assert determine_status(notable, []) == "notable"

    def test_alert_from_high_severity(self):
        notable = [{"severity": "high"}]
        assert determine_status(notable, []) == "alert"

    def test_alert_from_correlations(self):
        notable = [{"severity": "low"}]
        corrs = [{"severity": "medium"}]
        assert determine_status(notable, corrs) == "alert"


# ── Summary generation tests ───────────────────────────────────────────────


class TestGenerateSummary:
    def test_clear_summary(self):
        counts = {"protect": {"total": 10}, "access": {"total": 5}, "network": {"total": 2}}
        summary = generate_summary("clear", [], counts)
        assert "Quiet" in summary
        assert "17" in summary  # 10 + 5 + 2

    def test_notable_summary(self):
        notable = [{"severity": "medium"}, {"severity": "medium"}]
        counts = {"protect": {"total": 20}}
        summary = generate_summary("notable", notable, counts)
        assert "2 notable" in summary

    def test_alert_summary(self):
        notable = [{"severity": "high"}, {"severity": "medium"}]
        counts = {"protect": {"total": 30}}
        summary = generate_summary("alert", notable, counts)
        assert "Alert" in summary
        assert "1 high" in summary


# ── Recommendation tests ───────────────────────────────────────────────────


class TestBuildRecommendations:
    def test_no_events(self):
        recs = build_recommendations([], [])
        assert any("all clear" in r.lower() for r in recs)

    def test_with_correlations(self):
        corrs = [{"rule": "CORR-01", "description": "test"}]
        recs = build_recommendations([], corrs)
        assert any("footage" in r.lower() for r in recs)

    def test_corr02_recommendation(self):
        corrs = [{"rule": "CORR-02", "description": "test"}]
        recs = build_recommendations([], corrs)
        assert any("network device" in r.lower() for r in recs)

    def test_corr03_recommendation(self):
        corrs = [{"rule": "CORR-03", "description": "test"}]
        recs = build_recommendations([], corrs)
        assert any("denied" in r.lower() for r in recs)


# ── Integration: generate_digest in rich mode ──────────────────────────────


@pytest.mark.asyncio
async def test_generate_digest_rich_mode(tmp_path):
    """Test digest generation from pre-populated SQLite database."""
    conn = init_db(tmp_path)
    now = datetime.now(timezone.utc)
    events = [
        _make_event("e1", server="protect", event_type="person",
                     timestamp=(now - timedelta(hours=2)).isoformat(), severity="high",
                     details={"camera_name": "Front Door"}),
        _make_event("e2", server="protect", event_type="motion",
                     timestamp=(now - timedelta(hours=3)).isoformat(), severity="low"),
        _make_event("e3", server="access", event_type="ACCESS_GRANT",
                     timestamp=(now - timedelta(hours=2, minutes=30)).isoformat(), severity="low"),
    ]
    insert_events(conn, events)
    conn.close()

    result = await generate_digest(tmp_path, range_name="recent", now=now)

    assert result["success"] is True
    assert result["mode"] == "collector"
    assert result["status"] in ("clear", "notable", "alert")
    assert "notable_events" in result
    assert "correlations" in result
    assert "activity_counts" in result
    assert "recommendations" in result


@pytest.mark.asyncio
async def test_generate_digest_fallback_mode(tmp_path):
    """Test digest generation when no DB exists (fallback to MCP)."""
    # Patch fetch_all_events_fallback to return empty (no servers available)
    with patch.object(digest_mod, "fetch_all_events_fallback", new_callable=AsyncMock, return_value=[]):
        result = await generate_digest(tmp_path, range_name="recent")

    assert result["success"] is True
    assert result["mode"] == "fallback"
    assert result["status"] == "clear"


@pytest.mark.asyncio
async def test_generate_digest_output_structure(tmp_path):
    """Validate complete output structure."""
    conn = init_db(tmp_path)
    insert_events(conn, [_make_event("e1")])
    conn.close()

    result = await generate_digest(tmp_path, range_name="24h")

    required_keys = {
        "success", "timestamp", "time_range", "mode", "summary",
        "status", "notable_events", "correlations", "activity_counts",
        "recommendations",
    }
    assert required_keys.issubset(set(result.keys()))

    # time_range structure
    tr = result["time_range"]
    assert "start" in tr
    assert "end" in tr
    assert "name" in tr

    assert isinstance(result["notable_events"], list)
    assert isinstance(result["correlations"], list)
    assert isinstance(result["activity_counts"], dict)
    assert isinstance(result["recommendations"], list)


# ── Human format test ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_human_format(tmp_path):
    """Test human-readable output."""
    conn = init_db(tmp_path)
    now = datetime.now(timezone.utc)
    events = [
        _make_event("e1", server="protect", event_type="person",
                     timestamp=(now - timedelta(hours=1)).isoformat(), severity="high",
                     details={"camera_name": "Front Door"}),
    ]
    insert_events(conn, events)
    conn.close()

    result = await generate_digest(tmp_path, range_name="recent", now=now)
    text = format_human(result)

    assert "Security Digest" in text
    assert "Status:" in text
    assert "Summary" in text
    assert "Activity Counts" in text


# ── Timestamp parsing helpers ──────────────────────────────────────────────


class TestTimestampHelpers:
    def test_parse_iso_timestamp(self):
        dt = _parse_timestamp("2026-03-18T03:00:00+00:00")
        assert dt is not None
        assert dt.hour == 3

    def test_parse_z_timestamp(self):
        dt = _parse_timestamp("2026-03-18T03:00:00Z")
        assert dt is not None
        assert dt.hour == 3

    def test_parse_invalid(self):
        assert _parse_timestamp("not a date") is None

    def test_events_within_window(self):
        e1 = {"timestamp": "2026-03-18T03:00:00+00:00"}
        e2 = {"timestamp": "2026-03-18T03:01:00+00:00"}
        assert _events_within_window(e1, e2, 120) is True
        assert _events_within_window(e1, e2, 30) is False
