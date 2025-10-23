# Detection API Contract

**Feature**: UniFi OS Path Detection
**Branch**: 001-unifi-os-detection
**Date**: 2025-10-23

## Overview

This document defines the internal API contract for the UniFi OS path detection system. Since this is an infrastructure feature, there are no external MCP tools exposed. The contract defines the internal methods added to `ConnectionManager`.

---

## 1. Detection Function

### `detect_unifi_os_proactively()`

**Purpose**: Proactively detect which API path structure the controller requires by testing both variants.

**Signature**:

```python
async def detect_unifi_os_proactively(
    session: aiohttp.ClientSession,
    base_url: str,
    timeout: int = 5,
    retry_attempts: int = 3
) -> Optional[bool]:
    """
    Detect if controller is UniFi OS by testing endpoint variants.

    Args:
        session: Active aiohttp.ClientSession for making HTTP requests
        base_url: Base URL of controller (e.g., 'https://192.168.1.1:443')
        timeout: Timeout in seconds for each probe attempt (default: 5)
        retry_attempts: Number of retry attempts on failure (default: 3)

    Returns:
        True: UniFi OS detected (requires /proxy/network prefix)
        False: Standard controller detected (uses /api paths directly)
        None: Detection failed, caller should fall back to aiounifi's check_unifi_os()

    Raises:
        aiohttp.ClientError: Network error during detection (caught internally, returns None)
        asyncio.TimeoutError: Detection timeout (caught internally, returns None)

    Examples:
        # Successful UniFi OS detection
        >>> result = await detect_unifi_os_proactively(session, "https://192.168.1.1:443")
        >>> assert result is True

        # Successful standard controller detection
        >>> result = await detect_unifi_os_proactively(session, "https://192.168.1.1:8443")
        >>> assert result is False

        # Detection failure (both endpoints return errors)
        >>> result = await detect_unifi_os_proactively(session, "https://offline:443")
        >>> assert result is None
    """
```

**Behavior**:

1. **Try UniFi OS endpoint first** (newer controllers more common):
   - GET `{base_url}/proxy/network/api/self/sites`
   - If status 200 AND response contains `{"data": [...]}`, return `True`

2. **Try standard endpoint**:
   - GET `{base_url}/api/self/sites`
   - If status 200 AND response contains `{"data": [...]}`, return `True`

3. **Handle failures**:
   - If both probes fail (network error, timeout, 404), return `None`
   - Log diagnostic information for each failed probe
   - Use exponential backoff on retries: 1s, 2s, 4s

**Performance Contract**:
- Completes within `timeout * retry_attempts` seconds worst case
- Typical success: 100-300ms
- Typical failure: ~5 seconds (1 timeout)

**Error Handling**:
- All exceptions caught internally
- Never raises exceptions to caller
- Returns `None` on any error for safe fallback

---

## 2. Configuration Loading

### `load_controller_type_config()`

**Purpose**: Load and validate controller type configuration from environment variables and config files.

**Signature**:

```python
def load_controller_type_config() -> Optional[bool]:
    """
    Load controller type configuration from environment or config file.

    Configuration Precedence (highest to lowest):
    1. Environment variable UNIFI_CONTROLLER_TYPE
    2. .env file
    3. config.yaml controller_type setting
    4. Auto-detection (default)

    Returns:
        True: Force UniFi OS paths (UNIFI_CONTROLLER_TYPE=proxy)
        False: Force standard paths (UNIFI_CONTROLLER_TYPE=direct)
        None: Use auto-detection (UNIFI_CONTROLLER_TYPE=auto or not set)

    Raises:
        ConfigurationError: Invalid controller_type value

    Examples:
        # Manual override to proxy
        >>> os.environ["UNIFI_CONTROLLER_TYPE"] = "proxy"
        >>> result = load_controller_type_config()
        >>> assert result is True

        # Manual override to direct
        >>> os.environ["UNIFI_CONTROLLER_TYPE"] = "direct"
        >>> result = load_controller_type_config()
        >>> assert result is False

        # Auto-detection (default)
        >>> os.environ.pop("UNIFI_CONTROLLER_TYPE", None)
        >>> result = load_controller_type_config()
        >>> assert result is None

        # Invalid value
        >>> os.environ["UNIFI_CONTROLLER_TYPE"] = "invalid"
        >>> load_controller_type_config()  # Raises ConfigurationError
    """
```

**Valid Values**:
- `"auto"` or unset → `None` (auto-detect)
- `"proxy"` → `True` (force UniFi OS)
- `"direct"` → `False` (force standard)

**Case Insensitive**: `"PROXY"`, `"Proxy"`, `"proxy"` all accepted

