"""A dependency's log records keep their wording and lose the address."""

import logging

import pytest
from unifi_core.log_filters import (
    AddressMaskingFilter,
    install_address_masking,
    mask_network_locations,
)

HOST = "unifi-console.invalid"


@pytest.mark.parametrize(
    "text",
    [
        "wss://unifi-console.invalid:8443/proxy/network/wss/s/default/events",
        "Cannot connect to host unifi-console.invalid:8443 ssl:default",
        "401, message='Invalid response status', url='wss://unifi-console.invalid:8443/wss'",
    ],
)
def test_a_url_is_masked_and_the_sentence_survives(text: str) -> None:
    masked = mask_network_locations(text)
    assert "[redacted]" in masked
    assert HOST not in masked


@pytest.mark.parametrize(
    ("text", "gone"),
    [
        ("Error connecting to 192.168.1.89:11443", "192.168.1.89"),
        ("data (from https://10.0.0.1/api/self) ok", "10.0.0.1"),
        ("client aa:bb:cc:dd:ee:ff disconnected", "aa:bb:cc:dd:ee:ff"),
        ("peer [2001:db8::1]:8443 closed", "2001:db8::1"),
    ],
)
def test_addresses_are_masked(text: str, gone: str) -> None:
    assert gone not in mask_network_locations(text)


def test_the_wording_around_the_address_is_kept() -> None:
    masked = mask_network_locations("Server handshake error connecting to UniFi websocket: 'wss://h.invalid/w'")
    assert masked.startswith("Server handshake error connecting to UniFi websocket:")
    assert "h.invalid" not in masked


@pytest.mark.parametrize(
    "text",
    [
        "",
        "no addresses here",
        "version 1.2.3.4.5 of the thing",
        # A dotted name with no port is a module, not a host.
        "aiounifi.interfaces.connectivity is noisy",
        # A source location has the shape of a host and a port; the line number is
        # worth more than the theoretical leak.
        'File "connectivity.py:490" in websocket',
    ],
)
def test_text_without_an_address_is_untouched(text: str) -> None:
    assert mask_network_locations(text) == text


def test_the_aiohttp_connect_error_loses_its_host() -> None:
    """The single most common way the address reaches a log."""
    masked = mask_network_locations(
        "Cannot connect to host unifi-console.invalid:8443 ssl:default [Connect call failed]"
    )
    assert HOST not in masked
    assert "Cannot connect to host" in masked
    assert "[Connect call failed]" in masked


class TestFilter:
    @staticmethod
    def _record(msg, *args, exc_info=None):
        return logging.LogRecord("aiounifi.interfaces.connectivity", logging.ERROR, __file__, 1, msg, args, exc_info)

    def test_the_record_is_kept_and_rewritten(self) -> None:
        record = self._record("Error connecting to UniFi websocket: '%s'", "wss://h.invalid:8443/w")

        assert AddressMaskingFilter().filter(record) is True
        assert "h.invalid" not in record.getMessage()
        assert "Error connecting to UniFi websocket" in record.getMessage()

    def test_args_are_cleared_so_a_later_format_cannot_restore_them(self) -> None:
        record = self._record("to %s", "https://h.invalid/x")
        AddressMaskingFilter().filter(record)
        assert record.args == ()
        assert "h.invalid" not in record.getMessage()

    def test_a_traceback_is_dropped_because_it_reprints_the_url(self) -> None:
        try:
            raise ConnectionError("Cannot connect to host h.invalid:8443")
        except ConnectionError:
            import sys

            record = self._record("failed", exc_info=sys.exc_info())
        AddressMaskingFilter().filter(record)
        assert record.exc_info is None

    def test_a_broken_format_string_does_not_lose_the_record(self) -> None:
        record = self._record("%s and %s", "only-one")
        assert AddressMaskingFilter().filter(record) is True


class TestInstall:
    def test_it_reaches_child_loggers_a_parent_filter_would_miss(self) -> None:
        parent = "probe_pkg_child_reach"
        logging.getLogger(f"{parent}.deep.module")

        touched = install_address_masking(parent)

        assert f"{parent}.deep.module" in touched
        child = logging.getLogger(f"{parent}.deep.module")
        assert any(isinstance(f, AddressMaskingFilter) for f in child.filters)

    def test_it_is_idempotent(self) -> None:
        parent = "probe_pkg_idempotent"
        install_address_masking(parent)
        install_address_masking(parent)

        logger = logging.getLogger(parent)
        assert sum(isinstance(f, AddressMaskingFilter) for f in logger.filters) == 1

    def test_it_floors_the_level_so_payload_dumps_never_render(self) -> None:
        parent = "probe_pkg_floor"
        logging.getLogger(parent).setLevel(logging.DEBUG)

        install_address_masking(parent)

        assert not logging.getLogger(parent).isEnabledFor(logging.DEBUG)
