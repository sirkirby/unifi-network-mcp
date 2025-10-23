# Data Model: UniFi OS Path Detection

**Feature**: UniFi API Path Detection and Adaptation
**Branch**: 001-unifi-os-detection
**Date**: 2025-10-23

## Overview

This document defines the data structures and state management for UniFi OS path detection and interception. The feature uses minimal state, primarily cached detection results and configuration settings.

---

## 1. Detection Result

### 1.1 PathRequirement Enum

```python
from enum import Enum, auto

class PathRequirement(str, Enum):
    """Enumeration of UniFi controller path requirements."""

    PROXY_REQUIRED = "proxy"      # UniFi OS: /proxy/network prefix required
    DIRECT_PATH = "direct"         # Standard: /api paths without prefix
    AUTO_DETECT = "auto"           # Automatic detection (configuration only)
```

**Purpose**: Type-safe representation of path requirement states

**Usage**:
- Configuration: Users set `UNIFI_CONTROLLER_TYPE=proxy|direct|auto`
- Detection: Detection function returns `True` (proxy) or `False` (direct)
- Runtime: `_unifi_os_override` stores `bool` (not enum) for direct compatibility with aiounifi

**Validation Rules**:
- Must be one of: `"proxy"`, `"direct"`, `"auto"`
- Invalid values trigger warning and fall back to `"auto"`

### 1.2 DetectionResult (Optional Enhanced Model)

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class DetectionResult:
    """
    Cached detection result with diagnostic information.
    Optional: Use for enhanced diagnostics mode.
    """

    # Core result
    requires_proxy: bool                    # True = UniFi OS, False = Standard
    detection_method: str                   # "probe" | "manual" | "fallback"
    timestamp: datetime                     # When detection occurred

    # Diagnostic details
    proxy_probe_status: Optional[int]       # HTTP status from /proxy/network/api/self/sites
    direct_probe_status: Optional[int]      # HTTP status from /api/self/sites
    detection_duration_ms: float            # Time taken for detection
    retry_count: int = 0                    # Number of retries before success

    # Configuration
    manual_override: bool = False           # True if user set UNIFI_CONTROLLER_TYPE
    fallback_used: bool = False            # True if aiounifi's check_unifi_os() was used

    def __str__(self) -> str:
        """Human-readable detection summary."""
        mode = "UniFi OS (proxy)" if self.requires_proxy else "Standard (direct)"
        method = f"via {self.detection_method}"
        return f"{mode} {method} in {self.detection_duration_ms:.0f}ms"
```

**Purpose**: Enhanced diagnostics and debugging information

**Usage**: Optional - only instantiate when diagnostics mode enabled

**Validation Rules**:
- `detection_duration_ms` must be >= 0
- `retry_count` must be >= 0
- `timestamp` must not be in the future

---

## 2. Configuration Model

### 2.1 Connection Manager State

```python
class ConnectionManager:
    """Connection manager with path detection state."""

    def __init__(self, ...):
        # Existing attributes
        self.controller: Optional[Controller] = None
        self._aiohttp_session: Optional[aiohttp.ClientSession] = None

        # NEW: Path detection state
        self._unifi_os_override: Optional[bool] = None
        """
        Override for is_unifi_os flag:
        - None: Use aiounifi's detection (no override)
        - True: Force UniFi OS paths (/proxy/network)
        - False: Force standard paths (/api)
        """

        # Optional: Enhanced diagnostics
        self._detection_result: Optional[DetectionResult] = None
        """Cached detection result with diagnostics."""
```

**State Lifecycle**:
1. **Initialization**: `_unifi_os_override = None`
2. **Detection**: Set to `True` or `False` based on probes or config
3. **Runtime**: Applied in `request()` wrapper, never changed
4. **Cleanup**: No explicit cleanup (session-lifetime cache)

### 2.2 Configuration Schema

```python
# In src/config/config.yaml
unifi:
  # Existing configuration
  host: "192.168.1.1"
  port: 8443
  username: "admin"
  password: "password"
  site: "default"
  verify_ssl: false

  # NEW: Controller type configuration
  controller_type: "auto"  # auto | proxy | direct
  """
  UniFi controller path requirement:
  - auto: Automatically detect (default)
  - proxy: Force UniFi OS paths (/proxy/network prefix)
  - direct: Force standard paths (/api)
  """

  # NEW: Detection configuration
  detection:
    enabled: true          # Enable proactive detection
    timeout_seconds: 5     # Timeout for detection probes
    retry_attempts: 3      # Number of retry attempts
    retry_backoff: true    # Use exponential backoff
