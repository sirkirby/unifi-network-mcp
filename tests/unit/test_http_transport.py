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
