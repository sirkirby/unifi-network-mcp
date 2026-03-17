"""UniFi controller type detection.

Determines whether the controller is a UniFi OS appliance (UDM, UDR, etc.)
or a standalone/self-hosted Network Application. This affects API path
routing: UniFi OS uses /proxy/network/... while standalone uses /api/...
"""

import enum
import logging

import aiohttp

logger = logging.getLogger(__name__)


class ControllerType(enum.Enum):
    UNIFI_OS = "proxy"
    STANDALONE = "direct"
    AUTO = "auto"

    @classmethod
    def from_config(cls, value: str) -> "ControllerType":
        mapping = {"proxy": cls.UNIFI_OS, "direct": cls.STANDALONE, "auto": cls.AUTO}
        result = mapping.get(value.lower(), cls.AUTO)
        if value.lower() not in mapping:
            logger.warning("[detection] Unknown controller type '%s', falling back to auto", value)
        return result


async def detect_controller_type_pre_login(
    host: str, port: int, verify_ssl: bool = False, timeout: float = 10.0
) -> ControllerType | None:
    """Probe the controller before login to detect type.

    Strategy:
    - GET the base URL without following redirects
    - UniFi OS returns 200 with x-csrf-token header or HTML
    - Standalone controllers redirect (301/302) to /manage

    Returns:
        ControllerType.UNIFI_OS or ControllerType.STANDALONE if detected, None otherwise.
    """
    url = f"https://{host}:{port}"
    ssl_context = None if verify_ssl else False
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    try:
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            async with session.get(url, ssl=ssl_context, allow_redirects=False) as resp:
                headers = resp.headers
                if "x-csrf-token" in headers or resp.status == 200:
                    return ControllerType.UNIFI_OS
                if resp.status in (302, 301):
                    return ControllerType.STANDALONE
    except Exception as e:
        logger.debug("[detection] Pre-login probe failed: %s", e)

    return None


async def detect_controller_type_by_api_probe(
    session: aiohttp.ClientSession, host: str, port: int, verify_ssl: bool = False
) -> ControllerType | None:
    """Probe API endpoints to detect controller type (requires authenticated session).

    Tries both UniFi OS and standalone API paths for /api/self/sites.
    Returns the type corresponding to the first path that returns HTTP 200.

    Returns:
        ControllerType.UNIFI_OS or ControllerType.STANDALONE if detected, None otherwise.
    """
    url_base = f"https://{host}:{port}"
    ssl_context = None if verify_ssl else False

    for path, expected_type in [
        ("/proxy/network/api/self/sites", ControllerType.UNIFI_OS),
        ("/api/self/sites", ControllerType.STANDALONE),
    ]:
        try:
            async with session.get(f"{url_base}{path}", ssl=ssl_context) as resp:
                if resp.status == 200:
                    logger.info("[detection] Detected %s via %s", expected_type.name, path)
                    return expected_type
        except Exception:
            continue

    return None