```

**Environment Variable Mapping**:

| Config Key | Environment Variable | Default | Type |
|------------|---------------------|---------|------|
| `controller_type` | `UNIFI_CONTROLLER_TYPE` | `"auto"` | str (enum) |
| `detection.enabled` | `UNIFI_DETECTION_ENABLED` | `true` | bool |
| `detection.timeout_seconds` | `UNIFI_DETECTION_TIMEOUT` | `5` | int |
| `detection.retry_attempts` | `UNIFI_DETECTION_RETRIES` | `3` | int |

---

## 3. Request State

### 3.1 Per-Request Context

```python
# No persistent per-request state required
# Path interception uses cached _unifi_os_override
```

**Rationale**: Detection result is cached at connection initialization. No per-request state needed.

### 3.2 Temporary Override Pattern

```python
# In ConnectionManager.request()
async def request(self, api_request, return_raw=False):
    # Save original flag
    original_is_unifi_os = None

    # Apply override if set
    if self._unifi_os_override is not None:
        original_is_unifi_os = self.controller.connectivity.is_unifi_os
        self.controller.connectivity.is_unifi_os = self._unifi_os_override

    try:
        # Make request with override applied
        response = await self.controller.request(api_request)
        return response
    finally:
        # Always restore original flag
        if original_is_unifi_os is not None:
            self.controller.connectivity.is_unifi_os = original_is_unifi_os
```

**State Flow**:
1. **Save**: Store original `is_unifi_os` value
2. **Override**: Set to detection result
3. **Request**: aiounifi uses overridden value in `full_path()`
4. **Restore**: Always restore original in `finally` block

---

## 4. Error State

### 4.1 Detection Failure State

```python
class DetectionFailure(Exception):
    """Raised when path detection fails completely."""

    def __init__(
        self,
        message: str,
        proxy_error: Optional[str] = None,
        direct_error: Optional[str] = None,
        retry_count: int = 0
    ):
        super().__init__(message)
        self.proxy_error = proxy_error
        self.direct_error = direct_error
        self.retry_count = retry_count

    def troubleshooting_guide(self) -> str:
        """Generate user-friendly troubleshooting message."""
        return f"""
UniFi controller path detection failed after {self.retry_count} attempts.

Probe Results:
- UniFi OS path (/proxy/network/api/self/sites): {self.proxy_error or 'Failed'}
- Standard path (/api/self/sites): {self.direct_error or 'Failed'}

Troubleshooting Steps:
1. Verify network connectivity to controller
2. Check controller is accessible on configured port
3. Manually set controller type:
   - For UniFi OS (Cloud Gateway, UDM-Pro): UNIFI_CONTROLLER_TYPE=proxy
   - For standalone controllers: UNIFI_CONTROLLER_TYPE=direct

For more help, see: https://github.com/sirkirby/unifi-network-mcp/issues/19
"""
```

### 4.2 Validation Error State

```python
class ConfigurationError(Exception):
    """Raised when controller type configuration is invalid."""

    VALID_VALUES = {"auto", "proxy", "direct"}

    def __init__(self, invalid_value: str):
        self.invalid_value = invalid_value
        super().__init__(
            f"Invalid UNIFI_CONTROLLER_TYPE: '{invalid_value}'. "
            f"Must be one of: {', '.join(self.VALID_VALUES)}"
        )
