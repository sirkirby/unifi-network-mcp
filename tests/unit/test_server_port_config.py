"""Tests for MCP server host/port configuration via environment variables."""

import os
from unittest import mock

import pytest
from omegaconf import OmegaConf


class TestServerPortConfig:
    """Tests for UNIFI_MCP_HOST and UNIFI_MCP_PORT configuration."""

    @pytest.fixture
    def config_yaml_path(self, tmp_path):
        """Create a temporary config file with env var interpolation."""
        config_content = """
server:
  host: ${oc.env:UNIFI_MCP_HOST,0.0.0.0}
  port: ${oc.env:UNIFI_MCP_PORT,3000}
  log_level: INFO

unifi:
  host: localhost
  username: admin
  password: test
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        return config_file

    def test_default_host_when_env_not_set(self, config_yaml_path):
        """Verify default host 0.0.0.0 is used when UNIFI_MCP_HOST is not set."""
        # Ensure env var is not set
        env = {k: v for k, v in os.environ.items() if k != "UNIFI_MCP_HOST"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = OmegaConf.load(str(config_yaml_path))
            assert cfg.server.host == "0.0.0.0"

    def test_default_port_when_env_not_set(self, config_yaml_path):
        """Verify default port 3000 is used when UNIFI_MCP_PORT is not set."""
        # Ensure env var is not set
        env = {k: v for k, v in os.environ.items() if k != "UNIFI_MCP_PORT"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = OmegaConf.load(str(config_yaml_path))
            # OmegaConf returns string for env interpolation defaults
            assert int(cfg.server.port) == 3000

    def test_custom_host_from_env(self, config_yaml_path):
        """Verify UNIFI_MCP_HOST environment variable is respected."""
        with mock.patch.dict(os.environ, {"UNIFI_MCP_HOST": "127.0.0.1"}):
            cfg = OmegaConf.load(str(config_yaml_path))
            assert cfg.server.host == "127.0.0.1"

    def test_custom_port_from_env(self, config_yaml_path):
        """Verify UNIFI_MCP_PORT environment variable is respected."""
        with mock.patch.dict(os.environ, {"UNIFI_MCP_PORT": "8080"}):
            cfg = OmegaConf.load(str(config_yaml_path))
            # OmegaConf returns the interpolated value as string, int conversion happens in main.py
            assert str(cfg.server.port) == "8080"

    def test_both_host_and_port_from_env(self, config_yaml_path):
        """Verify both UNIFI_MCP_HOST and UNIFI_MCP_PORT can be set together."""
        with mock.patch.dict(
            os.environ, {"UNIFI_MCP_HOST": "192.168.1.100", "UNIFI_MCP_PORT": "9000"}
        ):
            cfg = OmegaConf.load(str(config_yaml_path))
            assert cfg.server.host == "192.168.1.100"
            assert str(cfg.server.port) == "9000"

    def test_port_conversion_to_int(self, config_yaml_path):
        """Verify port can be converted to int as done in main.py."""
        with mock.patch.dict(os.environ, {"UNIFI_MCP_PORT": "8080"}):
            cfg = OmegaConf.load(str(config_yaml_path))
            # Simulate the conversion done in main.py line 315
            port = int(cfg.server.get("port", 3000))
            assert port == 8080
            assert isinstance(port, int)


class TestServerConfigFromActualFile:
    """Tests that verify the actual config.yaml has correct interpolation syntax."""

    def test_actual_config_has_env_interpolation(self):
        """Verify src/config/config.yaml uses OmegaConf env interpolation for host/port."""
        from pathlib import Path

        config_path = Path(__file__).parent.parent.parent / "src" / "config" / "config.yaml"
        content = config_path.read_text()

        assert "${oc.env:UNIFI_MCP_HOST,0.0.0.0}" in content, (
            "config.yaml should use OmegaConf env interpolation for host"
        )
        assert "${oc.env:UNIFI_MCP_PORT,3000}" in content, (
            "config.yaml should use OmegaConf env interpolation for port"
        )
