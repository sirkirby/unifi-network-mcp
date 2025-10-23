import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import aiohttp
import time as _time

from aiounifi.controller import Controller
from aiounifi.models.configuration import Configuration
from aiounifi.errors import LoginRequired, RequestError, ResponseError
from aiounifi.models.api import ApiRequest, ApiRequestV2, TypedApiResponse

logger = logging.getLogger("unifi-network-mcp")


async def detect_with_retry(
    session: aiohttp.ClientSession,
    base_url: str,
    max_retries: int = 3,
    timeout: int = 5
) -> Optional[bool]:
    """
    Detect UniFi OS with exponential backoff retry.

    Args:
        session: Active aiohttp.ClientSession
        base_url: Base URL of controller
        max_retries: Maximum retry attempts (default: 3)
        timeout: Detection timeout per attempt in seconds (default: 5)

    Returns:
        True: UniFi OS detected
        False: Standard controller detected
        None: Detection failed after all retries

    Implementation:
        - Retries up to max_retries times
        - Uses exponential backoff: 1s, 2s, 4s, ...
        - Logs retry attempts at debug level
        - Returns None if all attempts fail
    """
    for attempt in range(max_retries):
        try:
            result = await detect_unifi_os_proactively(session, base_url, timeout)
            if result is not None:
                return result
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.debug(
                    f"Detection attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.warning(
                    f"Detection failed after {max_retries} attempts: {e}"
                )

    return None


def _generate_detection_failure_message(base_url: str, port: int) -> str:
    """Generate user-friendly troubleshooting message for detection failures."""
    return f"""
UniFi controller path detection failed.

Troubleshooting Steps:
1. Verify network connectivity to {base_url}
2. Check controller is accessible on port {port}
3. Manually set controller type using environment variable:
   - For UniFi OS (Cloud Gateway, UDM-Pro): export UNIFI_CONTROLLER_TYPE=proxy
   - For standalone controllers: export UNIFI_CONTROLLER_TYPE=direct

For more help, see: https://github.com/sirkirby/unifi-network-mcp/issues/19
"""


async def _probe_endpoint(
    session: aiohttp.ClientSession,
    url: str,
    timeout: aiohttp.ClientTimeout,
    endpoint_name: str
) -> bool:
    """
    Probe a single UniFi endpoint to check if it responds successfully.

    Args:
        session: Active aiohttp.ClientSession for making requests
        url: Full URL to probe
        timeout: Request timeout configuration
        endpoint_name: Human-readable name for logging (e.g., "UniFi OS", "standard")

    Returns:
        True if endpoint responds with 200 and valid JSON containing "data" key
        False otherwise
    """
    try:
        logger.debug(f"Probing {endpoint_name} endpoint: {url}")

        async with session.get(url, timeout=timeout, ssl=False) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    if "data" in data:
                        logger.debug(f"{endpoint_name} endpoint responded successfully")
                        return True
                except Exception as e:
                    logger.debug(f"{endpoint_name} endpoint returned 200 but invalid JSON: {e}")
    except asyncio.TimeoutError:
        logger.debug(f"{endpoint_name} endpoint probe timed out")
    except aiohttp.ClientError as e:
        logger.debug(f"{endpoint_name} endpoint probe failed: {e}")
    except Exception as e:
        logger.debug(f"Unexpected error probing {endpoint_name} endpoint: {e}")

    return False


