"""UniFi controller connectivity: auth, detection, retry, exceptions."""

from unifi_core.auth import AuthMethod, LocalAuthProvider, UniFiAuth
from unifi_core.connection import ConnectionConfig
from unifi_core.detection import ControllerType, detect_controller_type_by_api_probe, detect_controller_type_pre_login
from unifi_core.exceptions import (
    UniFiAuthError,
    UniFiConnectionError,
    UniFiError,
    UniFiPermissionError,
    UniFiRateLimitError,
)
from unifi_core.retry import RetryPolicy, retry_with_backoff

__all__ = [
    # auth
    "AuthMethod",
    "LocalAuthProvider",
    "UniFiAuth",
    # connection
    "ConnectionConfig",
    # detection
    "ControllerType",
    "detect_controller_type_by_api_probe",
    "detect_controller_type_pre_login",
    # exceptions
    "UniFiAuthError",
    "UniFiConnectionError",
    "UniFiError",
    "UniFiPermissionError",
    "UniFiRateLimitError",
    # retry
    "RetryPolicy",
    "retry_with_backoff",
]