**Invalid Values**: Raise `ConfigurationError` with helpful message

---

## 3. ConnectionManager Integration

### Modified `initialize()` Method

**Contract**:

```python
class ConnectionManager:
    async def initialize(self) -> bool:
        """
        Initialize controller connection with path detection.

        Behavior Changes:
        1. Load controller type configuration
        2. If auto-detection enabled, run proactive detection
        3. Cache detection result in _unifi_os_override
        4. Continue with normal Controller creation

        Returns:
            bool: True if connection initialized successfully

        Side Effects:
            - Sets self._unifi_os_override to detection result
            - Logs detection outcome
            - May raise ConnectionError if detection fails and no fallback
        """
```

**Execution Flow**:

```
1. Create aiohttp.ClientSession
2. Load controller type config (manual override or auto)
3. IF auto-detection:
   a. Run detect_unifi_os_proactively()
   b. Cache result in _unifi_os_override
   c. Log detection outcome
4. Create Controller (existing code)
5. Login to controller (existing code)
6. Return success
```

**Error Handling**:
- Detection failure (returns `None`) → Log warning, use aiounifi's check_unifi_os()
- Configuration error → Raise `ConfigurationError` with troubleshooting guide
- Connection error → Raise `ConnectionError` with detection diagnostics

### Modified `request()` Method

**Contract**:

```python
class ConnectionManager:
    async def request(
        self,
        api_request: ApiRequest | ApiRequestV2,
        return_raw: bool = False
    ) -> Any:
        """
        Make API request with optional path interception.

        Behavior Changes:
        1. If _unifi_os_override is set, temporarily override is_unifi_os
        2. Make request using aiounifi Controller
        3. Always restore original is_unifi_os in finally block

        Args:
            api_request: ApiRequest or ApiRequestV2 instance
            return_raw: If True, return raw response without extracting data

        Returns:
            Any: Response data (or full response if return_raw=True)

        Raises:
            ConnectionError: If controller not connected

        Side Effects:
            - Temporarily modifies controller.connectivity.is_unifi_os
            - Always restores original value in finally block
        """
```

**Override Behavior**:

| `_unifi_os_override` | Action |
|---------------------|--------|
| `None` | No override, use aiounifi's is_unifi_os |
| `True` | Force is_unifi_os=True (UniFi OS paths) |
| `False` | Force is_unifi_os=False (standard paths) |

**Concurrency Safety**:
- Uses try/finally to ensure restoration
- Safe for concurrent requests (each saves/restores independently)
- No locking required (asyncio single-threaded)

---

## 4. Detection Endpoint Contract

### Probe Endpoint

**Endpoint**: `/api/self/sites` (or `/proxy/network/api/self/sites`)

**Method**: GET

**Authentication**: Not required for detection (probes before login)

**Expected Response** (Success):

```json
{
  "meta": {
    "rc": "ok"
  },
  "data": [
    {
      "_id": "5f1234abcd5678ef90123456",
      "name": "default",
      "desc": "Default Site"
    }
  ]
}
```

**Success Criteria**:
- HTTP Status: 200
- Content-Type: application/json
- Response body contains `"data"` key
- Data is array (may be empty)

**Failure Indicators**:
- HTTP Status: 404 (endpoint not available on this path)
- HTTP Status: 401/403 (authentication required, indicates wrong path)
- HTTP Status: 500+ (server error, treat as detection failure)
- Timeout (controller not reachable)
- Connection error (network issue)

**Retry Policy**:
- Retry on: Timeout, connection error, 5xx errors
- Don't retry on: 404, 401, 403 (conclusive negative result)
- Exponential backoff: 1s, 2s, 4s

---

## 5. Logging Contract

### Detection Logging

**Log Levels**:

```python
# Info: Successful detection
logger.info(
    f"Detected controller type: {'UniFi OS' if result else 'Standard'} "
    f"in {duration_ms:.0f}ms"
)

# Debug: Probe attempts
logger.debug(
    f"Probing UniFi OS endpoint: {base_url}/proxy/network/api/self/sites"
)
logger.debug(
    f"UniFi OS probe: status={status}, response_time={time_ms}ms"
)

# Warning: Detection failure
logger.warning(
    f"Path detection failed after {retry_attempts} attempts, "
    f"falling back to aiounifi's check_unifi_os()"
)

# Error: Configuration error
logger.error(
    f"Invalid UNIFI_CONTROLLER_TYPE: '{value}'. "
    f"Must be one of: auto, proxy, direct"
)
```

**Diagnostics Mode** (when enabled):