async def detect_unifi_os_proactively(
    session: aiohttp.ClientSession,
    base_url: str,
    timeout: int = 5
) -> Optional[bool]:
    """
    Detect if controller is UniFi OS by testing endpoint variants.

    Probes both UniFi OS (/proxy/network/api/self/sites) and standard
    (/api/self/sites) endpoints to empirically determine path requirement.

    Args:
        session: Active aiohttp.ClientSession for making requests
        base_url: Base URL of controller (e.g., 'https://192.168.1.1:443')
        timeout: Detection timeout in seconds (default: 5)

    Returns:
        True: UniFi OS detected (requires /proxy/network prefix)
        False: Standard controller detected (uses /api paths)
        None: Detection failed, fall back to aiounifi's check_unifi_os()

    Implementation Notes:
        - Tries UniFi OS endpoint first (newer controllers)
        - Falls back to standard endpoint if UniFi OS fails
        - Returns None if both fail (timeout, network error, etc.)
        - Per FR-012: If both succeed, prefers direct (returns False)
    """
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    # Probe both endpoints
    unifi_os_url = f"{base_url}/proxy/network/api/self/sites"
    standard_url = f"{base_url}/api/self/sites"

    unifi_os_result = await _probe_endpoint(session, unifi_os_url, client_timeout, "UniFi OS")
    standard_result = await _probe_endpoint(session, standard_url, client_timeout, "standard")

    # Determine result based on probe outcomes
    if unifi_os_result and standard_result:
        # FR-012: Both succeed, prefer direct (standard)
        logger.info("Both endpoints succeeded - preferring standard (direct) paths")
        return False
    elif unifi_os_result:
        logger.info("Detected UniFi OS controller (proxy paths required)")
        return True
    elif standard_result:
        logger.info("Detected standard controller (direct paths)")
        return False
    else:
        logger.warning("Auto-detection failed - both endpoints unsuccessful")
        return None


