"""Dual authentication strategy for UniFi controllers."""

import enum
import logging
from typing import Protocol

import aiohttp

from unifi_core.exceptions import UniFiAuthError

logger = logging.getLogger(__name__)


class AuthMethod(enum.Enum):
    LOCAL_ONLY = "local_only"
    API_KEY_ONLY = "api_key_only"
    EITHER = "either"

    @classmethod
    def from_string(cls, value: str | None) -> "AuthMethod":
        if value is None:
            return cls.LOCAL_ONLY
        try:
            return cls(value)
        except ValueError:
            logger.warning("[auth] Unknown auth method '%s', defaulting to local_only", value)
            return cls.LOCAL_ONLY


class LocalAuthProvider(Protocol):
    """Contract that each app fulfills for local auth."""

    async def get_session(self) -> aiohttp.ClientSession: ...


class UniFiAuth:
    """Dual auth: API key and/or local auth provider."""

    def __init__(self, api_key: str | None = None, local_provider: LocalAuthProvider | None = None):
        self._api_key = api_key
        self._local_provider = local_provider

    @property
    def has_api_key(self) -> bool:
        return self._api_key is not None and self._api_key != ""

    @property
    def has_local(self) -> bool:
        return self._local_provider is not None

    def set_local_provider(self, provider: LocalAuthProvider) -> None:
        self._local_provider = provider

    async def get_api_key_session(self) -> aiohttp.ClientSession:
        if not self.has_api_key:
            raise UniFiAuthError("API key authentication not configured. Set UNIFI_API_KEY environment variable.")
        return aiohttp.ClientSession(headers={"X-API-Key": self._api_key})

    async def get_local_session(self) -> aiohttp.ClientSession:
        if not self.has_local:
            raise UniFiAuthError("Local authentication not configured. Set UNIFI_USERNAME and UNIFI_PASSWORD.")
        return await self._local_provider.get_session()

    async def get_session(self, method: AuthMethod) -> aiohttp.ClientSession:
        if method == AuthMethod.API_KEY_ONLY:
            return await self.get_api_key_session()
        elif method == AuthMethod.LOCAL_ONLY:
            return await self.get_local_session()
        elif method == AuthMethod.EITHER:
            if self.has_api_key:
                return await self.get_api_key_session()
            return await self.get_local_session()
        raise UniFiAuthError(f"Unknown auth method: {method}")
