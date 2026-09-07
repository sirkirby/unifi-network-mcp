"""Diagnostics record operation metadata without inspecting controller values."""

import json
import logging

import pytest
from unifi_core import diagnostics


@pytest.mark.parametrize("value,expected", [("false", False), ("0", False), ("true", True), (False, False)])
def test_configuration_boolean_strings_are_parsed(monkeypatch, value, expected):
    from omegaconf import OmegaConf

    config = OmegaConf.create({"server": {"diagnostics": {"enabled": value}}})
    monkeypatch.setattr(diagnostics, "_config_provider", lambda: config)
    assert diagnostics.diagnostics_enabled() is expected


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(
        diagnostics,
        "_diag_cfg",
        lambda: {
            "enabled": True,
            "log_tool_args": True,
            "log_tool_result": True,
            "max_payload_chars": 4000,
        },
    )
    monkeypatch.setattr(diagnostics, "_logger", logging.getLogger("diagnostics-test"))


@pytest.mark.parametrize(
    "value", ["client-name", "plain-hostname", "2001:db8::1234", "aa:bb:cc:dd:ee:ff", "password-secret"]
)
def test_tool_logs_only_metadata_even_with_payload_flags_enabled(enabled, caplog, value):
    with caplog.at_level(logging.INFO):
        diagnostics.log_tool_call("unifi_list_clients", (value,), {value: value}, {"success": True, "data": value}, 12)
    assert json.loads(caplog.records[-1].getMessage().removeprefix("TOOL ")) == {
        "tool": "unifi_list_clients",
        "duration_ms": 12,
        "success": True,
    }
    assert value not in caplog.text


def test_exception_logs_class_without_message_or_traceback(enabled, caplog):
    with caplog.at_level(logging.INFO):
        diagnostics.log_tool_call("unifi_list_clients", (), {}, None, 1, ValueError("private-controller"))
    assert "ValueError" in caplog.text
    assert "private-controller" not in caplog.text
    assert caplog.records[-1].exc_info is None


def test_api_ignores_paths_and_unserializable_payloads(enabled, caplog):
    class PrivatePayload:
        def __str__(self):
            raise AssertionError("diagnostics must not inspect payloads")

    with caplog.at_level(logging.INFO):
        diagnostics.log_api_request("post", "/private-client", PrivatePayload(), PrivatePayload(), 5, True)
    assert json.loads(caplog.records[-1].getMessage().removeprefix("API ")) == {
        "method": "POST",
        "duration_ms": 5,
        "ok": True,
    }


def test_disabled_diagnostics_emit_nothing(monkeypatch, caplog):
    monkeypatch.setattr(diagnostics, "_diag_cfg", lambda: {"enabled": False})
    with caplog.at_level(logging.INFO):
        diagnostics.log_tool_call("unifi_list_clients", (), {}, None, 1)
        diagnostics.log_api_request("GET", "/private-client", {}, {}, 1, True)
    assert not caplog.records