class ConnectionManager:
    """Manages the connection and session with the Unifi Network Controller."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 443,
        site: str = "default",
        verify_ssl: bool = False,
        cache_timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        """Initialize the Connection Manager."""
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.site = site
        self.verify_ssl = verify_ssl
        self.cache_timeout = cache_timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.controller: Optional[Controller] = None
        self._aiohttp_session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        self._connect_lock = asyncio.Lock()
        self._cache: Dict[str, Any] = {}
        self._last_cache_update: Dict[str, float] = {}

        # Path detection state
        self._unifi_os_override: Optional[bool] = None
        """
        Override for is_unifi_os flag:
        - None: Use aiounifi's detection (no override)
        - True: Force UniFi OS paths (/proxy/network)
        - False: Force standard paths (/api)
        """

    @property
    def url_base(self) -> str:
        proto = "https"
        return f"{proto}://{self.host}:{self.port}"

    async def initialize(self) -> bool:
        """Initialize the controller connection (correct for attached aiounifi version)."""
        if self._initialized and self.controller and self._aiohttp_session and not self._aiohttp_session.closed:
            return True

        async with self._connect_lock:
            if self._initialized and self.controller and self._aiohttp_session and not self._aiohttp_session.closed:
                 return True

            logger.info(f"Attempting to connect to Unifi controller at {self.host}...")
            for attempt in range(self._max_retries):
                session_created = False
                try:
                    if self.controller:
                        self.controller = None
                    if self._aiohttp_session and not self._aiohttp_session.closed:
                         await self._aiohttp_session.close()
                         self._aiohttp_session = None

                    connector = aiohttp.TCPConnector(ssl=False if not self.verify_ssl else None)
                    self._aiohttp_session = aiohttp.ClientSession(
                        connector=connector,
                        cookie_jar=aiohttp.CookieJar(unsafe=True)
                    )
                    session_created = True

                    # Manual override configuration (FR-004: runs before login, no auth needed)
                    from src.bootstrap import UNIFI_CONTROLLER_TYPE

                    if UNIFI_CONTROLLER_TYPE == "proxy":
                        self._unifi_os_override = True
                        logger.info("Controller type forced to UniFi OS (proxy) via config")
                    elif UNIFI_CONTROLLER_TYPE == "direct":
                        self._unifi_os_override = False
                        logger.info("Controller type forced to standard (direct) via config")

                    config = Configuration(
                        session=self._aiohttp_session,
                        host=self.host,
                        username=self.username,
                        password=self.password,
                        port=self.port,
                        site=self.site,
                    )

                    self.controller = Controller(config=config)

                    await self.controller.login()

                    # Auto-detection (FR-002: runs after login for authenticated probes)
                    if UNIFI_CONTROLLER_TYPE == "auto":
                        # Check if already detected (session cache - FR-011)
                        if self._unifi_os_override is None:
                            # Proactive detection with retry (FR-001, FR-005, FR-008)
                            detected = await detect_with_retry(
                                self._aiohttp_session,
                                self.url_base,
                                max_retries=3,
                                timeout=5
                            )
                            if detected is not None:
                                self._unifi_os_override = detected
                                mode = "UniFi OS (proxy)" if detected else "standard (direct)"
                                logger.info(f"Auto-detected controller type: {mode}")
                            else:
                                # Show clear error message (FR-009)
                                error_msg = _generate_detection_failure_message(self.url_base, self.port)
                                logger.warning(error_msg)
                                logger.warning("Falling back to aiounifi's check_unifi_os()")
                        else:
                            logger.debug(f"Using cached detection result: {self._unifi_os_override}")

                    self._initialized = True
                    logger.info(f"Successfully connected to Unifi controller at {self.host} for site '{self.site}'")
                    self._invalidate_cache()
                    return True

                except (LoginRequired, RequestError, ResponseError, asyncio.TimeoutError, aiohttp.ClientError) as e:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    if session_created and self._aiohttp_session and not self._aiohttp_session.closed:
                        await self._aiohttp_session.close()
                        self._aiohttp_session = None
                    self.controller = None
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_delay)
                    else:
                        logger.error(f"Failed to initialize Unifi controller after {self._max_retries} attempts: {e}")
                        self._initialized = False
                        return False
                except Exception as e:
                    logger.error(f"Unexpected error during controller initialization: {e}", exc_info=True)
                    if session_created and self._aiohttp_session and not self._aiohttp_session.closed:
                        await self._aiohttp_session.close()
                        self._aiohttp_session = None
                    self._initialized = False
                    self.controller = None
                    return False
            return False

    async def ensure_connected(self) -> bool:
        """Ensure the controller is connected, attempting to reconnect if necessary."""

        if (
            not self._initialized
            or not self.controller
            or not self._aiohttp_session
            or self._aiohttp_session.closed
        ):
            logger.warning(
                "Controller not initialized or session lost/closed, attempting to reconnect..."
            )
            return await self.initialize()

        try:
            internal_session = self.controller.connectivity.config.session
            if internal_session.closed:
                logger.warning(
                    "Controller session found closed (via connectivity.config.session), attempting to reconnect..."
                )
                return await self.initialize()
        except AttributeError:
            logger.debug(
                "connectivity.config.session attribute not found – skipping additional session check."
            )

        return True

    async def cleanup(self):
        """Clean up resources and close connections."""
        if self._aiohttp_session and not self._aiohttp_session.closed:
             await self._aiohttp_session.close()
             logger.info("aiohttp session closed.")
        self._initialized = False
        self.controller = None
        self._aiohttp_session = None
        self._cache = {}
        self._last_cache_update = {}
        logger.info("Unifi connection manager resources cleared.")

    async def request(
        self,
        api_request: ApiRequest | ApiRequestV2,
        return_raw: bool = False
    ) -> Any:
        """Make a request to the controller API, handling raw responses."""
        if not await self.ensure_connected() or not self.controller:
            raise ConnectionError("Unifi Controller is not connected.")

        # Apply override if we have better detection (FR-003: use cached detection)
        original_is_unifi_os = None
        if self._unifi_os_override is not None:
            original_is_unifi_os = self.controller.connectivity.is_unifi_os
            if original_is_unifi_os != self._unifi_os_override:
                logger.debug(
                    f"Overriding is_unifi_os from {original_is_unifi_os} "
                    f"to {self._unifi_os_override} for this request"
                )
                self.controller.connectivity.is_unifi_os = self._unifi_os_override

        request_method = self.controller.connectivity._request if return_raw else self.controller.request

        try:
            # Diagnostics: capture timing and payloads without leaking secrets
            start_ts = _time.perf_counter()
            response = await request_method(api_request)
            duration_ms = (_time.perf_counter() - start_ts) * 1000.0
            try:
                from src.utils.diagnostics import log_api_request, diagnostics_enabled  # lazy import to avoid cycles
                if diagnostics_enabled():
                    payload = getattr(api_request, "json", None) or getattr(api_request, "data", None)
                    log_api_request(api_request.method, api_request.path, payload, response, duration_ms, True)
            except Exception:
                pass
            return response if return_raw else response.get("data")

        except LoginRequired:
            logger.warning("Login required detected during request, attempting re-login...")
            if await self.initialize():
                if not self.controller:
                     raise ConnectionError("Re-login failed, controller not available.")
                logger.info("Re-login successful, retrying original request...")
                try:
                    start_ts = _time.perf_counter()
                    retry_response = await request_method(api_request)
                    duration_ms = (_time.perf_counter() - start_ts) * 1000.0
                    try:
                        from src.utils.diagnostics import log_api_request, diagnostics_enabled
                        if diagnostics_enabled():
                            payload = getattr(api_request, "json", None) or getattr(api_request, "data", None)
                            log_api_request(api_request.method, api_request.path, payload, retry_response, duration_ms, True)
                    except Exception:
                        pass
                    return retry_response if return_raw else retry_response.get("data")
                except Exception as retry_e:
                    logger.error(f"API request failed even after re-login: {api_request.method.upper()} {api_request.path} - {retry_e}")
                    raise retry_e from None
            else:
                raise ConnectionError("Re-login failed, cannot proceed with request.")
        except (RequestError, ResponseError, aiohttp.ClientError) as e:
            logger.error(f"API request error: {api_request.method.upper()} {api_request.path} - {e}")
            try:
                from src.utils.diagnostics import log_api_request, diagnostics_enabled
                if diagnostics_enabled():
                    payload = getattr(api_request, "json", None) or getattr(api_request, "data", None)
                    log_api_request(api_request.method, api_request.path, payload, {"error": str(e)}, 0.0, False)
            except Exception:
                pass
            raise
        except Exception as e:
            logger.error(f"Unexpected error during API request: {api_request.method.upper()} {api_request.path} - {e}", exc_info=True)
            try:
                from src.utils.diagnostics import log_api_request, diagnostics_enabled
                if diagnostics_enabled():
                    payload = getattr(api_request, "json", None) or getattr(api_request, "data", None)
                    log_api_request(api_request.method, api_request.path, payload, {"error": str(e)}, 0.0, False)
            except Exception:
                pass
            raise
        finally:
            # Always restore original value (FR-003: maintain session state)
            if original_is_unifi_os is not None:
                self.controller.connectivity.is_unifi_os = original_is_unifi_os

    # --- Cache Management ---

    def _update_cache(self, key: str, data: Any, timeout: Optional[int] = None):
        """Update the cache with new data."""
        self._cache[key] = data
        self._last_cache_update[key] = time.time()
        logger.debug(f"Cache updated for key '{key}' with timeout {timeout or self.cache_timeout}s")

    def _is_cache_valid(self, key: str, timeout: Optional[int] = None) -> bool:
        """Check if the cache for a given key is still valid."""
        if key not in self._cache or key not in self._last_cache_update:
            return False

        effective_timeout = timeout if timeout is not None else self.cache_timeout
        current_time = time.time()
        last_update = self._last_cache_update[key]

        is_valid = (current_time - last_update) < effective_timeout
        logger.debug(f"Cache check for key '{key}': {'Valid' if is_valid else 'Expired'} (Timeout: {effective_timeout}s)")
        return is_valid

    def get_cached(self, key: str, timeout: Optional[int] = None) -> Optional[Any]:
        """Get data from cache if valid."""
        if self._is_cache_valid(key, timeout):
            logger.debug(f"Cache hit for key '{key}'")
            return self._cache[key]
        logger.debug(f"Cache miss for key '{key}'")
        return None

    def _invalidate_cache(self, prefix: Optional[str] = None):
        """Invalidate cache entries, optionally by prefix."""
        if prefix:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
                if key in self._last_cache_update: del self._last_cache_update[key]
            logger.debug(f"Invalidated cache for keys starting with '{prefix}'")
        else:
            self._cache = {}
            self._last_cache_update = {}
            logger.debug("Invalidated entire cache")

    async def set_site(self, site: str):
        """Update the target site and invalidate relevant cache.

        Note: This attempts a dynamic switch. Full stability might require
        re-initializing the connection manager or restarting the server.
        """
        if self.controller and hasattr(self.controller.connectivity, 'config'):
            self.controller.connectivity.config.site = site
            self.site = site
            self._invalidate_cache()
            logger.info(f"Switched target site to '{site}'. Cache invalidated. Re-login might occur on next request.")
        else:
            logger.warning("Cannot set site dynamically, controller or config not available.")