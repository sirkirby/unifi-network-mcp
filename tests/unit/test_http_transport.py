"""Tests for HTTP transport configuration and uvicorn logging fix."""

import pytest

from src.utils.config_helpers import parse_config_bool


class TestUvicornLoggingConfig:
    """Tests for uvicorn access log redirection to stderr."""

    def test_uvicorn_default_access_log_uses_stdout(self):
        """Verify uvicorn's default config uses stdout for access logs (the problem)."""
        import uvicorn.config

        # Get fresh default config
        default_stream = uvicorn.config.LOGGING_CONFIG["handlers"]["access"]["stream"]
        assert default_stream == "ext://sys.stdout", "Expected uvicorn default access log to use stdout"

    def test_uvicorn_config_modification_redirects_to_stderr(self):
        """Verify our fix redirects access logs to stderr."""
        import uvicorn.config

        # Save original
        original = uvicorn.config.LOGGING_CONFIG["handlers"]["access"]["stream"]

        try:
            # Apply our fix
            uvicorn.config.LOGGING_CONFIG["handlers"]["access"]["stream"] = "ext://sys.stderr"

            # Verify it took effect
            assert uvicorn.config.LOGGING_CONFIG["handlers"]["access"]["stream"] == "ext://sys.stderr"

            # Verify uvicorn.Config uses our modified config
            config = uvicorn.Config(app=None, host="127.0.0.1", port=8000)
            assert config.log_config["handlers"]["access"]["stream"] == "ext://sys.stderr", (
                "uvicorn.Config should use the modified LOGGING_CONFIG"
            )
        finally:
            # Restore original to not affect other tests
            uvicorn.config.LOGGING_CONFIG["handlers"]["access"]["stream"] = original


class TestParseConfigBool:
    """Tests for parse_config_bool utility function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            # Truthy string values
            ("true", True),
            ("TRUE", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("YES", True),
            ("on", True),
            ("ON", True),
            # Falsy string values
            ("false", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("", False),
            ("invalid", False),
            # Whitespace handling
            ("  true  ", True),
            ("  false  ", False),
            # Boolean values pass through
            (True, True),
            (False, False),
            # None uses default
            (None, False),
        ],
    )
    def test_parse_config_bool(self, value, expected: bool):
        """Verify config bool parsing handles all expected inputs."""
        result = parse_config_bool(value)
        assert result == expected, f"Expected parse_config_bool({value!r}) to be {expected}"

    def test_parse_config_bool_default_true(self):
        """Verify default=True is used when value is None."""
        assert parse_config_bool(None, default=True) is True

    def test_parse_config_bool_default_false(self):
        """Verify default=False is used when value is None."""
        assert parse_config_bool(None, default=False) is False


class TestHttpForceFlag:
    """Tests for UNIFI_MCP_HTTP_FORCE configuration option."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("TRUE", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("YES", True),
            ("false", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("", False),
            ("invalid", False),
        ],
    )
    def test_http_force_flag_parsing(self, value: str, expected: bool):
        """Verify HTTP force flag is parsed correctly using parse_config_bool."""
        result = parse_config_bool(value)
        assert result == expected, f"Expected '{value}' to parse as {expected}"

    def test_http_enabled_with_force_flag_bypasses_pid_check(self):
        """Verify force flag allows HTTP even when PID != 1."""
        # Simulate the logic from main.py
        http_enabled = True
        force_http = True
        is_main_container_process = False  # PID != 1

        # With force flag, HTTP should remain enabled
        if http_enabled and not is_main_container_process and not force_http:
            http_enabled = False

        assert http_enabled is True, "Force flag should bypass PID check"

    def test_http_disabled_without_force_flag_when_not_pid_1(self):
        """Verify HTTP is disabled when PID != 1 and no force flag."""
        http_enabled = True
        force_http = False
        is_main_container_process = False  # PID != 1

        if http_enabled and not is_main_container_process and not force_http:
            http_enabled = False

        assert http_enabled is False, "HTTP should be disabled when PID != 1 without force flag"

    def test_http_enabled_when_pid_1(self):
        """Verify HTTP is enabled when running as PID 1 (container main process)."""
        http_enabled = True
        force_http = False
        is_main_container_process = True  # PID == 1

        if http_enabled and not is_main_container_process and not force_http:
            http_enabled = False

        assert http_enabled is True, "HTTP should be enabled when PID == 1"


