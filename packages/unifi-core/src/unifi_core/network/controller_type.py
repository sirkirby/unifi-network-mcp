"""Resolution of the UNIFI_CONTROLLER_TYPE environment variable.

Lives in unifi-core (not in any MCP server's bootstrap) because the
connection logic that consumes it lives in unifi-core. Previously the
constant was defined in `unifi_network_mcp.bootstrap` and the connection
manager imported it back across the package boundary, which broke any
unifi-core consumer that didn't also have unifi-network-mcp installed
(e.g. unifi-api-server).

`auto`   — detect controller type at login (default; works for UDM/UCK/Cloud)
`proxy`  — force UniFi OS path prefix (`/proxy/network/api`)
`direct` — force standard path prefix (`/api`)
"""

from __future__ import annotations

import logging
import os

VALID_CONTROLLER_TYPES = frozenset({"auto", "proxy", "direct"})

_logger = logging.getLogger(__name__)


def resolve_controller_type() -> str:
    """Return the configured controller type, falling back to 'auto'.

    Reads each call so env changes propagate without a process restart;
    consumers that want to cache should do so themselves.
    """
    value = os.getenv("UNIFI_CONTROLLER_TYPE", "auto").lower()
    if value not in VALID_CONTROLLER_TYPES:
        _logger.warning(
            "Invalid UNIFI_CONTROLLER_TYPE: %r. Must be one of: %s. Defaulting to 'auto'.",
            value,
            ", ".join(sorted(VALID_CONTROLLER_TYPES)),
        )
        return "auto"
    return value
