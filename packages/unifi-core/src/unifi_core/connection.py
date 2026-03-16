"""Base async connection primitives for UniFi controllers."""

from dataclasses import dataclass

import aiohttp  # noqa: F401


@dataclass
class ConnectionConfig:
    host: str
    port: int = 443
    verify_ssl: bool = False
    timeout: float = 30.0

    @property
    def url_base(self) -> str:
        return f"https://{self.host}:{self.port}"

    @property
    def ssl_context(self):
        if self.verify_ssl:
            return None
        return False