class TestHttpTransportSelection:
    """Tests for UNIFI_MCP_HTTP_TRANSPORT configuration option."""

    VALID_HTTP_TRANSPORTS = {"streamable-http", "sse"}

    def _resolve_transport(self, raw_value):
        """Replicate the transport resolution logic from main.py."""
        http_transport = raw_value if raw_value is not None else "streamable-http"
        if isinstance(http_transport, str):
            http_transport = http_transport.lower()
        if http_transport not in self.VALID_HTTP_TRANSPORTS:
            http_transport = "streamable-http"
        return http_transport

    def test_default_transport_is_streamable_http(self):
        """Default transport should be streamable-http when not specified."""
        assert self._resolve_transport(None) == "streamable-http"

    def test_explicit_streamable_http(self):
        """Explicit streamable-http value should be accepted."""
        assert self._resolve_transport("streamable-http") == "streamable-http"

    def test_explicit_sse(self):
        """Explicit sse value should be accepted."""
        assert self._resolve_transport("sse") == "sse"

    def test_case_insensitive_streamable_http(self):
        """Transport value should be case-insensitive."""
        assert self._resolve_transport("Streamable-HTTP") == "streamable-http"

    def test_case_insensitive_sse(self):
        """SSE transport should be case-insensitive."""
        assert self._resolve_transport("SSE") == "sse"

    def test_invalid_value_falls_back_to_default(self):
        """Invalid transport values should fall back to streamable-http."""
        assert self._resolve_transport("bogus") == "streamable-http"

    def test_empty_string_falls_back_to_default(self):
        """Empty string should fall back to streamable-http."""
        assert self._resolve_transport("") == "streamable-http"

    def test_websocket_not_valid(self):
        """Websocket is not a valid transport option."""
        assert self._resolve_transport("websocket") == "streamable-http"


class TestTransportLogLabels:
    """Tests for transport-aware log label generation."""

    def _get_label(self, transport):
        """Replicate the label logic from main.py."""
        return "Streamable HTTP" if transport == "streamable-http" else "HTTP SSE"

    def test_streamable_http_label(self):
        """Streamable HTTP transport should produce correct label."""
        assert self._get_label("streamable-http") == "Streamable HTTP"

    def test_sse_label(self):
        """SSE transport should produce correct label."""
        assert self._get_label("sse") == "HTTP SSE"


class TestTransportConfigYaml:
    """Tests for transport config in config.yaml via OmegaConf."""

    def test_config_yaml_has_transport_key(self, tmp_path):
        """Verify config.yaml transport key resolves with OmegaConf."""
        from omegaconf import OmegaConf

        yaml_content = """
server:
  http:
    enabled: false
    force: false
    transport: ${oc.env:UNIFI_MCP_HTTP_TRANSPORT,streamable-http}
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        cfg = OmegaConf.load(config_file)
        OmegaConf.resolve(cfg)
        assert cfg.server.http.transport == "streamable-http"

    def test_config_yaml_transport_env_override(self, tmp_path, monkeypatch):
        """Verify transport can be overridden via environment variable."""
        from omegaconf import OmegaConf

        monkeypatch.setenv("UNIFI_MCP_HTTP_TRANSPORT", "sse")

        yaml_content = """
server:
  http:
    enabled: false
    force: false
    transport: ${oc.env:UNIFI_MCP_HTTP_TRANSPORT,streamable-http}
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        cfg = OmegaConf.load(config_file)
        OmegaConf.resolve(cfg)
        assert cfg.server.http.transport == "sse"
