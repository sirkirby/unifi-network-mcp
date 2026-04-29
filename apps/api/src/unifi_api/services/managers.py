"""Per-controller manager factory.

Manual async-aware cache (NOT @lru_cache — async values + per-call session
arg make lru_cache the wrong tool). Per-controller asyncio.Lock around
construction prevents concurrent-cache-miss races.

Public surface:
- ManagerFactory(sessionmaker, cipher)
- get_connection_manager(session, controller_id, product) -> ConnectionManager
- invalidate_controller(controller_id)
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from unifi_api.db.crypto import ColumnCipher
from unifi_api.db.models import Controller


class UnknownProduct(Exception):
    """Raised when a requested product is not supported by the controller."""


def _split_base_url(base_url: str) -> tuple[str, int]:
    """Parse a base URL into (host, port). Defaults to 443 when port absent."""
    parsed = urlparse(base_url)
    host = parsed.hostname or base_url
    port = parsed.port or 443
    return host, port


class ManagerFactory:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        cipher: ColumnCipher,
    ) -> None:
        self._sm = sessionmaker
        self._cipher = cipher
        self._connection_cache: dict[tuple[str, str], Any] = {}
        self._domain_cache: dict[tuple[str, str, str], Any] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def get_connection_manager(
        self, session: AsyncSession, controller_id: str, product: str
    ) -> Any:
        key = (controller_id, product)
        cm = self._connection_cache.get(key)
        if cm is not None:
            return cm
        async with self._locks[controller_id]:
            cm = self._connection_cache.get(key)
            if cm is not None:
                return cm
            cm = await self._construct_connection_manager(session, controller_id, product)
            self._connection_cache[key] = cm
            return cm

    async def _construct_connection_manager(
        self, session: AsyncSession, controller_id: str, product: str
    ) -> Any:
        controller = await session.get(Controller, controller_id)
        if controller is None:
            raise ValueError(f"controller {controller_id} not found")
        products = [p for p in controller.product_kinds.split(",") if p]
        if product not in products:
            raise UnknownProduct(
                f"controller {controller_id} does not support product '{product}'"
            )
        creds = json.loads(self._cipher.decrypt(controller.credentials_blob))
        host, port = _split_base_url(controller.base_url)

        # ConnectionManager constructors all take (host, username, password,
        # port, verify_ssl, ...). They differ in optional kwargs:
        #   - network: site, cache_timeout, max_retries, retry_delay
        #   - protect: site, api_key
        #   - access:  api_key, api_port
        # Connections are NOT established at construction time — initialize()
        # is called lazily by callers, so this is safe to call eagerly here.
        if product == "network":
            from unifi_core.network.managers.connection_manager import (
                ConnectionManager as NetCM,
            )

            return NetCM(
                host=host,
                username=creds["username"],
                password=creds["password"],
                port=port,
                verify_ssl=controller.verify_tls,
            )
        if product == "protect":
            from unifi_core.protect.managers.connection_manager import (
                ConnectionManager as ProtectCM,
            )

            return ProtectCM(
                host=host,
                username=creds["username"],
                password=creds["password"],
                port=port,
                verify_ssl=controller.verify_tls,
                api_key=creds.get("api_token"),
            )
        if product == "access":
            from unifi_core.access.managers.connection_manager import (
                ConnectionManager as AccessCM,
            )

            return AccessCM(
                host=host,
                username=creds["username"],
                password=creds["password"],
                port=port,
                verify_ssl=controller.verify_tls,
                api_key=creds.get("api_token"),
            )
        raise UnknownProduct(f"unknown product '{product}'")

    async def invalidate_controller(self, controller_id: str) -> None:
        """Drop all cached managers for a controller and dispose their sessions."""
        keys_conn = [k for k in self._connection_cache if k[0] == controller_id]
        for k in keys_conn:
            cm = self._connection_cache.pop(k)
            close = getattr(cm, "close", None) or getattr(cm, "aclose", None)
            if close is not None:
                try:
                    result = close()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    pass
        keys_domain = [k for k in self._domain_cache if k[0] == controller_id]
        for k in keys_domain:
            self._domain_cache.pop(k, None)
