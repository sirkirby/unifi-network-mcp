"""Self-tests for scripts/live_api_smoke.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))


def test_load_env_returns_dict():
    """If .env exists, load_env returns a dict of key→value strings."""
    from live_api_smoke import load_env

    env = load_env()
    assert isinstance(env, dict)


def test_assertion_dataclass_serializes():
    from dataclasses import asdict

    from live_api_smoke import Assertion

    a = Assertion(name="x", product="network", surface="rest")
    d = asdict(a)
    assert d["name"] == "x"
    assert d["passed"] is False


def test_report_counters():
    from live_api_smoke import Assertion, Report

    r = Report()
    r.assertions.append(Assertion(name="ok", product="x", surface="rest", passed=True))
    r.assertions.append(Assertion(name="bad", product="x", surface="rest", passed=False))
    assert r.total == 2
    assert r.passed == 1
    assert r.failed == 1
