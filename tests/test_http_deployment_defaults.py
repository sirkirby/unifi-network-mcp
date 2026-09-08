"""Guard the packaged and Compose MCP exposure boundaries."""

from pathlib import Path

import pytest
import yaml
from omegaconf import OmegaConf

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("server", ["network", "protect", "access"])
def test_packaged_http_is_opt_in_and_loopback(server, monkeypatch):
    monkeypatch.delenv("UNIFI_MCP_HOST", raising=False)
    monkeypatch.delenv("UNIFI_MCP_HTTP_ENABLED", raising=False)
    path = ROOT / f"apps/{server}/src/unifi_{server}_mcp/config/config.yaml"
    config = OmegaConf.load(path).server
    assert config.host == "127.0.0.1"
    assert str(config.http.enabled).lower() == "false"
    monkeypatch.setenv("UNIFI_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("UNIFI_MCP_HTTP_ENABLED", "true")
    assert config.host == "0.0.0.0"
    assert str(config.http.enabled).lower() == "true"


def test_compose_publishes_only_loopback_and_keeps_relay_reachable():
    compose = yaml.safe_load((ROOT / "docker/docker-compose.yml").read_text())
    for server, port in [("network", 3000), ("protect", 3001), ("access", 3002)]:
        service = compose["services"][f"unifi-{server}-mcp"]
        assert service["ports"] == [f"127.0.0.1:{port}:{port}"]
        assert "UNIFI_MCP_HOST=0.0.0.0" in service["environment"]
        assert "UNIFI_MCP_HTTP_ENABLED=true" in service["environment"]
        relay_env = compose["services"]["unifi-mcp-relay"]["environment"]
        assert any(f"http://unifi-{server}-mcp:{port}" in value for value in relay_env)
