"""Keeping an address out of a log line without losing the line.

Two callers, one rule. Diagnostics logs whole tool payloads and API bodies at
INFO, and those payloads are controller records full of MACs, IPs and the
controller's own URL. A dependency (aiounifi) reports useful things — a rejected
handshake, a socket closed by the peer — and puts the address in the text while it
does. AGENTS.md says an address never reaches a log, which looked like a choice
between the message and the rule.

Masking keeps both: :func:`mask_network_locations` rewrites the text, and
:class:`AddressMaskingFilter` applies it to a logger this project does not own.

``unifi_core.redaction`` is the wrong tool for this and deliberately so: it decides
by key name and targets secret material, so it never sees a ``mac``, an ``ip`` or a
URL, and a tool that returns a client list is *supposed* to return those.

**What is masked:** every URL, every IPv4/IPv6 literal (with or without a port),
and every MAC-shaped token.

**What is masked** (continued): a bare ``host:port``, which is the form
aiohttp's ``ClientConnectorError`` uses — ``Cannot connect to host <host>:<port>``
— and therefore the single most common way the address reaches a log.

**What is not:** a hostname with no port and no scheme, and arbitrary strings
inside a controller payload (a client's name, say). Those appear only in
aiounifi's DEBUG dumps of whole JSON documents, which cannot be masked by pattern
with any confidence — so the package logger is also floored at INFO and those
never render.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable

from unifi_core.mac import mask_macs

__all__ = ["mask_network_locations", "AddressMaskingFilter", "install_address_masking"]

REDACTED = "[redacted]"

# A URL of any scheme, up to the first character that cannot be inside one. The
# quote is excluded because aiounifi writes url='wss://...' and the closing quote
# would otherwise be swallowed.
_URL_RE = re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s'\"<>\\\]},;)]+", re.IGNORECASE)

# A dotted-quad, optionally with a port. Bounded by non-digit/non-dot so a version
# string such as 1.2.3.4.5 is not half-matched.
_IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?(?![\d.])")

# A bracketed IPv6 literal, which is the form that appears in a URL or a host:port.
_IPV6_BRACKET_RE = re.compile(r"\[[0-9a-f:]{2,}(?:%[0-9a-z]+)?\](?::\d{1,5})?", re.IGNORECASE)

# A bare host:port. The port is required: without it this would mask every dotted
# module name, and "aiounifi.interfaces.connectivity" is not an address.
_HOST_PORT_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+([a-z][a-z0-9\-]*):\d{1,5}\b", re.IGNORECASE)

# ...which leaves one false positive worth excluding by name: a source location.
# "connectivity.py:490" is the same shape as a host and a port, and garbling it
# would cost a reader the line number for nothing.
_SOURCE_SUFFIXES = frozenset({"py", "pyi", "js", "ts", "json", "yaml", "yml", "toml", "md", "txt", "log", "sh"})


def _mask_host_port(match: re.Match[str]) -> str:
    if match.group(1).lower() in _SOURCE_SUFFIXES:
        return match.group(0)
    return REDACTED


def mask_network_locations(text: str) -> str:
    """Return *text* with every URL, IP literal and MAC replaced by a marker.

    URLs go first: a host inside one is then already gone, so the IP patterns
    cannot half-match what is left behind.
    """
    if not text:
        return text
    masked = _URL_RE.sub(REDACTED, text)
    masked = _IPV6_BRACKET_RE.sub(REDACTED, masked)
    masked = _IPV4_RE.sub(REDACTED, masked)
    masked = _HOST_PORT_RE.sub(_mask_host_port, masked)
    return mask_macs(masked)


class AddressMaskingFilter(logging.Filter):
    """Rewrite a record's message so it carries no address, and keep the record.

    Formats the record once and replaces ``msg`` with the masked result, clearing
    ``args`` so a later format cannot reintroduce them. ``exc_info`` and
    ``stack_info`` are dropped: a traceback re-renders the exception's own text,
    which is where the URL came from in the first place.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - a broken format string must not lose the record
            message = str(record.msg)
        record.msg = mask_network_locations(message)
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def install_address_masking(prefix: str, *, floor: int = logging.INFO) -> list[str]:
    """Attach the filter to *prefix* and every logger already created beneath it.

    Returns the logger names it touched. A filter attached to a logger runs only
    for records logged through that logger — a child does not inherit it — so the
    tree is walked. The dependency's modules bind their logger at import, and this
    is called from a module that imports them, so the tree is complete by now.

    Also floors each logger at *floor*, because the filter cannot make a dump of a
    whole controller payload safe.
    """
    touched: list[str] = []
    for name in _logger_names(prefix):
        logger = logging.getLogger(name)
        if not any(isinstance(existing, AddressMaskingFilter) for existing in logger.filters):
            logger.addFilter(AddressMaskingFilter())
        if logger.level == logging.NOTSET or logger.level < floor:
            logger.setLevel(floor)
        touched.append(name)
    return touched


def _logger_names(prefix: str) -> Iterable[str]:
    yield prefix
    for name in sorted(logging.Logger.manager.loggerDict):
        if name.startswith(f"{prefix}."):
            yield name
