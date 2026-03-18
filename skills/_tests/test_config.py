"""Tests for MCP server config discovery."""
import os
import pytest
from skills._shared.config import get_server_url, get_all_server_urls, DEFAULT_PORTS


def test_get_server_url_from_env(monkeypatch):
    monkeypatch.setenv("UNIFI_NETWORK_MCP_URL", "http://myhost:4000")
    assert get_server_url("network") == "http://myhost:4000"


def test_get_server_url_default():
    url = get_server_url("network")
    assert url == f"http://localhost:{DEFAULT_PORTS['network']}"


def test_get_server_url_protect():
    url = get_server_url("protect")
    assert url == f"http://localhost:{DEFAULT_PORTS['protect']}"


def test_get_server_url_access():
    url = get_server_url("access")
    assert url == f"http://localhost:{DEFAULT_PORTS['access']}"


def test_get_server_url_unknown_server():
    with pytest.raises(ValueError, match="Unknown server"):
        get_server_url("unknown")


def test_get_all_server_urls():
    urls = get_all_server_urls()
    assert "network" in urls
    assert "protect" in urls
    assert "access" in urls


def test_get_server_url_env_override_takes_priority(monkeypatch):
    monkeypatch.setenv("UNIFI_PROTECT_MCP_URL", "http://custom:9999")
    assert get_server_url("protect") == "http://custom:9999"


from skills._shared.config import get_state_dir


def test_get_state_dir_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("UNIFI_SKILLS_STATE_DIR", raising=False)
    state_dir = get_state_dir()
    assert state_dir == tmp_path / ".claude" / "unifi-skills"


def test_get_state_dir_override(monkeypatch):
    monkeypatch.setenv("UNIFI_SKILLS_STATE_DIR", "/tmp/custom-state")
    state_dir = get_state_dir()
    assert str(state_dir) == "/tmp/custom-state"


def test_get_state_dir_creates_on_ensure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("UNIFI_SKILLS_STATE_DIR", raising=False)
    state_dir = get_state_dir(ensure=True)
    assert state_dir.exists()
    assert state_dir.is_dir()
