"""Diagnostics must not be the way an address reaches a log.

`UNIFI_MCP_DIAGNOSTICS=true` logs whole tool payloads and API request/response
bodies at INFO. Those payloads are exactly the controller records the privacy rule
in AGENTS.md is about: client MACs, IPs, and the controller's own address.
`redact_sensitive_fields` does not cover them -- it decides by key name and targets
secret material, and none of `mac`, `ip` or `url` is in that vocabulary.
"""

import json
import logging

import pytest
from unifi_core import diagnostics

MAC = "aa:bb:cc:dd:ee:ff"
IP = "192.168.1.89"
URL = "https://unifi-console.invalid:11443/proxy/network/api/s/default/stat/sta"


@pytest.fixture
def diagnostics_on(monkeypatch):
    monkeypatch.setattr(diagnostics, "_diag_cfg", lambda: {"enabled": True, "max_payload_chars": 4000})
    monkeypatch.setattr(diagnostics, "_logger", logging.getLogger("unifi-core.diagnostics-test"))
    return diagnostics


def _emitted(caplog) -> str:
    return "\n".join(r.getMessage() for r in caplog.records)


class TestToolCalls:
    def test_a_mac_argument_is_masked(self, diagnostics_on, caplog) -> None:
        with caplog.at_level(logging.DEBUG):
            diagnostics_on.log_tool_call("unifi_block_client", (), {"mac_address": MAC}, {"success": True}, 1.0)

        assert MAC not in _emitted(caplog)
        assert "unifi_block_client" in _emitted(caplog)

    def test_a_result_carrying_clients_is_masked(self, diagnostics_on, caplog) -> None:
        result = {"clients": [{"mac": MAC, "ip": IP, "hostname": "a-laptop"}]}
        with caplog.at_level(logging.DEBUG):
            diagnostics_on.log_tool_call("unifi_list_clients", (), {}, result, 1.0)

        emitted = _emitted(caplog)
        assert MAC not in emitted
        assert IP not in emitted

    def test_an_error_string_quoting_an_address_is_masked(self, diagnostics_on, caplog) -> None:
        with caplog.at_level(logging.DEBUG):
            diagnostics_on.log_tool_call(
                "unifi_get_client_details", (), {}, None, 1.0, error=ConnectionError(f"no route to {IP}")
            )

        assert IP not in _emitted(caplog)

    def test_the_shape_survives_masking(self, diagnostics_on, caplog) -> None:
        """A masked payload is still the payload: an operator reads it to see the call."""
        with caplog.at_level(logging.DEBUG):
            diagnostics_on.log_tool_call("unifi_block_client", (), {"mac_address": MAC}, {"success": True}, 12.0)

        payload = json.loads(_emitted(caplog).split("TOOL ", 1)[1])
        assert payload["tool"] == "unifi_block_client"
        assert payload["duration_ms"] == 12
        assert "mac_address" in payload["kwargs"]
        assert payload["result"] == {"success": True}


class TestApiRequests:
    def test_the_url_the_path_and_the_body_are_masked(self, diagnostics_on, caplog) -> None:
        with caplog.at_level(logging.DEBUG):
            diagnostics_on.log_api_request(
                "post",
                f"/proxy/network/api/s/default/stat/sta/{MAC}",
                {"macs": [MAC], "target": URL},
                {"data": [{"ip": IP}]},
                5.0,
                True,
            )

        emitted = _emitted(caplog)
        for secret in (MAC, IP, "unifi-console.invalid"):
            assert secret not in emitted
        assert "POST" in emitted

    def test_a_clean_payload_is_unchanged(self, diagnostics_on, caplog) -> None:
        with caplog.at_level(logging.DEBUG):
            diagnostics_on.log_api_request("get", "/api/self", None, {"data": [{"name": "admin"}]}, 5.0, True)

        assert '"name": "admin"' in _emitted(caplog)


def test_nothing_is_logged_when_diagnostics_are_off(monkeypatch, caplog) -> None:
    monkeypatch.setattr(diagnostics, "_diag_cfg", lambda: {"enabled": False})
    with caplog.at_level(logging.DEBUG):
        diagnostics.log_tool_call("unifi_block_client", (), {"mac_address": MAC}, None, 1.0)
        diagnostics.log_api_request("get", f"/x/{MAC}", {"mac": MAC}, None, 1.0, True)

    assert _emitted(caplog) == ""


@pytest.mark.parametrize("limit", range(20, 120, 4))
def test_no_fragment_of_an_address_survives_truncation(limit: int) -> None:
    """Masking runs BEFORE truncation on purpose. Truncating first can cut a MAC in
    half, and half a MAC no longer matches the pattern, so the fragment ships."""
    payload = {"tool": "unifi_block_client", "kwargs": {"mac_address": MAC}}

    text = diagnostics._safe_json(payload, limit)

    assert "aa:bb:cc:dd" not in text
    assert len(text) <= limit + len("... [truncated 9999 chars]")


def test_truncation_still_reports_the_length_of_what_was_written() -> None:
    payload = {"tool": "unifi_block_client", "kwargs": {"mac_address": MAC, "note": "x" * 500}}

    text = diagnostics._safe_json(payload, 80)

    assert text.startswith('{"tool": "unifi_block_client"')
    assert "truncated" in text
