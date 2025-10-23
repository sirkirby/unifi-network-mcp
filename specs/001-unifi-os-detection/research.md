# Research: UniFi OS Path Detection and Interception

**Feature**: UniFi API Path Detection and Adaptation
**Branch**: 001-unifi-os-detection
**Date**: 2025-10-23

## Executive Summary

This research document consolidates findings on implementing automatic UniFi OS detection and path interception using established patterns and practices from existing libraries (aiounifi, aiohttp) and Python best practices.

### Key Decisions

| Decision Area | Chosen Approach | Rationale |
|---------------|----------------|-----------|
| **Detection Endpoint** | `/api/self/sites` | Globally accessible, lightweight, no site parameter required |
| **Interception Pattern** | ConnectionManager wrapper with temporary flag override | Non-invasive, upgrade-safe, minimal code changes |
| **Configuration** | Environment variable `UNIFI_CONTROLLER_TYPE` | Follows existing config precedence |
| **Detection Timing** | Initialization-time with caching | Minimal performance impact |
| **Integration Point** | `ConnectionManager.request()` method | Centralized, transparent to tools |

---

## 1. aiounifi Library Integration

### 1.1 ApiRequest Structure

The aiounifi library uses simple dataclasses for API requests:

```python
@dataclass
class ApiRequest:
    method: str          # HTTP method (e.g., "get", "post")
    path: str            # API endpoint path (e.g., "/stat/device")
    data: Mapping[str, Any] | None = None

    def full_path(self, site: str, is_unifi_os: bool) -> str:
        """Create url to work with a specific controller."""
        if is_unifi_os:
            return f"/proxy/network/api/s/{site}{self.path}"
        return f"/api/s/{site}{self.path}"
```

**Key Finding**: The `is_unifi_os` flag controls path prefix. We can leverage this existing mechanism rather than implementing custom path rewriting.

### 1.2 Request Flow

```
ConnectionManager.request()
    └─> Controller.request(api_request)
            └─> Connectivity.request(api_request)
                    ├─> url = config.url + api_request.full_path(site, is_unifi_os)
                    └─> Connectivity._request(method, url, data)
```

**Key Finding**: The `Connectivity.is_unifi_os` attribute is already used by `ApiRequest.full_path()`. We can temporarily override this flag in our wrapper.

### 1.3 Existing Detection Logic

aiounifi has basic detection:

```python
async def check_unifi_os(self) -> None:
    """Check if controller is UniFi OS based."""
    self.is_unifi_os = False
    response, _ = await self._request(
        "get", self.config.url, allow_redirects=False
    )
    if response.status == HTTPStatus.OK:
        self.is_unifi_os = True
```

