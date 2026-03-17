"""Connection management for UniFi Access.

Handles authentication and communication with the UniFi Access controller
via two independent auth paths:

1. **API key path** -- uses ``py-unifi-access`` (``UnifiAccessApiClient``) on the
   dedicated Access API port (default 12445).
2. **Proxy session path** -- logs in via ``/api/auth/login`` on the UniFi OS
   Console (port 443) and proxies requests through
   ``/proxy/access/api/v2/...`` with cookie + CSRF token.

At least one path must succeed during :meth:`initialize`.  When both are
available the caller can choose which path to use per-request (API client
is generally preferred for supported endpoints; the proxy path covers
everything else).
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any, Dict

import aiohttp

from unifi_core.exceptions import UniFiAuthError, UniFiConnectionError
from unifi_core.retry import RetryPolicy, retry_with_backoff

logger = logging.getLogger(__name__)


class AccessConnectionManager:
    """Manages the dual-path connection to the UniFi Access controller.

    Parameters
    ----------
    host:
        IP or hostname of the UniFi OS Console running Access.
    username:
        Local admin username (required for proxy path).
    password:
        Local admin password (required for proxy path).
    port:
        HTTPS port for the UniFi OS Console (default 443).
    verify_ssl:
        Whether to verify the server's TLS certificate.
    api_key:
        Optional API key for the official Access API (port ``api_port``).
    api_port:
        Port for the ``py-unifi-access`` API (default 12445).
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 443,
        verify_ssl: bool = False,
        api_key: str | None = None,
        api_port: int = 12445,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.verify_ssl = verify_ssl

        # Path 1: py-unifi-access (API key auth on dedicated port)
        self._api_client: Any | None = None  # UnifiAccessApiClient
        self._api_key = api_key
        self._api_port = api_port
        self._api_session: aiohttp.ClientSession | None = None

        # Path 2: Proxy session (cookie + CSRF on UniFi OS Console port)
        self._proxy_session: aiohttp.ClientSession | None = None
        self._csrf_token: str = ""
        self._auth_lock = asyncio.Lock()

        # State
        self._api_client_available = False
        self._proxy_available = False
        self._initialized = False

    # ------------------------------------------------------------------
    # SSL helper
    # ------------------------------------------------------------------

    @property
    def _ssl_context(self) -> ssl.SSLContext | bool:
        """Return an SSL context appropriate for the current verify_ssl setting."""
        if self.verify_ssl:
            return True
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> bool:
        """Authenticate via API key and/or proxy session.

        Tries both paths independently.  At least one must succeed or
        :class:`UniFiConnectionError` is raised.

        Uses ``retry_with_backoff`` from :mod:`unifi_core.retry` so
        transient network errors during startup are retried.

        Returns ``True`` on success.
        """
        if self._initialized and (self._api_client_available or self._proxy_available):
            return True

        policy = RetryPolicy(
            max_retries=3,
            base_delay=2.0,
            max_delay=30.0,
            retryable_exceptions=(Exception,),
        )

        async def _connect() -> None:
            await self._try_api_client()
            await self._try_proxy_session()

            if not self._api_client_available and not self._proxy_available:
                raise UniFiConnectionError(
                    f"Failed to establish any auth path to UniFi Access at {self.host}. "
                    "Ensure either an API key or username/password credentials are configured."
                )

        try:
            await retry_with_backoff(_connect, policy=policy)
            self._initialized = True
            logger.info(
                "[access-cm] Connected to UniFi Access at %s (api_client=%s, proxy=%s)",
                self.host,
                self._api_client_available,
                self._proxy_available,
            )
            return True
        except Exception as exc:
            logger.error(
                "[access-cm] Failed to connect to UniFi Access at %s: %s",
                self.host,
                exc,
                exc_info=True,
            )
            self._initialized = False
            raise

    async def _try_api_client(self) -> None:
        """Attempt to initialise the py-unifi-access API client."""
        if not self._api_key:
            logger.debug("[access-cm] No API key configured; skipping API client path.")
            return

        try:
            from unifi_access_api import UnifiAccessApiClient

            connector = aiohttp.TCPConnector(ssl=self._ssl_context)
            self._api_session = aiohttp.ClientSession(connector=connector)
            self._api_client = UnifiAccessApiClient(
                host=f"https://{self.host}:{self._api_port}",
                api_token=self._api_key,
                session=self._api_session,
                verify_ssl=self.verify_ssl,
            )
            await self._api_client.authenticate()
            self._api_client_available = True
            logger.info("[access-cm] API client authenticated on port %s", self._api_port)
        except Exception as exc:
            logger.warning(
                "[access-cm] API client auth failed (non-fatal, will try proxy): %s",
                exc,
            )
            # Clean up the failed session
            if self._api_session and not self._api_session.closed:
                await self._api_session.close()
                self._api_session = None
            self._api_client = None
            self._api_client_available = False

    async def _try_proxy_session(self) -> None:
        """Attempt to establish a proxy session via UniFi OS Console login."""
        if not self.username or not self.password:
            logger.debug("[access-cm] No username/password configured; skipping proxy path.")
            return

        try:
            self._proxy_session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=self._ssl_context),
                cookie_jar=aiohttp.CookieJar(unsafe=True),
            )
            await self._proxy_login()
            self._proxy_available = True
            logger.info("[access-cm] Proxy session established via %s:%s", self.host, self.port)
        except Exception as exc:
            logger.warning(
                "[access-cm] Proxy login failed (non-fatal if API client available): %s",
                exc,
            )
            if self._proxy_session and not self._proxy_session.closed:
                await self._proxy_session.close()
                self._proxy_session = None
            self._proxy_available = False

    async def _proxy_login(self) -> None:
        """Authenticate to the UniFi OS Console and store the CSRF token.

        The session's cookie jar automatically stores the auth cookie.
        """
        url = f"https://{self.host}:{self.port}/api/auth/login"
        payload = {"username": self.username, "password": self.password}

        async with self._proxy_session.post(url, json=payload, ssl=self._ssl_context) as resp:
            if resp.status != 200:
                body = ""
                try:
                    body = await resp.text()
                except Exception:
                    pass
                raise UniFiAuthError(f"Proxy login failed: HTTP {resp.status}{(' — ' + body[:200]) if body else ''}")
            self._csrf_token = resp.headers.get("x-updated-csrf-token", resp.headers.get("x-csrf-token", ""))
            logger.debug("[access-cm] Proxy login successful, CSRF token obtained.")

    # ------------------------------------------------------------------
    # Proxy request helper
    # ------------------------------------------------------------------

    async def proxy_request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Make a request via the UniFi OS proxy path.

        Parameters
        ----------
        method:
            HTTP method (GET, POST, PUT, DELETE).
        path:
            API path relative to ``/proxy/access/api/v2/``.
        **kwargs:
            Extra keyword arguments forwarded to ``aiohttp.ClientSession.request``
            (e.g. ``json=``, ``params=``).

        Returns
        -------
        dict
            Parsed JSON response body.

        Raises
        ------
        UniFiConnectionError
            If the proxy session is not available.
        """
        if not self._proxy_available or self._proxy_session is None:
            raise UniFiConnectionError("Proxy session is not available. Call initialize() first.")

        url = f"https://{self.host}:{self.port}/proxy/access/api/v2/{path.lstrip('/')}"
        headers = {"X-CSRF-Token": self._csrf_token}

        async with self._proxy_session.request(method, url, headers=headers, ssl=self._ssl_context, **kwargs) as resp:
            if resp.status == 401:
                # Session expired — re-login under lock to prevent concurrent re-auths
                async with self._auth_lock:
                    # Double-check: another coroutine may have already re-authenticated
                    logger.info("[access-cm] Proxy session expired, re-authenticating...")
                    await self._proxy_login()

                # Retry the original request with the refreshed CSRF token
                retry_headers = {"X-CSRF-Token": self._csrf_token}
                async with self._proxy_session.request(
                    method, url, headers=retry_headers, ssl=self._ssl_context, **kwargs
                ) as retry_resp:
                    if retry_resp.status != 200:
                        raise UniFiConnectionError(
                            f"Proxy request failed after re-auth: HTTP {retry_resp.status} {method} {path}"
                        )
                    return await retry_resp.json()

            if resp.status != 200:
                body = ""
                try:
                    body = await resp.text()
                except Exception:
                    pass
                raise UniFiConnectionError(
                    f"Proxy request failed: HTTP {resp.status} {method} {path}{(' — ' + body[:200]) if body else ''}"
                )
            return await resp.json()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def api_client(self) -> Any | None:
        """Return the :class:`UnifiAccessApiClient` instance, or ``None``."""
        return self._api_client

    @property
    def has_api_client(self) -> bool:
        """Return ``True`` if the API client path is available."""
        return self._api_client_available and self._api_client is not None

    @property
    def has_proxy(self) -> bool:
        """Return ``True`` if the proxy session path is available."""
        return self._proxy_available and self._proxy_session is not None

    @property
    def is_connected(self) -> bool:
        """Return ``True`` if at least one auth path is initialised."""
        return self._initialized and (self._api_client_available or self._proxy_available)

    # ------------------------------------------------------------------
    # Websocket
    # ------------------------------------------------------------------

    def start_websocket(self, handlers: Dict[str, Any], **kwargs: Any) -> Any:
        """Start a websocket connection via the API client.

        Delegates to :meth:`UnifiAccessApiClient.start_websocket`.

        Raises :class:`UniFiConnectionError` if no API client is available.
        """
        if not self.has_api_client:
            raise UniFiConnectionError("Cannot start websocket — API client not available.")
        return self._api_client.start_websocket(handlers, **kwargs)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Gracefully shut down both sessions."""
        if self._api_client is not None:
            try:
                await self._api_client.close()
            except Exception:
                logger.debug("[access-cm] Error closing API client", exc_info=True)
            self._api_client = None

        if self._api_session is not None and not self._api_session.closed:
            try:
                await self._api_session.close()
            except Exception:
                logger.debug("[access-cm] Error closing API session", exc_info=True)
            self._api_session = None

        if self._proxy_session is not None and not self._proxy_session.closed:
            try:
                await self._proxy_session.close()
            except Exception:
                logger.debug("[access-cm] Error closing proxy session", exc_info=True)
            self._proxy_session = None

        self._api_client_available = False
        self._proxy_available = False
        self._initialized = False
        logger.info("[access-cm] Connection closed.")
