"""Shared exception hierarchy for UniFi MCP servers."""


class UniFiError(Exception):
    """Base exception for all UniFi errors."""


class UniFiAuthError(UniFiError):
    """Authentication failed."""


class UniFiConnectionError(UniFiError):
    """Connection to controller failed."""


class UniFiRateLimitError(UniFiError):
    """Rate limit exceeded."""


class UniFiPermissionError(UniFiError):
    """Insufficient permissions for operation."""