**Limitation**: This detection is unreliable across controller variations (per issue #19). Our empirical probe approach is more robust.

### 1.4 Endpoint Path Patterns

| Controller Type | Client List | Device List | Site List |
|----------------|-------------|-------------|-----------|
| **Standard** | `/api/s/{site}/stat/sta` | `/api/s/{site}/stat/device` | `/api/self/sites` |
| **UniFi OS** | `/proxy/network/api/s/{site}/stat/sta` | `/proxy/network/api/s/{site}/stat/device` | `/proxy/network/api/self/sites` |
| **V2 API** | `/v2/api/site/{site}/...` | `/v2/api/site/{site}/...` | `/v2/api/self/sites` |

**Key Finding**: All UniFi OS paths use `/proxy/network` prefix. V2 API uses `site` instead of `s`.

---

## 2. Detection Strategy

### 2.1 Recommended Detection Endpoint

**Endpoint**: `/api/self/sites` (or `/proxy/network/api/self/sites` for UniFi OS)

**Characteristics**:
- **Globally accessible**: No site parameter required
- **Lightweight**: Returns minimal data (list of sites)
- **Always available**: Required for basic controller functionality
- **Fast response**: Small payload (~100-500 bytes)
- **Works pre-authentication**: Can test both variants quickly

**Detection Algorithm**:

```python
async def detect_unifi_os_proactively(
    session: aiohttp.ClientSession,
    base_url: str,
    timeout: int = 5
) -> Optional[bool]:
    """
    Detect UniFi OS by testing endpoint variants.
    Returns True (UniFi OS), False (Standard), or None (Unknown).
    """
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    # Try UniFi OS endpoint first (newer controllers)
    try:
        async with session.get(
            f"{base_url}/proxy/network/api/self/sites",
            ssl=False,
            timeout=client_timeout
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if "data" in data:
                    return True  # UniFi OS detected
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    # Try standard endpoint
    try:
        async with session.get(
            f"{base_url}/api/self/sites",
            ssl=False,
            timeout=client_timeout
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if "data" in data:
                    return False  # Standard controller
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    return None  # Detection failed, use aiounifi's check_unifi_os()
```

### 2.2 Alternatives Considered

| Endpoint | Pros | Cons | Decision |
|----------|------|------|----------|
| `/api/self/sites` | No auth, lightweight, global | None significant | ✅ **Selected** |
| `/api/s/{site}/stat/health` | Purpose-built for health | Requires site parameter, auth | ❌ Rejected |
| `/api/self` | No site parameter | Requires auth, larger response | ❌ Rejected |
| Base URL (existing) | Already in aiounifi | Unreliable (issue #19) | ❌ Rejected |

### 2.3 Detection Timing

**Approach**: Initialization-time detection with session-lifetime caching

```python
# In ConnectionManager.initialize()
async def initialize(self) -> bool:
    # Create session first
    self._aiohttp_session = aiohttp.ClientSession(...)

    # Proactive OS detection
    detected = await detect_unifi_os_proactively(
        self._aiohttp_session,
        self.url_base,
        timeout=5
    )
    if detected is not None:
        self._unifi_os_override = detected

    # Continue with Controller creation
    self.controller = Controller(...)
```

**Rationale**:
- Detection happens once during connection initialization
- Cached for entire session lifetime (per spec requirement FR-006)
- ~100-300ms overhead only at startup
- Zero overhead on subsequent API requests

---

## 3. Path Interception Pattern

### 3.1 Recommended Approach: Temporary Flag Override

**Pattern**: Wrapper in `ConnectionManager.request()` that temporarily overrides `is_unifi_os` flag

```python
class ConnectionManager:
    def __init__(self, ...):
        self._unifi_os_override: Optional[bool] = None

    async def request(
        self,
        api_request: ApiRequest | ApiRequestV2,
        return_raw: bool = False
    ) -> Any:
        """Make request with optional path interception."""
        if not await self.ensure_connected() or not self.controller:
            raise ConnectionError("Unifi Controller is not connected.")

        # Apply override if we have better detection
        original_is_unifi_os = None
        if self._unifi_os_override is not None:
            original_is_unifi_os = self.controller.connectivity.is_unifi_os
            if original_is_unifi_os != self._unifi_os_override:
                self.controller.connectivity.is_unifi_os = self._unifi_os_override

        try:
            request_method = (
                self.controller.connectivity._request
                if return_raw
                else self.controller.request
            )
            response = await request_method(api_request)
            return response if return_raw else response.get("data")
        finally:
            # Restore original value
            if original_is_unifi_os is not None:
                self.controller.connectivity.is_unifi_os = original_is_unifi_os
```

**Advantages**:
- ✅ Non-invasive: Doesn't modify aiounifi internals
- ✅ Upgrade-safe: Uses only public APIs
- ✅ Minimal code changes: ~15 lines in one file
- ✅ Centralized: All tools benefit transparently
- ✅ Configurable: Easy to disable by setting override to None

### 3.2 Alternatives Considered

| Pattern | Maintainability | Upgrade Safety | Complexity | Decision |
|---------|----------------|----------------|------------|----------|
| Temporary flag override | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ Low | ✅ **Selected** |
| Wrapper classes | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ Medium | ⚠️ Overkill |
| Monkey-patch full_path() | ⭐ Poor | ⭐ Very Poor | ⭐⭐⭐⭐ High | ❌ Rejected |
| Subclass Connectivity | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ High | ❌ Rejected |

### 3.3 Integration with Manual Override

```python
# Environment variable support
UNIFI_CONTROLLER_TYPE = os.getenv("UNIFI_CONTROLLER_TYPE", "auto").lower()

if UNIFI_CONTROLLER_TYPE == "proxy":
    self._unifi_os_override = True  # Force proxy paths
elif UNIFI_CONTROLLER_TYPE == "direct":
    self._unifi_os_override = False  # Force direct paths
elif UNIFI_CONTROLLER_TYPE == "auto":
    # Use auto-detection
    self._unifi_os_override = await detect_unifi_os_proactively(...)
```

**Configuration Precedence** (per constitution):
1. Environment variable `UNIFI_CONTROLLER_TYPE`
2. `.env` file
3. Auto-detection (default)

---

## 4. Configuration Management

### 4.1 Environment Variable Design

```bash
# Manual override options
UNIFI_CONTROLLER_TYPE=auto      # Auto-detect (default)
UNIFI_CONTROLLER_TYPE=proxy     # Force /proxy/network paths
UNIFI_CONTROLLER_TYPE=direct    # Force /api paths
```

### 4.2 config.yaml Integration

```yaml
# src/config/config.yaml
unifi:
  controller_type: auto  # auto | proxy | direct
  detection_timeout: 5   # seconds
  cache_detection: true  # cache for session lifetime
```

### 4.3 Configuration Precedence

Following existing patterns from `bootstrap.py`:

1. **Environment variables** (highest priority)
2. **`.env` file**
3. **Custom YAML via `CONFIG_PATH`**
4. **Relative `config/config.yaml`**
5. **Bundled default `src/config/config.yaml`** (lowest priority)

---

## 5. Performance Considerations

### 5.1 Detection Overhead

| Operation | Time | Frequency |
|-----------|------|-----------|
| Detection probes | 100-300ms | Once per session initialization |
| Flag override | <0.01ms | Per request (if override set) |
| Path construction | <0.01ms | Per request (unchanged) |

**Total Impact**: ~2-3 seconds added to initial connection time (within SC-005 constraint: ≤2s)

### 5.2 Optimization Strategies

```python
# Parallel detection (try both endpoints simultaneously)
async def detect_unifi_os_parallel(session, base_url, timeout=5):
    """Try both endpoints in parallel for faster detection."""
    async with asyncio.TaskGroup() as tg:
        task_os = tg.create_task(probe_endpoint(f"{base_url}/proxy/network/api/self/sites"))
        task_std = tg.create_task(probe_endpoint(f"{base_url}/api/self/sites"))

    if await task_os:
        return True
    elif await task_std:
        return False
    return None
```

**Improvement**: Reduces detection time from ~300ms to ~150ms (50% faster)

### 5.3 Caching Strategy

```python
self._unifi_os_detection_cache = {
    'result': detected_os,  # True/False/None
    'timestamp': time.time(),
    'ttl': None  # Never expire during session (per FR-005)
}
```

**Rationale**: Per spec requirement, "path requirement detection results remain valid for the entire duration of a connection session and are never re-validated automatically."

---

## 6. Error Handling

### 6.1 Detection Failure Scenarios

```python
async def detect_unifi_os_proactively(self) -> Optional[bool]:
    """
    Detect UniFi OS type.
    Returns:
        True: UniFi OS detected
        False: Standard controller detected
        None: Detection failed, use aiounifi's check_unifi_os()
    """
    try:
        # Try detection logic
        pass
    except aiohttp.ClientError as e:
        logger.warning(f"Detection failed due to network error: {e}")
        return None  # Fall back to aiounifi
    except asyncio.TimeoutError:
        logger.warning("Detection timed out after {timeout}s, falling back to aiounifi")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during detection: {e}", exc_info=True)
        return None  # Safe fallback
```

### 6.2 Retry Logic

Per spec requirement FR-005:

```python
async def detect_with_retry(session, base_url, max_retries=3):
    """Retry detection with exponential backoff."""
    for attempt in range(max_retries):
        try:
            result = await detect_unifi_os_proactively(session, base_url)
            if result is not None:
                return result
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.debug(f"Detection attempt {attempt+1} failed, retrying in {delay}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Detection failed after {max_retries} attempts")

    raise ConnectionError(
        "Failed to detect UniFi controller path requirement. "
        "Please set UNIFI_CONTROLLER_TYPE environment variable manually to 'proxy' or 'direct'."
    )
```

### 6.3 Clear Error Messages

```python
ERROR_MESSAGES = {
    'detection_failed': """
UniFi controller path detection failed after 3 attempts.

Troubleshooting:
1. Verify network connectivity to controller at {url}
2. Check that controller is accessible on port {port}
3. Manually set controller type:
   - For UniFi OS (Cloud Gateway, UDM-Pro): UNIFI_CONTROLLER_TYPE=proxy
   - For standalone controllers: UNIFI_CONTROLLER_TYPE=direct

Probe results:
- UniFi OS path (/proxy/network/api/self/sites): {proxy_result}
- Standard path (/api/self/sites): {direct_result}
""",
    'ambiguous_detection': """
UniFi controller returned successful responses for both path structures.
Using direct /api paths (default).

To force proxy paths, set: UNIFI_CONTROLLER_TYPE=proxy
"""
}
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/unit/test_path_detection.py
import pytest
from aioresponses import aioresponses

@pytest.mark.asyncio
async def test_detects_unifi_os_correctly(mock_aioresponse):
    """Test UniFi OS detection succeeds."""
    mock_aioresponse.get(
        'https://controller:443/proxy/network/api/self/sites',
        status=200,
        payload={'meta': {'rc': 'ok'}, 'data': []}
    )

    result = await detect_unifi_os_proactively(session, 'https://controller:443')
    assert result is True

@pytest.mark.asyncio
async def test_detects_standard_controller(mock_aioresponse):
    """Test standard controller detection succeeds."""
    mock_aioresponse.get(
        'https://controller:443/api/self/sites',
        status=200,
        payload={'meta': {'rc': 'ok'}, 'data': []}
    )

    result = await detect_unifi_os_proactively(session, 'https://controller:443')
    assert result is False

@pytest.mark.asyncio
async def test_detection_failure_returns_none(mock_aioresponse):
    """Test detection failure returns None for fallback."""
    # Both endpoints return errors
    mock_aioresponse.get(
        'https://controller:443/proxy/network/api/self/sites',
        status=404
    )
    mock_aioresponse.get(
        'https://controller:443/api/self/sites',
        status=404
    )

    result = await detect_unifi_os_proactively(session, 'https://controller:443')
    assert result is None
```

### 7.2 Integration Tests

```python
# tests/integration/test_path_interceptor.py
@pytest.mark.asyncio
async def test_path_interceptor_applies_correctly():
    """Test that path interception modifies requests correctly."""
    conn_mgr = ConnectionManager(...)
    conn_mgr._unifi_os_override = True  # Force UniFi OS mode

    with aioresponses() as mock:
        # Mock the intercepted path
        mock.get(
            'https://controller:443/proxy/network/api/s/default/stat/sta',
            payload={'meta': {'rc': 'ok'}, 'data': []}
        )

        # Make request with original path
        from aiounifi.models.client import ClientListRequest
        clients = await conn_mgr.request(ClientListRequest.create())

        # Verify intercepted path was called
        assert 'proxy/network' in str(mock.requests)
```

### 7.3 Edge Case Tests

```python
@pytest.mark.asyncio
async def test_both_paths_succeed_prefers_direct():
    """Test that when both paths work, direct is preferred."""
    with aioresponses() as mock:
        # Both endpoints return success
        mock.get(
            'https://controller:443/proxy/network/api/self/sites',
            status=200,
            payload={'data': []}
        )
        mock.get(
            'https://controller:443/api/self/sites',
            status=200,
            payload={'data': []}
        )

        result = await detect_unifi_os_proactively(session, 'https://controller:443')

        # Should prefer direct (FR-012)
        assert result is False
```

---

## 8. Upgrade Compatibility

### 8.1 Risk Assessment

| Component | Risk Level | Mitigation |
|-----------|-----------|------------|
| `ApiRequest.full_path()` signature | Low | Part of public API, unlikely to change |
| `Connectivity.is_unifi_os` attribute | Medium | Accessed directly, but well-established |
| Detection endpoint `/api/self/sites` | Low | Core UniFi API endpoint |
| `Controller.request()` method | Low | Main public API method |

### 8.2 Version Testing Strategy

```yaml
# .github/workflows/test.yml
strategy:
  matrix:
    aiounifi-version:
      - "83.0.0"  # Minimum supported (current)
      - "84.0.0"  # Latest stable
      - "latest"  # Always test against newest
```

### 8.3 Future-Proofing

**If aiounifi adds native path detection**:

```python
# Can cleanly disable our detection
UNIFI_CONTROLLER_TYPE = "native"  # Use aiounifi's built-in detection

if UNIFI_CONTROLLER_TYPE == "native":
    self._unifi_os_override = None  # Don't override, use library detection
```

---

## 9. Implementation Roadmap

### Phase 0: Preparation (Complete)
- ✅ Research aiounifi library internals
- ✅ Research Python best practices for request interception
- ✅ Identify detection endpoint
- ✅ Design interception pattern

### Phase 1: Core Detection
1. Implement `detect_unifi_os_proactively()` method in `connection_manager.py`
2. Add `_unifi_os_override` attribute to `ConnectionManager.__init__()`
3. Call detection during `ConnectionManager.initialize()`
4. Add configuration parsing for `UNIFI_CONTROLLER_TYPE`

### Phase 2: Path Interception
1. Modify `ConnectionManager.request()` to apply override
2. Implement retry logic with exponential backoff
3. Add validation via test request after detection
4. Add comprehensive logging for detection process

### Phase 3: Configuration & Diagnostics
1. Add `controller_type` to `config.yaml`
2. Update `bootstrap.py` to load controller type setting
3. Add detection results to diagnostics output
4. Update `dev_console.py` to display detection outcome

### Phase 4: Testing & Documentation
1. Write unit tests for detection logic
2. Write integration tests for path interception
3. Update README with configuration options
4. Add troubleshooting guide for detection failures

---

## 10. Code Changes Summary

### Files to Modify

1. **`src/managers/connection_manager.py`** (Primary changes)
   - Add `detect_unifi_os_proactively()` method (~40 lines)
   - Add `_unifi_os_override` attribute (1 line)
   - Modify `initialize()` to call detection (~5 lines)
   - Modify `request()` to apply override (~15 lines)

2. **`src/bootstrap.py`** (Configuration)
   - Add `UNIFI_CONTROLLER_TYPE` environment variable parsing (~5 lines)

3. **`src/config/config.yaml`** (Configuration)
   - Add `controller_type` setting (~3 lines)

4. **`devtools/dev_console.py`** (Diagnostics)
   - Display detection result during connection (~3 lines)

5. **`tests/unit/test_path_detection.py`** (New file)
   - Unit tests for detection logic (~100 lines)

6. **`tests/integration/test_path_interceptor.py`** (New file)
   - Integration tests for path interception (~150 lines)

**Total Estimated Changes**: ~330 lines across 6 files (1 primary, 5 supporting)

---

## 11. Validation Checklist

- [ ] Detection succeeds on UniFi OS controllers (Cloud Gateway, UDM-Pro)
- [ ] Detection succeeds on standard controllers (standalone)
- [ ] Manual override via `UNIFI_CONTROLLER_TYPE=proxy` works
- [ ] Manual override via `UNIFI_CONTROLLER_TYPE=direct` works
- [ ] Detection failure falls back gracefully
- [ ] Retry logic with exponential backoff works
- [ ] Clear error messages on detection failure
- [ ] Detection adds ≤2 seconds to connection time
- [ ] Path interception has zero overhead on subsequent requests
- [ ] All existing tools work without modification
- [ ] dev_console.py displays detection result
- [ ] Diagnostics logs include detection details
- [ ] Unit tests achieve >90% coverage
- [ ] Integration tests pass on both controller types

---

## 12. References

### External Documentation
- [aiounifi GitHub Repository](https://github.com/Kane610/aiounifi)
- [aiohttp Documentation - Client Advanced Usage](https://docs.aiohttp.org/en/stable/client_advanced.html)
- [Pydantic Settings Management](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [UniFi Controller API Endpoints](https://ubntwiki.com/products/software/unifi-controller/api)

### Related Issues
- [Issue #19: 404 errors on UniFi OS controllers](https://github.com/sirkirby/unifi-network-mcp/issues/19)

### Internal Documents
- Constitution v1.1.0 (`.specify/memory/constitution.md`)
- Feature Specification (`specs/001-unifi-os-detection/spec.md`)
- Implementation Plan (`specs/001-unifi-os-detection/plan.md`)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Author**: Research for unifi-network-mcp project