```

---

## 5. State Transitions

### 5.1 Detection State Machine

```
┌─────────────┐
│ UNDETECTED  │ (initial state: _unifi_os_override = None)
└──────┬──────┘
       │
       ├─ Manual Override (env var)
       │  ├─> PROXY_FORCED (_unifi_os_override = True)
       │  └─> DIRECT_FORCED (_unifi_os_override = False)
       │
       ├─ Auto-Detection Success
       │  ├─> PROXY_DETECTED (_unifi_os_override = True)
       │  └─> DIRECT_DETECTED (_unifi_os_override = False)
       │
       └─ Auto-Detection Failure
          └─> FALLBACK (uses aiounifi's check_unifi_os)
```

### 5.2 Request Override State Machine

```
┌─────────────────┐
│ Request Starts  │
└────────┬────────┘
         │
         ├─ No Override Set (_unifi_os_override = None)
         │  └─> Pass through to aiounifi (no change)
         │
         └─ Override Set (_unifi_os_override = True/False)
            ├─> Save original is_unifi_os
            ├─> Apply override
            ├─> Make request
            └─> Restore original in finally block
```

**Invariants**:
- `_unifi_os_override` never changes after initialization
- Original `is_unifi_os` always restored after request
- Detection never re-runs during session lifetime

---

## 6. Persistence

### 6.1 No Database Persistence

**Decision**: Detection results are NOT persisted to disk

**Rationale**:
- Per FR-005: Path requirement remains valid for connection session only
- Controllers may change firmware/configuration between sessions
- Stale cached results could cause connection failures
- Re-detection overhead (~300ms) is acceptable on restart

### 6.2 Session-Lifetime Cache

```python
# Detection result cached in memory
self._unifi_os_override: Optional[bool] = None
self._detection_result: Optional[DetectionResult] = None

# Cache lifetime: Until ConnectionManager instance destroyed
# No TTL, no expiration, no refresh
```

**Cache Invalidation**: Only on service restart or ConnectionManager re-initialization

---

## 7. Thread Safety

### 7.1 Concurrency Considerations

**asyncio Context**:
- Single event loop: No thread concurrency
- Async tasks: Detection runs before controller creation (serial)
- Request override: Uses `finally` block for safe restoration

**Safety Guarantees**:
- ✅ Detection runs once during initialization (serial)
- ✅ `_unifi_os_override` set once, never modified (read-only after init)
- ✅ Request override uses try/finally for safe restoration
- ✅ No shared mutable state between requests

### 7.2 Race Condition Analysis

**Potential Race**: Multiple requests in flight simultaneously

**Mitigation**: Each request saves/restores `is_unifi_os` independently

```python
# Request A
original_A = self.controller.connectivity.is_unifi_os  # True
self.controller.connectivity.is_unifi_os = False
# ... Request A in progress ...

# Request B (concurrent)
original_B = self.controller.connectivity.is_unifi_os  # False (!)
self.controller.connectivity.is_unifi_os = False
# ... Request B in progress ...

# Request A completes
self.controller.connectivity.is_unifi_os = original_A  # Restore to True

# Request B completes
self.controller.connectivity.is_unifi_os = original_B  # Restore to False (wrong!)
```

**Resolution**: This is acceptable because:
1. All requests use same override value (`_unifi_os_override`)
2. Final state always converges to override value
3. aiounifi constructs path before making request (no cross-request state)
4. Worth noting for future async locking if needed

---

## 8. Validation Rules

### 8.1 Detection Input Validation

```python
def validate_detection_config(config: dict) -> None:
    """Validate detection configuration."""
    timeout = config.get("detection", {}).get("timeout_seconds", 5)
    if not 1 <= timeout <= 30:
        raise ConfigurationError(f"Detection timeout must be 1-30 seconds, got {timeout}")

    retry_attempts = config.get("detection", {}).get("retry_attempts", 3)
    if not 1 <= retry_attempts <= 10:
        raise ConfigurationError(f"Retry attempts must be 1-10, got {retry_attempts}")

    controller_type = config.get("controller_type", "auto").lower()
    if controller_type not in PathRequirement.__members__.values():
        raise ConfigurationError(f"Invalid controller_type: {controller_type}")
```

### 8.2 Detection Result Validation

```python
def validate_detection_result(result: bool, proxy_status: int, direct_status: int) -> bool:
    """Validate that detection result matches probe responses."""
    if result is True:
        # UniFi OS detected: proxy endpoint should return 200
        assert proxy_status == 200, "Proxy endpoint should return 200 for UniFi OS"
    elif result is False:
        # Standard detected: direct endpoint should return 200
        assert direct_status == 200, "Direct endpoint should return 200 for standard"
    return True
```

---

## 9. Relationship Diagram

```
┌─────────────────────────┐
│ Configuration           │
│ (config.yaml / env var) │
└────────────┬────────────┘
             │
             ├─> controller_type: "auto" | "proxy" | "direct"
             ├─> detection.enabled: bool
             └─> detection.timeout_seconds: int
                          │
                          v
             ┌────────────────────────┐
             │ ConnectionManager      │
             │ .__init__()            │
             └────────┬───────────────┘
                      │
                      ├─> _unifi_os_override: Optional[bool]
                      └─> _detection_result: Optional[DetectionResult]
                                   │
                                   v
                      ┌────────────────────────┐
                      │ detect_unifi_os_       │
                      │   proactively()        │
                      └────────┬───────────────┘
                               │
                               ├─ Success -> bool (True/False)
                               └─ Failure -> None (fallback)
                                            │
                                            v
                               ┌────────────────────────┐
                               │ ConnectionManager      │
                               │ .request()             │
                               └────────┬───────────────┘
                                        │
                                        ├─> Save original is_unifi_os
                                        ├─> Apply override
                                        ├─> Make request
                                        └─> Restore original
                                                     │
                                                     v
                                        ┌────────────────────────┐
                                        │ aiounifi.Controller    │
                                        │ .request()             │
                                        └────────┬───────────────┘
                                                 │
                                                 v
                                        ┌────────────────────────┐
                                        │ ApiRequest             │
                                        │ .full_path()           │
                                        └────────┬───────────────┘
                                                 │
                   Uses is_unifi_os flag ─────────┘
                   to determine path prefix
```

---

## 10. Example Instances

### 10.1 UniFi OS Detection (Success)

```python
detection_result = DetectionResult(
    requires_proxy=True,
    detection_method="probe",
    timestamp=datetime(2025, 10, 23, 14, 30, 0),
    proxy_probe_status=200,
    direct_probe_status=404,
    detection_duration_ms=250.5,
    retry_count=0,
    manual_override=False,
    fallback_used=False
)

# Stored in ConnectionManager
conn_mgr._unifi_os_override = True  # requires_proxy
conn_mgr._detection_result = detection_result  # for diagnostics
```

### 10.2 Standard Controller Detection (Success)

```python
detection_result = DetectionResult(
    requires_proxy=False,
    detection_method="probe",
    timestamp=datetime(2025, 10, 23, 14, 30, 0),
    proxy_probe_status=404,
    direct_probe_status=200,
    detection_duration_ms=180.2,
    retry_count=0,
    manual_override=False,
    fallback_used=False
)

conn_mgr._unifi_os_override = False
conn_mgr._detection_result = detection_result
```

### 10.3 Manual Override

```python
# User set UNIFI_CONTROLLER_TYPE=proxy
detection_result = DetectionResult(
    requires_proxy=True,
    detection_method="manual",
    timestamp=datetime(2025, 10, 23, 14, 30, 0),
    proxy_probe_status=None,  # Skipped probes
    direct_probe_status=None,
    detection_duration_ms=0.0,
    retry_count=0,
    manual_override=True,
    fallback_used=False
)

conn_mgr._unifi_os_override = True
conn_mgr._detection_result = detection_result
```

### 10.4 Detection Failure (Fallback)

```python
detection_result = DetectionResult(
    requires_proxy=False,  # Fallback to aiounifi's detection
    detection_method="fallback",
    timestamp=datetime(2025, 10, 23, 14, 30, 0),
    proxy_probe_status=None,  # Both failed
    direct_probe_status=None,
    detection_duration_ms=5000.0,  # Timeout
    retry_count=3,
    manual_override=False,
    fallback_used=True
)

conn_mgr._unifi_os_override = None  # Use aiounifi's detection
conn_mgr._detection_result = detection_result
```

---

## 11. Migration Notes

### 11.1 Existing Data

**No existing data**: This is a new feature, no migration required

### 11.2 Backward Compatibility

**100% Compatible**: Feature is transparent to existing tools

- Existing tools don't need modification
- If detection disabled, behaves identically to current implementation
- Manual override allows users to force old behavior

### 11.3 Future Enhancements

Possible enhancements without breaking changes:

1. **Persistent cache** (optional): Store detection result in `.cache/unifi_detection.json`
2. **Multi-controller support**: Cache detection per controller host
3. **Detection history**: Log detection results over time
4. **A/B testing**: Validate detection by trying both paths

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Status**: Design Complete