```python
# Detailed probe results
logger.debug(
    f"Detection probes completed:\n"
    f"  UniFi OS (/proxy/network): status={proxy_status}, time={proxy_time}ms\n"
    f"  Standard (/api): status={direct_status}, time={direct_time}ms\n"
    f"  Decision: {'UniFi OS' if result else 'Standard'}"
)
```

---

## 6. Metrics Contract

### Detection Metrics (Optional)

**Metrics to Track** (if metrics system available):

```python
# Detection success/failure
metrics.increment("unifi.detection.success", tags=["type:proxy"])
metrics.increment("unifi.detection.success", tags=["type:direct"])
metrics.increment("unifi.detection.failure")

# Detection duration
metrics.histogram("unifi.detection.duration_ms", duration_ms)

# Manual override usage
metrics.increment("unifi.config.manual_override", tags=["value:proxy"])
metrics.increment("unifi.config.manual_override", tags=["value:direct"])

# Fallback usage
metrics.increment("unifi.detection.fallback")
```

---

## 7. Error Contract

### Exception Types

```python
class DetectionError(Exception):
    """Base exception for detection errors."""
    pass

class DetectionTimeoutError(DetectionError):
    """Detection exceeded timeout."""
    pass

class ConfigurationError(Exception):
    """Invalid configuration value."""
    pass

class ConnectionError(Exception):
    """Connection to controller failed."""
    pass
```

### Error Responses

**Detection Failure**:

```python
# Detection returns None (fallback)
result = await detect_unifi_os_proactively(...)
if result is None:
    logger.warning("Detection failed, using aiounifi's check_unifi_os()")
    # Continue with fallback
```

**Configuration Error**:

```python
# Raise ConfigurationError
raise ConfigurationError(
    f"Invalid UNIFI_CONTROLLER_TYPE: '{value}'. "
    f"Must be one of: auto, proxy, direct. "
    f"See https://github.com/sirkirby/unifi-network-mcp#configuration"
)
```

**Connection Error with Diagnostics**:

```python
# Raise ConnectionError with detection details
raise ConnectionError(
    f"Failed to connect to UniFi controller at {url}. "
    f"Detection attempted but both paths failed:\n"
    f"  - UniFi OS path: {proxy_error}\n"
    f"  - Standard path: {direct_error}\n"
    f"Try setting UNIFI_CONTROLLER_TYPE=proxy or UNIFI_CONTROLLER_TYPE=direct manually."
)
```

---

## 8. Testing Contract

### Unit Test Requirements

```python
# Must provide test fixtures for:
@pytest.fixture
async def mock_unifi_os_controller():
    """Mock controller that returns 200 for /proxy/network paths."""
    pass

@pytest.fixture
async def mock_standard_controller():
    """Mock controller that returns 200 for /api paths."""
    pass

@pytest.fixture
async def mock_offline_controller():
    """Mock controller that times out on all requests."""
    pass

# Must test these scenarios:
async def test_detects_unifi_os_successfully(): ...
async def test_detects_standard_controller_successfully(): ...
async def test_detection_failure_returns_none(): ...
async def test_manual_override_proxy(): ...
async def test_manual_override_direct(): ...
async def test_path_interception_applies_correctly(): ...
async def test_path_interception_restores_original(): ...
```

### Integration Test Requirements

```python
# Must test against real endpoints:
async def test_real_unifi_os_controller(): ...
async def test_real_standard_controller(): ...

# Must test error scenarios:
async def test_both_paths_fail_gracefully(): ...
async def test_timeout_handling(): ...
async def test_retry_logic_with_backoff(): ...
```

---

## 9. Compatibility Contract

### Backward Compatibility

**Guarantees**:
- ✅ If detection disabled, behaves identically to current implementation
- ✅ Existing tools require no modifications
- ✅ Default behavior (auto-detection) maintains compatibility
- ✅ Manual override allows forcing old behavior

**Breaking Changes**:
- ❌ None

### Forward Compatibility

**Preparation for**:
- Future aiounifi versions with native detection
- Future UniFi API path structures
- Future configuration options

**Extensibility Points**:
- Detection function accepts additional parameters
- Configuration supports new controller types
- Error handling supports new failure modes

---

## 10. Performance Contract

### Latency Guarantees

| Operation | Latency Target | Measured |
|-----------|---------------|----------|
| Successful detection | < 300ms | To be measured |
| Failed detection (timeout) | < timeout × retries | To be measured |
| Path interception overhead | < 0.01ms per request | To be measured |
| Manual override | 0ms (config load only) | Immediate |

### Resource Usage

| Resource | Limit |
|----------|-------|
| Memory | < 1 KB (detection result only) |
| Network | 2-4 HTTP requests (probes) |
| CPU | Negligible (< 1% during detection) |

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Status**: Design Complete
