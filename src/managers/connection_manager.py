import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import aiohttp

from aiounifi.controller import Controller
from aiounifi.models.configuration import Configuration
from aiounifi.errors import LoginRequired, RequestError, ResponseError
from aiounifi.models.api import ApiRequest, ApiRequestV2, TypedApiResponse

logger = logging.getLogger("unifi-network-mcp")

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

        request_method = self.controller.connectivity._request if return_raw else self.controller.request

        try:
            response = await request_method(api_request)
            return response if return_raw else response.get("data")

        except LoginRequired:
            logger.warning("Login required detected during request, attempting re-login...")
            if await self.initialize():
                if not self.controller:
                     raise ConnectionError("Re-login failed, controller not available.")
                logger.info("Re-login successful, retrying original request...")
                try:
                    retry_response = await request_method(api_request)
                    return retry_response if return_raw else retry_response.get("data")
                except Exception as retry_e:
                    logger.error(f"API request failed even after re-login: {api_request.method.upper()} {api_request.path} - {retry_e}")
                    raise retry_e from None
            else:
                raise ConnectionError("Re-login failed, cannot proceed with request.")
        except (RequestError, ResponseError, aiohttp.ClientError) as e:
            logger.error(f"API request error: {api_request.method.upper()} {api_request.path} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during API request: {api_request.method.upper()} {api_request.path} - {e}", exc_info=True)
            raise

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